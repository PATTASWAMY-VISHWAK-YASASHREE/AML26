"""Environment capability probe: which libraries exist in a given venv.

Run as:  & <venv>\\Scripts\\python.exe env_probe.py
Writes nothing; prints a fixed-width table. Used to decide which analysis
stages are actually runnable on this box.
"""
import importlib
import sys

MODS = [
    "pandas", "numpy", "polars", "duckdb", "pyarrow",
    "rapidfuzz", "jellyfish", "regex", "Levenshtein",
    "faiss", "sklearn", "lightgbm", "xgboost", "scipy",
    "unidecode", "fasttext", "langdetect", "sentence_transformers",
    "torch", "transformers", "networkx", "Levenshtein",
]

print("python", sys.version.split()[0])
ok, missing = [], []
for m in MODS:
    try:
        mod = importlib.import_module(m)
        ok.append((m, getattr(mod, "__version__", "?")))
    except Exception:
        missing.append(m)

for m, v in ok:
    print("  OK       {:24s} {}".format(m, v))
print("  MISSING  " + ", ".join(missing) if missing else "  MISSING  (none)")
