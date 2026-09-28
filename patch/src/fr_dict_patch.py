"""task_0002 - France dictionary patches, applied at import time.

############################################################################
# READ THIS BEFORE USING IT IN THE PIPELINE. IT WILL NOT WORK IN prep.py.  ##
############################################################################
prep.py does `import normalize as N` and then

    with Pool(nproc) as p:
        p.imap(_proc, jobs)

The default start method on Windows is SPAWN, so every worker process re-imports
`prep`, which re-imports a PRISTINE `normalize` from disk. A patch applied only to
the parent process is therefore invisible to all workers.

MEASURED, not assumed -- see patch_upstream/task_0002/check_multiprocessing.py:
    A) real file edit (git apply the .patch)
         parent  : ['12','rue','paix','75001','paris']
         workers : ['12','rue','paix','75001','paris']   -> propagates: True
    B) this module, parent only
         parent  : ['12','rue','paix','75001','paris']
         workers : ['12','rue','de','la','paix', ...]    -> propagates: False
Mechanism B is a SILENT NO-OP: it would burn hours of compute and change nothing.

=> USE `git apply -p1 task0002_fr_function_words.patch` INSTEAD. That module is
   retained only for interactive/one-off use and for A/B measurement inside a
   single process, where `revert()` also exists.
############################################################################

What it changes
---------------
DEFECT 3 (the one that matters) - 14 French function words mapped to "". NOTE the
SHIPPING patch ships only the ZERO-BLOCKING-RISK subset of these 8:
de du des la le et au en. A token only becomes a blocking key if it is len>=3
(keys.py:42) and absent from keys.ADDR_GENERIC (keys.py:39); all 8 fail both, so
make_keys() output is byte-identical before and after. The other 6
(les aux sur chez par sous) are withheld here: they CAN reach blocking and carry
only 0.44% of the removed mass. See task0002_fr_function_words.patch.

What it changes
---------------
DEFECT 3 (applied, the one that matters)
    ADDR_CANON_FR gains 14 French function words mapped to "". `normalize_address`
    already drops a token whose canon value is "" (its `if t: ctoks.append(t)`),
    which is the convention ADDR_CANON_FR already uses for "no"/"n"/"numero".
    Evidence: addr_tokens["France"] occurrence counts, test_s1/s2/s3 --
        de 257,777/381,880/410,366   la 116,064/176,186/188,981
        du  34,709/ 90,693/ 94,953   des 31,485/82,399/85,299
        le   1,992/  4,882/  5,050   les    631/ 1,451/ 1,603
        et     804/  2,030/  2,062   aux     438/ 1,127/ 1,237
        au     250/    668/    686   en      200/    557/    550
        chez   202/    365/    418   sur     127/    298/    314
        par     74/    117/    136   sous     30/     68/     86
    The top six are 737,491 of 4,745,780 listed France test_s2 address-token mass
    = 15.54%, against 0.38% for US and 0.01% for India on the same six words.

DEFECT 2 (applied, behaviour-preserving)
    FR_REGIONS is added to the "abbreviations are canonical themselves" loop so
    "hdf"/"naq"/"pdl"/"idf" map to themselves, as the US and India loops already do.
    Measured effect on this dataset: ZERO -- those four strings never occur as an
    address component. Kept for consistency, not for a measured gain.
    A region <-> department gazetteer is deliberately NOT added: re-deriving the
    bound from the profile puts the whole recoverable set at 6,802 occurrences
    (0.4014% of 1,694,445 France rows), and `normalize_address` CONSUMES a matched
    component, so a new key deletes a department name from `atoks` instead of
    adding signal.

DEFECT 1 (NOT applied)
    The `pin` rule stays `len(n) == 6 and country == "India"`. Measured exposure of
    a French 5-digit rule is dig5 = 8,604 occurrences over 1,694,445 France rows
    = 0.508%, and `pin_eq` is effectively dead in training because India
    dig6/rows is 0.019-0.023% across the three train files while France is never
    trained at all (crossfit.py iterates only ("US","India")).
    If a human decides the US side is worth it anyway, enable_postal_codes()
    below is provided, OFF by default, and it does not touch France.

Every entry is labelled CONFIRMED / NO-EVIDENCE / NO-OP in FR_FUNCTION_WORDS.
"""
import normalize as _N

# token -> CONFIRMED means addr_tokens["France"] shows a non-zero count in all
# three France test files. NO EVIDENCE / NO-OP entries are deliberately skipped.
FR_FUNCTION_WORDS = {
    "de":   "CONFIRMED",   # 1,050,023 occurrences, the largest function word
    "la":   "CONFIRMED",   #   481,231
    "du":   "CONFIRMED",   #   220,355
    "des":  "CONFIRMED",   #   199,183
    "le":   "CONFIRMED",   #    11,924  (profile OVERCOUNTS: it has no
                           #              strip_accents, so "Ile-de-France"
                           #              is profiled as the token "le")
    "les":  "CONFIRMED",   #     3,685
    "et":   "CONFIRMED",   #     4,896
    "aux":  "CONFIRMED",   #     2,802
    "au":   "CONFIRMED",   #     1,604
    "en":   "CONFIRMED",   #     1,307
    "chez": "CONFIRMED",   #       985
    "sur":  "CONFIRMED",   #       739
    "par":  "CONFIRMED",   #       327
    "sous": "CONFIRMED",   #       184
    # Measured 0 occurrences in every France file -> NOT added, per the brief's
    # "do not estimate" rule. Listed so a human can add them on one line.
    "dans":  "NO EVIDENCE (0 occurrences, not added)",
    "avec":  "NO EVIDENCE (0 occurrences, not added)",
    "pour":  "NO EVIDENCE (0 occurrences, not added)",
    "vers":  "NO EVIDENCE (0 occurrences, not added)",
    # Profile shows l=39,967 and d=20,787, but those are PROFILE ARTEFACTS: the
    # profile tokeniser splits on "'" while normalize_address strips apostrophes
    # first, so the pipeline never emits a standalone "l" or "d". No-op to add.
    "l": "NO-OP (profile tokeniser artefact, never emitted by normalize_address)",
    "d": "NO-OP (profile tokeniser artefact, never emitted by normalize_address)",
}

