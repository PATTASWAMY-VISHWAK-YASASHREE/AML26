"""Pre-commit gate: parse every .py and load every .json in the repo.

Added after a real failure: the staging step once wrote two *files* named
`src` and `colab` (captured tool output), so the pipeline and every Colab
cell were silently absent from the repository for two commits. Verifying "what
is in the commit" was not enough -- this verifies that the code which is
supposed to be there actually parses, and that a stray log or dataset file
has not been staged.

Colab cells are Jupyter notebooks, not Python: lines like `!pip install ...`
are shell magics and are not valid Python. Those lines are masked out before
parsing, so a genuine syntax error still fails but a magic does not.
"""
import ast
import json
import pathlib
import re
import subprocess
import sys

root = pathlib.Path(".")
tracked = subprocess.run(
    ["git", "ls-files"], capture_output=True, text=True, check=True
).stdout.split()

problems: list[str] = []

# 1. required deliverables must exist as real, non-empty files
REQUIRED = [
    "src/er_pipeline.py",
    "src/sweep_threshold.py",
    "src/typed_decisions.py",
    "src/postprocess.py",
    "src/decoy_shim.py",
    "colab/amazon_ml_colab_cell.py",
    "colab/colab_addon_cell.py",
    "README.md",
]
for rel in REQUIRED:
    p = root / rel
    if not p.is_file():
        problems.append(f"MISSING or not a regular file (stray file?): {rel}")
    elif p.stat().st_size == 0:
        problems.append(f"EMPTY: {rel}")

# 2. no dataset, log, or dependency directories may be tracked
FORBIDDEN_SUFFIX = (".tsv", ".csv", ".parquet", ".log", ".err", ".out", ".bin", ".zip")
for rel in tracked:
    if rel.lower().endswith(FORBIDDEN_SUFFIX):
        problems.append(f"FORBIDDEN FILE TRACKED: {rel}")
    if "student_resource" in rel or "node_modules" in rel or rel.startswith(".venv"):
        problems.append(f"FORBIDDEN PATH TRACKED: {rel}")

# 2b. markdown must render: code fences balanced, no heading trapped inside one
#     (an unclosed fence once swallowed the whole README and rendered every
#     heading as literal text inside a grey code block)
md = root / "README.md"
if md.is_file():
    lines = md.read_text(encoding="utf-8-sig").splitlines()
    fences = [i for i, ln in enumerate(lines) if ln.startswith("```")]
    if len(fences) % 2:
        problems.append(
            f"README.md: {len(fences)} code-fence markers (odd) - a fence is unclosed")
    inside = False
    for i, ln in enumerate(lines, 1):
        if ln.startswith("```"):
            inside = not inside
        elif inside and ln.startswith("#"):
            problems.append(f"README.md:{i}: heading trapped inside a code fence: {ln[:60]}")
            inside = False  # report once per fence
else:
    problems.append("MISSING: README.md")

# 3. every tracked .py must parse
#
# Colab cells are notebooks, not Python: `!pip install ...` is a shell magic and
# is invalid Python. But masking those lines unconditionally is WRONG -- a line
# inside a multi-line string can begin with `%` (e.g. "    %-34s state=%r"),
# and rewriting it to `pass` breaks the literal and invents fake syntax errors.
# So: parse verbatim first (authoritative), and only if that fails, retry with
# the magics masked.
MAGIC = re.compile(r"^\s*[!%]")
n_py = n_nb = 0
for rel in tracked:
    if not rel.endswith(".py"):
        continue
    p = root / rel
    n_py += 1
    src = p.read_text(encoding="utf-8-sig", errors="replace")
    try:
        ast.parse(src)
        continue
    except SyntaxError as verbatim:
        masked = "\n".join("pass  # masked magic" if MAGIC.match(ln) else ln
                           for ln in src.splitlines())
        try:
            ast.parse(masked)
        except SyntaxError:
            problems.append(
                f"SYNTAX ERROR {rel}: {type(verbatim).__name__}: {verbatim}"[:160])
        else:
            n_nb += 1
            print(f"  note: {rel} is a notebook cell (magics masked)")

# 4. every tracked .json must parse
n_json = 0
for rel in tracked:
    if not rel.endswith(".json"):
        continue
    p = root / rel
    n_json += 1
    try:
        json.loads(p.read_text(encoding="utf-8-sig"))
    except Exception as exc:  # noqa: BLE001
        problems.append(f"INVALID JSON {rel}: {type(exc).__name__}: {exc}"[:160])

print(f"tracked files    : {len(tracked)}")
print(f"python parsed    : {n_py} ({n_nb} notebook cells, magics masked)")
print(f"json parsed      : {n_json}")
print(f"required present : {len(REQUIRED)}")
print(f"problems         : {len(problems)}")
for pr in problems[:25]:
    print(f"  {pr}")
sys.exit(1 if problems else 0)

