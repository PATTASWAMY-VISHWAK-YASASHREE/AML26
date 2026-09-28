"""Reconcile deliverables against the task roster, and audit roster integrity.

WHY THIS EXISTS
Batch 1 of the analysis fleet (D070-D079) completed at 19:54. At 20:07-20:09
someone re-ran build_roster.py, which REWROTE analysis_out/tasks/. The ten
completed deliverables are now keyed to a roster generation that no longer
exists on disk. This script measures the damage precisely instead of guessing.

THREE CHECKS
1. filename-vs-embedded-id: every task file's name must equal its "id" field.
2. id collisions: two task files claiming the same id means one overwrote the
   other, so a work order silently changed meaning.
3. deliverable reconciliation: for each slot covered by a completed sidecar,
   does a task file still exist that asks for that work?

Read-only. Prints a report; writes nothing except the manifest when asked.
"""
from __future__ import annotations

import json
import os
from collections import defaultdict

ROOT = os.path.dirname(os.path.abspath(__file__))
TASKS = os.path.join(ROOT, "analysis_out", "tasks")
FIND = os.path.join(ROOT, "analysis_out", "findings")
LEDGER = os.path.join(ROOT, "analysis_out", "id_ledger.json")


def load_tasks() -> list[dict]:
    out = []
    for fn in sorted(os.listdir(TASKS)):
        if fn.endswith(".json"):
            with open(os.path.join(TASKS, fn), encoding="utf-8") as f:
                out.append(json.load(f))
    return out


def check_filename_matches_id(tasks: list[dict]) -> list[tuple[str, str, str]]:
    bad = []
    for fn in sorted(os.listdir(TASKS)):
        if not fn.endswith(".json"):
            continue
        with open(os.path.join(TASKS, fn), encoding="utf-8") as f:
            t = json.load(f)
        if os.path.splitext(fn)[0] != t["id"]:
            bad.append((fn, t["id"], t["title"]))
    return bad


def check_collisions(tasks: list[dict]) -> dict[str, list[tuple[str, str]]]:
    by_id: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for fn in sorted(os.listdir(TASKS)):
        if not fn.endswith(".json"):
            continue
        with open(os.path.join(TASKS, fn), encoding="utf-8") as f:
            t = json.load(f)
        by_id[t["id"]].append((fn, t["title"]))
    return {k: v for k, v in by_id.items() if len(v) > 1}


def completed_slots() -> list[tuple[str, str, str]]:
    """(deliverable stem, task id self-reported, title) for each D sidecar."""
    out = []
    for fn in sorted(os.listdir(FIND)):
        if not (fn.startswith("D") and fn.endswith(".json")):
            continue
        with open(os.path.join(FIND, fn), encoding="utf-8") as f:
            d = json.load(f)
        keys = list(d.keys())
        idk = next((k for k in keys if k.lower() in ("task_id", "task", "id")), None)
        tik = next((k for k in keys if "title" in k.lower()), None)
        out.append((os.path.splitext(fn)[0],
                    str(d.get(idk, "?")) if idk else "?",
                    str(d.get(tik, "?")) if tik else "?"))
    return out


def main() -> None:
    tasks = load_tasks()
    print(f"task files on disk : {len(tasks)}")
    print(f"unique ids         : {len({t['id'] for t in tasks})}")
    fams: dict[str, int] = {}
    for t in tasks:
        fams[t["family"]] = fams.get(t["family"], 0) + 1
    print(f"by family          : {fams}\n")

    print("CHECK 1 - filename vs embedded id")
    mism = check_filename_matches_id(tasks)
    if not mism:
        print("  PASS - every file's name equals its id\n")
    else:
        for fn, tid, title in mism:
            print(f"  FAIL {fn} contains id={tid!r}  ({title})")
        print()

    print("CHECK 2 - id collisions")
    coll = check_collisions(tasks)
    if not coll:
        print("  PASS - no id claimed twice\n")
    else:
        for tid, owners in sorted(coll.items()):
            print(f"  FAIL id {tid} claimed by {len(owners)} files:")
            for fn, title in owners:
                print(f"         {fn}  ->  {title}")
        print()

    print("CHECK 3 - completed deliverables vs live roster")
    want = {os.path.splitext(os.path.basename(t["deliverable"]))[0]: t
            for t in tasks}
    orphans = []
    for stem, self_id, title in completed_slots():
        t = want.get(stem)
        if t is None:
            orphans.append((stem, self_id, title, "no live task asks for this file"))
        elif t["title"] != title:
            orphans.append((stem, self_id, title,
                            f"live task {t['id']} asks for a DIFFERENT slot: {t['title']!r}"))
    if not orphans:
        print("  PASS - every completed deliverable maps to a live task\n")
    else:
        for stem, sid, title, why in orphans:
            print(f"  ORPHAN {stem}.md  (self-reported id {sid})")
            print(f"         slot: {title}")
            print(f"         {why}")
        print()

    ledger = {}
    if os.path.exists(LEDGER):
        with open(LEDGER, encoding="utf-8") as f:
            ledger = json.load(f)
    print(f"ledger slots: {len(ledger)} (this is the stable-id intent)")
    for slot, tid in sorted(ledger.items(), key=lambda x: x[1]):
        print(f"  {tid} <- {slot}")


if __name__ == "__main__":
    main()
