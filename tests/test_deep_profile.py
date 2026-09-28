"""Regression test for deep_profile's per-row accounting.

A previous revision silently lost the punctuation/case block: the file still
compiled and ran to completion, but name_has_punct / name_has_upper /
name_all_lower were all 0 for every row. Nothing crashed, so nothing complained.
These assertions pin each counter against a hand-computed fixture so that a
clobbered block fails loudly instead of yielding plausible-looking zeros.

Run: & .venv\\Scripts\\python.exe test_deep_profile.py
"""
import csv
import os
import tempfile

import deep_profile as dp

fails = []


def eq(label, got, want):
    if got != want:
        fails.append(f"{label}: got {got!r} want {want!r}")


# fixture rows chosen to exercise every branch at once
ROWS = [
    # id, name, address, country
    ("S1-1", "Orelee's Barbershop", "1795 Westchester Drive, High Point, NC 27260", "US"),
    ("S1-2", "B+ Retail Inc", "1712 Montebello Avenue, Phoenix, AZ", "US"),
    ("S1-3", "\u0930\u093e\u092e \u092e\u093e\u0930\u094d\u0915\u0947\u091f\u093f\u0902\u0917 \u092a\u094d\u0930\u093e\u0907\u0935\u0947\u091f \u0932\u093f\u092e\u093f\u091f\u0947\u0921",
     "KH NO. -570/13, NEW DELHI, Delhi 110058", "India"),
    ("S1-4", "<< Team Ecole", "175 Boulevard du President Roosevelt, Bordeaux", "France"),
    ("S1-5", "   ", "Near SBI ATM, MG Road", "India"),   # whitespace-only name
    ("S1-6", "Solo", "", "US"),                          # empty address
]


def run():
    tmp = os.path.join(dp.SCRATCH, "_fixture.tsv")
    os.makedirs(dp.SCRATCH, exist_ok=True)
    with open(tmp, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, delimiter="\t", quoting=csv.QUOTE_NONE,
                       lineterminator="\n")
        w.writerow(["entity_id", "business_name", "business_address", "country"])
        for r in ROWS:
            w.writerow(list(r))
    out = dp.stream_source(tmp, "fixture", 1)
    os.remove(tmp)
    return out


res = run()
res = run()

# Fixture recap. S1-5 has a WHITESPACE-ONLY name and S1-6 an EMPTY address,
# but both still carry a country, so country row counts are US=3, India=2,
# France=1.
#   S1-1 US     "Orelee's Barbershop"  -> 1 punct char (apostrophe)
#   S1-2 US     "B+ Retail Inc"        -> 1 punct char (plus), legal form 'inc'
#   S1-6 US     "Solo"                 -> uppercase, no punct
#   S1-3 India  Devanagari name        -> no Latin, no case
#   S1-5 India  "   " whitespace-only  -> lands in name_empty, not ws_only
#   S1-4 France "<< Team Ecole"        -> 2 punct chars
us = res["by_country"]["US"]
in_ = res["by_country"]["India"]
fr = res["by_country"]["France"]

eq("total rows", res["rows"], 6)
eq("US rows", us["rows"], 3)
eq("India rows", in_["rows"], 2)
eq("France rows", fr["rows"], 1)

# --- punctuation and case on names (the block that was lost) --------------
eq("US name_has_punct", us["name_has_punct"], 2)        # S1-1, S1-2
eq("US punct_chars_name", us["punct_chars_name"], 2)    # ' and +
eq("US name_has_upper", us["name_has_upper"], 3)        # all three US names
eq("US name_all_lower", us["name_all_lower"], 0)
eq("France name_has_punct", fr["name_has_punct"], 1)
eq("France punct_chars_name", fr["punct_chars_name"], 2)   # '<' twice
eq("US digit_chars_name", us["digit_chars_name"], 0)   # no digits in US names
# Devanagari has no letter case, so neither upper nor lower applies
eq("India name_has_upper", in_["name_has_upper"], 0)
eq("India name_all_lower", in_["name_all_lower"], 0)

# --- whitespace must be COLLAPSED, never deleted -------------------------
# "B+ Retail Inc" has to stay three tokens, not the one token "B+RetailInc".
# This is the regression guard for the token-fusing bug.
# US token counts: "Orelee's Barbershop" -> 3 (the apostrophe splits, since '
#                  is not a \w character), "B+ Retail Inc" -> 3, "Solo" -> 1
eq("US name_tokens", us["name_tokens"], 3 + 3 + 1)
# TOKEN_RE = [^\W_]+ splits on apostrophes, so the Devanagari name yields one
# token per akshara cluster rather than one per space-separated word. That is
# a known property of this tokenizer, asserted here so a change is noticed.
eq("India name_tokens", in_["name_tokens"], 15)
# a whitespace-only name is empty after strip -> name_empty, not name_ws_only
eq("India name_empty", in_["name_empty"], 1)
eq("India name_ws_only", in_["name_ws_only"], 0)
eq("India name_empty_addr_present", in_["name_empty_addr_present"], 1)
eq("US addr_empty", us["addr_empty"], 1)                # S1-6

# --- scripts (section 2) --------------------------------------------------
eq("India no_latin", in_["no_latin_name"], 1)           # only S1-3
eq("India devanagari_only", in_["devanagari_only_name"], 1)
eq("US latin_only", us["latin_only_name"], 3)
eq("France latin_only", fr["latin_only_name"], 1)

# --- postal and address structure (section 6) ----------------------------
eq("US dig5", us["dig5"], 1)                            # 27260
eq("India dig6", in_["dig6"], 1)                        # 110058
eq("France dig5", fr["dig5"], 0)                        # no French postcode
eq("US housenum", us["addr_housenum"], 2)               # 1795..., 1712...
eq("France housenum", fr["addr_housenum"], 1)           # 175 Boulevard
eq("US landmark", us["addr_has_landmark"], 0)
eq("India landmark", in_["addr_has_landmark"], 1)       # "Near SBI ATM"

# --- legal forms and noise tokens (section 3) ----------------------------
eq("US legal_rows", us["legal_rows"], 1)                # "Inc"
eq("US legal_pos_last", us["legal_pos_last"], 1)        # suffix position
eq("France noise_lead_rows", fr["noise_lead_rows"], 1)
# the lead-junk token keeps the collapsed space, so it is "<< " not "<<"
eq("France noise_lead_token", fr["noise_lead"][0][0], "<< ")

# --- exact duplicates (section 9) ----------------------------------------
eq("dup rows_hashed", res["dup_exact_name_addr"]["rows_hashed"], 6)
eq("dup distinct", res["dup_exact_name_addr"]["distinct"], 6)
eq("dup excess", res["dup_exact_name_addr"]["dup_excess"], 0)

if fails:
    print("FAIL")
    for f in fails:
        print("  " + f)
    raise SystemExit(1)
print("all deep_profile accounting tests passed")

