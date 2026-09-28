"""Is the `null` token a WHOLE-ADDRESS placeholder or just one component?

The existing P006 deliverable claims the literal `null` leaves a row with "no
usable address" and adds it to `addr_empty` to get an "effective null rate".
A sample line from my own scan contradicts that reading:

    '9689 Nevada St, NULL, Beaumont, Texas'

Here `null` is ONE component of a four-component address that still carries a
street, a city and a state. If that is the typical shape, the row has a usable
address and the "effective null rate" is overstated.

This streams test_source3.tsv one row at a time and, for every US row, counts:
  - rows whose ENTIRE address (stripped, lowercased) is a null-ish literal
  - rows merely CONTAINING a null-ish component
  - of those, how many still yield a non-empty `atoks` from the real normalizer

READ-ONLY on the dataset. Writes one evidence JSON.
"""
import csv
import json
import re
import sys
from collections import Counter

sys.path.insert(0, "_upstream/src")
import normalize as N  # noqa: E402

NULLISH = ("null", "<null>", "n/a", "na", "none")
PATH = "amazon_ml_2026_research/student_resource/dataset/test/test_source3.tsv"

whole_null = 0        # the entire address is a null-ish literal
comp_null = 0         # some component is a null-ish literal
comp_null_but_usable = 0   # ...and the row still produced real address tokens
both = 0
examples = []
atoks_empty = 0
n = 0
lost_tokens = Counter()

with open(PATH, encoding="utf-8", errors="replace", newline="") as fh:
    rd = csv.reader(fh, delimiter="\t", quoting=csv.QUOTE_NONE)
    next(rd)
    for rec in rd:
        if len(rec) < 4 or rec[3].strip() != "US":
            continue
        n += 1
        ba = rec[2].strip()
        low = ba.lower()
        comps = [c.strip() for c in low.split(",")]
        has_comp = any(c in NULLISH for c in comps)
        is_whole = low in NULLISH
        if is_whole:
            whole_null += 1
        if has_comp:
            comp_null += 1
            if is_whole:
                both += 1
            if len(examples) < 10:
                examples.append(ba)
            # does the row STILL produce a usable address from the real code?
            atoks, anums, st, pin, city = N.normalize_address(ba, "US")
            if not atoks:
                atoks_empty += 1
            else:
                comp_null_but_usable += 1
            if len(lost_tokens) < 4000:
                lost_tokens[re.sub(r"\d+", "#", low)] += 1

print(f"US rows scanned                        : {n:,}")
print(f"rows whose WHOLE address is null-ish   : {whole_null:,} ({whole_null/max(n,1):.4%})")
print(f"rows CONTAINING a null-ish component   : {comp_null:,} ({comp_null/max(n,1):.4%})")
print(f"  of those, whole-address is null-ish  : {both:,}")
print(f"  of those, still yield non-empty atoks: {comp_null_but_usable:,} "
      f"({comp_null_but_usable/max(comp_null,1):.4%})")
print(f"  of those, atoks came back EMPTY      : {atoks_empty:,}")
print("\nsample addresses containing a null-ish component:")
for a in examples:
    print(f"  {a!r}")

ev = {
    "file": "test_source3.tsv", "country": "US", "us_rows": n,
    "whole_address_nullish": whole_null,
    "contains_nullish_component": comp_null,
    "both": both,
    "component_null_but_still_usable": comp_null_but_usable,
    "component_null_atoks_empty": atoks_empty,
    "examples": examples,
}
with open("analysis_out/findings/_p006_null_evidence.json", "w", encoding="utf-8") as f:
    json.dump(ev, f, ensure_ascii=False, indent=1)
print("\nwrote analysis_out/findings/_p006_null_evidence.json")
