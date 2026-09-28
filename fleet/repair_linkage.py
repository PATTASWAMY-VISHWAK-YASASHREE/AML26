"""Repair the id/deliverable linkage broken by the country-scope fix.

The fix reduced the B-family mining slots from 24 to 13, which renumbered every
D-id. Ten completed reports are still on disk, named with their ORIGINAL ids, so
the task files now declare deliverable paths that do not exist.

Rather than renumber anything again, this repoints each task's `deliverable` (and
`id`, for consistency) at the file that actually exists for the same slot. The
reports are the valuable artefact; the ids are bookkeeping, so the bookkeeping
should yield to the work.

Idempotent: safe to re-run.
"""
from __future__ import annotations

import json
import os
import re

ROOT = os.path.dirname(os.path.abspath(__file__))
FIND = os.path.join(ROOT, "analysis_out", "findings")
TASKS = os.path.join(ROOT, "analysis_out", "tasks")

DICTS = ["FR_REGIONS", "US_STATES", "IN_STATES", "ADDR_CANON_FR",
         "ADDR_CANON_COMMON", "LEET", "ADDR_GENERIC", "indic_token_dict"]
COUNTRIES = ["US", "India", "France"]
KINDS = ["audit", "mine", "gaps", "fr_design", "fr_places", "fr_order",
         "shape", "numeric", "addr_vocab", "name_vocab", "shift",
         "crosscountry", "fr_digits", "balance", "edge", "tail"]


def signature(name: str) -> tuple | None:
    """(kind, dictionary, country) for a deliverable filename, or None."""
    m = re.match(r"^[PD]\d{3}_(.+)\.md$", name)
    if not m:
        return None
    rest = m.group(1)
    country = next((c for c in COUNTRIES if rest.endswith(f"_{c}")), None)
    if country:
        rest = rest[: -len(country) - 1]
    kind = next((k for k in KINDS if rest.startswith(f"{k}_")
                 or rest == k), None)
    dname = next((d for d in DICTS if d in rest), None)
    if kind and dname and country:
        return (kind, dname, country)
    if kind and dname:            # audit/gaps carry no country
        return (kind, dname, None)
    return None


# index what exists on disk, by signature
on_disk: dict[tuple, str] = {}
for fn in sorted(os.listdir(FIND)):
    if not fn.endswith(".md"):
        continue
    sig = signature(fn)
    if sig and sig not in on_disk:
        on_disk[sig] = fn

print(f"indexed {len(on_disk)} deliverable signatures on disk\n")

# repoint task files
fixed, already_ok = [], 0
taken: set[str] = set()
for cur in sorted(os.listdir(TASKS)):
    if not cur.endswith(".json"):
        continue
    p = os.path.join(TASKS, cur)
    with open(p, encoding="utf-8") as f:
        t = json.load(f)
    decl = t.get("deliverable", "")
    if os.path.exists(os.path.join(ROOT, decl)):
        already_ok += 1
        continue
    sig = signature(os.path.basename(decl))
    if not sig or sig not in on_disk:
        continue
    target = on_disk[sig]
    if target in taken:
        continue
    taken.add(target)
    t["deliverable"] = f"analysis_out/findings/{target}"
    t["id"] = target.split("_")[0]
    t["_repointed_from"] = f"{os.path.basename(decl)}"
    with open(p, "w", encoding="utf-8") as f:
        json.dump(t, f, indent=1, ensure_ascii=False)
    fixed.append((target.split("_")[0], target, os.path.basename(decl)))

print(f"already correct: {already_ok}")
print(f"repointed       : {len(fixed)}\n")
for new_id, target, old in fixed:
    print(f"  {new_id}  ->  {target}   (was {old})")
