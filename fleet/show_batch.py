"""Print the batch-1 work orders (id, deliverable, title) for dispatch."""
import json

plan = json.load(open("analysis_out/dispatch_plan.json", encoding="utf-8"))
b = plan[0]
print(f"batch {b['batch']}  agents: {b['agents']}\n")
for t in b["tasks"]:
    print(f"{t['id']}  {t['deliverable']}")
    print(f"      {t['title']}")
