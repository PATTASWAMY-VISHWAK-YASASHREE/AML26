"""P006: does normalize_address actually recover `state` for US rows?

The profile shows a format split nobody has looked at. Across the six files the
US address tokens are EITHER state abbreviations ("tx", "il") OR full names
("texas", "illinois"), and the balance flips by SOURCE:

    file       abbr/non-empty   full-name/non-empty
    test_s1         1.0266             0.0289
    test_s2         1.0331             0.0278
    test_s3         0.0817             0.8237

normalize.py:333 only emits a state when a WHOLE comma-component exactly equals
a key:  `ck = " ".join(...); if ck in smap`. A US line is normally
"<street>, <city>, <state> <zip>", so the state component is "texas 78701" - NOT
equal to "texas" - and the lookup fails. That would make `state` empty for most
US rows, making features.py:114 `state_eq = tri(q_state, s_state)` a near-dead
feature like the refuted pin_eq.

This streams test_source3.tsv ONE ROW AT A TIME (never loading the file) and
replicates the real component matching, so the answer is measured, not inferred.
READ-ONLY on the dataset. Memory is O(1) plus small counters.
"""
import ast
import csv
import re
import sys
from collections import Counter

sys.path.insert(0, "_upstream/src")
import normalize as N  # noqa: E402  (imported read-only)

# pull US_STATES from source so the check cannot drift from the dictionary
_src = ast.parse(open("_upstream/src/normalize.py", encoding="utf-8").read())
US_STATES = None
for _node in _src.body:
    if isinstance(_node, ast.Assign) and getattr(_node.targets[0], "id", "") == "US_STATES":
        US_STATES = ast.literal_eval(_node.value)
assert US_STATES, "US_STATES not found"

# normalize.py:252-254 adds a runtime self-map so abbreviations are keys too.
# ast.literal_eval only sees the literal, so replay that loop here or the check
# would under-count resolution by every abbreviated-state row.
for _v in list(US_STATES.values()):
    US_STATES.setdefault(_v, _v)

FULL = {k for k in US_STATES if len(k) > 2}
ABBR = {k for k in US_STATES if len(k) <= 2}
print(f"US_STATES: {len(US_STATES)} keys after the abbreviation self-map "
      f"({len(FULL)} full names, {len(ABBR)} abbreviations)\n")

EMPTYISH = ("null", "<null>", "n/a", "na", "none")


def state_of(addr):
    """Exact replication of normalize.py's state branch (lines 328-335)."""
    found = ""
    for c in addr.lower().split(","):
        c = c.strip()
        if not c or c in EMPTYISH:
            continue
        ck = re.sub(r"[^a-z0-9& ]+", " ", c).replace("&", " and ")
        ck = " ".join(ck.split())
        if ck in US_STATES:
            found = US_STATES[ck]
    return found


def has_state_token(ck):
    """Would a token-level (not component-level) match have found the state?"""
    return ck in FULL or ck in ABBR


PATH = "amazon_ml_2026_research/student_resource/dataset/test/test_source3.tsv"

# Which of the 52 codes actually appear? (46 resolved - which 6 are missing,
# and is the absence real or a vocabulary-pruning artefact?)
seen_codes = set()
n = 0
resolved = 0
recoverable = 0          # component had a state token but exact match failed
truly_absent = 0         # no state token anywhere in the address
by_fmt = Counter()       # which style the LAST component used
state_codes = Counter()
unmatched = Counter()
examples = []
seen_shapes = {}
state_comp_with_digits = 0     # a component containing a state token
state_comp_digits_lost = 0     # ...and yet no state was emitted
zip_bearing_state_comp = 0     # ...and that component also held a digit (ZIP)
city_rows = 0                  # rows contributing >=1 city component

# the six never-emitted codes, plus two controls that DO resolve
PROBES = ["michigan", "hawaii", "mississippi", "new hampshire",
          "new jersey", "puerto rico", "nevada", "florida"]
probe_rows = Counter()
probe_ctx = {p_: [] for p_ in PROBES}

with open(PATH, encoding="utf-8", errors="replace", newline="") as fh:
    rd = csv.reader(fh, delimiter="\t", quoting=csv.QUOTE_NONE)
    next(rd)
    for rec in rd:
        if len(rec) < 4 or rec[3].strip() != "US":
            continue
        n += 1
        addr = rec[2]
        st = state_of(addr)

        # keep a bounded sample of REAL addresses for cross-validation
        # (done for EVERY row, resolved or not, before any `continue`)
        if len(seen_shapes) < 4000:
            key = re.sub(r"\d+", "#", ",".join(
                c.strip() for c in addr.split(",")).lower())
            seen_shapes.setdefault(key, addr)

        if st:
            resolved += 1
            state_codes[st] += 1
        else:
            toks = re.findall(r"[a-z0-9]+", addr.lower())
            hit_tok = [t for t in toks if has_state_token(t)]
            if hit_tok:
                recoverable += 1
                by_fmt["full" if hit_tok[0] in FULL else "abbr"] += 1
            else:
                truly_absent += 1
            if len(examples) < 8 and hit_tok:
                comps = [c.strip() for c in addr.split(",")]
                examples.append((addr, hit_tok, comps[-1] if comps else ""))

        # --- the hypothesis under test: does a ZIP sitting in the SAME
        # comma-component as the state block the exact-match lookup? ---
        for c in addr.lower().split(","):
            c = c.strip()
            if not c or c in EMPTYISH:
                continue
            ck = re.sub(r"[^a-z0-9& ]+", " ", c).replace("&", " and ")
            ck = " ".join(ck.split())
            toks_in = ck.split()
            if any(t in FULL or t in ABBR for t in toks_in):
                state_comp_with_digits += 1
                if not st:
                    state_comp_digits_lost += 1
                if re.search(r"\d", c):
                    zip_bearing_state_comp += 1
                break

        # city signal: components with no digits, as normalize.py:351 collects
        if any(not re.search(r"\d", cc.strip()) and cc.strip()
               and cc.strip() not in EMPTYISH
               for cc in addr.split(",")):
            city_rows += 1

        if len(unmatched) < 4000:
            comps = [c.strip() for c in addr.split(",")]
            if comps:
                unmatched[re.sub(r"\d+", "#", comps[-1].lower())] += 1

        # Why is 'mi' never emitted although "michigan" occurs 1,288 times as a
        # token? Capture the components that actually contain those state names.
        for probe in PROBES:
            if probe in addr.lower():
                probe_rows[probe] += 1
                if len(probe_ctx[probe]) < 6:
                    probe_ctx[probe].append(addr)

