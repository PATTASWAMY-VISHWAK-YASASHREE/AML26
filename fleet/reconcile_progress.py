"""Reconcile completed tasks against the 120-task roster."""
from __future__ import annotations

import json
import os
import re

ROOT = os.path.dirname(os.path.abspath(__file__))
FIND = os.path.join(ROOT, "analysis_out", "findings")
TASKS = os.path.join(ROOT, "analysis_out", "tasks")

done: set[str] = set()
for fn in os.listdir(FIND):
    m = re.match(r"^([PD]\d{3})[_.]", fn)
    if m:
        done.add(m.group(1))

allids = sorted(
    os.path.splitext(f)[0] for f in os.listdir(TASKS) if f.endswith(".json")
)
missing = [t for t in allids if t not in done]

print(f"roster      : {len(allids)}")
print(f"with output : {len(done)}")
print(f"outstanding : {len(missing)}\n")

# sanity: any output with no matching task?
orphan = sorted(done - set(allids))
if orphan:
    print(f"ORPHAN output (no matching task file): {orphan}")
else:
    print("no orphan output - every file maps to a roster task\n")

# verify each completed task's .md deliverable path actually exists
bad = []
for t in sorted(done & set(allids)):
    with open(os.path.join(TASKS, f"{t}.json"), encoding="utf-8") as f:
        spec = json.load(f)
    if not os.path.exists(os.path.join(ROOT, spec["deliverable"])):
        bad.append((t, spec["deliverable"]))
if bad:
    print("MISSING declared deliverable:")
    for t, p in bad:
        print(f"  {t} -> {p}")
else:
    print("every completed task's declared .md deliverable exists on disk")

print(f"\nfirst 12 outstanding: {', '.join(missing[:12])}")
if len(missing) > 12:
    print(f"... and {len(missing) - 12} more")
