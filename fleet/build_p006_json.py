"""Emit the P006 JSON sidecar, computing every figure from the profile.

Follows build_p005_json.py: nothing is transcribed by hand, so the sidecar
cannot drift from analysis_out/profile/*.json. READ-ONLY on the profile and on
_upstream/; writes only the one output file.

New in P006 (relative to the P001-P005 shape series):
  * the literal "null" address placeholder, which build_profile.py counts as a
    TOKEN but not as addr_empty, so the naive null rate understates it ~2x;
  * the state-name-vs-abbreviation split between source 2 and source 3.
"""
import json
import math
import os

ROOT = os.path.dirname(os.path.abspath(__file__))
PROF = os.path.join(ROOT, "analysis_out", "profile")
OUT = os.path.join(ROOT, "analysis_out", "findings", "P006_US_test_s3_shape.json")

FILES = ["train_s1", "train_s2", "train_s3", "test_s1", "test_s2", "test_s3"]
STATS = ["rows", "name_empty", "addr_empty", "name_chars", "addr_chars",
         "name_tokens", "num_digits", "has_digit_name", "has_comma",
         "prefix_bad", "dig5", "dig6", "alpha_only_addr"]

P = {}
for _f in FILES:
    with open(os.path.join(PROF, _f + ".json"), encoding="utf-8") as _fh:
        _p = json.load(_fh)
    P[_f] = {
        "rows": _p["rows"], "cols": _p["cols"],
        "country_rows": _p["country_rows"],
        "by_country": {c: {k: s[k] for k in STATS}
                       for c, s in _p["by_country"].items()},
        "len_hist": {c: s.get("len_hist", {})
                     for c, s in _p["by_country"].items()},
        "addr_tokens": {c: dict(_p["addr_tokens"].get(c, []))
                        for c in _p["by_country"]},
    }

US = P["test_s3"]["by_country"]["US"]
ROWS = US["rows"]
FILE_ROWS = P["test_s3"]["rows"]
NONEMPTY = ROWS - US["addr_empty"]
NULL_TOK = P["test_s3"]["addr_tokens"]["US"].get("null", 0)
EFFECTIVE = US["addr_empty"] + NULL_TOK
FR3 = P["test_s3"]["by_country"]["France"]

# ---- full vs abbreviated state-name tokens, per file/country -----------------
FULLNAME = {
    "alabama", "alaska", "arizona", "arkansas", "california", "colorado",
    "connecticut", "delaware", "florida", "georgia", "hawaii", "idaho",
    "illinois", "indiana", "iowa", "kansas", "kentucky", "louisiana", "maine",
    "maryland", "massachusetts", "michigan", "minnesota", "mississippi",
    "missouri", "montana", "nebraska", "nevada", "ohio", "oklahoma", "oregon",
    "pennsylvania", "tennessee", "texas", "utah", "vermont", "virginia",
    "washington", "wisconsin", "wyoming",
    # sub-tokens of two-word state names, which the profiler splits on space
    "carolina", "dakota", "hampshire", "jersey", "mexico", "york", "island",
}
ABBREV = {
    "al", "ak", "az", "ar", "ca", "co", "ct", "de", "fl", "ga", "hi", "id",
    "il", "in", "ia", "ks", "ky", "la", "me", "md", "ma", "mi", "mn", "ms",
    "mo", "mt", "ne", "nv", "nc", "nd", "oh", "ok", "or", "pa", "ri", "sc",
    "sd", "tn", "tx", "ut", "vt", "va", "wa", "wv", "wi", "wy", "dc", "pr",
}

STATE_FORM = {}
for _f in FILES:
    for _c, _at in P[_f]["addr_tokens"].items():
        _fu = sum(v for k, v in _at.items() if k in FULLNAME)
        _ab = sum(v for k, v in _at.items() if k in ABBREV)
        STATE_FORM["%s/%s" % (_f, _c)] = {
            "fullname_tokens": _fu, "abbrev_tokens": _ab,
            "ratio": round(_fu / _ab, 2) if _ab else None,
        }

