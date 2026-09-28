"""
Split the single-cell Colab notebook into separate, independently-runnable cells.

WHY SPLIT
The generated `amazon_ml_colab_cell.py` is ~1,140 lines in one cell. That is
un-debuggable: a typo 900 lines in reports a line number that means nothing, and
any edit risks corrupting the embedded pipeline literal. Splitting on the cell's
own `SECTION` markers gives one cell per stage, so a failure localises
immediately and each stage can be re-run on its own.

The embedded pipeline module (SECTION 3) stays ONE cell. It is a single raw
triple-quoted string and splitting it would break the literal - that is a
structural constraint, not a preference. It is the only large cell.

Run:  .\\.venv\\Scripts\\python.exe split_colab_cells.py
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "amazon_ml_colab_cell.py"
OUTDIR = ROOT / "colab_cells"

HEADER_END = "# SECTION 1 - dependencies"

SECTIONS = [
    (1, "deps", "Install dependencies. Fast, safe to re-run."),
    (2, "mount", "Mount Drive and locate the dataset."),
    (3, "pipeline_module", "The pipeline module (single raw string - do not split)."),
    (4, "config", "Configuration. EDIT THIS to tune for your runtime."),
    (5, "run", "Run the pipeline end to end."),
]


def main() -> int:
    text = SRC.read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)

    # Cell 0 is the banner: it carries the OOM tuning order and the "GPU is not
    # needed" note, which is exactly the guidance that is easiest to lose when a
    # notebook is copied around. Keep it as the first cell.
    head = ""
    for i, ln in enumerate(lines):
        if ln.startswith("# SECTION 1 - "):
            head = "".join(lines[:i]).rstrip() + "\n"
            break

    # A section starts at its "# SECTION n -" banner and ends just before the
    # banner of the next section, so trailing prose lands with its own section.
    marks = []
    for i, ln in enumerate(lines):
        m = re.match(r"^# SECTION (\d+) - ", ln)
        if m:
            marks.append((int(m.group(1)), i))
    if not marks:
        raise SystemExit("no SECTION markers found - was the cell rebuilt?")
    bounds = {n: i for n, i in marks}
    order = [n for n, _ in marks]

    def span(n: int) -> str:
        start = bounds[n]
        later = [bounds[m] for m in order if m > n]
        end = min(later) if later else len(lines)
        # stop before the dashed rule that precedes the next banner
        while end - 1 > start and set(lines[end - 1].strip()) <= {"#", "-"}:
            end -= 1
        return "".join(lines[start:end]).rstrip() + "\n"

    OUTDIR.mkdir(exist_ok=True)
    written = []

    if head.strip():
        p = OUTDIR / "cell0_header.py"
        p.write_text(head, encoding="utf-8")
        written.append((0, "header", "Banner: OOM tuning order + 'GPU not needed' note.",
                        len(head.splitlines()), p.stat().st_size))

    for n, name, desc in SECTIONS:
        if n not in bounds:
            continue
        body = span(n)
        p = OUTDIR / f"cell{n}_{name}.py"
        p.write_text(body, encoding="utf-8")
        written.append((n, name, desc, len(body.splitlines()), p.stat().st_size))

    # Every cell must be valid Python on its own, even though cells 2-5 share
    # a namespace: a syntax error in cell 4 should show up here, not in Colab.
    #
    # Colab cells may contain IPython magics (!pip, %cd, ?obj), which are NOT
    # valid Python and will always fail ast.parse. That is expected, not a bug,
    # so magic lines are blanked out before the check rather than skipped
    # wholesale - otherwise a real syntax error in the same cell would hide.
    import ast

    def strip_magics(src: str) -> str:
        out = []
        for ln in src.splitlines():
            s = ln.lstrip()
            if s[:1] in ("!", "%", "?"):
                out.append("")
            else:
                out.append(ln)
        return "\n".join(out)

    bad, magics = [], {}
    for w in written:
        f = OUTDIR / f"cell{w[0]}_{w[1]}.py"
        src = f.read_text(encoding="utf-8")
        n_magic = sum(1 for ln in src.splitlines() if ln.lstrip()[:1] in ("!", "%", "?"))
        if n_magic:
            magics[f.name] = n_magic
        try:
            ast.parse(strip_magics(src))
        except SyntaxError as exc:
            bad.append(f"{f.name}: line {exc.lineno} {exc.msg}")

    # a run order, so it is unambiguous which cell follows which
    order_txt = ["# Colab cells - run in this order", ""]
    for n, name, desc, nl, size in written:
        order_txt.append(f"cell{n}_{name}.py   {nl:>5} lines  {size:>7,} B   {desc}")
    order_txt.append("")
    order_txt.append(f"Total across cells: {sum(w[3] for w in written)} lines "
                     f"({sum(w[4] for w in written):,} B)")
    order_txt.append("")
    order_txt.append("Cells 2-5 share one namespace, so run them top to bottom in a")
    order_txt.append("single Colab session. cell2 defines WORK_DIR / SPILL_DIR /")
    order_txt.append("DATASET_DIR; cell3 defines ER; cell4 and cell5 consume both.")
    (OUTDIR / "00_RUN_ORDER.md").write_text("\n".join(order_txt) + "\n", encoding="utf-8")

    print(f"split {SRC.name} ({len(lines)} lines) into {len(written)} cells\n")
    for n, name, desc, nl, size in written:
        print(f"  cell{n}_{name}.py  {nl:>5} lines {size:>7,} B   {desc}")
    print(f"\n  order file: {OUTDIR / '00_RUN_ORDER.md'}")
    print(f"  total: {sum(w[3] for w in written)} lines")
    if bad:
        print("\n  SYNTAX ERRORS:")
        for b in bad:
            print(f"    {b}")
        return 1
    print("\n  all cells parse as valid Python")
    if magics:
        print("  IPython magics present (valid in Colab, not valid Python):")
        for k, v in magics.items():
            print(f"    {k}: {v} magic line(s)")
    print("  NOTE: cell3 stays one block. It is a single raw triple-quoted")
    print("  string; splitting it would break the literal.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
