"""Fold the revision-2 measurements into the P006 JSON sidecar.

The .md deliverable was corrected after two claims were refuted against the raw
file. This script makes the structured sidecar agree with it, so the two cannot
contradict each other. It reads the two evidence files produced by the raw scans
and rewrites only the sidecar. READ-ONLY on the profile and on _upstream/.
"""
import json
import os

ROOT = os.path.dirname(os.path.abspath(__file__))
FIND = os.path.join(ROOT, "analysis_out", "findings")
DOC_PATH = os.path.join(FIND, "P006_US_test_s3_shape.json")
NULL_EV = os.path.join(FIND, "_p006_null_evidence.json")
STATE_EV = os.path.join(FIND, "_p006_state_evidence.json")

with open(DOC_PATH, encoding="utf-8") as f:
    DOC = json.load(f)
with open(NULL_EV, encoding="utf-8") as f:
    NEV = json.load(f)
with open(STATE_EV, encoding="utf-8") as f:
    SEV = json.load(f)

DOC["revision"] = 2
DOC["revision_note"] = (
    "Revision 2 retracts two revision-1 claims after measuring the raw file: "
    "(a) the 'null placeholder doubles the null rate' finding is FALSE - 0 rows "
    "have null as the entire address and 100.00% of rows containing a null-ish "
    "component still yield a usable address, so addr_empty is correct as "
    "published; (b) state resolution is now MEASURED at 100.0000% of non-empty "
    "US rows rather than being an open gap, so the trailing-ZIP fix is not "
    "warranted for this slice."
)

# --- retract the null-placeholder finding, replace with the measurement ---
DOC["RETRACTED_finding_null_placeholder"] = {
    "status": "RETRACTED - false",
    "previous_claim": (
        "The literal 'null' leaves a row with no usable address, so the "
        "effective US test_s3 null rate is 5.6470% (addr_empty 55,317 + null "
        "tokens 54,557) rather than the published 2.8430%, and every published "
        "US/India null rate should be restated."
    ),
    "why_it_was_wrong": (
        "The premise - that a 'null' token marks a row whose address is absent "
        "- was never checked. It is always a single COMPONENT of an otherwise "
        "complete address, not the whole address."
    ),
    "measured": {
        "us_rows_scanned": NEV["us_rows"],
        "rows_whole_address_nullish": NEV["whole_address_nullish"],
        "rows_containing_nullish_component": NEV["contains_nullish_component"],
        "of_which_still_yield_nonempty_atoks": NEV["component_null_but_still_usable"],
        "of_which_atoks_empty": NEV["component_null_atoks_empty"],
        "pct_of_nullish_rows_still_usable": round(
            100.0 * NEV["component_null_but_still_usable"]
            / max(NEV["contains_nullish_component"], 1), 4),
    },
    "verdict": (
        "addr_empty = 55,317 (2.8430%) is CORRECT as published. There is no 2x "
        "understatement and no null rate needs restating."
    ),
    "still_true_from_revision_1": [
        "Source 1 has no null placeholder at all (null = 0 in train_s1 and "
        "test_s1 for every country) and both source-1 files have addr_empty = 0.",
        "France has exactly zero null tokens in all three test files, so the "
        "scored country is unaffected.",
        "normalize.py:329 absorbs the placeholder correctly; q_addr_empty fires "
        "only for genuinely blank addresses.",
    ],
    "evidence_script": "check_null_placeholder.py",
    "confidence": "CONFIRMED by measurement over all US rows",
}
DOC.pop("finding_null_placeholder", None)

# --- new measured state finding ---
DOC["finding_state_resolution_measured"] = {
    "status": "NEW in revision 2",
    "headline": (
        f"State resolves for {SEV['state_resolved']:,} of {SEV['us_rows']:,} US "
        f"rows = {SEV['state_resolved_pct']}%, which is 100.0000% of every "
        "non-empty row, with zero exceptions. The trailing-ZIP fragility "
        "demonstrated in revision 1 costs exactly 0 rows here."
    ),
    "us_rows": SEV["us_rows"],
    "state_resolved": SEV["state_resolved"],
    "state_resolved_pct_of_all_rows": SEV["state_resolved_pct"],
    "state_resolved_pct_of_nonempty": 100.0,
    "unresolved_with_state_token_present": SEV["state_unresolved_but_token_present"],
    "unresolved_no_state_token": SEV["state_unresolved_no_token"],
    "rows_with_state_token_component": SEV["rows_with_state_token_component"],
    "rows_zip_in_state_component": SEV["rows_zip_in_state_component"],
    "rows_state_token_component_but_no_state": SEV["rows_state_token_component_but_no_state"],
    "rows_with_city_component": SEV["rows_with_city_component"],
    "city_pct": SEV["city_pct"],
    "distinct_codes_emitted": SEV["distinct_codes_emitted"],
    "codes_never_emitted": SEV["codes_never_emitted"],
    "never_emitted_explanation": {
        "conclusion": (
            "The 6 never-emitted codes are a DATA fact, not a dictionary gap. "
            "These names occur in US addresses only as street names, each paired "
            "with a different real state, so adding them would create keys that "
            "correctly match nothing."
        ),
        "probe_rows": SEV["probe_rows"],
        "michigan_example": "'43 Michigan Ave, Bristol, Connecticut'",
        "hawaii_example": "'Hawaii Ave, Alamogordo, New Mexico'",
    },
    "methodological_note": (
        "A first run of check_us_state.py reported 93.3052% resolution and 1,684 "
        "recoverable rows. That was a BUG in the check, not a finding: US_STATES "
        "was extracted with ast.literal_eval, which misses the runtime "
        "abbreviation self-map added at normalize.py:252-254. Replaying that loop "
        "gave 97.1570% of all rows. Any reimplementation of upstream logic must be "
        "cross-validated against the shipped code; this one was, on 400 real "
        "address shapes with 0 mismatches."
    ),
    "cross_validation": {
        "shapes_checked": SEV["cross_validation_shapes_checked"],
        "mismatches": SEV["cross_validation_mismatches"],
    },
    "evidence_script": "check_us_state.py",
    "confidence": "CONFIRMED (exact integer identity, cross-validated)",
}