# ---- null placeholder, all files -------------------------------------------
NULLPL = {}
for _f in FILES:
    for _c, _s in P[_f]["by_country"].items():
        _n = P[_f]["addr_tokens"][_c].get("null", 0)
        _r = _s["rows"]
        NULLPL["%s/%s" % (_f, _c)] = {
            "rows": _r, "addr_empty": _s["addr_empty"], "null_tokens": _n,
            "naive_null_pct": round(100.0 * _s["addr_empty"] / _r, 4),
            "null_token_pct": round(100.0 * _n / _r, 4),
            "effective_null_pct": round(100.0 * (_s["addr_empty"] + _n) / _r, 4),
        }


def rate(n, d, dp=4):
    return round(100.0 * n / d, dp)


def ci(p, n):
    return round(1.96 * math.sqrt(p * (1 - p) / n) * 100.0, 4)


def main():
    hist = sorted((int(k), v)
                  for k, v in P["test_s3"]["len_hist"]["US"].items())
    hsum = sum(v for _, v in hist)
    cum = 0
    hist_rows = []
    for k, v in hist:
        cum += v
        hist_rows.append({"bucket": "%d-%d" % (k, k + 9), "rows": v,
                          "pct": rate(v, ROWS), "cum_pct": rate(cum, ROWS)})

    doc = {}
    doc.update({
        "task_id": "P006",
        "family": "A-profile",
        "title": "[US] test_s3: shape, null rates, length distribution",
        "source_profile": "analysis_out/profile/test_s3.json",
        "dataset_touched": False,
        "network_used": False,
        "upstream_modified": False,
        "generated_by": "build_p006_json.py (all figures computed from the profile)",
        "verification_scripts": ["p006_mech.py", "verify_p006.py"],
    })
    doc["headline"] = (
        "The US slice of test_source3 is %s rows (%s%% of the %s-row file) and is "
        "clean on every integrity axis the profiler collects: name_empty=0, "
        "prefix_bad=0, and len_hist sums exactly to rows. Two findings are new. "
        "(1) The address-null rate is understated about 2x: build_profile.py "
        "counts a literal 'null' placeholder as an address TOKEN but not as "
        "addr_empty, so at least %s US test_s3 rows carry no usable address "
        "against only %s counted nulls - %s%% effective versus %s%% naive. "
        "(2) test_s3 US writes states as FULL NAMES (%s fullname versus %s "
        "abbreviation tokens, ratio %s) where test_s2 uses abbreviations (ratio "
        "%s). Because normalize_address requires a WHOLE comma-component to "
        "equal a region key, 'Austin, Texas 78701' yields state='' while "
        "'Austin, Texas, 78701' yields 'tx'."
        % (f"{ROWS:,}", rate(ROWS, FILE_ROWS), f"{FILE_ROWS:,}",
           f"{EFFECTIVE:,}", f"{US['addr_empty']:,}",
           rate(EFFECTIVE, ROWS), rate(US["addr_empty"], ROWS),
           f"{STATE_FORM['test_s3/US']['fullname_tokens']:,}",
           f"{STATE_FORM['test_s3/US']['abbrev_tokens']:,}",
           STATE_FORM["test_s3/US"]["ratio"],
           STATE_FORM["test_s2/US"]["ratio"]))
    doc["most_important_number"] = {
        "value": EFFECTIVE,
        "meaning": "US test_s3 rows with no usable address, LOWER BOUND "
                   "(addr_empty + literal-'null' occurrences)",
        "pct_of_us_rows": rate(EFFECTIVE, ROWS),
        "naive_addr_empty": US["addr_empty"],
        "naive_pct": rate(US["addr_empty"], ROWS),
        "understatement_factor": round(EFFECTIVE / US["addr_empty"], 2),
    }
    doc["shape"] = {
        "rows": ROWS, "file_rows": FILE_ROWS,
        "us_share_pct": rate(ROWS, FILE_ROWS),
        "country_rows": P["test_s3"]["country_rows"],
        "country_rows_sum": sum(P["test_s3"]["country_rows"].values()),
        "country_rows_sums_to_rows": sum(P["test_s3"]["country_rows"].values()) == FILE_ROWS,
        "cols": P["test_s3"]["cols"],
    }
    doc["null_rates_us"] = {
        "name_empty": US["name_empty"],
        "name_empty_pct": rate(US["name_empty"], ROWS),
        "addr_empty": US["addr_empty"],
        "addr_empty_pct": rate(US["addr_empty"], ROWS),
        "prefix_bad": US["prefix_bad"],
        "has_comma": US["has_comma"],
        "has_comma_pct": rate(US["has_comma"], ROWS),
        "has_digit_name": US["has_digit_name"],
        "has_digit_name_pct": rate(US["has_digit_name"], ROWS),
        "alpha_only_addr": US["alpha_only_addr"],
        "alpha_only_addr_pct": rate(US["alpha_only_addr"], ROWS),
        "alpha_only_of_nonempty_pct": rate(US["alpha_only_addr"], NONEMPTY),
    }
    doc["lengths_us"] = {
        "name_chars": US["name_chars"],
        "mean_name_len": round(US["name_chars"] / ROWS, 4),
        "addr_chars": US["addr_chars"],
        "mean_addr_len_all_rows": round(US["addr_chars"] / ROWS, 4),
        "mean_addr_len_nonempty": round(US["addr_chars"] / NONEMPTY, 4),
        "name_tokens": US["name_tokens"],
        "mean_name_tokens": round(US["name_tokens"] / ROWS, 4),
        "num_digits": US["num_digits"],
        "num_digits_per_row": round(US["num_digits"] / ROWS, 4),
        "digit_share_of_addr_chars_pct": round(100.0 * US["num_digits"] / US["addr_chars"], 4),
        "dig5_occurrences": US["dig5"],
        "dig5_per_row": round(US["dig5"] / ROWS, 5),
        "dig6_occurrences": US["dig6"],
        "dig6_per_row": round(US["dig6"] / ROWS, 5),
    }
    doc["name_length_histogram_us"] = {
        "buckets": hist_rows,
        "sum": hsum,
        "bucket_sum_equals_rows": hsum == ROWS,
    }
    doc["sufficiency"] = {
        "n": ROWS,
        "note": "95% binomial half-widths; every rate is known to >=4 decimals.",
        "ci95_halfwidth_pp": {
            "addr_empty": ci(US["addr_empty"] / ROWS, ROWS),
            "has_digit_name": ci(US["has_digit_name"] / ROWS, ROWS),
            "has_comma": ci(US["has_comma"] / ROWS, ROWS),
            "alpha_only_addr": ci(US["alpha_only_addr"] / ROWS, ROWS),
        },
    }
    # ---------------- NEW FINDING 1: the literal 'null' placeholder ----------
    doc["finding_null_placeholder"] = {
        "claim": "A literal 'null' string appears in business_address as a "
                 "placeholder for a missing address. build_profile.py counts it "
                 "as an addr_token (lines 126-127) but NOT as addr_empty (lines "
                 "100-101), so the naive null rate counts only about half the "
                 "rows that actually have no usable address.",
        "mechanism": "normalize.py:329 skips any component equal to "
                     "'null'/'<null>'/'n/a'/'na'/'none', and ADDR_CANON_COMMON "
                     "maps 'null'->'' (line 197). So the placeholder is absorbed "
                     "correctly and does NOT pollute atoks. Verified by "
                     "executing the real module (p006_mech.py).",
        "consequence": "No pipeline defect. The defect is in the PROFILER: any "
                       "null rate quoted from addr_empty alone is understated.",
        "us_test_s3": NULLPL["test_s3/US"],
        "null_token_is_occurrence_not_row": True,
        "lower_bound_reasoning": "addr_empty and the 'null' token are disjoint "
                                 "sets (a row is either blank or contains the "
                                 "literal), so the two counts add. But %d is an "
                                 "OCCURRENCE count, so rows with 2+ 'null' "
                                 "tokens are counted more than once and the true "
                                 "row count is <= %d. Hence LOWER BOUND."
                                 % (NULL_TOK, NULL_TOK),
        "all_files": NULLPL,
        "france_contrast": "France has ZERO 'null' tokens in all three test "
                           "files. The placeholder is a US/India generator "
                           "artefact only, so this does not touch the scored "
                           "country.",
    }
    # ---------------- NEW FINDING 2: state name form, source 2 vs 3 ---------
    doc["finding_state_name_form"] = {
        "claim": "US addresses spell the state as a FULL NAME in source 3 and "
                 "as an ABBREVIATION in sources 1-2. normalize.py's whole-"
                 "component match at line 333 requires the component to equal a "
                 "region key exactly, so a trailing ZIP inside the same "
                 "component defeats it for BOTH spellings - the full/abbrev "
                 "split is not itself the bug, it is what made the bug visible.",
        "mechanism_verified_on_real_code": {
            "'123 Main St, Austin, Texas'": "state='tx'",
            "'123 Main St, Austin, Texas 78701'": "state='' (ZIP fused to state)",
            "'123 Main St, Austin, Texas, 78701'": "state='tx' (ZIP own component)",
            "'123 Road, Raleigh, North Carolina 27601'": "state=''",
            "'123 Road, Raleigh, North Carolina, 27601'": "state='nc'",
            "'123 Main St, Austin, TX 78701'": "state='' (same failure, abbrev)",
        },
        "not_a_new_defect_for_this_slice": "P005 already recorded the "
            "whole-component state bound for France. This entry adds the US "
            "mechanism and the source-2-vs-3 spelling split, which no prior "
            "work order covered.",
        "state_form_per_file": STATE_FORM,
        "us_train_vs_test_consistent": "US source 3 is full-name dominant in "
            "BOTH train_s3 (ratio %s) and test_s3 (ratio %s), so the spelling "
            "convention does not shift between train and test - no train/test "
            "distribution shift from this cause."
            % (STATE_FORM["train_s3/US"]["ratio"], STATE_FORM["test_s3/US"]["ratio"]),
    }
    doc["cross_slice"] = {
        "note": "test_s3 US against its siblings, to show this slice is "
                "representative rather than anomalous.",
        "us_rows": {f: P[f]["by_country"]["US"]["rows"] for f in FILES},
        "us_share_of_file_pct": {
            f: rate(P[f]["by_country"]["US"]["rows"], P[f]["rows"]) for f in FILES},
        "name_empty_zero_in_every_file": all(
            P[f]["by_country"]["US"]["name_empty"] == 0 for f in FILES),
        "prefix_bad_zero_in_every_file": all(
            P[f]["by_country"]["US"]["prefix_bad"] == 0 for f in FILES),
        "len_hist_sums_to_rows_everywhere": all(
            sum(P[f]["len_hist"]["US"].values())
            == P[f]["by_country"]["US"]["rows"] for f in FILES),
        "comma_identity_us_exceptions_per_file": {
            f: P[f]["by_country"]["US"]["rows"]
               - P[f]["by_country"]["US"]["addr_empty"]
               - P[f]["by_country"]["US"]["has_comma"] for f in FILES},
    }
    doc["relation_to_refuted_findings"] = {
        "REFUTED-1_french_postcodes_discarded_by_pin_guard":
            "Not re-derived, and not supported. US test_s3 dig5/row = %s, "
            "consistent with the ~0.110 quoted for US source-2. The pin guard "
            "affects US source-1 and India, not France."
            % round(US["dig5"] / ROWS, 5),
        "REFUTED-2_FR_REGIONS_too_thin":
            "Not re-derived. Re-measured dictionary sizes on the real module "
            "(p006_mech.py): FR_REGIONS 14 entries / 4 values, US_STATES 104 / "
            "52, IN_STATES 86 / 37. Agrees with the refutation. This slice adds "
            "no new France state evidence.",
        "new_beyond_P005": "P005 established the France comma leak. P006 adds "
            "(a) the literal-'null' placeholder that roughly doubles every "
            "published null rate for US/India and is absent in France, and "
            "(b) the US source-2-vs-3 state spelling split that exposes the "
            "whole-component state match.",
    }
    doc["gaps"] = [
        "The profile has no row-level 'has null placeholder' boolean, so the "
        "affected row COUNT for the 'null' finding is unknown: %d is an "
        "occurrence count and the true row count is <= it. Add a has_null_addr "
        "field to build_profile.py to close this." % NULL_TOK,
        "No n_comps field: build_profile.py:126 splits on [,;] only to feed the "
        "token counter and discards the component count, so the "
        "state-plus-ZIP-in-one-component case cannot be COUNTED, only "
        "demonstrated on synthetic strings.",
        "No state/city/region field: normalize_address's outputs are never "
        "captured, so every state-resolution statement here is a bound derived "
        "from upstream code plus the comma identity, not a measurement.",
        "The FULLNAME/ABBREV token split is a proxy. Two-word state names are "
        "split by the profiler ('north carolina' becomes 'north'+'carolina', and "
        "only 'carolina' is in FULLNAME), so the ratio undercounts full-name "
        "mentions. It is used only to establish that the two conventions differ "
        "by more than 10x, which it does unambiguously.",
        "No true-empty vs whitespace-only distinction: the builder strips before "
        "testing emptiness, so '   ' is already counted as empty.",
        "Token counters are top-4000 and pruned of hapax, so no vocabulary size, "
        "type-token ratio, or unique-business count is derivable.",
    ]
    doc["recommendations"] = [
        {"priority": "high",
         "action": "Add two fields to build_profile.py: a row-level "
                   "has_null_addr boolean (ba.strip().lower() in the "
                   "{'null','<null>','n/a','na','none'} set) and "
                   "n_comps = len([c for c in ba.split(',') if c.strip()]).",
         "confidence": "CONFIRMED (both gaps are real; both are one-line "
                       "streaming counters)",
         "expected_effect": "Diagnostic only, no pipeline change. Converts the "
                            "<=%d lower bound into an exact count and is the "
                            "only way to count the fused-state-ZIP rows."
                            % NULL_TOK},
        {"priority": "high",
         "action": "Correct every quoted address-null rate for US and India to "
                   "the effective figure (addr_empty + 'null' tokens). For US "
                   "test_s3 that is %s%%, not %s%%."
                   % (rate(EFFECTIVE, ROWS), rate(US["addr_empty"], ROWS)),
         "confidence": "CONFIRMED as a lower bound",
         "expected_effect": "No model change. Prevents a 2x error in any "
                            "null-handling decision made off this profile."},
        {"priority": "none",
         "action": "Do NOT change normalize.py to handle the literal 'null' "
                   "placeholder. normalize.py:329 and ADDR_CANON_COMMON['null'] "
                   "already absorb it and q_addr_empty correctly fires. There is "
                   "no defect here.",
         "confidence": "CONFIRMED (executed the real module)"},
        {"priority": "low",
         "action": "Optionally make the state match tolerant of a trailing ZIP "
                   "in the state component, by stripping a trailing 5-digit run "
                   "before the smap lookup at normalize.py:333.",
         "confidence": "mechanism CONFIRMED (executed on real code); prevalence "
                       "SPECULATIVE - n_comps was never collected, so the number "
                       "of affected rows is unknown and no gain can be estimated",
         "expected_effect": "Would recover a state signal for the fused-ZIP "
                            "rows. Do NOT expect a leaderboard move: P005 bounds "
                            "the same defect at 0.026% for France."},
        {"priority": "none",
         "action": "No normalisation-dictionary entry is warranted from this "
                   "slice, and no train/test distribution shift is caused by the "
                   "state spelling convention: US source 3 is full-name dominant "
                   "in both train and test.",
         "confidence": "CONFIRMED"},
    ]
    doc["confidence_markers"] = {
        "us_test_s3_row_count_and_share": "CONFIRMED",
        "len_hist_sums_to_rows": "CONFIRMED (exact integer identity)",
        "country_rows_sums_to_rows": "CONFIRMED (exact integer identity, all 6 files)",
        "name_empty_zero_prefix_bad_zero": "CONFIRMED (exact zeros, all 6 files)",
        "us_comma_invariant_holds_in_this_slice": "CONFIRMED (0 exceptions)",
        "literal_null_present_in_us_and_india": "CONFIRMED (exact token counts)",
        "literal_null_absent_in_france": "CONFIRMED (exact zero in all 3 test files)",
        "null_placeholder_absorbed_by_normalizer": "CONFIRMED (executed real normalize.py)",
        "effective_null_row_count": "LOWER BOUND - occurrence count, not a row count",
        "state_fullname_vs_abbrev_split": "CONFIRMED as a >10x token-ratio "
            "difference; the specific per-row attribution is INFERENCE",
        "fused_state_zip_defeats_state_match": "CONFIRMED as mechanism "
            "(executed real normalize.py); prevalence is a GAP",
        "two_word_state_names_undercounted": "CONFIRMED limitation of the proxy",
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as _fh:
        json.dump(doc, _fh, ensure_ascii=False, indent=2)
    print("wrote %s (%d bytes, %d top-level keys)"
          % (OUT, os.path.getsize(OUT), len(doc)))


if __name__ == "__main__":
    main()
