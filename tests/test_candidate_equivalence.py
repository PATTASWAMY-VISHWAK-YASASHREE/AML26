"""Prove the per-channel candidate rewrite is exactly equivalent to the old
single-query UNION ALL version.

The rewrite caps each channel independently before merging. That is only valid
if the cap is exact: the final answer is the top `max_candidates` per S1 ordered
by (priority, tid). This checks that on adversarial synthetic data - including
heavy collisions on a single exact key, where a common name matches thousands of
targets - against a reference implementation that does no early capping.
"""
from __future__ import annotations

import random
import sys
import tempfile
from pathlib import Path

import er_pipeline as P

HDR = "entity_id\tbusiness_name\tbusiness_address\tcountry\n"


def build(ds: Path, seed: int = 3) -> None:
    rng = random.Random(seed)
    rows = {1: [], 2: [], 3: []}
    # Deliberate mass collision: many S1 rows share the exact name "cafe", so the
    # exact-name channel alone produces a huge number of pairs at full scale.
    names = ["cafe"] * 60 + [f"shop {i}" for i in range(40)]
    for i in range(100):
        rows[1].append((f"S1-{i:04d}", rng.choice(names), f"{rng.randint(1, 9)} main st"))
    for src in (2, 3):
        for i in range(300):
            rows[src].append((f"S{src}-{i:04d}", rng.choice(names),
                              f"{rng.randint(1, 9)} main st"))
    for split in ("train", "test"):
        (ds / split).mkdir(parents=True, exist_ok=True)
        for src in (1, 2, 3):
            (ds / split / f"{split}_source{src}.tsv").write_text(
                HDR + "".join(f"{a}\t{b}\t{c}\tUS\n" for a, b, c in rows[src]),
                encoding="utf-8")
    (ds / "train" / "train_ground_truth.tsv").write_text(
        "source1_entity_id\tmatched_entity_ids\nS1-0000\t\n", encoding="utf-8")


def reference(con, norm: Path, split: str, cap: int) -> set:
    """Single-query version: all channels unioned, no per-channel early cap."""
    parts = [
        f"""SELECT {prio} AS prio, s.entity_id AS sid, t.entity_id AS tid
            FROM (SELECT entity_id, country, {key} AS k
                  FROM read_parquet({P.lit(norm / f'{split}_s1.parquet')})) s
            JOIN (SELECT entity_id, country, {key} AS k
                  FROM read_parquet({P.lit(norm / f'{split}_s2.parquet')})
                  UNION ALL
                  SELECT entity_id, country, {key} AS k
                  FROM read_parquet({P.lit(norm / f'{split}_s3.parquet')})) t
              ON s.country = t.country AND s.k = t.k
            WHERE s.k IS NOT NULL"""
        for prio, key in P.EXACT_CHANNELS
    ]
    for prio, kind, tok_col in P.TOKEN_CHANNELS:
        parts.append(
            f"""SELECT {prio} AS prio, p.sid, q.entity_id AS tid
            FROM (SELECT entity_id AS sid, country, unnest({tok_col}) AS token
                  FROM read_parquet({P.lit(norm / f'{split}_s1.parquet')})
                  WHERE {tok_col} IS NOT NULL AND list_count({tok_col}) > 0) p
            JOIN read_parquet({P.lit(norm / f'{split}_tgt_tok.parquet')}) q
              ON q.kind = {P.lit(kind)} AND q.token = p.token AND q.country = p.country
            WHERE length(p.token) >= {P.CFG['min_token_len']}""")
    rows = con.execute(
        f"""WITH raw AS ({(chr(10) + ' UNION ALL ' + chr(10)).join(parts)}),
            dedup AS (SELECT sid, tid, min(prio) AS prio FROM raw GROUP BY 1, 2),
            ranked AS (SELECT sid, tid, prio,
                              row_number() OVER (PARTITION BY sid ORDER BY prio, tid) AS rn
                       FROM dedup)
            SELECT sid, tid FROM ranked WHERE rn <= {cap}""").fetchall()
    return set(rows)


def main() -> int:
    base = Path(tempfile.mkdtemp(prefix="cand_equiv_"))
    ds = base / "dataset"
    build(ds)
    work = base / "w"
    norm = work / "er_work" / "norm"
    norm.mkdir(parents=True, exist_ok=True)
    (work / "er_work" / "tmp").mkdir(parents=True, exist_ok=True)
    con = P.connect(work / "er_work" / "er.duckdb", work / "er_work" / "tmp")
    try:
        paths = P.find_dataset_files(ds)
        fp = P.source_fingerprint(paths)
        P.stage_normalize(con, paths, norm, fp)
        P.stage_tokens(con, norm, fp)
        for cap in (5, 30, 1000):
            P.CFG["max_candidates"] = cap
            for split in ("train", "test"):
                out = norm / f"{split}_cand.parquet"
                out.unlink(missing_ok=True)
                out.with_name(out.name + ".meta.json").unlink(missing_ok=True)
                for stale in norm.glob(f"{split}_cand_*_ch*.parquet"):
                    stale.unlink()
                P.stage_candidates(con, norm, split, out, fp)
                got = set(con.execute(
                    f"SELECT sid, tid FROM read_parquet({P.lit(out)})").fetchall())
                want = reference(con, norm, split, cap)
                assert got == want, (
                    f"cap={cap} {split}: rewrite differs - "
                    f"missing {sorted(want - got)[:5]}, extra {sorted(got - want)[:5]}")
                print(f"  PASS cap={cap:<5} {split}: {len(got)} pairs identical "
                      f"to the uncapped reference")
        leftovers = sorted(p.name for p in norm.glob("*_cand_*_ch*.parquet"))
        assert not leftovers, f"intermediate channel files not cleaned: {leftovers}"
        print("  PASS intermediate channel files cleaned up")
    finally:
        con.close()
    print("\nper-channel cap is EXACTLY equivalent to the single-query version")
    return 0


if __name__ == "__main__":
    sys.exit(main())