# --- revise the affected recommendations ---
DOC["recommendations"] = [
    {"priority": "medium",
     "action": "Add a n_comps field to build_profile.py recording "
               "len([c for c in ba.split(',') if c.strip()]) per row.",
     "confidence": "CONFIRMED (downgraded from high; the has_null_addr half of "
                   "the revision-1 recommendation is withdrawn)",
     "expected_effect": "Pure diagnostic. The only way to answer component-"
                        "structure questions from the profile instead of "
                        "re-streaming a 480 MB file."},
    {"priority": "withdrawn",
     "action": "WITHDRAWN: restate every published US/India null rate as the "
               "effective figure (5.6470% not 2.8430%).",
     "confidence": "CONFIRMED FALSE - premise refuted by measurement",
     "expected_effect": "None. Acting on it would have introduced a 2x error "
                        "into every null-handling decision. addr_empty is correct "
                        "as published."},
    {"priority": "none",
     "action": "Do NOT change normalize.py to handle the literal 'null'. It is "
               "absorbed at line 329 and via ADDR_CANON_COMMON; q_addr_empty "
               "fires correctly.",
     "confidence": "CONFIRMED (real module executed on all 72,639 affected rows)"},
    {"priority": "none",
     "action": "Do NOT add trailing-ZIP tolerance for this slice (downgraded from "
               "low). The mechanism is real but its measured prevalence in US "
               "test_s3 is exactly 0 rows.",
     "confidence": "CONFIRMED for this slice",
     "expected_effect": "None here. Revisit only if a test_s1/test_s2 scan shows "
                        "real losses. No leaderboard move should be expected."},
    {"priority": "none",
     "action": "No normalisation-dictionary entry is warranted. The 6 never-"
               "emitted codes are absent because those names occur only as street "
               "names in this corpus.",
     "confidence": "CONFIRMED by raw-address probe"},
    {"priority": "low",
     "action": "Record the state-spelling convention as a per-source fact AND "
               "record that US state extraction is healthy (100.00% of non-empty "
               "rows), so nobody re-raises it as an open defect.",
     "confidence": "CONFIRMED"},
    {"priority": "low",
     "action": "Re-run check_us_state.py against test_s1 and test_s2 - the one "
               "open question from this work order.",
     "confidence": "harness CONFIRMED; s1/s2 prevalence unmeasured",
     "expected_effect": "Those files use the abbreviation style AND carry ZIPs, "
                        "so they are where a fused state+ZIP component would "
                        "actually appear if it exists anywhere."},
]

DOC["gaps"] = [g for g in DOC.get("gaps", [])
              if "has_null_addr" not in json.dumps(g)]

DOC["confidence_markers"].update({
    "state_resolution_us_test_s3":
        "CONFIRMED (100.0000% of non-empty rows, exact integer identity, "
        "cross-validated against the shipped normalize_address on 400 shapes)",
    "null_placeholder_doubles_null_rate": "RETRACTED - FALSE",
    "addr_empty_us_test_s3_2.8430pct_is_correct": "CONFIRMED (unchanged)",
    "trailing_zip_costs_zero_rows_here": "CONFIRMED (0 of 78,696)",
    "codes_hi_mi_ms_nh_nj_pr_absent_because_street_names":
        "CONFIRMED (raw-address probe; michigan 1,302 rows, all Michigan Ave/St)",
})

with open(DOC_PATH, "w", encoding="utf-8") as f:
    json.dump(DOC, f, ensure_ascii=False, indent=2)

print(f"updated {DOC_PATH}")
print(f"  revision          : {DOC['revision']}")
print(f"  top-level keys    : {len(DOC)}")
print(f"  retracted finding : {DOC['RETRACTED_finding_null_placeholder']['status']}")
print(f"  old finding removed: {'finding_null_placeholder' not in DOC}")
print(f"  recommendations   : {len(DOC['recommendations'])} "
      f"({sum(1 for r in DOC['recommendations'] if r['priority'] == 'withdrawn')} withdrawn)")
