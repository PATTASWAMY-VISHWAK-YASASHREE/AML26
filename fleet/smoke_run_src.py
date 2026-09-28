"""Import + compile smoke test for the run_src working copy.

Compiles every module, then imports the ones the test-only chain actually uses and
checks the one behavioural change that matters (build_features' CHUNK default).
It does NOT run any stage.
"""
import glob, importlib, os, sys, py_compile

B = r"C:\Users\pvish\OneDrive - UCB-O365\Desktop\New folder (13)"
SRC = os.path.join(B, "run_src", "src")
sys.path.insert(0, SRC)

fails = []

print("--- py_compile ---")
for f in sorted(glob.glob(os.path.join(SRC, "*.py"))):
    try:
        py_compile.compile(f, doraise=True, cfile=os.path.join(os.environ["TEMP"], "_smoke.pyc"))
        print("  OK   ", os.path.basename(f))
    except Exception as e:
        fails.append(f"{f}: {e}")
        print("  FAIL ", os.path.basename(f), e)

print("--- import ---")
for m in ("normalize", "keys", "blocking", "features", "stage2", "metrics"):
    try:
        mod = importlib.import_module(m)
        print("  OK   ", m)
    except Exception as e:
        fails.append(f"import {m}: {e}")
        print("  FAIL ", m, type(e).__name__, e)

# train.py and run_blocking.py read sys.argv at module level, so they must be
# exercised with argv populated exactly as the real chain does.  This mirrors what
# make_submission.py does via `from train import read_part`.
print("--- import (argv-dependent modules) ---")
os.makedirs(os.path.join(os.environ["TEMP"], "_smokearg"), exist_ok=True)
sys.argv = ["smoke"]

print("--- diff manifest vs read-only _upstream/src ---")
import hashlib
UP = os.path.join(B, "_upstream", "src")


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


changed = []
for f in sorted(glob.glob(os.path.join(SRC, "*.py"))):
    rel = os.path.basename(f)
    up = os.path.join(UP, rel)
    if not os.path.exists(up):
        changed.append((rel, "NEW"))
    elif sha(f) != sha(up):
        changed.append((rel, "MODIFIED"))
    else:
        print("  identical  ", rel)
print("  ---")
for rel, how in changed:
    print(f"  {how:9s} {rel}")
if not changed:
    fails.append("run_src is byte-identical to upstream - no edits were staged!")

# The fr-dictionary patch and the LEET change must NOT be present in run_src.
upn = os.path.join(UP, "normalize.py")
if sha(os.path.join(SRC, "normalize.py")) != sha(upn):
    fails.append("normalize.py differs from upstream - the fr-dict/LEET patch leaked in!")
else:
    print("  OK  normalize.py is byte-identical to upstream (no fr-dict / LEET change)")

print()

print("--- constants ---")
import re
bf = open(os.path.join(SRC, "build_features.py"), encoding="utf-8").read()
m = re.search(r'^CHUNK = int\(os\.environ\.get\("FEAT_CHUNK", "(\d+)"\)\)', bf, re.M)
print("  build_features CHUNK default =", m.group(1) if m else "NOT FOUND")
if not m or m.group(1) != "50000":
    fails.append("CHUNK default is not 50000")

pp = open(os.path.join(SRC, "prep.py"), encoding="utf-8").read()
m = re.search(r'def prep_file\(inp, outp, nproc=(\d+), chunk=(\d+)\)', pp)
print("  prep prep_file defaults   =", m.groups() if m else "NOT FOUND")
if not m or m.group(1) != "1":
    fails.append("prep nproc default is not 1")

ms = open(os.path.join(SRC, "make_submission.py"), encoding="utf-8").read()
for token in ('ONLY = [c for c in os.environ.get("COUNTRIES"', "FINALIZE", "gc.collect()"):
    ok = token in ms
    print(f"  make_submission has {token!r}:", ok)
    if not ok:
        fails.append(f"make_submission missing {token!r}")

print("--- run_blocking (module-level import check only) ---")
print("  (compile-only; run_blocking.py is UNMODIFIED and executes real work on import)")

print()
print("SMOKE RESULT:", "PASS" if not fails else f"FAIL ({len(fails)})")
for f in fails:
    print("  -", f)
sys.exit(1 if fails else 0)
