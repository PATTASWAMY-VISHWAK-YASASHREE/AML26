"""Why does France state resolve only 65-67% in sources 2/3 but 100% in source 1?

My earlier F2 refutation measured test_source1.tsv ONLY and concluded 100%
coverage. That was the wrong file: the matching task pairs a source-2/3 QUERY
against a source-1 record, and state_eq = tri(q_state, s_state) returns -1 when
EITHER side is empty. So the query-side rate is what actually matters.

Find the French region/place components in sources 2 and 3 that FR_REGIONS
does NOT resolve.
"""
import ast
import csv
import re
import sys
from collections import Counter

sys.path.insert(0, "_upstream/src")
import normalize as N  # noqa: E402

src = open("_upstream/src/normalize.py", encoding="utf-8").read()
FR = None
for node in ast.parse(src).body:
    if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", "") == "FR_REGIONS":
        FR = ast.literal_eval(node.value)

BASE = "amazon_ml_2026_research/student_resource/dataset/test"
EMPTYISH = ("null", "<null>", "n/a", "na", "none")


def state_of(addr):
    for c in addr.lower().split(","):
        c = c.strip()
        if not c or c in EMPTYISH:
            continue
        ck = re.sub(r"[^a-z0-9& ]+", " ", c).replace("&", " and ")
        ck = " ".join(ck.split())
        if ck in FR:
            return FR[ck]
    return ""


for srcno in (1, 2, 3):
    path = f"{BASE}/test_source{srcno}.tsv"
    n = hit = 0
    miss = Counter()
    with open(path, encoding="utf-8", errors="replace", newline="") as fh:
        rd = csv.reader(fh, delimiter="\t", quoting=csv.QUOTE_NONE)
        next(rd)
        for i, rec in enumerate(rd):
            if len(rec) < 4 or rec[3].strip() != "France":
                continue
            n += 1
            if state_of(rec[2]):
                hit += 1
            else:
                for c in rec[2].lower().split(","):
                    c = c.strip()
                    if not c or c in EMPTYISH:
                        continue
                    ck = " ".join(re.sub(r"[^a-z0-9& ]+", " ", c).replace(
                        "&", " and ").split())
                    if ck and not re.match(r"^\d+$", ck):
                        miss[ck] += 1
            if n >= 120_000:
                break
    rate = hit / max(n, 1)
    print(f"test_source{srcno}: France rows={n:,}  state resolved={hit:,} "
          f"({rate:.2%})  MISSING={n - hit:,}")
    if srcno in (2, 3) and miss:
        print("   top unresolved components:")
        for c, k in miss.most_common(12):
            print(f"     {k:>7,}  {c!r}")
    print()
