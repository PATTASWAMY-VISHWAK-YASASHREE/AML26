"""Plan the OUTSTANDING tasks into batches of 10, ready to dispatch.

Batch 1 (D070-D079) is already delivered, so this planner is now resume-aware: a
task whose declared .md deliverable exists on disk counts as DONE and is
excluded. Re-dispatching finished work would burn fleet slots and risk an agent
overwriting a good report. The previous version planned every task regardless,
which is why dispatch_plan.json went stale and still named slots that had moved.

WHY BATCHING DOES NOT FIX THE FAILURE
The observed pattern is a failed auth token, not a concurrency or rate limit:

  run_00004  a001  started 12:08:03  -> COMPLETED
  run_00005  a002  started 12:08:11  -> FAILED   (8s after the success above)
  run_00006  a003  started 12:13:26  -> FAILED
  run_00007  a004  started 12:13:52  -> COMPLETED (sandwiched between failures)
  run_00008  a005  started 12:14:02  -> FAILED
  run_00009-13      started 12:23:12-12:23:57 -> all FAILED within 1-2s each

Successes and failures interleave in time at the same concurrency, and a single
no-op probe with one agent also fails. A concurrency cap would produce
throughput-shaped degradation, not alternating success. This is an expired or
racing credential.

Batching to 10 is still the RIGHT operating pattern once auth is restored - it
bounds blast radius and makes progress legible - so this planner produces the
exact order. High-value France tasks are placed in the first batches so that if
only a few batches run, they are the ones that matter.
"""
from __future__ import annotations

import json
import os

ROOT = os.path.dirname(os.path.abspath(__file__))
TASKS = os.path.join(ROOT, "analysis_out", "tasks")
PLAN = os.path.join(ROOT, "analysis_out", "dispatch_plan.json")
BATCH = 10


def load() -> list[dict]:
    out = []
    for fn in sorted(os.listdir(TASKS)):
        if fn.endswith(".json"):
            with open(os.path.join(TASKS, fn), encoding="utf-8") as f:
                out.append(json.load(f))
    return out


def is_done(t: dict) -> bool:
    """A task is done when its declared .md deliverable is on disk."""
    return os.path.exists(os.path.join(ROOT, t["deliverable"]))


def priority(t: dict) -> tuple:
    """France first, then dictionary work, then bulk profile."""
    fam, tid, title = t["family"], t["id"], t["title"]
    if fam == "B-dictionary":
        # France-only dictionary work is the single scored country; put the
        # explicitly-France tasks ahead of the cross-country dictionary work.
        rank = 0 if ("France" in title or "_fr_" in t["deliverable"]) else 1
    elif "France" in title or "_fr_" in t["deliverable"]:
        rank = 2
    else:
        rank = 3
    return (rank, tid)


def main() -> None:
    every = load()
    done = [t for t in every if is_done(t)]
    tasks = sorted((t for t in every if not is_done(t)), key=priority)
    batches = [tasks[i:i + BATCH] for i in range(0, len(tasks), BATCH)]
    plan = []
    for bi, batch in enumerate(batches, 1):
        plan.append({
            "batch": bi,
            "agents": [f"b{bi:02d}_{i + 1:02d}" for i in range(len(batch))],
            "tasks": [{"id": t["id"], "title": t["title"],
                       "deliverable": t["deliverable"]} for t in batch],
        })
    with open(PLAN, "w", encoding="utf-8") as f:
        json.dump(plan, f, indent=1, ensure_ascii=False)

    print(f"roster {len(every)} | already delivered {len(done)} | "
          f"outstanding {len(tasks)} -> {len(batches)} batches of <= {BATCH}\n")
    for b in plan[:4]:
        ids = ", ".join(t["id"] for t in b["tasks"])
        print(f"  batch {b['batch']:>2}: {ids}")
    if len(plan) > 4:
        print("  ...")
        ids = ", ".join(t["id"] for t in plan[-1]["tasks"])
        print(f"  batch {plan[-1]['batch']:>2}: {ids}")

    # sanity: no duplicates, full coverage of the OUTSTANDING set only
    seen = [t["id"] for b in plan for t in b["tasks"]]
    assert len(seen) == len(set(seen)) == len(tasks), "duplicate or missing task"
    assert not (set(seen) & {t["id"] for t in done}), "plan re-dispatches finished work"
    print(f"\nverified: {len(seen)} unique outstanding tasks, no gaps, no duplicates, "
          f"no completed task re-planned")
    print(f"wrote {PLAN}")


if __name__ == "__main__":
    main()
