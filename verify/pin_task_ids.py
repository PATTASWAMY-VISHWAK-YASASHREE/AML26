"""Pin the task ids of already-completed deliverables, so regenerating the roster
cannot orphan them.

The country-scope fix in build_roster.py reduced the B-family from 24 mining
slots to 13, which shifted every D-id and broke the link between ten finished
reports and their work orders. This rebuilds id_ledger.json from what is actually
on disk, keyed by (family, kind, dictionary, country), and rewrites the affected
task files to carry the SAME id their deliverable already uses.

Run once, then build_roster.py becomes id-stable.
"""
from __future__ import annotations

import json
import os
import re

ROOT = os.path.dirname(os.path.abspath(__file__))
FIND = os.path.join(ROOT, "analysis_out", "findings")
TASKS = os.path.join(ROOT, "analysis_out", "tasks")
LEDGER = os.path.join(ROOT, "analysis_out", "id_ledger.json")

COUNTRIES = ["US", "India", "France"]
DICTS = ["FR_REGIONS", "US_STATES", "IN_STATES", "ADDR_CANON_FR",
         "ADDR_CANON_COMMON", "LEET", "ADDR_GENERIC", "indic_token_dict"]

ledger: dict[str, str] = {}
pat = re.compile(
    r"^(?P<id>[PD]\d{3})_(?P<kind>audit|mine|gaps|fr_design|balance|edge|"
    r"shape|numeric|addr_vocab|name_vocab|shift|crosscountry|fr_digits|"
    r"fr_places|fr_order|edge|tail)_?(?P<rest>.*)\.md$")

for fn in sorted(os.listdir(FIND)):
    m = pat.match(fn)
    if not m:
        continue
    tid, kind, rest = m.group("id"), m.group("kind"), m.group("rest")
    dname = next((d for d in DICTS if rest.startswith(d)), None)
    country = next((c for c in COUNTRIES if rest.endswith(c)), None)
    if dname and country:
        ledger[json.dumps(["B", kind, dname, country])] = tid

with open(LEDGER, "w", encoding="utf-8") as f:
    json.dump(ledger, f, indent=1)

print(f"pinned {len(ledger)} completed slots:")
for k, v in sorted(ledger.items(), key=lambda kv: kv[1]):
    print(f"  {v}  {k}")

# Now repoint the task files whose id disagrees with their deliverable.
moved = 0
for key, tid in ledger.items():
    fam, kind, dname, country = json.loads(key)
    want = f"{tid}_{kind}_{dname}_{country}.md" if kind in ("mine",) else \
           f"{tid}_audit_{dname}.md"
    for cur in sorted(os.listdir(TASKS)):
        if not cur.endswith(".json"):
            continue
        p = os.path.join(TASKS, cur)
        with open(p, encoding="utf-8") as f:
            t = json.load(f)
        if t.get("deliverable", "").endswith(os.path.basename(want)):
            if t["id"] != tid:
                print(f"  repoint {t['id']} -> {tid}  ({cur})")
                t["id"] = tid
                with open(p, "w", encoding="utf-8") as f:
                    json.dump(t, f, indent=1, ensure_ascii=False)
                moved += 1
            break
print(f"\nrepointed {moved} task files; {len(ledger)} slots pinned")
