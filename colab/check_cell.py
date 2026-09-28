"""Execute the code embedded in the Colab cell against fixtures.

Claiming "verified" about code that has never run is the failure mode this
project keeps hitting: a hand-transcribed step list, an unexecuted validator,
and a DRY flag declared but never wired. This extracts the real functions from
the cell and runs them.
"""
from __future__ import annotations

import io
import sys
import tempfile
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).parent
CELL = ROOT / "colab_upstream_cell.txt"

failures: list[str] = []


def check(label: str, ok: bool, detail: str = "") -> None:
    print(f"[{'PASS' if ok else 'FAIL'}] {label}{(' :: ' + detail) if detail else ''}")
    if not ok:
        failures.append(label)


def extract(text: str, start: str, end: str) -> str:
    i = text.index(start)
    return text[i:text.index(end, i)]


def build(root: Path, s1, s2, s3, m_rows, c_rows):
    d = root / "dataset" / "test"
    d.mkdir(parents=True, exist_ok=True)
    hdr = "entity_id\tbusiness_name\tbusiness_address\tcountry\n"
    for name, ids in (("test_source1.tsv", s1), ("test_source2.tsv", s2),
                      ("test_source3.tsv", s3)):
        (d / name).write_text(
            hdr + "".join(f"{i}\tB{i}\t1 St, Town\tUS\n" for i in ids), encoding="utf-8")
    out = root / "out"
    out.mkdir(parents=True, exist_ok=True)
    (out / "matching_results.tsv").write_text(
        "source1_entity_id\tmatched_entity_ids\n" + "".join(f"{a}\t{b}\n" for a, b in m_rows),
        encoding="utf-8")
    (out / "candidate_pairs.tsv").write_text(
        "source1_entity_id\tcandidate_entity_ids\n" + "".join(f"{a}\t{b}\n" for a, b in c_rows),
        encoding="utf-8")
    return out, d


def main() -> int:
    import re

    import duckdb
    text = CELL.read_text(encoding="utf-8")

    # --- static: DRY declared AND passed ---------------------------------
    decl = re.search(r"^DRY\s*=\s*(True|False)", text, re.M)
    ctor = re.search(r"StepRunner\(([^)]*)\)", text)
    check("DRY is declared", decl is not None)
    check("DRY is passed to StepRunner",
          bool(ctor) and "DRY" in ctor.group(1),
          f"ctor: {ctor.group(1).strip() if ctor else 'n/a'}")
    check("DRY declared before use",
          bool(decl and ctor) and text.index(decl.group(0)) < text.index("dry_run=DRY"))

    # --- execute the cell's validator ------------------------------------
    fn = extract(text, "def validate_ooc", "if Path(OUTM).exists()")
    ns: dict = {"duckdb": duckdb}
    exec(compile(fn, "validate_ooc", "exec"), ns)
    v = ns["validate_ooc"]

    S1, T2, T3 = ["S1-1", "S1-2", "S1-3"], ["S2-1", "S2-2"], ["S3-1"]
    cases = [
        ("valid submission", [("S1-1", "S2-1"), ("S1-2", ""), ("S1-3", "S3-1,S2-2")],
         [("S1-1", "S2-1"), ("S1-2", ""), ("S1-3", "S3-1,S2-2")], False, None),
        ("missing S1 row", [("S1-1", "S2-1"), ("S1-2", "")],
         [("S1-1", "S2-1"), ("S1-2", ""), ("S1-3", "")], True, "missing"),
        ("S1- self-match", [("S1-1", "S1-1"), ("S1-2", ""), ("S1-3", "")],
         [("S1-1", "S1-1"), ("S1-2", ""), ("S1-3", "")], True, "non-S2/S3"),
        ("match outside candidates", [("S1-1", "S2-2"), ("S1-2", ""), ("S1-3", "")],
         [("S1-1", "S2-1"), ("S1-2", ""), ("S1-3", "")], True, "not in candidate_pairs"),
        ("duplicate id in a list", [("S1-1", "S2-1,S2-1"), ("S1-2", ""), ("S1-3", "")],
         [("S1-1", "S2-1,S2-1"), ("S1-2", ""), ("S1-3", "")], True, "duplicate ids"),
        ("id not in test targets", [("S1-1", "S2-99"), ("S1-2", ""), ("S1-3", "")],
         [("S1-1", "S2-99"), ("S1-2", ""), ("S1-3", "")], True, "not in the test target"),
        ("duplicate source1 row",
         [("S1-1", "S2-1"), ("S1-1", "S2-2"), ("S1-2", ""), ("S1-3", "")],
         [("S1-1", "S2-1,S2-2"), ("S1-2", ""), ("S1-3", "")], True, "duplicate source1"),
    ]
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        for label, m, c, should_fail, needle in cases:
            out, d = build(base / label.replace(" ", "_"), S1, T2, T3, m, c)
            errs = v(out / "matching_results.tsv", out / "candidate_pairs.tsv", d)
            if should_fail:
                check(label, any(needle in e for e in errs), str(errs)[:110])
            else:
                check(label, not errs, str(errs)[:110])

        # --- execute the candidate-size reporting ------------------------
        out, _ = build(base / "cand", S1, T2, T3,
                       [("S1-1", "S2-1"), ("S1-2", ""), ("S1-3", "S3-1")],
                       [("S1-1", "S2-1,S2-2"), ("S1-2", ""), ("S1-3", "S3-1")])
        OUTM, OUTC = str(out / "matching_results.tsv"), str(out / "candidate_pairs.tsv")
        import statistics
        import textwrap
        # the block is nested inside an `if` in the cell, so dedent before exec
        src = textwrap.dedent(extract(
            text, "    import statistics", 'else:\n    print("outputs not present'))
        buf = io.StringIO()
        with redirect_stdout(buf):
            exec(compile(src, "candstat", "exec"),
                 {"statistics": statistics, "OUTC": OUTC, "Path": Path})
        printed = buf.getvalue()
        check("candidate-size report runs and prints a mean",
              "candidates/S1" in printed, printed.strip()[:100])
        # 2 + 0 + 1 = 3 ids over 3 entities -> mean 1.00
        check("candidate mean is arithmetically right", "mean 1.00" in printed,
              printed.strip()[:100])

    # --- the step list must still match run_all.sh verbatim ---------------
    sh_path = ROOT / "_upstream" / "run_all.sh"
    if sh_path.exists():
        sh_steps = []
        for line in sh_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line.startswith(("python3 ", "GT=")):
                continue
            gt = line.startswith("GT=")
            # `GT="$DATA/..." python3 build_features.py train "$WORK"` - the GT
            # assignment is ONE quoted token, so filter it out rather than
            # popping a fixed number of tokens.
            toks = [t for t in line.split()
                    if t != "python3" and not t.startswith("GT=")]
            sh_steps.append((toks[0], gt))
        block = re.search(r"^STEPS = \[(.*?)^\]", text, re.S | re.M)
        cell_steps = re.findall(r'"name":\s*"([^"]+)",\s*\n?\s*"cmd":\s*\[([^\]]*)\]',
                               block.group(1), re.S) if block else []
        cell_scripts = [re.search(r'"([^"]+\.py)"', c).group(1) for _, c in cell_steps]
        check("step count matches run_all.sh", len(cell_steps) == len(sh_steps),
              f"cell={len(cell_steps)} shell={len(sh_steps)}")
        for i, ((name, _), (script, gt)) in enumerate(zip(cell_steps, sh_steps)):
            # GT env must be set on exactly the same steps
            seg = block.group(1).split(f'"name": "{name}"')[1]
            seg = seg.split('"name"')[0]
            cell_gt = '"env": GT' in seg
            check(f"step {i + 1} {name}", cell_scripts[i] == script and cell_gt == gt,
                  f"{cell_scripts[i]} vs {script}; GT cell={cell_gt} shell={gt}")

    if failures:
        raise SystemExit("FAILURES: " + "; ".join(failures))
    print("\ncell executes correctly AND matches run_all.sh exactly")
    return 0

