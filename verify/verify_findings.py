import json
L=lambda n: json.load(open("analysis_out/profile/"+n+".json",encoding="utf-8"))
F=lambda n: json.load(open("analysis_out/findings/"+n,encoding="utf-8"))
bad=[]
def ck(lbl,got,exp):
    good=(abs(got-exp)<1e-9) if isinstance(exp,float) else got==exp
    if not good: bad.append((lbl,got,exp))
    print(("  PASS " if good else "  FAIL ")+lbl)

def g(d,*keys):
    """Resolve the first of `keys` present in `d`, else raise naming what was tried.

    The sidecars disagree on field names for the same quantity: under `shape`,
    P006 stores the US row count as `rows` while P001/P003/P004/P005 store it
    as `us_rows`. Accept either rather than hard-coding one, but fail loudly if
    none exists, so a future schema change cannot silently pass.

    Tolerates both call styles:
      g(s, "shape", "rows", "us_rows")   - descend through "shape", then match
      g(s["shape"], "rows", "us_rows")   - already inside "shape"
    """
    keys = list(keys)
    # If the first key names a section, descend into it (no-op when already there).
    if len(keys) > 1 and isinstance(d, dict) and keys[0] in d \
            and isinstance(d[keys[0]], dict):
        d = d[keys[0]]
        keys = keys[1:]
    for k in keys:
        if isinstance(d, dict) and k in d:
            return d[k]
    raise KeyError("none of %s present in keys %s"
                   % (keys, sorted(d) if isinstance(d, dict) else d))


def find_has_comma(s):
    """The sidecars disagree on where has_comma lives; locate it without guessing."""
    for path in (("null_rates_us","has_comma"),("comma_identity","us","has_comma"),
                 ("null_and_integrity_rates","has_comma","count")):
        cur=s
        try:
            for k in path: cur=cur[k]
            return cur
        except (KeyError,TypeError):
            continue
    return None

d2=L("train_s2"); s2=F("P002_US_train_s2_shape.json"); u2=d2["by_country"]["US"]
print("P002 (legacy schema)")
ck(" us_rows", s2["slice"]["us_rows"], u2["rows"])
ck(" file_rows", s2["slice"]["file_rows"], d2["rows"])
ck(" name_empty", s2["null_and_integrity_rates"]["name_empty"]["count"], u2["name_empty"])
ck(" prefix_bad", s2["null_and_integrity_rates"]["prefix_bad"]["count"], u2["prefix_bad"])
ck(" len_hist sum==rows", s2["len_hist"]["sum_equals_rows"], True)
ck(" has_comma", find_has_comma(s2), u2["has_comma"])

for tag,f,src in [("P001","P001_US_train_s1_shape.json","train_s1"),
                  ("P003","P003_US_train_s3_shape.json","train_s3"),
                  ("P004","P004_US_test_s1_shape.json","test_s1"),
                  ("P005","P005_US_test_s2_shape.json","test_s2"),
                  ("P006","P006_US_test_s3_shape.json","test_s3")]:
    d=L(src); s=F(f); u=d["by_country"]["US"]
    print(tag)
    ck(" us_rows", g(s["shape"],"us_rows","rows"), u["rows"])
    ck(" file_rows", s["shape"]["file_rows"], d["rows"])
    ck(" hist==rows", s["name_length_histogram_us"]["bucket_sum_equals_rows"], True)
    ck(" name_empty", s["null_rates_us"]["name_empty"], u["name_empty"])
    ck(" addr_empty", s["null_rates_us"]["addr_empty"], u["addr_empty"])
    ck(" prefix_bad", s["null_rates_us"]["prefix_bad"], u["prefix_bad"])
    ck(" has_comma", find_has_comma(s), u["has_comma"])

# Shares are the one figure that has been transcribed by hand, so re-derive them.
print("shares (md-transcribed figures re-derived from profile)")
for tag,src,md in [("P006","test_s3",{"us":38.2837,"india":47.3209,"france":14.3953})]:
    d=L(src)
    for c,key in (("US","us"),("India","india"),("France","france")):
        ck(" %s %s share" % (tag,c), round(100*d["by_country"][c]["rows"]/d["rows"],4), md[key])
print()

print("P006 revision-2 claims (retraction + raw-scan measurements)")
s6 = F("P006_US_test_s3_shape.json")
d6 = L("test_s3"); u6 = d6["by_country"]["US"]
nev = F("_p006_null_evidence.json")
sev = F("_p006_state_evidence.json")
ck(" revision", s6["revision"], 2)
ck(" retracted flag", s6["RETRACTED_finding_null_placeholder"]["status"],
   "RETRACTED - false")
ck(" old finding removed", "finding_null_placeholder" in s6, False)
# the retraction's own numbers must match the evidence file exactly
ck(" whole-address null rows", nev["whole_address_nullish"], 0)
ck(" null-component rows all still usable",
   nev["component_null_but_still_usable"], nev["contains_nullish_component"])
ck(" null rows with empty atoks", nev["component_null_atoks_empty"], 0)
# the state measurement must match both the evidence file and the profile
ck(" state scan row count", sev["us_rows"], u6["rows"])
ck(" state resolved == non-empty", sev["state_resolved"],
   u6["rows"] - u6["addr_empty"])
ck(" state unresolved == addr_empty", sev["state_unresolved_no_token"],
   u6["addr_empty"])
ck(" state token present but lost", sev["state_unresolved_but_token_present"], 0)
ck(" zip-in-state rows lost", sev["rows_state_token_component_but_no_state"], 0)
ck(" cross-validation clean", sev["cross_validation_mismatches"], 0)
ck(" sidecar state pct agrees", s6["finding_state_resolution_measured"]
   ["state_resolved_pct_of_all_rows"], sev["state_resolved_pct"])
ck(" one recommendation withdrawn",
   sum(1 for r in s6["recommendations"] if r["priority"] == "withdrawn"), 1)

print()
print("ALL PASS - all 6 sidecars reconcile with their profiles" if not bad else "FAILURES: %s"%bad)
