"""Dispatch the 120-task roster across a pool of teammates.

The role prompt is identical for every agent; only the task file changes. This
builds the exact prompt text for a given task id so spawning is mechanical and
cannot drift between agents.

Usage:  python dispatch_text.py P004
"""
from __future__ import annotations

import json
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
TASKS = os.path.join(ROOT, "analysis_out", "tasks")

TEMPLATE = """You are analysis agent {agent} in a fleet analysing the Amazon ML
Challenge 2026 entity-resolution dataset. Working dir: {root}

FIRST: read AGENT_PROMPT.md in full. It defines the profile schema, the hard
constraints and the evidence standard. Then read your work order at
analysis_out/tasks/{task}.json and execute exactly that one task.

CRITICAL CONSTRAINTS:
- The machine has under 1 GB free RAM. Read ONLY the compact JSON profile files
  in analysis_out/profile/ (each ~575-865 KB). NEVER open the raw *.tsv files
  under amazon_ml_2026_research/student_resource/dataset/ - a 480 MB scan was
  OOM-killed on this box and will kill you too.
- READ-ONLY on the dataset and on _upstream/. Never modify, move or delete
  anything there. _upstream is a pristine git clone and must stay that way.
- No network access whatsoever. The competition prohibits external data lookup,
  with immediate disqualification as the penalty.
- Write exactly two files: the .md deliverable named in your work order, and a
  .json sidecar in analysis_out/findings/ holding the structured numbers.

Also read build_profile.py to pin the exact semantics of every field you quote.
Several have subtle meanings: num_digits counts the ADDRESS only, and dig5/dig6
are lookaround-guarded so a digit inside a longer run does not count. A previous
agent found reading the builder necessary and it prevented a wrong conclusion.

Your work order contains an already_checked block describing two earlier
findings that were tested against real data. REFUTED-1 (a claimed France-postcode
loss) is dead - do not re-derive it. REFUTED-2 (the France-region claim) has been
RE-SCOPED, not upheld: the famous "state resolves for 100% of France rows" is a
test_source1-only denominator covering just 15.31% of French rows, and at most
71.10% resolve a state across all three test sources. Do not repeat that figure as
a France-wide rate, and do not assume French geography is settled. If your own
evidence bears on either, say so loudly and show the numbers.

Every number must be traceable to a named profile field, with the arithmetic
shown. If a field you need was not collected, label it a gap - never invent a
plausible figure. A clean "no defect found" is a valid and useful result.

Known good technique: look for exact arithmetic invariants between fields (one
field equalling rows minus another, a histogram summing exactly to the row
count). These surface real previously-unremarked structure.

When done, reply with a 5-line summary: task id, headline, the single most
important number, whether you found any NEW defect, and your deliverable path."""


def role_prompt(task_id: str, agent_id: str) -> str:
    return TEMPLATE.format(agent=agent_id, root=ROOT, task=task_id)


def task_text(task_id: str) -> str:
    return (f"Read AGENT_PROMPT.md, then execute the single work order in "
            f"analysis_out/tasks/{task_id}.json. Respect every constraint in your "
            f"role prompt, especially the RAM limit.")


def all_task_ids() -> list[str]:
    return sorted(
        os.path.splitext(f)[0] for f in os.listdir(TASKS) if f.endswith(".json")
    )


if __name__ == "__main__":
    tid = sys.argv[1] if len(sys.argv) > 1 else "P001"
    print(role_prompt(tid, "a000"))
    ids = all_task_ids()
    print(f"\n# {len(ids)} tasks: {ids[0]} .. {ids[-1]}")
