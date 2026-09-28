"""Create a compact, disk-backed DuckDB view of the official TSV data.

DuckDB is used here as an out-of-core columnar scanner. The script does not
materialize a full pandas dataframe and does not alter the raw competition
files. It creates a small metadata file documenting the scan.
"""
from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path

import duckdb

EXPECTED_COLUMNS = ("entity_id", "business_name", "business_address", "country")


def lit(path: Path | str) -> str:
    return "'" + str(path).replace("'", "''") + "'"


def header_of(path: Path) -> list[str]:
    """Read the first line of a TSV without loading the file."""
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        first = handle.readline()
    if not first.strip():
        raise ValueError(f"{path} is empty; expected a header row")
    return [c.strip().lstrip("\ufeff") for c in first.rstrip("\r\n").split("\t")]


def create_view(con: duckdb.DuckDBPyConnection, view: str, path: Path) -> None:
    """Create a file-backed view, failing closed on schema drift.

    DuckDB binds read_csv columns POSITIONALLY, so `header=true` plus an
    explicit `columns={...}` struct silently accepts a renamed or reordered
    4-column file and mis-maps every field. Validate the real header line
    before creating the view and raise on any mismatch.
    """
    if not path.exists():
        raise FileNotFoundError(f"expected source file is missing: {path}")
    actual = header_of(path)
    if tuple(actual) != EXPECTED_COLUMNS:
        raise ValueError(
            f"schema drift in {path}: header is {actual}, expected {list(EXPECTED_COLUMNS)}"
        )
    con.execute(
        f"CREATE OR REPLACE VIEW {view} AS SELECT * FROM read_csv({lit(path)}, delim='\\t', header=true, "
        "columns={'entity_id':'VARCHAR','business_name':'VARCHAR','business_address':'VARCHAR','country':'VARCHAR'}, "
        "ignore_errors=false)"
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--threads", type=int, default=4)
    parser.add_argument("--memory-limit", default="2GB")
    args = parser.parse_args()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    spill = args.out.parent / "duckdb_scan_tmp"
    spill.mkdir(parents=True, exist_ok=True)
    # Register file-backed views. Column names are explicit to fail closed on
    # schema drift; no row values are printed.
    root = args.dataset

    with duckdb.connect(str(args.out)) as con:
        con.execute("SET threads=?", [int(args.threads)])
        con.execute(f"SET memory_limit={lit(args.memory_limit)}")
        con.execute("SET preserve_insertion_order=false")
        con.execute("SET temp_directory=?", [str(spill)])
        for split in ("train", "test"):
            for source in (1, 2, 3):
                create_view(con, f"{split}_s{source}", root / split / f"{split}_source{source}.tsv")
        # A compact metadata query proves all files are readable and records counts
        # without copying their text columns into RAM.
        start = time.perf_counter()
        rows = con.execute(
            """
            SELECT 'train_s1' AS table_name, count(*) AS rows FROM train_s1
            UNION ALL SELECT 'train_s2', count(*) FROM train_s2
            UNION ALL SELECT 'train_s3', count(*) FROM train_s3
            UNION ALL SELECT 'test_s1', count(*) FROM test_s1
            UNION ALL SELECT 'test_s2', count(*) FROM test_s2
            UNION ALL SELECT 'test_s3', count(*) FROM test_s3
            ORDER BY table_name
            """
        ).fetchall()
        elapsed = time.perf_counter() - start
        metadata = {
            "database": str(args.out),
            "threads": args.threads,
            "memory_limit": args.memory_limit,
            "elapsed_seconds": elapsed,
            "counts": {name: int(count) for name, count in rows},
        }
    # with_suffix('.json') would return --out itself for e.g. `--out report.json`
    # and truncate the live DuckDB database. Use a distinct suffix, written
    # atomically via a temp file + replace.
    meta_path = args.out.with_name(args.out.name + ".meta.json")
    tmp_meta = meta_path.with_name(meta_path.name + f".tmp{os.getpid()}")
    tmp_meta.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp_meta, meta_path)
    print(json.dumps(metadata, indent=2))


if __name__ == "__main__":
    main()
