"""Which of the ~64 pairwise features are actually LIVE?

pin_eq is already proven dead (pin set on 0.0083% of rows). This audits the
whole feature set the same way: run the REAL prep.py normalisation, then measure
how often each feature's underlying field is populated, per country.

A feature is DEAD if its source field is empty so often that the model cannot
learn from it. The `tri()` helper returns -1 when either side is empty, so a
field that is empty N% of the time pushes the feature to -1 N% of the time and
makes it uninformative there.

Criteria:
  DEAD      field populated < 1% of rows
  WEAK      1% - 25%
  LIVE      > 25%
"""
import csv
import sys
from collections import Counter, defaultdict

sys.path.insert(0, "_upstream/src")
import normalize as N  # noqa: E402
import keys as K       # noqa: E402

BASE = "amazon_ml_2026_research/student_resource/dataset"
CAP = 60_000

FIELDS = ["nfull", "ncore", "nalt", "atoks", "anums", "state", "pin", "acity"]

print("field population rate, real prep-time normalisation")
print(f"(capped at {CAP:,} rows per file)\n")
hdr = f"{'split':6s} {'src':3s} {'country':8s} {'rows':>9s}  "
hdr += "  ".join(f"{f:>7s}" for f in FIELDS)
print(hdr)
print("-" * len(hdr))

agg = defaultdict(lambda: defaultdict(int))
for split in ("train", "test"):
    for src in (1, 2, 3):
        path = f"{BASE}/{split}/{split}_source{src}.tsv"
        rows = Counter()
        pop = defaultdict(lambda: defaultdict(int))
        with open(path, encoding="utf-8", errors="replace", newline="") as fh:
            rd = csv.reader(fh, delimiter="\t", quoting=csv.QUOTE_NONE)
            next(rd)
            for i, rec in enumerate(rd):
                if len(rec) < 4:
                    continue
                c = rec[3].strip()
                rows[c] += 1
                full, core, alt, is_dom, is_dba = N.normalize_name(rec[1])
                atoks, anums, st, pin, cc = N.normalize_address(rec[2], c)
                vals = {
                    "nfull": " ".join(full), "ncore": " ".join(core),
                    "nalt": " ".join(alt), "atoks": " ".join(atoks),
                    "anums": " ".join(anums), "state": st, "pin": pin,
                    "acity": "|".join(cc),
                }
                for f, v in vals.items():
                    if v:
                        pop[c][f] += 1
                if i >= CAP:
                    break
        for c in sorted(rows):
            r = rows[c]
            cells = []
            for f in FIELDS:
                p = pop[c].get(f, 0)
                rate = p / r
                cells.append(f"{rate:>6.1%} " if rate > 0 else "      .")
                agg[c][f] += p
            agg[c]["_rows"] += r          # once per row, not once per field
            print(f"{split:6s} s{src:<2d} {c:8s} {r:>9,}  " + "  ".join(cells))

print("\n\nPOOLED, all files, by country:")
print(f"{'country':8s} {'rows':>10s}  " + "  ".join(f"{f:>7s}" for f in FIELDS))
print("-" * 90)
verdict = {}
for c in ("US", "India", "France"):
    a = agg[c]
    if not a.get("_rows"):
        continue
    r = a["_rows"]
    cells = []
    for f in FIELDS:
        rate = a[f] / r
        v = "DEAD" if rate < 0.01 else ("WEAK" if rate < 0.25 else "LIVE")
        verdict.setdefault(f, {})[c] = v
        mark = {"DEAD": "**", "WEAK": " *", "LIVE": "  "}[v]
        cells.append(f"{rate:>5.1%}{mark}")
    print(f"{c:8s} {r:>10,}  " + "  ".join(cells))

print("\n(* = weak, <25% populated.  ** = dead, <1%. A tri() feature on a dead")
print(" field is -1 for ~all rows, so the model learns nothing from it.)")
print("\nper-field verdict by country:")
print(f"{'field':8s} {'US':>8s} {'India':>8s} {'France':>8s}")
for f in FIELDS:
    v = verdict.get(f, {})
    print(f"{f:8s} {v.get('US','-'):>8s} {v.get('India','-'):>8s} {v.get('France','-'):>8s}")
