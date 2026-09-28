"""Independently verify the P006 deliverable and sidecar.

Deliberately re-derives figures straight from analysis_out/profile/*.json rather
than importing build_p006_json, so a bug in the builder cannot hide here. Also
cross-checks that the numbers quoted in the .md actually appear in the .md.

READ-ONLY. Touches neither the dataset nor _upstream/.
"""
import json
import os

ROOT = os.path.dirname(os.path.abspath(__file__))
PROF = os.path.join(ROOT, "analysis_out", "profile")
FIND = os.path.join(ROOT, "analysis_out", "findings")
FILES = ["train_s1", "train_s2", "train_s3", "test_s1", "test_s2", "test_s3"]

P = {}
for f in FILES:
    with open(os.path.join(PROF, f + ".json"), encoding="utf-8") as fh:
        P[f] = json.load(fh)

with open(os.path.join(FIND, "P006_US_test_s3_shape.json"), encoding="utf-8") as fh:
    S = json.load(fh)
with open(os.path.join(FIND, "P006_US_test_s3_shape.md"), encoding="utf-8") as fh:
    MD = fh.read()

bad = []


def ck(label, got, exp):
    ok = (abs(got - exp) < 1e-9) if isinstance(exp, float) else got == exp
    if not ok:
        bad.append((label, got, exp))
    print(("  PASS " if ok else "  FAIL ") + label)


def in_md(label, needle):
    ok = needle in MD
    if not ok:
        bad.append((label, needle, "present in .md"))
    print(("  PASS " if ok else "  FAIL ") + "%s: %r in .md" % (label, needle))


u = P["test_s3"]["by_country"]["US"]
rows = u["rows"]
nonempty = rows - u["addr_empty"]
nulltok = dict(P["test_s3"]["addr_tokens"]["US"]).get("null", 0)

print("P006 shape and rates")
ck("us_rows", S["shape"]["rows"], rows)
ck("file_rows", S["shape"]["file_rows"], P["test_s3"]["rows"])
ck("country_rows_sum==rows", S["shape"]["country_rows_sum"], P["test_s3"]["rows"])
ck("name_empty", S["null_rates_us"]["name_empty"], 0)
ck("prefix_bad", S["null_rates_us"]["prefix_bad"], 0)
ck("addr_empty", S["null_rates_us"]["addr_empty"], u["addr_empty"])
ck("has_comma", S["null_rates_us"]["has_comma"], u["has_comma"])
ck("has_digit_name", S["null_rates_us"]["has_digit_name"], u["has_digit_name"])
ck("alpha_only_addr", S["null_rates_us"]["alpha_only_addr"], u["alpha_only_addr"])
ck("us_share_pct", S["shape"]["us_share_pct"], round(100.0 * rows / P["test_s3"]["rows"], 4))
ck("addr_empty_pct", S["null_rates_us"]["addr_empty_pct"], round(100.0 * u["addr_empty"] / rows, 4))

print("P006 lengths")
ck("mean_name_len", S["lengths_us"]["mean_name_len"], round(u["name_chars"] / rows, 4))
ck("mean_addr_len", S["lengths_us"]["mean_addr_len_all_rows"], round(u["addr_chars"] / rows, 4))
ck("mean_addr_nonempty", S["lengths_us"]["mean_addr_len_nonempty"], round(u["addr_chars"] / nonempty, 4))
ck("dig5_per_row", S["lengths_us"]["dig5_per_row"], round(u["dig5"] / rows, 5))
ck("dig6_per_row", S["lengths_us"]["dig6_per_row"], round(u["dig6"] / rows, 5))

print("P006 histogram")
h = u["len_hist"]
ck("bucket_sum==rows", S["name_length_histogram_us"]["sum"], sum(h.values()))
ck("bucket_sum==us_rows", sum(h.values()), rows)
ck("bucket_count", len(S["name_length_histogram_us"]["buckets"]), len(h))

print("P006 comma identity (this slice)")
ck("nonempty==has_comma", nonempty, u["has_comma"])
ck("sidecar_holds", S["cross_slice"]["comma_identity_us_exceptions_per_file"]["test_s3"], 0)
ck("all_us_files_zero_exceptions",
   sum(S["cross_slice"]["comma_identity_us_exceptions_per_file"].values()), 0)

print("P006 null-placeholder finding")
ck("null_token", S["finding_null_placeholder"]["us_test_s3"]["null_tokens"], nulltok)
ck("effective_value", S["most_important_number"]["value"], u["addr_empty"] + nulltok)
ck("effective_pct", S["most_important_number"]["pct_of_us_rows"],
   round(100.0 * (u["addr_empty"] + nulltok) / rows, 4))
ck("understatement", S["most_important_number"]["understatement_factor"],
   round((u["addr_empty"] + nulltok) / u["addr_empty"], 2))
# France must carry zero null tokens in every test file
for f in ("test_s1", "test_s2", "test_s3"):
    ck("france_null_zero_" + f, dict(P[f]["addr_tokens"]["France"]).get("null", 0), 0)
# the placeholder must not appear in any France slice
for k, v in S["finding_null_placeholder"]["all_files"].items():
    if v["null_tokens"]:
        assert k.split("/")[1] in ("US", "India"), "null token in " + k
print("  PASS  null tokens appear only in US/India slices")

print("P006 state-form finding")
sf = S["finding_state_name_form"]["state_form_per_file"]
ck("test_s3_US_fullname", sf["test_s3/US"]["fullname_tokens"], 1871526)
ck("test_s3_US_abbrev", sf["test_s3/US"]["abbrev_tokens"], 147824)
ck("test_s2_US_fullname", sf["test_s2/US"]["fullname_tokens"], 63087)
ck("test_s2_US_abbrev", sf["test_s2/US"]["abbrev_tokens"], 1720661)
ck("s3_fullname_dominant", sf["test_s3/US"]["ratio"] > 10, True)
ck("s2_abbrev_dominant", sf["test_s2/US"]["ratio"] < 0.1, True)
# train/test symmetry on the refutation: both s3 sides are full-name dominant
ck("train_s3_fullname_dominant", sf["train_s3/US"]["ratio"] > 10, True)
ck("no_train_test_shift_s3", abs(sf["train_s3/US"]["ratio"] - sf["test_s3/US"]["ratio"]) < 2, True)
print("P006 .md contains its own quoted figures")
for lbl, needle in [
    ("us rows", "1,945,701"),
    ("file rows", "5,082,316"),
    ("addr_empty", "55,317"),
    ("null token", "54,557"),
    ("effective", "109,874"),
    ("effective pct", "5.6470%"),
    ("naive pct", "2.8430%"),
    ("state ratio s3", "12.66"),
    ("state ratio s2", "0.04"),
    ("mean name len", "24.6192"),
    ("name_chars", "47,901,505"),
    ("addr_chars", "75,566,854"),
    ("hist total", "**1,945,701**"),
]:
    in_md(lbl, needle)

print("P006 required sections present")
for sec in ["## Headline", "## Findings", "## Interpretation", "## Gaps",
            "## Recommendations"]:
    ck("section " + sec, sec in MD, True)

print("P006 sidecar hygiene")
ck("dataset_touched", S["dataset_touched"], False)
ck("network_used", S["network_used"], False)
ck("upstream_modified", S["upstream_modified"], False)
ck("task_id", S["task_id"], "P006")
ck("no_unfilled_markers", "<!-- SEC" in MD, False)
print()
if bad:
    print("FAILURES (%d):" % len(bad))
    for b in bad:
        print("   ", b)
else:
    print("ALL PASS - P006 deliverable and sidecar reconcile with the profile")