_PATCHED_TOKENS = ("de", "du", "des", "la", "le", "les", "et", "au", "aux", "en",
                   "sur", "chez", "par", "sous")
_applied = False


def apply():
    """Idempotently patch the dictionaries in the already-imported normalize."""
    global _applied
    if _applied:
        return _N
    for tok in _PATCHED_TOKENS:          # DEFECT 3
        _N.ADDR_CANON_FR[tok] = ""
    for v in set(_N.FR_REGIONS.values()):   # DEFECT 2
        _N.FR_REGIONS.setdefault(v, v)
    _applied = True
    return _N


def revert():
    """Undo apply(). Only useful for A/B measurement inside one process."""
    global _applied
    for tok in _PATCHED_TOKENS:
        _N.ADDR_CANON_FR.pop(tok, None)
    for v in set(_N.FR_REGIONS.values()):
        _N.FR_REGIONS.pop(v, None)
    _applied = False
    return _N


# <<PART2>>

def enable_postal_codes(include_us=False, include_france=False):
    """OPT-IN, DEFAULT OFF. Replaces the India-only `pin` rule.

    Per-country rule, with the measured justification for each choice:

      India  6 digits -- UNCHANGED. dig6/rows is 0.019-0.023% in train and
             0.02% in test, i.e. the feature is already near-dead; widening it
             changes nothing measurable.
      US     5 digits -- the only setting with real exposure: dig5 = 492,398
             occurrences over 4,480,137 US rows = 10.99%. US IS a training
             country, so `pin_eq` would be learnable rather than out-of-range.
             RISK, NOT RESOLVED BY THE PROFILE: 89% of US addresses contain
             digits yet have no standalone 5-digit run, so we cannot tell from
             the available fields how many of the 10.99% are ZIPs and how many
             are 5-digit house numbers. Component position is not collected.
             -> a human must decide this; it is off by default.
      France 5 digits -- the defect named in the original brief, deliberately
             left off. Exposure is 8,604 occurrences = 0.508% of France rows,
             and France is never trained (crossfit.py iterates only
             ("US","India")), so a French `pin` would be a feature value the
             model has essentially no training exposure to. The recognised
             France 5-digit tokens in the top-4000 are 59000/59100/59200/59800
             (Nord), 44000/44100/44600/44300 (Loire-Atlantique), 33000
             (Gironde), 62100 (Pas-de-Calais) -- real postcodes, so false
             positives are unlikely, but the upside is only 0.5%.
    """
    import re
    if not (include_us or include_france):
        return _N
    if getattr(_N, "_task0002_pin_patched", False):
        return _N

    def _pin_match(n, country):
        if len(n) == 6 and country == "India":
            return True
        if len(n) == 5 and country == "US" and include_us:
            return True
        if len(n) == 5 and country == "France" and include_france:
            return True
        return False

    def _normalize_address(raw, country):
        # Upstream normalize_address, with ONLY the pin test swapped.
        s = _N.strip_accents(_N.translit_text(raw or "")).lower()
        smap = _N.STATE_MAPS.get(country, {})
        canon = dict(_N.ADDR_CANON_COMMON)
        if country == "France":
            canon = {**{k: v for k, v in _N.ADDR_CANON_COMMON.items()
                        if k not in ("st", "ste", "dr", "n", "s", "e", "w")},
                     **_N.ADDR_CANON_FR}
        comps = [c.strip() for c in s.split(",")]
        state, toks, nums, pin, city_comps = "", [], [], "", []
        for c in comps:
            if not c or c in ("null", "<null>", "n/a", "na", "none"):
                continue
            ck = re.sub(r"[^a-z0-9& ]+", " ", c).replace("&", " and ")
            ck = " ".join(ck.split())
            if ck in smap:
                state = smap[ck]
                continue
            for n in _N.NUM_RE.findall(c):
                if _pin_match(n, country):
                    pin = n
                nums.append(n.lstrip("0") or "0")
            ctoks = []
            for t in _N._non_alnum.split(c.replace("'", "")):
                if not t:
                    continue
                if t.isdigit():
                    t = t.lstrip("0") or "0"
                t = canon.get(t, t)
                if t:
                    ctoks.append(t)
            toks.extend(ctoks)
            if not any(ch.isdigit() for ch in c) and ctoks:
                city_comps.append(" ".join(ctoks))
        return toks, nums, state, pin, city_comps

    _N.normalize_address = _normalize_address
    _N._task0002_pin_patched = True
    return _N


apply()