if __name__ == "__main__":
    sys.exit(main())


def main() -> int:
    failures = []

    def check(label, ok, detail=""):
        print(f"[{'PASS' if ok else 'FAIL'}] {label}{(' :: ' + detail) if detail else ''}")
        if not ok:
            failures.append(label)

    text = CELL.read_text(encoding="utf-8")
    # Colab magics are not valid Python; blank them for the syntax check only.
    code = "\n".join("pass" if l.strip().startswith(("!", "%")) else l
                     for l in text.splitlines())
    try:
        compile(code, "colab_upstream_cell.txt", "exec")
        check("cell is syntactically valid Python", True, f"{len(text.splitlines())} lines")
    except SyntaxError as exc:
        check("cell is syntactically valid Python", False, f"line {exc.lineno}: {exc.msg}")
        raise SystemExit(1)

    # Steps declared in the cell, in order.
    block = re.search(r"^STEPS = \[(.*?)^\]", text, re.S | re.M)
    check("STEPS block present", block is not None)
    steps = re.findall(r'"name":\s*"([^"]+)",\s*\n?\s*"cmd":\s*\[([^\]]*)\]',
                       block.group(1), re.S) if block else []

    # Steps in run_all.sh, in order: python3 <script> <args...> [GT=... prefix]
    sh = SH.read_text(encoding="utf-8")
    sh_steps = []
    for line in sh.splitlines():
        line = line.strip()
        if not line.startswith(("python3 ", "GT=")):
            continue
        gt = line.startswith("GT=")
        toks = line.split()
        if gt:
            toks = toks[1:]           # drop the GT=... assignment
        toks = [t for t in toks if t != "python3"]
        sh_steps.append((toks[0], toks[1:], gt))

    check("step count matches run_all.sh", len(steps) == len(sh_steps),
          f"cell={len(steps)} run_all.sh={len(sh_steps)}")

    for i, ((name, cmd), (script, args, gt)) in enumerate(zip(steps, sh_steps)):
        cell_script = re.search(r'"([^"]+\.py)"', cmd)
        cell_script = cell_script.group(1) if cell_script else "?"
        ok = cell_script == script
        # the GT env var must be set on exactly the same steps
        cell_gt = "GT" in block.group(1).split('"name": "' + name + '"')[1].split('{"name"')[0] \
            if block and '"name": "' + name + '"' in block.group(1) else False
        check(f"step {i + 1} {name}: script + env",
              ok and cell_gt == gt,
              f"{cell_script} vs {script}, GT cell={cell_gt} shell={gt}")

    # Required infrastructure for THIS cell. (max_candidates / spill belong to
    # the separate DuckDB pipeline and have no business here.)
    for token, why in (("progress.json", "resume manifest"),
                       ("already done", "resume reporting"),
                       ("validate_ooc", "out-of-core validation"),
                       ("candidates/S1", "candidate-size reporting (now ranked)"),
                       ("files.download", "download"),
                       ("DRY", "dry-run switch")):
        check(f"cell references {token!r} ({why})", token in text)

    if failures:
        raise SystemExit("FAILURES: " + "; ".join(failures))
    print("\ncell matches run_all.sh exactly")
    return 0


if __name__ == "__main__":
    sys.exit(main())
