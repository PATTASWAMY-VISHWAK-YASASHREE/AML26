"""Assemble the single-cell Colab notebook from the tested er_pipeline.py.

Generating the cell from the real module (rather than hand-copying it into a
triple-quoted string) guarantees the code the user pastes is byte-identical to
the code that passed test_candidate_equivalence.py and
test_pipeline_tight_memory.py.

The header/footer live in plain .txt files so this module stays small enough to
edit reliably; the only thing spliced in is the raw triple-quote marker.
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).parent
Q3 = chr(39) * 3


def main() -> None:
    pipeline = (ROOT / "er_pipeline.py").read_text(encoding="utf-8")
    assert Q3 not in pipeline, "pipeline contains a triple single-quote"
    header = (ROOT / "colab_cell_header.txt").read_text(encoding="utf-8")
    footer = (ROOT / "colab_cell_footer.txt").read_text(encoding="utf-8")
    cell = header + pipeline + footer

    dest = ROOT / "amazon_ml_colab_cell.py"
    dest.write_text(cell, encoding="utf-8")

    # The embedded module must still compile standalone, and the cell must
    # contain exactly one raw-triple-quote pair.
    compile(pipeline, "er_pipeline.py", "exec")
    assert cell.count(Q3) == 2, "cell must have exactly 2 triple-quote markers"

    print(f"wrote {dest.name}: {len(cell.splitlines())} lines, {len(cell):,} chars")
    print("embedded pipeline compiles standalone :", True)
    print("OOM fix - temp spill enabled          :", "max_temp_directory_size" in cell)
    print("OOM fix - per-channel COPY            :", "EXACT_CHANNELS" in cell)
    # The only remaining SELECT * is over the *capped* candidate file in
    # stage_features (3 columns, <= max_candidates per S1). What must not exist
    # is a SELECT * over the normalised corpus shards, which carry the token
    # lists and are the actual memory problem.
    corpus_star = re.findall(r"SELECT \* FROM read_parquet\([^)]*_s[123]\.parquet",
                             pipeline)
    print("OOM fix - no SELECT * over corpus shards:", not corpus_star,
          f"(found {len(corpus_star)})")
    print("remaining SELECT * is over the capped candidate file:",
          pipeline.count("SELECT * FROM read_parquet({lit(cand_path)})") == 1)
    print("correct F_0.5 denominator kept       :",
          "den = 5 * tp + 4 * fp + fn" in pipeline)
    print("DuckDB-backed validator (no Py sets)  :",
          "def validate_outputs(con," in pipeline)


if __name__ == "__main__":
    main()
