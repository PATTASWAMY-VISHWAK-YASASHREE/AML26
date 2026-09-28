# SECTION 3 - install the pipeline module
# -----------------------------------------------------------------------------
PIPELINE = r'''
"""
Amazon ML Challenge 2026 - Business Entity Resolution pipeline (DuckDB, out-of-core).

Runs unchanged in Google Colab on a ~1 GB dataset zip. Everything except the
final (small) linear model fit happens inside DuckDB, so peak RAM is bounded by
`memory_limit` rather than by the 23M-row dataset.

Stages
  1. locate + extract zip (skips macOS __MACOSX / ._* AppleDouble junk)
  2. normalize TSV -> ZSTD parquet shards (ids, country, keys, token lists)
  3. rare-token document-frequency posting tables
  4. candidate generation (selective multi-channel blocking, capped per S1)
  5. pair features computed entirely in SQL (no Python round trip)
  6. fit linear scorer, tune threshold against entity-level macro F_0.5
  7. apply the scorer inside SQL, write contract-compliant outputs
  8. validate against the official submission rules, emit submission.zip
"""
from __future__ import annotations

import csv
import hashlib
import json
import os
import shutil
import sys
import time
import zipfile
from pathlib import Path

import duckdb
import numpy as np

CFG = {
    "threads": max(1, min(8, os.cpu_count() or 2)),
    "memory_limit": "6GB",
    "temp_directory_size": "40GB",  # spill budget; must be set or DuckDB won't spill
    "max_token_df": 5000,        # token must be this rare in the target corpus
    "min_token_len": 4,
    # The brief ranks a SMALLER candidate set per Source-1 entity HIGHER, beyond
    # the leaderboard score, so this is a ranking lever and not only a recall
    # knob. Measured on 22,691 real train S1 entities against the full corpus
    # with all 7 channels: cap 5 -> 4.89 cands/S1 at 0.4108 gold recall,
    # cap 8 -> 7.74 at 0.4502, cap 10 -> 9.63 at 0.4652, cap 20 -> 18.96 at
    # 0.5081. Ten roughly halves the candidate set for ~8% of the recall
    # ceiling, which is the right trade under the published ranking rule.
    "max_candidates": 10,        # per Source-1 entity after priority ranking
    "train_sample_pct": 2,       # percent of train candidate rows used for fitting
    "candidate_sample_rows": 800000,
}

# Legal-entity noise dropped from the "core" name key. Rendered as a quoted SQL
# value list so it can be spliced into a NOT IN (...) predicate.
LEGAL = ", ".join(f"'{s}'" for s in (
    "llc", "inc", "incorporated", "ltd", "limited", "pvt", "private",
    "company", "co", "corp", "corporation", "the", "of", "and",
))


def log(msg: str) -> None:
    print(f"[*] {msg}", flush=True)


def lit(value) -> str:
    """Quote a value as a DuckDB SQL string literal (defends against injection)."""
    return "'" + str(value).replace("'", "''") + "'"


def _fingerprint(*parts) -> str:
    return hashlib.sha256(
        json.dumps(parts, sort_keys=True, default=str).encode("utf-8")).hexdigest()[:16]


def source_fingerprint(paths: dict) -> str:
    """Identify the dataset revision the parquet shards were built from.

    Size only, deliberately: this tree syncs through OneDrive, which can touch
    mtimes without changing content, and a spurious invalidation would throw
    away hours of DuckDB work.
    """
    return _fingerprint(*(f"{p.name}:{p.stat().st_size}" for p in sorted(paths.values())))


def cached(out_path: Path, fingerprint: str) -> bool:
    """True only if `out_path` exists AND was built with this exact fingerprint.

    Stage caching on `out.exists()` alone means editing `max_candidates`,
    `max_token_df` or `min_token_len` silently reuses the previous run's
    parquet, so the reported blocking recall, threshold and coefficients end up
    describing a stale mixture of configurations.
    """
    meta = out_path.with_name(out_path.name + ".meta.json")
    if not out_path.exists() or not meta.exists():
        return False
    try:
        return json.loads(meta.read_text(encoding="utf-8")).get("fingerprint") == fingerprint
    except (OSError, ValueError):
        return False


def mark_cached(out_path: Path, fingerprint: str) -> None:
    out_path.with_name(out_path.name + ".meta.json").write_text(
        json.dumps({"fingerprint": fingerprint}, indent=2), encoding="utf-8")


def find_dataset_files(root: Path) -> dict:
    """Return the real TSV files, ignoring macOS AppleDouble sidecars."""
    wanted = {
        "train_s1": "train_source1.tsv", "train_s2": "train_source2.tsv",
        "train_s3": "train_source3.tsv", "train_gt": "train_ground_truth.tsv",
        "test_s1": "test_source1.tsv", "test_s2": "test_source2.tsv",
        "test_s3": "test_source3.tsv",
    }
    found: dict[str, Path] = {}
    for path in root.rglob("*.tsv"):
        if path.name.startswith("._") or "__MACOSX" in path.parts:
            continue  # macOS resource fork, not data
        for key, target in wanted.items():
            if path.name == target and key not in found:
                found[key] = path
    missing = sorted(k for k in wanted if k not in found)
    if missing:
        raise FileNotFoundError(
            f"Missing {missing} under {root}. The archive must contain "
            "dataset/train/*.tsv and dataset/test/*.tsv."
        )
    return found


def mount_drive() -> Path:
    """Mount Google Drive in Colab and return the mount point."""
    from google.colab import drive

    drive.mount("/content/drive", force_remount=True)
    return Path("/content/drive")


def find_source_zip(search_dir: Path) -> Path:
    """Locate the dataset zip in a directory (top level or one level of nesting)."""
    candidates = [p for p in search_dir.rglob("*.zip")
                  if "submission" not in p.name.lower()]
    if not candidates:
        raise FileNotFoundError(f"No .zip dataset archive found under {search_dir}")
    return max(candidates, key=lambda p: p.stat().st_size)


def extract_zip(zip_path: Path, extract_dir: Path) -> None:
    """Unpack the dataset archive to fast local scratch storage."""
    extract_dir.mkdir(parents=True, exist_ok=True)
    log(f"extracting {zip_path.name} ({zip_path.stat().st_size / 2**20:.0f} MB) -> {extract_dir}")
    with zipfile.ZipFile(zip_path) as zf:
        zf.extractall(extract_dir)


def connect(db_path: Path, tmp_dir: Path) -> duckdb.DuckDBPyConnection:
    """Open the working database with settings tuned for a 12 GB Colab VM.

    Colab's standard runtime is ~12.7 GB of RAM across 2 vCPUs, so the default
    DuckDB budget (80% of RAM) is too generous: the OS, the Python process and
    the parquet writer all need headroom too, and an over-large limit lets a
    single operator grow until the kernel is OOM-killed instead of spilling.

    The important part is `max_temp_directory_size`. Without it DuckDB refuses
    to spill and an operator that will not fit in the buffer pool raises
    OutOfMemoryError rather than writing to disk - which is exactly the failure
    this pipeline originally hit in the candidate-generation stage.
    """
    tmp_dir.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(db_path))
    con.execute(f"SET threads={CFG['threads']}")
    con.execute(f"SET memory_limit={lit(CFG['memory_limit'])}")
    con.execute(f"SET temp_directory={lit(tmp_dir)}")
    con.execute(f"SET max_temp_directory_size={lit(CFG.get('temp_directory_size', '40GB'))}")
    con.execute("SET preserve_insertion_order=false")
    con.execute("SET enable_progress_bar=false")
    return con


def _norm_expr(column: str) -> str:
    """Deterministic lowercase-alphanumeric key; empty string becomes NULL."""
    return (
        "nullif(nullif(lower(trim(regexp_replace(regexp_replace("
        f"coalesce({column}, ''), '[^a-zA-Z0-9]+', ' ', 'g'), '\\s+', ' ', 'g'))), ''), 'nan')"
    )


def _core_tokens(column: str) -> str:
    """Token list with legal-suffix / stopword noise removed."""
    return (
        "list_filter(string_split(coalesce(" + column + ", ''), ' '), "
        f"x -> length(x) >= 2 AND lower(x) NOT IN ({LEGAL}))"
    )


def stage_normalize(con, paths: dict, norm_dir: Path, src_fp: str) -> None:
    """TSV -> parquet carrying ids, country, blocking keys and token lists."""
    norm_dir.mkdir(parents=True, exist_ok=True)
    cols = ("{'entity_id':'VARCHAR','business_name':'VARCHAR',"
            "'business_address':'VARCHAR','country':'VARCHAR'}")
    fp = _fingerprint("normalize", src_fp, CFG["min_token_len"])
    for split in ("train", "test"):
        for source in (1, 2, 3):
            out = norm_dir / f"{split}_s{source}.parquet"
            if cached(out, fp):
                continue
            t0 = time.perf_counter()
            con.execute(
                f"""
                COPY (
                  SELECT
                    entity_id,
                    {_norm_expr('business_name')}  AS n_name,
                    {_norm_expr('business_address')} AS n_addr,
                    nullif(nullif(trim(coalesce(country, '')), ''), 'nan') AS country,
                    nullif(array_to_string(list_sort(string_split(n_name, ' ')), ' '), '') AS n_sorted,
                    nullif(array_to_string(list_sort({_core_tokens('n_name')}), ' '), '') AS n_core_sorted,
                    nullif(array_to_string(list_sort(string_split(n_addr, ' ')), ' '), '') AS a_sorted,
                    {_core_tokens('n_name')} AS name_tokens,
                    list_filter(string_split(coalesce(n_addr, ''), ' '),
                                x -> length(x) >= {CFG['min_token_len']}) AS addr_tokens,
                    list_filter(regexp_extract_all(coalesce(n_name, ''), '[0-9]{{2,}}'),
                                x -> length(x) >= 2) AS name_nums,
                    list_filter(regexp_extract_all(coalesce(n_addr, ''), '[0-9]{{2,}}'),
                                x -> length(x) >= 2) AS addr_nums
                  FROM read_csv({lit(paths[f'{split}_s{source}'])}, delim='\\t',
                                header=true, columns={cols}, ignore_errors=false)
                ) TO {lit(out)} (FORMAT PARQUET, COMPRESSION ZSTD, ROW_GROUP_SIZE 100000)
                """
            )
            rows = con.execute(f"SELECT count(*) FROM read_parquet({lit(out)})").fetchone()[0]
            mark_cached(out, fp)
            log(f"normalized {out.name}: {rows:,} rows in {time.perf_counter() - t0:.1f}s")


def stage_tokens(con, norm_dir: Path, src_fp: str) -> None:
    """Posting list of *rare* target tokens, joined on (kind, token, country)."""
    for split in ("train", "test"):
        out = norm_dir / f"{split}_tgt_tok.parquet"
        fp = _fingerprint("tokens", src_fp, CFG["max_token_df"], CFG["min_token_len"], split)
        if cached(out, fp):
            continue
        t0 = time.perf_counter()
        s2 = lit(norm_dir / f"{split}_s2.parquet")
        s3 = lit(norm_dir / f"{split}_s3.parquet")
        con.execute(
            f"""
            CREATE OR REPLACE TEMP VIEW tgt AS
            SELECT entity_id, country, unnest(name_tokens) AS token, 'name' AS kind FROM read_parquet({s2})
            UNION ALL
            SELECT entity_id, country, unnest(name_tokens), 'name' FROM read_parquet({s3})
            UNION ALL
            SELECT entity_id, country, unnest(addr_tokens), 'addr' FROM read_parquet({s2})
            UNION ALL
            SELECT entity_id, country, unnest(addr_tokens), 'addr' FROM read_parquet({s3})
            """
        )
        df_out = norm_dir / f"{split}_tok_df.parquet"
        con.execute(
            f"""
            COPY (
              SELECT kind, token, count(DISTINCT entity_id) AS df
              FROM tgt
              WHERE token IS NOT NULL AND length(token) >= {CFG['min_token_len']}
              GROUP BY 1, 2
            ) TO {lit(df_out)} (FORMAT PARQUET, COMPRESSION ZSTD)
            """
        )
        con.execute(
            f"""
            COPY (
              SELECT t.kind, t.token, t.entity_id, t.country
              FROM tgt t
              JOIN read_parquet({lit(df_out)}) d ON d.kind = t.kind AND d.token = t.token
              WHERE t.token IS NOT NULL AND length(t.token) >= {CFG['min_token_len']}
                AND d.df <= {CFG['max_token_df']}
            ) TO {lit(out)} (FORMAT PARQUET, COMPRESSION ZSTD)
            """
        )
        n = con.execute(f"SELECT count(*) FROM read_parquet({lit(out)})").fetchone()[0]
        df_n = con.execute(f"SELECT count(*) FROM read_parquet({lit(df_out)})").fetchone()[0]
        mark_cached(out, fp)
        log(f"rare-token postings {split}: {n:,} rows over {df_n:,} distinct keys "
            f"in {time.perf_counter() - t0:.1f}s")


def stage_ground_truth(con, paths: dict, gt_path: Path, src_fp: str) -> None:
    """Explode matched_entity_ids into one row per positive (source1, target) link."""
    if cached(gt_path, _fingerprint("gt", src_fp)):
        return
    con.execute(
        f"""
        COPY (
          SELECT trim(source1_entity_id) AS sid, trim(t) AS tid
          FROM read_csv({lit(paths['train_gt'])}, delim='\\t', header=true,
                        columns={{'source1_entity_id':'VARCHAR','matched_entity_ids':'VARCHAR'}}),
               UNNEST(string_split(coalesce(matched_entity_ids, ''), ',')) AS u(t)
          WHERE trim(t) <> '' AND trim(t) IS NOT NULL
        ) TO {lit(gt_path)} (FORMAT PARQUET, COMPRESSION ZSTD)
        """
    )
    n = con.execute(f"SELECT count(*) FROM read_parquet({lit(gt_path)})").fetchone()[0]
    mark_cached(gt_path, _fingerprint("gt", src_fp))
    log(f"ground-truth positive links: {n:,}")


# Blocking channels, cheapest/most selective first. Lower priority number wins
# when several channels produce the same pair.
#
# EXACT_CHANNELS are equi-joins on a single derived key. Each is run as its own
# query projecting only (entity_id, country, key) - never the token lists, which
# would multiply the working set by the size of the corpus.
#
# TOKEN_CHANNELS join the exploded Source-1 token stream against the rare-token
# posting table built by stage_tokens.
EXACT_CHANNELS = [
    (1, "n_name"),        # exact normalised name
    (2, "n_sorted"),      # name with tokens sorted (word-order invariant)
    (3, "n_core_sorted"),  # same, minus legal suffixes / stopwords
    (4, "n_addr"),        # exact normalised address
    (5, "a_sorted"),      # address with components sorted
]

TOKEN_CHANNELS = [
    (6, "name", "name_tokens"),
    (7, "addr", "addr_tokens"),
]

CHANNEL_LABELS = {
    1: "exact name", 2: "name sorted", 3: "name core-sorted",
    4: "exact address", 5: "address sorted",
    6: "rare name token", 7: "rare addr token",
}


def stage_candidates(con, norm_dir: Path, split: str, out_path: Path, src_fp: str) -> None:
    """Selective multi-channel blocking -> deduplicated, priority ranked, capped.

    Memory safety is the whole point of the shape here. Unioning all channels
    into one query makes DuckDB hold every channel's join output at once, and
    each join must project only the columns that channel actually uses -
    `SELECT *` would drag the token-list columns through all 10M target rows.

    So each channel is a separate COPY that streams to its own parquet file,
    then the small capped files are merged. The per-channel cap is exact, not
    an approximation: the final set is the top `max_candidates` of each S1
    ordered by (priority, tid), and priority is constant within a channel, so
    any row of channel p that survives the final cap is necessarily within
    channel p's own top `max_candidates` by tid.
    """
    fp = _fingerprint("candidates", src_fp, CFG["max_candidates"],
                      CFG["max_token_df"], CFG["min_token_len"], split)
    if cached(out_path, fp):
        return
    t0 = time.perf_counter()
    cap = CFG["max_candidates"]
    min_len = CFG["min_token_len"]
    # The per-channel files MUST be fingerprinted too, not just gated on
    # existence. An aborted run leaves partial channel files behind, and the
    # token channels depend on max_token_df - so a rerun with a different
    # max_token_df would silently reuse candidates built from the old posting
    # table, producing a mixture of two configurations.
    tag = fp[:10]
    s1p = norm_dir / f"{split}_s1.parquet"
    s2p = norm_dir / f"{split}_s2.parquet"
    s3p = norm_dir / f"{split}_s3.parquet"
    tokp = norm_dir / f"{split}_tgt_tok.parquet"
    files: list[tuple[int, Path]] = []

    # --- exact-match channels: narrow equi-joins on one key at a time --------
    for prio, key in EXACT_CHANNELS:
        dst = out_path.parent / f"{split}_cand_{tag}_ch{prio}.parquet"
        if not dst.exists():
            con.execute(
                f"""
                COPY (
                  WITH pairs AS (
                    SELECT s.entity_id AS sid, t.entity_id AS tid
                    FROM (SELECT entity_id, country, {key} AS k
                          FROM read_parquet({lit(s1p)})) s
                    JOIN (
                      SELECT entity_id, country, {key} AS k FROM read_parquet({lit(s2p)})
                      UNION ALL
                      SELECT entity_id, country, {key} AS k FROM read_parquet({lit(s3p)})
                    ) t ON s.country = t.country AND s.k = t.k
                    WHERE s.k IS NOT NULL
                  ),
                  ranked AS (
                    SELECT sid, tid, row_number() OVER (PARTITION BY sid ORDER BY tid) AS rn
                    FROM pairs
                  )
                  SELECT sid, tid FROM ranked WHERE rn <= {cap}
                ) TO {lit(dst)} (FORMAT PARQUET, COMPRESSION ZSTD)
                """
            )
        files.append((prio, dst))

    # --- rare-token channels: posting-list join against the exploded S1 side -
    for prio, kind, tok_col in TOKEN_CHANNELS:
        dst = out_path.parent / f"{split}_cand_{tag}_ch{prio}.parquet"
        if not dst.exists():
            con.execute(
                f"""
                COPY (
                  WITH s_tok AS (
                    SELECT entity_id AS sid, country, unnest({tok_col}) AS token
                    FROM read_parquet({lit(s1p)})
                    WHERE {tok_col} IS NOT NULL AND list_count({tok_col}) > 0
                  ),
                  pairs AS (
                    SELECT p.sid, q.entity_id AS tid
                    FROM s_tok p
                    JOIN read_parquet({lit(tokp)}) q
                      ON q.kind = {lit(kind)} AND q.token = p.token AND q.country = p.country
                    WHERE length(p.token) >= {min_len}
                  ),
                  ranked AS (
                    SELECT sid, tid, row_number() OVER (PARTITION BY sid ORDER BY tid) AS rn
                    FROM pairs
                  )
                  SELECT sid, tid FROM ranked WHERE rn <= {cap}
                ) TO {lit(dst)} (FORMAT PARQUET, COMPRESSION ZSTD)
                """
            )
        files.append((prio, dst))

    union = " UNION ALL ".join(
        f"SELECT {p} AS prio, sid, tid FROM read_parquet({lit(f)})" for p, f in files)
    con.execute(
        f"""
        COPY (
          WITH raw AS ({union}),
          dedup AS (SELECT sid, tid, min(prio) AS prio FROM raw GROUP BY 1, 2),
          ranked AS (
            SELECT sid, tid, prio,
                   row_number() OVER (PARTITION BY sid ORDER BY prio, tid) AS rn
            FROM dedup
          )
          SELECT sid, tid, prio FROM ranked WHERE rn <= {cap}
        ) TO {lit(out_path)} (FORMAT PARQUET, COMPRESSION ZSTD)
        """
    )
    # Per-channel accounting. The token channels are the LAST priority, so a
    # token candidate only survives when the five exact channels produced fewer
    # than `cap` pairs for that S1 - that ratio is what tells you whether
    # tightening max_token_df (the biggest memory lever) is cheap or costly.
    kept = dict(con.execute(
        f"SELECT prio, count(*) FROM read_parquet({lit(out_path)}) GROUP BY 1"
    ).fetchall())
    for prio, path in files:
        raw_n = con.execute(
            f"SELECT count(*) FROM read_parquet({lit(path)})").fetchone()[0]
        n = int(kept.get(prio, 0))
        log(f"  {split} ch{prio} {CHANNEL_LABELS.get(prio, '?'):<16} "
            f"{raw_n:>12,} pairs -> {n:>12,} kept "
            f"({n / max(1, raw_n):6.1%} survives)")
    # Drop channel files from any other fingerprint. They can be tens of GB
    # across a failed run, and reusing them would silently mix configurations.
    for stale in out_path.parent.glob(f"{split}_cand_*_ch*.parquet"):
        if stale.name not in {p.name for _, p in files}:
            try:
                stale.unlink()
                log(f"  removed stale {stale.name}")
            except OSError:
                pass
    for _, f in files:
        f.unlink(missing_ok=True)
    row = con.execute(
        f"""
        SELECT coalesce(sum(n), 0), count(*),
               coalesce(approx_quantile(n, 0.5), 0), coalesce(approx_quantile(n, 0.9), 0)
        FROM (SELECT sid, count(*) AS n FROM read_parquet({lit(out_path)}) GROUP BY sid)
        """
    ).fetchone()
    mark_cached(out_path, fp)
    log(f"{split} candidates: {row[0]:,} pairs over {row[1]:,} S1 "
        f"(p50={float(row[2]):.0f}, p90={float(row[3]):.0f}) in {time.perf_counter() - t0:.1f}s")

FEATURES = [
    "name_jw", "addr_jw", "name_dl", "addr_dl",
    "name_exact", "addr_exact", "name_sorted_exact", "name_core_exact",
    "name_p2", "name_p4", "name_p6", "addr_p5", "addr_p8",
    "name_tok_overlap", "name_tok_jaccard", "addr_tok_overlap",
    "name_len_ratio", "addr_len_ratio", "country_eq",
    "name_digits_eq", "addr_digits_eq",
]
# Columns pulled from the S1 / target shards by the feature join.
KEY_COLS = ("n_name, n_addr, n_sorted, n_core_sorted, a_sorted, name_tokens, addr_tokens, "
            "country, name_nums, addr_nums")


def stage_features(con, norm_dir: Path, split: str, cand_path: Path, out_path: Path,
                   src_fp: str) -> None:
    """Compute every pair feature in SQL - no Python round trip over candidate rows."""
    fp = _fingerprint("features", src_fp, FEATURES, KEY_COLS, split)
    if cached(out_path, fp):
        return
    t0 = time.perf_counter()
    con.execute(
        f"""
        COPY (
          WITH c AS (SELECT * FROM read_parquet({lit(cand_path)})),
          s AS (SELECT entity_id, {KEY_COLS} FROM read_parquet({lit(norm_dir / f'{split}_s1.parquet')})),
          t AS (
            SELECT entity_id, {KEY_COLS} FROM read_parquet({lit(norm_dir / f'{split}_s2.parquet')})
            UNION ALL BY NAME
            SELECT entity_id, {KEY_COLS} FROM read_parquet({lit(norm_dir / f'{split}_s3.parquet')})
          )
          SELECT
            c.sid,
            c.tid,
            c.prio,
            CASE WHEN s.n_name IS NOT NULL AND t.n_name IS NOT NULL
                 THEN jaro_winkler_similarity(s.n_name, t.n_name) ELSE 0.0 END AS name_jw,
            CASE WHEN s.n_addr IS NOT NULL AND t.n_addr IS NOT NULL
                 THEN jaro_winkler_similarity(s.n_addr, t.n_addr) ELSE 0.0 END AS addr_jw,
            CASE WHEN s.n_name IS NOT NULL AND t.n_name IS NOT NULL
                 THEN 1.0 - least(1.0, damerau_levenshtein(s.n_name, t.n_name)::DOUBLE
                                        / greatest(length(s.n_name), length(t.n_name)))
                 ELSE 0.0 END AS name_dl,
            CASE WHEN s.n_addr IS NOT NULL AND t.n_addr IS NOT NULL
                 THEN 1.0 - least(1.0, damerau_levenshtein(s.n_addr, t.n_addr)::DOUBLE
                                        / greatest(length(s.n_addr), length(t.n_addr)))
                 ELSE 0.0 END AS addr_dl,
            (s.n_name IS NOT NULL AND s.n_name = t.n_name)::INT AS name_exact,
            (s.n_addr IS NOT NULL AND s.n_addr = t.n_addr)::INT AS addr_exact,
            (s.n_sorted IS NOT NULL AND s.n_sorted = t.n_sorted)::INT AS name_sorted_exact,
            (s.n_core_sorted IS NOT NULL AND s.n_core_sorted = t.n_core_sorted)::INT AS name_core_exact,
            (s.n_name IS NOT NULL AND t.n_name IS NOT NULL
             AND left(s.n_name,2) = left(t.n_name,2))::INT AS name_p2,
            (s.n_name IS NOT NULL AND t.n_name IS NOT NULL
             AND left(s.n_name,4) = left(t.n_name,4))::INT AS name_p4,
            (s.n_name IS NOT NULL AND t.n_name IS NOT NULL
             AND left(s.n_name,6) = left(t.n_name,6))::INT AS name_p6,
            (s.n_addr IS NOT NULL AND t.n_addr IS NOT NULL
             AND left(s.n_addr,5) = left(t.n_addr,5))::INT AS addr_p5,
            (s.n_addr IS NOT NULL AND t.n_addr IS NOT NULL
             AND left(s.n_addr,8) = left(t.n_addr,8))::INT AS addr_p8,
            CASE WHEN s.name_tokens IS NULL OR t.name_tokens IS NULL THEN 0
                 ELSE length(list_intersect(s.name_tokens, t.name_tokens)) END AS name_tok_overlap,
            CASE WHEN s.name_tokens IS NULL OR t.name_tokens IS NULL
                      OR (list_count(s.name_tokens) + list_count(t.name_tokens)) = 0 THEN 0.0
                 ELSE length(list_intersect(s.name_tokens, t.name_tokens))::DOUBLE
                      / list_count(list_distinct(list_concat(s.name_tokens, t.name_tokens)))
            END AS name_tok_jaccard,
            CASE WHEN s.addr_tokens IS NULL OR t.addr_tokens IS NULL THEN 0
                 ELSE length(list_intersect(s.addr_tokens, t.addr_tokens)) END AS addr_tok_overlap,
            CASE WHEN s.n_name IS NULL OR t.n_name IS NULL THEN 0.0
                 ELSE least(length(s.n_name), length(t.n_name))::DOUBLE
                      / greatest(length(s.n_name), length(t.n_name)) END AS name_len_ratio,
            CASE WHEN s.n_addr IS NULL OR t.n_addr IS NULL THEN 0.0
                 ELSE least(length(s.n_addr), length(t.n_addr))::DOUBLE
                      / greatest(length(s.n_addr), length(t.n_addr)) END AS addr_len_ratio,
            (s.country IS NOT NULL AND s.country = t.country)::INT AS country_eq,
            -- shared numeric runs (house numbers, PIN codes): agreement is evidence
            CASE WHEN s.name_nums IS NULL OR t.name_nums IS NULL
                      OR (list_count(s.name_nums) + list_count(t.name_nums)) = 0 THEN 0
                 ELSE (length(list_intersect(s.name_nums, t.name_nums)) > 0)::INT END AS name_digits_eq,
            CASE WHEN s.addr_nums IS NULL OR t.addr_nums IS NULL
                      OR (list_count(s.addr_nums) + list_count(t.addr_nums)) = 0 THEN 0
                 ELSE (length(list_intersect(s.addr_nums, t.addr_nums)) > 0)::INT END AS addr_digits_eq
          FROM c
          JOIN s ON s.entity_id = c.sid
          JOIN t ON t.entity_id = c.tid
        ) TO {lit(out_path)} (FORMAT PARQUET, COMPRESSION ZSTD)
        """
    )
    n = con.execute(f"SELECT count(*) FROM read_parquet({lit(out_path)})").fetchone()[0]
    mark_cached(out_path, fp)
    log(f"{split} features: {n:,} rows in {time.perf_counter() - t0:.1f}s")


def entity_f05(gold: set, pred: set) -> float:
    """F_0.5 for one entity: 5*TP / (5*TP + 4*FP + FN).

    Derived from the challenge formula F_0.5 = 1.25*P*R / (0.25*P + R), where
    beta weights RECALL. Substituting P = TP/(TP+FP) and R = TP/(TP+FN) and
    multiplying through by 4 gives 5*TP / (5*TP + 4*FP + FN): the extra factor
    lands on FN, the recall-side error, so a false merge is penalised 4x a
    missed link. This matches sklearn's fbeta_score(beta=0.5) and the worked
    example in the challenge PDF (TP=2, FP=1, FN=0 -> 10/14 = 0.714).

    Do not "correct" this to 5*TP + 1*FP + 4*FN: that swaps the two error
    terms and is the F2 (recall-weighted) form, which contradicts both the PDF
    and sklearn.
    """
    if not gold and not pred:
        return 1.0
    if not gold or not pred:
        return 0.0
    tp, fp, fn = len(gold & pred), len(pred - gold), len(gold - pred)
    den = 5 * tp + 4 * fp + fn
    return 5.0 * tp / den if den else 0.0


def macro_f05(triples, all_entities=None) -> float:
    """Macro entity-level F_0.5 over (sid, tid, is_gold, is_kept) tuples.

    A tuple is one candidate row: `is_gold` marks a true positive link and
    `is_kept` marks a pair the scorer kept at the current threshold. The gold
    set of an entity is every true link (kept or not, so a missed link costs
    recall); the prediction set is every kept pair, whether or not it is gold.

    `all_entities` must enumerate every evaluated Source-1 entity, including
    true singletons: a singleton with an empty prediction scores 1.0 and one with
    a false merge scores 0.0, so dropping them would inflate the average.
    """
    gold, pred = {}, {}
    for sid, tid, is_gold, is_kept in triples:
        if is_gold:
            gold.setdefault(sid, set()).add(tid)
        if is_kept:
            pred.setdefault(sid, set()).add(tid)
    entities = set(all_entities) if all_entities is not None else set(gold)
    if not entities:
        return 0.0
    return float(np.mean([entity_f05(gold.get(s, set()), pred.get(s, set())) for s in entities]))


def stage_train(con, feat_path: Path, gt_path: Path, s1_path: Path) -> tuple:
    """Fit a linear scorer on a labelled sample, then tune the F_0.5 threshold.

    The sample is split by Source-1 entity into a fit half and a disjoint
    tuning half. Fitting the classifier and picking its threshold on the same
    rows would make the threshold search see its own training data, so the
    reported macro F_0.5 would be optimistic and the operating point would sit
    too low (it is rewarded for memorising held-in pairs). Entities are split
    rather than rows, so all candidate pairs of an entity stay on one side.
    """
    t0 = time.perf_counter()
    cols = ", ".join(FEATURES)
    rows = con.execute(
        f"""
        SELECT f.sid, f.tid, {cols}, (g.tid IS NOT NULL)::INT AS label,
               (hash(f.sid) % 2) AS is_tune
        FROM read_parquet({lit(feat_path)}) f
        LEFT JOIN read_parquet({lit(gt_path)}) g ON g.sid = f.sid AND g.tid = f.tid
        WHERE hash(f.sid) % 100 < {CFG['train_sample_pct']}
        ORDER BY f.sid, f.tid
        LIMIT {CFG['candidate_sample_rows']}
        """
    ).fetchall()
    if not rows:
        raise RuntimeError("no candidate rows for training - check the blocking output")
    X = np.array([[float(v) for v in r[2:-2]] for r in rows], dtype=np.float64)
    y = np.array([int(r[-2]) for r in rows], dtype=np.int32)
    is_tune = np.array([int(r[-1]) for r in rows], dtype=bool)
    log(f"training rows {len(y):,} (positives {int(y.sum()):,}) in {time.perf_counter() - t0:.1f}s")
    if int(y.min()) == int(y.max()):
        raise RuntimeError("training sample is single-class; blocking produced no contrast")

    # Sampled S1 entities that have no gold link at all: true singletons. They
    # still count in the macro average, so collect them for threshold tuning.
    singletons = [
        r[0] for r in con.execute(
            f"""
            SELECT entity_id FROM read_parquet({lit(s1_path)})
            WHERE hash(entity_id) % 100 < {CFG['train_sample_pct']}
              AND hash(entity_id) % 2 = 0
              AND entity_id NOT IN (SELECT sid FROM read_parquet({lit(gt_path)}))
            """
        ).fetchall()
    ]

    fit = ~is_tune
    if int(y[fit].min()) == int(y[fit].max()) or int(y[is_tune].min()) == int(y[is_tune].max()):
        # Too small a sample to split; tuning on the fit rows is optimistic, so
        # say so rather than silently reporting an inflated macro score.
        log("WARNING: sample too small for a clean fit/tune split; "
            "the tuned threshold is fitted in-sample and its F_0.5 is optimistic")
        fit = np.ones(len(y), dtype=bool)
        is_tune = np.ones(len(y), dtype=bool)
        singletons = [
            r[0] for r in con.execute(
                f"""
                SELECT entity_id FROM read_parquet({lit(s1_path)})
                WHERE hash(entity_id) % 100 < {CFG['train_sample_pct']}
                  AND entity_id NOT IN (SELECT sid FROM read_parquet({lit(gt_path)}))
                """
            ).fetchall()
        ]
    if singletons:
        log(f"true singletons in the tuning sample: {len(singletons):,}")

    from sklearn.linear_model import LogisticRegression

    mu, sigma = X[fit].mean(0), X[fit].std(0)
    sigma[sigma == 0] = 1.0
    clf = LogisticRegression(max_iter=3000, class_weight="balanced")
    clf.fit((X[fit] - mu) / sigma, y[fit])
    # Fold standardisation into raw-feature weights so the scorer becomes a plain
    # dot product that DuckDB can evaluate without a Python round trip.
    coef = (clf.coef_[0] / sigma).tolist()
    intercept = float(clf.intercept_[0] - np.dot(clf.coef_[0] / sigma, mu))

    scores = X @ np.array(coef) + intercept
    sids = [r[0] for r in rows]
    tids = [r[1] for r in rows]
    labels = y.tolist()
    # Every tuning entity counts, including true singletons that produced no
    # candidate row at all - the official macro average includes them.
    entities = {s for s, t in zip(sids, is_tune) if t} | set(singletons)

    # Threshold search runs on the tuning half only; the fit half is what the
    # classifier saw, so including it would reward memorisation.
    tune_scores = scores[is_tune]
    best_t, best_f = float(np.median(tune_scores)), -1.0
    for q in np.linspace(0.50, 0.9995, 60):
        t = float(np.quantile(tune_scores, q))
        triples = [(s, ti, bool(lab), bool(keep))
                   for s, ti, lab, keep, tune in zip(sids, tids, labels, scores >= t, is_tune)
                   if tune]
        if (f := macro_f05(triples, entities)) > best_f:
            best_f, best_t = f, t
    log(f"threshold {best_t:.4f} -> held-out macro F_0.5 {best_f:.4f} "
        f"({time.perf_counter() - t0:.1f}s)")
    return coef, intercept, best_t


def score_expression(coef: list, intercept: float) -> str:
    """SQL for the linear scorer; logistic() is monotone so the raw logit suffices."""
    terms = " + ".join(f"({w:.10f}) * coalesce({c}, 0)" for w, c in zip(coef, FEATURES))
    return f"({intercept:.10f} + {terms})"


def stage_write_outputs(con, s1_path: Path, feat_path: Path, scorer: str,
                       threshold: float, out_dir: Path) -> None:
    """Write both TSVs straight from SQL, one row per S1 entity, no quoting.

    Line endings are forced to LF: the official validator strips only ``\\n``, so
    a trailing CR would end up inside the last ID of every row.
    """
    t0 = time.perf_counter()
    for fname, header, keep_sql in (
        ("matching_results.tsv", "source1_entity_id\tmatched_entity_ids",
         f"""SELECT sid, tid FROM read_parquet({lit(feat_path)})
            WHERE ({scorer}) >= {threshold!r}"""),
        ("candidate_pairs.tsv", "source1_entity_id\tcandidate_entity_ids",
         f"SELECT sid, tid FROM read_parquet({lit(feat_path)})"),
    ):
        out = out_dir / fname
        con.execute(
            f"""
            COPY (
              WITH all_s1 AS (SELECT entity_id FROM read_parquet({lit(s1_path)})),
              agg AS (
                SELECT sid, string_agg(DISTINCT tid, ',' ORDER BY tid) AS ids
                FROM ({keep_sql}) GROUP BY sid
              )
              SELECT s.entity_id, coalesce(agg.ids, '')
              FROM all_s1 s LEFT JOIN agg ON agg.sid = s.entity_id
              ORDER BY s.entity_id
            ) TO {lit(out)} (FORMAT CSV, DELIMITER '\t', QUOTE '', NULL '', HEADER false)
            """
        )
        # COPY overwrites the file, so (re-)attach the exact header line.
        body = out.read_bytes().replace(b"\r\n", b"\n")
        out.write_bytes(header.encode("utf-8") + b"\n" + body)
    log(f"outputs written in {time.perf_counter() - t0:.1f}s")


def validate_outputs(con, out_dir: Path, s1_path: Path, target_paths: list) -> list:
    """Enforce every rule the official submission validator checks.

    Every check is expressed as SQL over the written TSVs and the normalized
    parquet shards. At the documented scale the ID universe is tens of millions
    of strings, so pulling it into Python sets is what would exhaust RAM - not
    the parquet stages - so nothing is materialised here. Only a handful of
    example values per check ever reach Python.
    """
    errors: list[str] = []

    def scalar(sql: str) -> int:
        return int(con.execute(sql).fetchone()[0] or 0)

    def examples(sql: str) -> str:
        return ", ".join(str(r[0]) for r in con.execute(sql).fetchall())

    con.execute("CREATE OR REPLACE TEMP VIEW v_s1 AS SELECT entity_id "
                f"FROM read_parquet({lit(s1_path)})")
    con.execute("CREATE OR REPLACE TEMP VIEW v_tgt AS "
                + " UNION ALL ".join(
                    f"SELECT entity_id FROM read_parquet({lit(p)})" for p in target_paths))

    views = {}
    for fname, second in (("matching_results.tsv", "matched_entity_ids"),
                          ("candidate_pairs.tsv", "candidate_entity_ids")):
        path = out_dir / fname
        if not path.exists():
            errors.append(f"{fname}: missing")
            continue
        with path.open("r", encoding="utf-8", newline="") as fh:
            got = next(csv.reader(fh, delimiter="\t", quoting=csv.QUOTE_NONE), None)
        if got != ["source1_entity_id", second]:
            errors.append(f"{fname}: header {got!r} != ['source1_entity_id', {second!r}]")
        view = f"v_{second}"
        con.execute(
            f"CREATE OR REPLACE TEMP VIEW {view} AS SELECT source1_entity_id AS sid, "
            f"coalesce(\"{second}\", '') AS cell FROM read_csv({lit(path)}, delim='\\t', "
            f"header=true, quote='', columns={{'source1_entity_id':'VARCHAR',"
            f"'{second}':'VARCHAR'}}, null_padding=true)"
        )
        # Raw explode (duplicates preserved) - the duplicate-in-list check needs
        # to see them. `_uniq` is the de-duplicated form used for every join.
        con.execute(
            f"CREATE OR REPLACE TEMP VIEW {view}_ids AS SELECT sid, trim(u) AS tid "
            f"FROM {view}, unnest(string_split(cell, ',')) AS s(u) WHERE trim(u) <> ''"
        )
        con.execute(
            f"CREATE OR REPLACE TEMP VIEW {view}_uniq AS SELECT DISTINCT sid, tid "
            f"FROM {view}_ids"
        )
        views[second] = view

        dup_rows = examples(f"SELECT sid FROM {view} GROUP BY sid HAVING count(*) > 1 LIMIT 3")
        if dup_rows:
            errors.append(f"{fname}: duplicate source1_entity_id rows (e.g. {dup_rows})")
        n_missing = scalar(
            f"SELECT count(*) FROM v_s1 s WHERE NOT EXISTS "
            f"(SELECT 1 FROM {view} v WHERE v.sid = s.entity_id)")
        if n_missing:
            errors.append(f"{fname}: {n_missing} S1 entities missing from the submission")
        n_unknown = scalar(
            f"SELECT count(*) FROM (SELECT DISTINCT sid FROM {view}) v WHERE NOT EXISTS "
            f"(SELECT 1 FROM v_s1 s WHERE s.entity_id = v.sid)")
        if n_unknown:
            errors.append(f"{fname}: {n_unknown} source1_entity_id rows are not test S1 ids")
        dup_ids = examples(
            f"SELECT sid FROM {view}_ids GROUP BY sid, tid HAVING count(*) > 1 LIMIT 3")
        if dup_ids:
            errors.append(f"{fname}: duplicate ids within a list (e.g. {dup_ids})")
        bad = examples(f"SELECT tid FROM {view}_uniq WHERE tid NOT LIKE 'S2-%' "
                       f"AND tid NOT LIKE 'S3-%' LIMIT 3")
        if bad:
            errors.append(f"{fname}: ids lacking an S2-/S3- prefix (e.g. {bad})")
        n_absent = scalar(
            f"SELECT count(*) FROM {view}_uniq v WHERE NOT EXISTS "
            f"(SELECT 1 FROM v_tgt t WHERE t.entity_id = v.tid)")
        if n_absent:
            errors.append(f"{fname}: {n_absent} ids do not exist in the test targets")

    if len(views) == 2:
        extra = examples(
            f"SELECT sid FROM (SELECT sid, tid FROM {views['matched_entity_ids']}_uniq "
            f"EXCEPT SELECT sid, tid FROM {views['candidate_entity_ids']}_uniq) LIMIT 3")
        if extra:
            errors.append(
                f"matching_results: ids absent from candidate_pairs for {extra} "
                f"(final matches must be a subset of the candidate set)")
    return errors


def blocking_recall(con, feat_path: Path, gt_path: Path) -> dict:
    """Recall ceiling of the candidate generator, per target source."""
    out = {}
    for src in ("S2", "S3"):
        row = con.execute(
            f"""
            SELECT count(*) AS gold,
                   (SELECT count(*)
                      FROM read_parquet({lit(gt_path)}) g
                      JOIN read_parquet({lit(feat_path)}) f ON f.sid = g.sid AND f.tid = g.tid
                     WHERE g.tid LIKE ?) AS recovered
            FROM read_parquet({lit(gt_path)}) WHERE tid LIKE ?
            """,
            [f"{src}-%", f"{src}-%"],
        ).fetchone()
        out[src] = {"gold_links": int(row[0]), "recovered": int(row[1]),
                    "recall": round(row[1] / row[0], 4) if row[0] else None}
    return out


def package_submission(out_dir: Path, work: Path) -> Path:
    """Bundle the two TSVs (plus the run summary) into submission.zip."""
    zpath = work / "submission.zip"
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as zf:
        for fname in ("matching_results.tsv", "candidate_pairs.tsv", "run_summary.json"):
            src = out_dir / fname
            if src.exists():
                zf.write(src, arcname=f"output/{fname}")
    log(f"packaged {zpath.name} ({zpath.stat().st_size / 2**20:.1f} MB)")
    return zpath


def run(work_dir: str = "/content", source_dir: str | None = None,
        dataset_dir: str | None = None, spill_dir: str | None = None) -> dict:
    """Run the full pipeline.

    work_dir    : where the parquet shards, the outputs and the DuckDB file live.
                  Put this on Drive if the run must survive a pre-empted Colab
                  session, since each completed stage is fingerprinted and will
                  not be recomputed on a rerun.
    spill_dir   : where DuckDB writes overflow blocks. Defaults to
                  ``work_dir/er_work/tmp``, but you almost always want to
                  override this onto fast LOCAL disk. Spill is throwaway and
                  does not need to survive, and it is large - the candidate
                  stage alone can emit tens of GB - so putting it next to the
                  cache on Drive fills the Drive quota and then fails with
                  "failed to offload data block ... max_temp_directory_size".
    dataset_dir : a directory that ALREADY contains the TSVs (e.g. an extracted
                  dataset folder on a mounted Drive). Read directly, no unzip.
    source_dir  : a directory containing the dataset .zip, used only when
                  dataset_dir is not given.

    Only the raw TSVs are read from Drive, and each is read exactly once
    (TSV -> parquet).
    """
    work = Path(work_dir)
    wdir = work / "er_work"
    norm = wdir / "norm"
    out_dir = work / "output"
    spill = Path(spill_dir) if spill_dir else wdir / "tmp"
    for d in (norm, out_dir, spill):
        d.mkdir(parents=True, exist_ok=True)
    free = shutil.disk_usage(spill).free / 2**30
    log(f"cache dir : {wdir}")
    log(f"spill dir : {spill}  ({free:.1f} GB free)")

    if dataset_dir:
        root = Path(dataset_dir)
        paths = find_dataset_files(root)
        log(f"using pre-extracted dataset at {root}")
    else:
        source = Path(source_dir) if source_dir else work
        extract = work / "extracted_data"
        already_extracted = (
            extract.exists() and any(p.name == "train_source1.tsv" for p in extract.rglob("*.tsv")))
        if not already_extracted:
            extract_zip(find_source_zip(source), extract)
        root = extract
        paths = find_dataset_files(root)
    log("dataset: " + ", ".join(f"{k}={v.relative_to(root)}" for k, v in sorted(paths.items())))

    con = connect(wdir / "er.duckdb", spill)
    try:
        src_fp = source_fingerprint(paths)
        stage_normalize(con, paths, norm, src_fp)
        stage_tokens(con, norm, src_fp)
        gt_path = norm / "train_gt_links.parquet"
        stage_ground_truth(con, paths, gt_path, src_fp)

        feat = {}
        for split in ("train", "test"):
            cand = norm / f"{split}_cand.parquet"
            stage_candidates(con, norm, split, cand, src_fp)
            feat[split] = norm / f"{split}_feat.parquet"
            stage_features(con, norm, split, cand, feat[split], src_fp)

        recall = blocking_recall(con, feat["train"], gt_path)
        log("blocking recall: " + json.dumps(recall))

        coef, intercept, threshold = stage_train(con, feat["train"], gt_path,
                                                 norm / "train_s1.parquet")

        # Persist the fitted scorer. Without this the coefficients live only in
        # this process, so re-tuning the decision threshold later - which is the
        # highest-leverage knob, since a false merge zeroes a whole S1 entity -
        # means re-running blocking, features AND training instead of one cheap
        # SQL pass over the already-cached feature parquet.
        (norm / "model.json").write_text(json.dumps({
            "features": list(FEATURES),
            "coef": [float(c) for c in coef],
            "intercept": float(intercept),
            "threshold": float(threshold),
        }, indent=2), encoding="utf-8")

        stage_write_outputs(con, norm / "test_s1.parquet", feat["test"],
                            score_expression(coef, intercept), threshold, out_dir)

        # Validation stays inside DuckDB: the test ID universe is tens of
        # millions of strings, so building Python sets here is what would OOM.
        s1_path = norm / "test_s1.parquet"
        target_paths = [norm / "test_s2.parquet", norm / "test_s3.parquet"]
        if errors := validate_outputs(con, out_dir, s1_path, target_paths):
            log("VALIDATION FAILED:")
            for e in errors[:20]:
                log("  - " + e)
            raise SystemExit(1)
        log("validation PASSED (headers, S1 coverage, prefixes, dedup, subset invariant)")

        n_s1 = con.execute(f"SELECT count(*) FROM read_parquet({lit(s1_path)})").fetchone()[0]
        n_tgt = con.execute(
            "SELECT count(*) FROM (" + " UNION ALL ".join(
                f"SELECT entity_id FROM read_parquet({lit(p)})" for p in target_paths)
            + ")").fetchone()[0]
        summary = {"config": CFG, "blocking_recall": recall, "threshold": threshold,
                   "coefficients": dict(zip(FEATURES, coef)),
                   "test_s1_entities": int(n_s1), "test_target_entities": int(n_tgt)}
        (out_dir / "run_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
        package_submission(out_dir, work)
        return summary
    finally:
        con.close()


if __name__ == "__main__":
    run(sys.argv[1] if len(sys.argv) > 1 else "/content")
'''

Path(WORK_DIR, "er_pipeline.py").write_text(PIPELINE, encoding="utf-8")
sys.path.insert(0, WORK_DIR)
import er_pipeline as ER

# -----------------------------------------------------------------------------