print(f"US rows streamed from test_source3.tsv : {n:,}")
print(f"state resolved by normalize.py          : {resolved:,} ({resolved/max(n,1):.4%})")
print(f"  of those, distinct state codes        : {len(state_codes)}")
print(f"NOT resolved, but a state token exists  : {recoverable:,} ({recoverable/max(n,1):.4%})")
print(f"NOT resolved, no state token at all     : {truly_absent:,} ({truly_absent/max(n,1):.4%})")
print(f"\nrecoverable rows by state style         : {dict(by_fmt)}")
print(f"\nstate_eq would be TRUE for {resolved/max(n,1):.4%} of US rows")

print("\n--- ZIP-in-state-component test (the mechanism I hypothesised) ---")
print(f"rows with a component containing a state token : {state_comp_with_digits:,}")
print(f"  of those, ZIP present in that same component: {zip_bearing_state_comp:,}")
print(f"  of those, state was NOT emitted at all       : {state_comp_digits_lost:,}")
print(f"rows contributing >=1 city component          : {city_rows:,} "
      f"({city_rows/max(n,1):.4%})")

ALL_CODES = set(US_STATES.values())
print(f"\ndistinct state codes emitted: {len(state_codes)} of {len(ALL_CODES)} in US_STATES")
print(f"  never emitted: {sorted(ALL_CODES - set(state_codes))}")
print(f"  rarest emitted: {state_codes.most_common()[-6:]}")

print("\n--- why are 6 codes never emitted? substring probe over the raw address ---")
for pr_ in PROBES:
    print(f"  {pr_:<15} appears in {probe_rows[pr_]:>7,} US addresses")
    for a in probe_ctx[pr_][:3]:
        print(f"        e.g. {a!r}")

print("\nsample failures (address | state token found | last comma-component):")
for a, t, last in examples:
    print(f"  {a!r}\n      token={t}  last_comp={last!r}")

print("\nmost common last-component shapes (digits masked):")
for c, k in unmatched.most_common(15):
    print(f"  {k:>9,}  {c!r}")

# Cross-validate: my state_of() must agree with the REAL normalize_address on
# every distinct address shape seen. A disagreement would mean this whole check
# is measuring my reimplementation rather than the shipped code.
print("\ncross-validating state_of() against the real normalize_address ...")
check = list(seen_shapes.items())[:400]
bad = 0
for shape, k in check:
    addr = shape.replace("#", "12345") if "#" in shape else shape
    mine = state_of(addr)
    real = N.normalize_address(addr, "US")[2]
    if mine != real:
        bad += 1
        if bad <= 5:
            print(f"  MISMATCH {addr!r}: mine={mine!r} real={real!r}")
print(f"  checked {len(check)} shapes, {bad} mismatches -> "
      f"{'AGREES with shipped code' if bad == 0 else 'REIMPLEMENTATION IS WRONG'}")


# machine-readable evidence, written last so it can quote the cross-validation
import json as _json

_ev = {
    "file": "test_source3.tsv", "country": "US",
    "us_rows": n,
    "state_resolved": resolved,
    "state_resolved_pct": round(100.0 * resolved / max(n, 1), 4),
    "state_unresolved_but_token_present": recoverable,
    "state_unresolved_no_token": truly_absent,
    "distinct_codes_emitted": len(state_codes),
    "codes_never_emitted": sorted(ALL_CODES - set(state_codes)),
    "rows_with_state_token_component": state_comp_with_digits,
    "rows_zip_in_state_component": zip_bearing_state_comp,
    "rows_state_token_component_but_no_state": state_comp_digits_lost,
    "rows_with_city_component": city_rows,
    "city_pct": round(100.0 * city_rows / max(n, 1), 4),
    "probe_rows": dict(probe_rows),
    "cross_validation_shapes_checked": len(check),
    "cross_validation_mismatches": bad,
    "state_codes_counts": dict(state_codes.most_common()),
}
with open("analysis_out/findings/_p006_state_evidence.json", "w", encoding="utf-8") as _f:
    _json.dump(_ev, _f, ensure_ascii=False, indent=1)
print("\nwrote analysis_out/findings/_p006_state_evidence.json")
