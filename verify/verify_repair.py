"""Adjudicate every quarantined orphan against the live roster.

Read-only. The prior session quarantined six reports as "out of scope", but that
was an assumption, not a check. This re-derives the verdict from DICT_SCOPE in
build_roster.py and compares it against what the live roster actually asks for.
A report is only correctly quarantined if NO live task covers its slot.
"""
from __future__ import annotations

import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
TASKS = os.path.join(ROOT, "analysis_out", "tasks")
QD = os.path.join(ROOT, "analysis_out", "findings", "deprecated_slots")

import build_roster as br   # noqa: E402  (read-only import; build() not called)

tasks = []
for fn in sorted(os.listdir(TASKS)):
    if fn.endswith(".json"):
        with open(os.path.join(TASKS, fn), encoding="utf-8") as f:
            tasks.append(json.load(f))

# What slots does the live roster actually ask about?
live_slots: set[tuple] = set()
for t in tasks:
    m = re.match(r"^D\d{3}_(mine|audit|gaps)_(.+?)(?:_(US|India|France))?\.md$",
                 os.path.basename(t["deliverable"]))
    if m:
        live_slots.add((m.group(1), m.group(2), m.group(3)))

print(f"DICT_SCOPE in build_roster.py: "
      f"{ {k: v for k, v in br.DICT_SCOPE.items()} }\n")
print(f"live roster covers {len(live_slots)} dictionary slots\n")

print(f"{'orphan':<34} {'slot':<40} verdict")
print("-" * 100)
for fn in sorted(os.listdir(QD)):
    if not fn.endswith(".md"):
        continue
    stem = os.path.splitext(fn)[0]
    dname = next((d for d in br.DICT_FILES if f"_{d}_" in stem), None)
    country = next((c for c in br.COUNTRIES if stem.endswith(f"_{c}")), None)
    if not dname or not country:
        print(f"{stem:<34} {'(unparsed)':<40} ?")
        continue
    in_scope = country in br.DICT_SCOPE.get(dname, br.COUNTRIES)
    covered = ("mine", dname, country) in live_slots
    if not in_scope:
        verdict = "CORRECT quarantine - slot is out of scope"
    elif covered:
        verdict = "*** WRONG - live task covers this slot; must be RESTORED"
    else:
        verdict = "in scope but no live task (roster gap)"
    print(f"{stem:<34} {dname+' / '+country:<40} {verdict}")

# Roster progress, and confirmation that every pinned task points at a real report.
print()
for tid in ("D070", "D073", "D074", "D075", "D078"):
    t = next((x for x in tasks if x["id"] == tid), None)
    if t is None:
        print(f"  {tid}  not in live roster")
        continue
    ok = os.path.exists(os.path.join(ROOT, t["deliverable"]))
    print(f"  {'OK ' if ok else 'MISSING'} {tid}  "
          f"{os.path.basename(t['deliverable']):38} {t['title']}")

done = [t for t in tasks if os.path.exists(os.path.join(ROOT, t["deliverable"]))]
todo = [t for t in tasks if not os.path.exists(os.path.join(ROOT, t["deliverable"]))]
print(f"\nroster total        : {len(tasks)}")
print(f"deliverable on disk : {len(done)}  (already answered)")
print(f"awaiting an agent   : {len(todo)}")
