"""Fixture-based checks for er_pipeline.validate_outputs (DuckDB-backed).

Builds tiny parquet shards + TSVs with one deliberate violation at a time and
asserts the validator flags exactly the expected rule.
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import duckdb

import er_pipeline as P

HDR_M = "source1_entity_id\tmatched_entity_ids"
HDR_C = "source1_entity_id\tcandidate_entity_ids"


def build(tmp: Path, s1: list[str], t2: list[str], t3: list[str],
          m_rows: list[tuple[str, str]], c_rows: list[tuple[str, str]]) -> tuple:
    norm = tmp / "norm"
    out = tmp / "output"
    norm.mkdir(parents=True, exist_ok=True)
    out.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect()
    for name, ids in (("test_s1", s1), ("test_s2", t2), ("test_s3", t3)):
        # COPY ... TO does not accept a bound parameter for the target path.
        con.execute(
            f"COPY (SELECT unnest(?::VARCHAR[]) AS entity_id) "
            f"TO {P.lit(norm / f'{name}.parquet')} (FORMAT PARQUET)",
            [ids],
        )
    con.close()
    for fname, header, rows in (("matching_results.tsv", HDR_M, m_rows),
                                ("candidate_pairs.tsv", HDR_C, c_rows)):
        (out / fname).write_text(
            header + "\n" + "".join(f"{a}\t{b}\n" for a, b in rows), encoding="utf-8")
    return con_connect(tmp), out, norm


def con_connect(tmp: Path):
    return P.connect(tmp / "er.duckdb", tmp / "tmp")


def check(name: str, tmp: Path, out: Path, norm: Path, must_contain: str | None) -> None:
    con = con_connect(tmp)
    try:
        errs = P.validate_outputs(con, out, norm / "test_s1.parquet",
                                  [norm / "test_s2.parquet", norm / "test_s3.parquet"])
    finally:
        con.close()
    joined = " | ".join(errs)
    if must_contain is None:
        assert not errs, f"{name}: expected clean, got {errs}"
        print(f"  PASS {name}: no errors")
    else:
        assert any(must_contain in e for e in errs), \
            f"{name}: expected {must_contain!r} in {errs}"
        print(f"  PASS {name}: {errs[0]}")


def main() -> None:
    S1 = ["S1-1", "S1-2", "S1-3"]
    T2, T3 = ["S2-1", "S2-2"], ["S3-1"]

    with tempfile.TemporaryDirectory() as td:
        base = Path(td)

        # 1. clean submission, singleton included with an empty cell
        t = base / "clean"; t.mkdir()
        _, out, norm = build(t, S1, T2, T3,
                             [("S1-1", "S2-1,S3-1"), ("S1-2", ""), ("S1-3", "S2-2")],
                             [("S1-1", "S2-1,S3-1"), ("S1-2", ""), ("S1-3", "S2-2")])
        check("clean submission", t, out, norm, None)

        # 2. missing S1 entity
        t = base / "missing"; t.mkdir()
        _, out, norm = build(t, S1, T2, T3,
                             [("S1-1", "S2-1"), ("S1-2", "")],
                             [("S1-1", "S2-1"), ("S1-2", ""), ("S1-3", "")])
        check("missing S1 entity", t, out, norm, "S1 entities missing")

        # 3. bad prefix (self-match to S1)
        t = base / "prefix"; t.mkdir()
        _, out, norm = build(t, S1, T2, T3,
                             [("S1-1", "S2-1"), ("S1-2", ""), ("S1-3", "S1-1")],
                             [("S1-1", "S2-1"), ("S1-2", ""), ("S1-3", "S1-1")])
        check("S1- prefix in id list", t, out, norm, "prefix")

        # 4. id absent from the test targets
        t = base / "absent"; t.mkdir()
        _, out, norm = build(t, S1, T2, T3,
                             [("S1-1", "S2-99"), ("S1-2", ""), ("S1-3", "")],
                             [("S1-1", "S2-99"), ("S1-2", ""), ("S1-3", "")])
        check("unknown target id", t, out, norm, "do not exist in the test targets")

        # 5. duplicate id inside one list
        t = base / "dupid"; t.mkdir()
        _, out, norm = build(t, S1, T2, T3,
                             [("S1-1", "S2-1,S2-1"), ("S1-2", ""), ("S1-3", "")],
                             [("S1-1", "S2-1,S2-1"), ("S1-2", ""), ("S1-3", "")])
        check("duplicate id in list", t, out, norm, "duplicate ids within a list")

        # 6. duplicate source1 row
        t = base / "duprow"; t.mkdir()
        _, out, norm = build(t, S1, T2, T3,
                             [("S1-1", "S2-1"), ("S1-1", "S2-2"), ("S1-2", ""), ("S1-3", "")],
                             [("S1-1", "S2-1,S2-2"), ("S1-2", ""), ("S1-3", "")])
        check("duplicate source1 row", t, out, norm, "duplicate source1_entity_id rows")

        # 7. final match not present in the candidate set
        t = base / "subset"; t.mkdir()
        _, out, norm = build(t, S1, T2, T3,
                             [("S1-1", "S2-2"), ("S1-2", ""), ("S1-3", "")],
                             [("S1-1", "S2-1"), ("S1-2", ""), ("S1-3", "")])
        check("match outside candidate set", t, out, norm, "absent from candidate_pairs")

        # 8. wrong header (singular column name, the PDF's ambiguous form)
        t = base / "hdr"; t.mkdir()
        _, out, norm = build(t, S1, T2, T3,
                             [("S1-1", "S2-1"), ("S1-2", ""), ("S1-3", "")],
                             [("S1-1", "S2-1"), ("S1-2", ""), ("S1-3", "")])
        (out / "matching_results.tsv").write_text(
            "source1_entity_id\tmatched_entity_id\nS1-1\tS2-1\nS1-2\t\nS1-3\t\n",
            encoding="utf-8")
        check("wrong header", t, out, norm, "header")

        # 9. non-S1 row id
        t = base / "unknown"; t.mkdir()
        _, out, norm = build(t, S1, T2, T3,
                             [("S1-1", "S2-1"), ("S1-2", ""), ("S1-3", ""), ("S1-9", "")],
                             [("S1-1", "S2-1"), ("S1-2", ""), ("S1-3", ""), ("S1-9", "")])
        check("row id not in test S1", t, out, norm, "not test S1 ids")

    print("\nall validate_outputs fixtures passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
