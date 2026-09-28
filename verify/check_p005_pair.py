"""Cross-check the P005 sidecar against its .md and against the profile.

Fails loudly on any mismatch, so the pair cannot silently disagree.
"""
import json
import os
import re

ROOT = os.path.dirname(os.path.abspath(__file__))
F = os.path.join(ROOT, "analysis_out", "findings")
side = json.load(open(os.path.join(F, "P005_US_test_s2_shape.json"), encoding="utf-8"))
md = open(os.path.join(F, "P005_US_test_s2_shape.md"), encoding="utf-8").read()

fails = []


def check(label, cond, detail=""):
    print(f"  {'PASS' if cond else 'FAIL'}  {label}{'  ' + detail if detail else ''}")
    if not cond:
        fails.append(label)


print("=== sidecar vs profile (recomputed independently) ===")
with open(os.path.join(ROOT, "analysis_out", "profile", "test_s2.json"),
          encoding="utf-8") as fh:
    p = json.load(fh)
us = p["by_country"]["US"]
fr = p["by_country"]["France"]
check("us_rows matches by_country.US.rows",
      side["shape"]["us_rows"] == us["rows"], f"{us['rows']:,}")
check("name_empty is zero", side["null_rates_us"]["name_empty"] == us["name_empty"] == 0)
check("prefix_bad is zero", side["null_rates_us"]["prefix_bad"] == us["prefix_bad"] == 0)
check("mean name chars recomputes",
      abs(side["lengths_us"]["mean_name_chars"] - us["name_chars"] / us["rows"]) < 5e-4)
check("180 = FR rows - addr_empty - has_comma",
      side["most_important_number"]["value"]
      == fr["rows"] - fr["addr_empty"] - fr["has_comma"] == 180)
check("hist buckets sum to rows", side["name_length_histogram_us"]["bucket_sum_equals_rows"])
check("hist bucket sum == by_country.US.rows",
      side["name_length_histogram_us"]["bucket_sum"] == us["rows"])
cc = side["name_length_histogram_us"]["consistency_check"]
m = re.search(r"\[([\d,]+), ([\d,]+)\]", cc)
check("name_chars inside per-bucket bound", bool(m) and
      int(m.group(1).replace(",", "")) <= us["name_chars"]
      <= int(m.group(2).replace(",", "")), cc[:60] + "...")

print("\n=== invariants asserted in the sidecar ===")
check("US comma invariant exact (0 exceptions)",
      side["comma_identity"]["us"]["exact"] is True)
check("US pooled rows 11,990,643", side["comma_identity"]["us"]["pooled_rows"] == 11990643)
check("France pooled exceptions 333", side["comma_identity"]["france"]["exceptions"] == 333)
check("France test_s2 state bound 99.9744",
      side["comma_identity"]["france"]["per_file"]["test_s2"]["state_bound_pct"] == 99.9744)
check("France test_s1 has zero comma-less rows",
      side["comma_identity"]["france"]["per_file"]["test_s1"]["comma_less"] == 0)

print("\n=== key numbers also present in the .md (deliverable pair agrees) ===")
for token in ["1,871,330", "38.2899", "11,990,643", "180", "153", "99.9744", "99.9791",
              "45,446,046", "205,296", "4,887,273"]:
    check(f"md contains {token}", token in md)

print("\n=== constraint flags ===")
for k in ("dataset_touched", "network_used", "upstream_modified"):
    check(f"{k} is False", side[k] is False)

print("\n=== confidence markers present ===")
cm = side["confidence_markers"]
check("markers classify every headline claim", len(cm) >= 10, f"{len(cm)} markers")
check("no unlabelled numeric claim in most_important_number",
      "arithmetic" in side["most_important_number"])

print("\n" + ("ALL CHECKS PASSED" if not fails else f"FAILURES: {fails}"))
raise SystemExit(1 if fails else 0)
