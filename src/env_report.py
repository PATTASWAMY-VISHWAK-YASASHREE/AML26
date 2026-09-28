"""Report the interpreter's environment and which pipeline modules are importable.

Run:  C:\\Users\\pvish\\major101\\.venv\\Scripts\\python.exe env_report.py

Written because the shell harness swallows stderr, so `python -c "import polars"`
showed only a truncated traceback. This prints to STDOUT and cannot be lost.
"""
import importlib
import sys

REQS = {
    "polars": "1.44.2",
    "pyarrow": "25.0.1",
    "numpy": "2.4.4",
    "lightgbm": "4.7.0",
    "rapidfuzz": "3.14.6",
}

print(f"python  : {sys.version.split()[0]}")
print(f"exe     : {sys.executable}")
print(f"prefix  : {sys.prefix}")
print()

missing = []
for mod, want in REQS.items():
    try:
        m = importlib.import_module(mod)
        got = getattr(m, "__version__", "?")
        flag = "OK  " if got == want else "DIFF"
        print(f"  {flag} {mod:<10} want {want:<9} got {got}")
        if got != want:
            missing.append(f"{mod} (version {got} != {want})")
    except Exception as exc:
        print(f"  MISS {mod:<10} want {want:<9} {type(exc).__name__}: {exc}")
        missing.append(mod)

print()
print("MISSING/DIFFERENT:", ", ".join(missing) if missing else "none - requirements satisfied")
