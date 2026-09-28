"""Text normalisation for business names and addresses.

Everything here is rule-based or learned from the provided training data only
(the Indic-script -> Latin token dictionary is learned from train ground truth
pairs by `learn_translit.py`).  No external data or services are used.
"""
import json
import os
import re
import unicodedata

import polars as pl

# --------------------------------------------------------------------------
# Indic script handling
# --------------------------------------------------------------------------
INDIC_RE = re.compile(r"[ऀ-ൿ]")
INDIC_TOKEN_RE = re.compile(r"[ऀ-ൿ‌‍]+")

# Rule-based romaniser (fallback for tokens missing from the learned dictionary).
# All Brahmic blocks share the Devanagari layout, so map each code point to its
# Devanagari equivalent (offset within the 0x80 block) and romanise that.
_DEV_CONS = {
    0x15: "k", 0x16: "kh", 0x17: "g", 0x18: "gh", 0x19: "n", 0x1A: "ch", 0x1B: "chh",
    0x1C: "j", 0x1D: "jh", 0x1E: "n", 0x1F: "t", 0x20: "th", 0x21: "d", 0x22: "dh",
    0x23: "n", 0x24: "t", 0x25: "th", 0x26: "d", 0x27: "dh", 0x28: "n", 0x29: "n",
    0x2A: "p", 0x2B: "ph", 0x2C: "b", 0x2D: "bh", 0x2E: "m", 0x2F: "y", 0x30: "r",
    0x31: "r", 0x32: "l", 0x33: "l", 0x34: "zh", 0x35: "v", 0x36: "sh", 0x37: "sh",
    0x38: "s", 0x39: "h", 0x58: "q", 0x59: "kh", 0x5A: "g", 0x5B: "z", 0x5C: "r",
    0x5D: "rh", 0x5E: "f", 0x5F: "y",
}
_DEV_VOW = {0x05: "a", 0x06: "a", 0x07: "i", 0x08: "i", 0x09: "u", 0x0A: "u", 0x0B: "ri",
            0x0D: "e", 0x0E: "e", 0x0F: "e", 0x10: "ai", 0x11: "o", 0x12: "o", 0x13: "o", 0x14: "au"}
_DEV_SIGN = {0x3E: "a", 0x3F: "i", 0x40: "i", 0x41: "u", 0x42: "u", 0x43: "ri", 0x45: "e",
             0x46: "e", 0x47: "e", 0x48: "ai", 0x49: "o", 0x4A: "o", 0x4B: "o", 0x4C: "au",
             0x57: "au", 0x62: "l", 0x63: "l"}
_MAL_CHILLU = {0x0D7A: "n", 0x0D7B: "n", 0x0D7C: "r", 0x0D7D: "l", 0x0D7E: "l", 0x0D7F: "k"}


def romanize(tok: str) -> str:
    out = []
    pending = False  # consonant waiting for vowel
    for ch in tok:
        cp = ord(ch)
        if cp in _MAL_CHILLU:
            if pending:
                out.append("a")
            out.append(_MAL_CHILLU[cp]); pending = False; continue
        if not (0x0900 <= cp <= 0x0D7F):
            continue
        off = (cp - 0x0900) % 0x80
        if off == 0x3C:  # nukta
            continue
        if off in _DEV_CONS:
            if pending:
                out.append("a")
            out.append(_DEV_CONS[off]); pending = True
        elif off in _DEV_SIGN:
            out.append(_DEV_SIGN[off]); pending = False
        elif off == 0x4D:  # virama
            pending = False
        elif off in _DEV_VOW:
            if pending:
                out.append("a")
            out.append(_DEV_VOW[off]); pending = False
        elif off in (0x01, 0x02):  # candrabindu / anusvara
            if pending:
                out.append("a"); pending = False
            out.append("n")
        elif off == 0x03:
            if pending:
                out.append("a"); pending = False
            out.append("h")
    # schwa deletion at word end (pending consonant => no trailing 'a')
    return "".join(out)


_DICT = None


def _load_dict():
    global _DICT
    if _DICT is None:
        p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "resources", "indic_token_dict.json")
        _DICT = json.load(open(p, encoding="utf-8")) if os.path.exists(p) else {}
    return _DICT


def translit_text(s: str) -> str:
    """Replace every Indic-script token by its Latin equivalent."""
    if not s or not INDIC_RE.search(s):
        return s
    d = _load_dict()

    def rep(m):
        t = m.group(0).replace("‌", "").replace("‍", "")
        if t in d:
            return d[t]
        t2 = m.group(0)
        if t2 in d:
            return d[t2]
        return romanize(t)
    return INDIC_TOKEN_RE.sub(rep, s)


# --------------------------------------------------------------------------
# Canonical token maps
# --------------------------------------------------------------------------
NAME_CANON = {
    "private": "pvt", "pvt": "pvt", "prv": "pvt", "pte": "pvt", "priv": "pvt",
    "limited": "ltd", "ltd": "ltd", "ltda": "ltd", "lt": "ltd",
    "corporation": "corp", "corp": "corp", "corpn": "corp", "corporate": "corp",
    "incorporated": "inc", "inc": "inc", "incorporation": "inc",
    "company": "co", "co": "co", "cos": "co", "compagnie": "co", "cie": "co",
    "llc": "llc", "llp": "llp", "lp": "lp", "plc": "plc", "pc": "pc", "pllc": "pllc",
    "international": "intl", "intl": "intl", "internationale": "intl",
    "manufacturing": "mfg", "mfg": "mfg",
    "associates": "assoc", "assoc": "assoc", "associate": "assoc", "assocs": "assoc",
    "brothers": "bros", "bros": "bros",
    "group": "group", "grp": "group", "groupe": "group",
    "holdings": "holdings", "hldgs": "holdings", "holding": "holdings",
    "management": "mgmt", "mgmt": "mgmt", "mgt": "mgmt",
    "national": "natl", "natl": "natl",
    "center": "center", "centre": "center", "ctr": "center", "cntr": "center",
    "services": "services", "svcs": "services", "service": "services", "svc": "services",
    "technologies": "technologies", "technology": "technologies", "tech": "technologies",
    "industries": "industries", "inds": "industries", "industry": "industries",
    "enterprises": "enterprises", "ent": "enterprises", "enterprise": "enterprises",
    "solutions": "solutions", "soln": "solutions", "solution": "solutions",
    "university": "univ", "univ": "univ",
    "saint": "saint", "st": "saint", "ste": "sainte", "sainte": "sainte",
    "sri": "shree", "sree": "shree", "shri": "shree", "shree": "shree", "shrí": "shree",
    "jai": "jai", "jay": "jai", "jaya": "jai",
    "lakshmi": "laxmi", "laxmi": "laxmi", "laksmi": "laxmi",
    "shiv": "shiva", "shiva": "shiva",
    "sarl": "sarl", "sas": "sas", "sasu": "sasu", "eurl": "eurl", "sa": "sa", "ei": "ei",
    "sci": "sci", "snc": "snc", "scop": "scop", "selarl": "selarl", "scm": "scm",
    "and": "and", "et": "and", "und": "and",
    "the": "the", "of": "of", "le": "le", "la": "la", "les": "les", "de": "de", "du": "du", "des": "des",
    "dds": "dds", "md": "md", "cpa": "cpa", "pa": "pa",
    "opc": "opc",
}
# tokens that carry (almost) no identity -> removed from the "core" name
NAME_STOP = {
    "pvt", "ltd", "corp", "inc", "co", "llc", "llp", "lp", "plc", "pc", "pllc", "the", "and",
    "of", "sarl", "sas", "sasu", "eurl", "sa", "ei", "sci", "snc", "scop", "selarl", "scm",
    "opc", "le", "la", "les", "de", "du", "des", "d", "l", "a", "an", "dba", "aka", "fka",
    "et", "fils", "null", "na", "none",
}
LEGAL = {"pvt", "ltd", "corp", "inc", "co", "llc", "llp", "lp", "plc", "pc", "pllc", "sarl",
         "sas", "sasu", "eurl", "sa", "ei", "sci", "snc", "scop", "selarl", "opc"}

ADDR_CANON_COMMON = {
    "street": "st", "st": "st", "str": "st", "strt": "st",
    "road": "rd", "rd": "rd",
    "avenue": "ave", "ave": "ave", "av": "ave", "aven": "ave", "avn": "ave",
    "drive": "dr", "dr": "dr", "drv": "dr",
    "boulevard": "blvd", "blvd": "blvd", "boul": "blvd", "bd": "blvd", "bvd": "blvd",
    "lane": "ln", "ln": "ln",
    "court": "ct", "ct": "ct", "crt": "ct",
    "place": "pl", "pl": "pl", "plc": "pl",
    "square": "sq", "sq": "sq",
    "highway": "hwy", "hwy": "hwy", "hiway": "hwy",
    "parkway": "pkwy", "pkwy": "pkwy", "pky": "pkwy",
    "circle": "cir", "cir": "cir", "circ": "cir",
    "terrace": "ter", "ter": "ter", "terr": "ter",
    "trail": "trl", "trl": "trl",
    "point": "pt", "pt": "pt",
    "mount": "mt", "mt": "mt", "mountain": "mtn", "mtn": "mtn",
    "fort": "ft", "ft": "ft",
    "north": "n", "n": "n", "south": "s", "s": "s", "so": "s", "east": "e", "e": "e",
    "west": "w", "w": "w", "northeast": "ne", "ne": "ne", "northwest": "nw", "nw": "nw",
    "southeast": "se", "se": "se", "southwest": "sw", "sw": "sw",
    "suite": "ste", "ste": "ste", "apartment": "apt", "apt": "apt", "floor": "fl", "fl": "fl",
    "flr": "fl", "building": "bldg", "bldg": "bldg", "bld": "bldg", "unit": "unit",
    "way": "way", "wy": "way", "expressway": "expy", "expy": "expy", "freeway": "fwy",
    "fwy": "fwy", "route": "rte", "rte": "rte", "rt": "rte", "plaza": "plz", "plz": "plz",
    "center": "ctr", "centre": "ctr", "ctr": "ctr", "heights": "hts", "hts": "hts",
    "junction": "jct", "jct": "jct", "crossing": "xing", "xing": "xing",
    "near": "near", "nr": "near", "opp": "opposite", "opposite": "opposite",
    "cross": "cross", "main": "main", "nagar": "nagar", "ngr": "nagar",
    "sector": "sector", "sec": "sector", "phase": "phase", "ph": "phase",
    "ground": "ground", "grd": "ground", "gf": "ground",
    "first": "1st", "second": "2nd", "third": "3rd", "fourth": "4th", "fifth": "5th",
    "apartments": "apts", "apts": "apts", "complex": "complex", "cmplx": "complex",
    "industrial": "indl", "indl": "indl", "estate": "estate", "est": "estate",
    "colony": "colony", "col": "colony", "post": "po", "po": "po", "box": "box",
    "district": "dist", "dist": "dist", "dt": "dist", "taluk": "taluk", "tq": "taluk",
    "village": "vill", "vill": "vill", "vil": "vill", "city": "city",
    "bengaluru": "bangalore", "bangalore": "bangalore", "bombay": "mumbai", "mumbai": "mumbai",
    "gurugram": "gurgaon", "gurgaon": "gurgaon", "trivandrum": "thiruvananthapuram",
    "calcutta": "kolkata", "madras": "chennai", "poona": "pune", "odisha": "orissa",
    "keralam": "kerala", "ahmadabad": "ahmedabad", "vishakhapatnam": "visakhapatnam",
    "vizag": "visakhapatnam", "mysuru": "mysore", "mangaluru": "mangalore", "cochin": "kochi",
    "belagavi": "belgaum", "kozhikode": "calicut", "calicut": "calicut",
    "number": "", "no": "", "nos": "", "num": "", "h": "", "hno": "", "house": "", "door": "",
    "plot": "", "flat": "", "shop": "", "null": "", "na": "", "none": "", "nil": "",
}
ADDR_CANON_FR = {
    "rue": "rue", "r": "rue", "avenue": "ave", "av": "ave", "ave": "ave", "avn": "ave",
    "boulevard": "blvd", "bd": "blvd", "bld": "blvd", "blvd": "blvd", "boul": "blvd",
    "chemin": "chemin", "ch": "chemin", "chem": "chemin", "che": "chemin",
    "impasse": "impasse", "imp": "impasse", "place": "pl", "pl": "pl",
    "route": "rte", "rte": "rte", "allee": "allee", "all": "allee", "al": "allee",
    "square": "sq", "sq": "sq", "faubourg": "fbg", "fbg": "fbg", "fg": "fbg",
    "cours": "crs", "crs": "crs", "quai": "quai", "q": "quai", "qu": "quai",
    "saint": "saint", "st": "saint", "sainte": "sainte", "ste": "sainte",
    "general": "gen", "gen": "gen", "gal": "gen", "docteur": "dr", "dr": "dr",
    "professeur": "prof", "prof": "prof", "marechal": "mal", "mal": "mal",
    "president": "pres", "pres": "pres", "residence": "res", "res": "res",
    "batiment": "bat", "bat": "bat", "bis": "bis", "b": "bis", "ter": "ter", "t": "ter",
    "lieu": "lieu", "lieudit": "lieudit", "zone": "zone", "za": "za", "zi": "zi", "zac": "zac",
    "no": "", "n": "", "numero": "", "null": "", "na": "",
    # ---------------------------------------------------------------------
    # task_0002 / DEFECT 3 - French function words -> dropped.
    #
    # WHY: `_name_tokens` strips French function words from the NAME core via
    # NAME_STOP (normalize.py:147: le/la/les/de/du/des), but the ADDRESS path had
    # no equivalent, so these tokens survive into `atoks` and dilute every French
    # address feature. Mapping a token to "" removes it (normalize.py:348-349,
    # `if t: ctoks.append(t)`), which is the same convention this dict already
    # uses for "no"/"n"/"numero"/"null"/"na" on the line above.
    #
    # MEASURED, from addr_tokens["France"], occurrences (s1 / s2 / s3, test):
    #     de   257,777 / 381,880 / 410,366   = 1,050,023   CONFIRMED
    #     la   116,064 / 176,186 / 188,981   =   481,231   CONFIRMED
    #     du    34,709 /  90,693 /  94,953   =   220,355   CONFIRMED
    #     des   31,485 /  82,399 /  85,299   =   199,183   CONFIRMED
    #     le     1,992 /   4,882 /   5,050   =    11,924   CONFIRMED (see caveat)
    #     les      631 /   1,451 /   1,603   =     3,685   CONFIRMED
    #     et      804 /   2,030 /   2,062   =     4,896   CONFIRMED
    #     aux     438 /   1,127 /   1,237   =     2,802   CONFIRMED
    #     au      250 /     668 /     686   =     1,604   CONFIRMED
    #     en      200 /     557 /     550   =     1,307   CONFIRMED
    #     chez    202 /     365 /     418   =       985   CONFIRMED
    #     sur     127 /     298 /     314   =       739   CONFIRMED
    #     par      74 /     117 /     136   =       327   CONFIRMED
    #     sous     30 /      68 /      86   =       184   CONFIRMED
    # Top six (de/la/du/des/le/les) = 737,491 of the 4,745,780 listed France
    # test_s2 address-token mass = 15.54%.  US on the same six words is 0.38%
    # and India 0.01% -- this is a France-shaped problem, not a generic one.
    #
    # `le` CAVEAT (stated, not smoothed over): the profile tokeniser
    # (build_profile.py:28) has NO strip_accents, so "Ile-de-France" is profiled
    # as the token "le". The pipeline does strip accents, so it sees "ile" --
    # and the component "ile de france" is an FR_REGIONS key and is consumed
    # whole at normalize.py:333-335. The profile therefore OVERCOUNTS "le".
    # It is still a real French article, so the entry is kept.
    #
    # `d` and `l` DELIBERATELY ABSENT. The profile shows 20,787 and 39,967
    # occurrences in test_s2, but those are a PROFILE ARTEFACT: the profile
    # tokeniser splits on "'", so "d'Italie" -> ["d","italie"], while
    # normalize_address strips apostrophes first (normalize.py:342,
    # `c.replace("'","")`) and never emits a standalone "d" or "l". Adding
    # them would be a no-op. Recorded as a known tokeniser divergence.
    #
    # "dans", "avec", "pour", "vers" measure 0 occurrences in every France
    # file, so they are NOT added here: no evidence, and the brief says do not
    # estimate. See task_0002/TASK_0002_FR_DICTIONARY_PATCHES.md.
    #
    # REACH (why this matters): every one of these reaches fuzz a_* on raw atoks
    # (features.py:83-86), a_len/a_inter/a_jac/a_cont (features.py:112-124),
    # the IDF-weighted wa_* (features.py:129, idf built at build_features.py:26
    # via token_idf(frames,"atoks")) and city_tset/city_last via acity
    # (features.py:88-90). Known cost: "les"/"aux"/"sur"/"par"/"sous"/"chez"
    # are len>=3 and not in keys.ADDR_GENERIC, so they were the only function
    # words reaching the blocking keys at keys.py:42; removing them drops some
    # non-selective kind-2 keys (which keys.py:23 CAPS=30 would drop as
    # non-selective anyway). [INFERENCE - not measured, no per-key frequency
    # in the profile.]
    "de": "", "du": "", "des": "", "la": "", "le": "", "les": "",
    "et": "", "au": "", "aux": "", "en": "", "sur": "", "chez": "", "par": "", "sous": "",
}

US_STATES = {
    "alabama": "al", "alaska": "ak", "arizona": "az", "arkansas": "ar", "california": "ca",
    "colorado": "co", "connecticut": "ct", "delaware": "de", "district of columbia": "dc",
    "florida": "fl", "georgia": "ga", "hawaii": "hi", "idaho": "id", "illinois": "il",
    "indiana": "in", "iowa": "ia", "kansas": "ks", "kentucky": "ky", "louisiana": "la",
    "maine": "me", "maryland": "md", "massachusetts": "ma", "michigan": "mi", "minnesota": "mn",
    "mississippi": "ms", "missouri": "mo", "montana": "mt", "nebraska": "ne", "nevada": "nv",
    "new hampshire": "nh", "new jersey": "nj", "new mexico": "nm", "new york": "ny",
    "north carolina": "nc", "north dakota": "nd", "ohio": "oh", "oklahoma": "ok", "oregon": "or",
    "pennsylvania": "pa", "rhode island": "ri", "south carolina": "sc", "south dakota": "sd",
    "tennessee": "tn", "texas": "tx", "utah": "ut", "vermont": "vt", "virginia": "va",
    "washington": "wa", "west virginia": "wv", "wisconsin": "wi", "wyoming": "wy",
    "puerto rico": "pr",
}
IN_STATES = {
    "andhra pradesh": "ap", "arunachal pradesh": "ar", "assam": "as", "bihar": "br",
    "chhattisgarh": "cg", "chattisgarh": "cg", "goa": "ga", "gujarat": "gj", "haryana": "hr",
    "himachal pradesh": "hp", "jharkhand": "jh", "karnataka": "ka", "kerala": "kl",
    "keralam": "kl", "madhya pradesh": "mp", "maharashtra": "mh", "manipur": "mn",
    "meghalaya": "ml", "mizoram": "mz", "nagaland": "nl", "orissa": "od", "odisha": "od",
    "or": "od", "punjab": "pb", "rajasthan": "rj", "sikkim": "sk", "tamil nadu": "tn",
    "tamilnadu": "tn", "telangana": "tg", "ts": "tg", "tripura": "tr", "uttar pradesh": "up",
    "uttarakhand": "uk", "uttaranchal": "uk", "ut": "uk", "west bengal": "wb", "delhi": "dl",
    "new delhi": "dl", "nct of delhi": "dl", "jammu and kashmir": "jk", "jammu & kashmir": "jk",
    "chandigarh": "ch", "puducherry": "py", "pondicherry": "py", "dadra and nagar haveli": "dn",
    "daman and diu": "dd", "ladakh": "la", "lakshadweep": "ld", "andaman and nicobar islands": "an",
}
FR_REGIONS = {
    "hauts de france": "hdf", "nord": "hdf", "pas de calais": "hdf", "somme": "hdf",
    "aisne": "hdf", "oise": "hdf",
    "nouvelle aquitaine": "naq", "gironde": "naq", "landes": "naq",
    "pays de la loire": "pdl", "loire atlantique": "pdl", "vendee": "pdl",
    "ile de france": "idf", "paris": "idf",
}
STATE_MAPS = {"US": US_STATES, "India": IN_STATES, "France": FR_REGIONS}
# abbreviations are canonical themselves
#
# task_0002 / DEFECT 2 (the only part of DEFECT 2 that is patched):
# FR_REGIONS was missing from this loop. Adding it is a pure CONSISTENCY fix --
# it registers "hdf","naq","pdl","idf" as keys that map to themselves, exactly
# as the US and India loops already do for "ca","ny","mh","ap" etc.
#
# MEASURED EFFECT ON THIS DATASET: ZERO. The four canonical values do not occur
# as address components in any France slice, so the new keys never fire. D116
# reaches the same conclusion. The patch is kept because it is provably
# behaviour-preserving on the measured data and removes a real asymmetry, not
# because it fixes a measured loss.
#
# WHAT IS DELIBERATELY NOT PATCHED HERE: a region <-> department gazetteer.
# task_0002 re-derived the coverage bound from scratch (see
# task_0002/analyze_task0002.py sections D and D2) and CONFIRMS the refutation:
# only 13 department/region names beyond the current 14 keys appear in the
# France top-4000 at all, and excluding the polysemous token "loire" they sum
# to 6,802 occurrences across all three test files = 0.4014% of the 1,694,445
# France test rows. D116 independently measured 8,400 rows / 0.496%. Two
# methods, same order of magnitude: the recoverable set is a rounding error.
# And normalize.py:333-335 CONSUMES a matched component (`continue`), so adding
# a key DELETES that department name from `atoks` -- it removes signal from the
# IDF-weighted feature at features.py:129 rather than adding any.
for _m in (US_STATES, IN_STATES, FR_REGIONS):
    for _v in list(_m.values()):
        _m.setdefault(_v, _v)

LEET = str.maketrans({"0": "o", "1": "l", "3": "e", "4": "a", "5": "s", "6": "g", "7": "t", "8": "b", "@": "a", "$": "s"})

# Ordinal / unit guard for LEET.
#
# DEFECT: `_name_tokens` applies LEET to any token containing both a letter and a
# digit (normalize.py:279-280). Any token of that shape gets its digits rewritten,
# which destroys three measured classes of legitimate token:
#
#   D1  French ordinals   3eme -> eeme  (1,111 occurrences)
#   N1  24-hour notation  24hr -> 2ahr  (3,657) - the 2nd-largest mixed type in
#       the whole dataset, and the single largest corruption
#   N2  English ordinals  1st  -> lst   (1,060)
#
# Total 5,828 corrupted occurrences. These are not leetspeak: "3eme" means third,
# "24hr" means twenty-four hours. The mangled tokens then enter the IDF-weighted
# similarity features and corrupt the match signal.
#
# A French-suffix-only guard fixes 1,111 of 5,828 (19.1%) and leaves the largest
# defect untouched. N1 and N2 are US and India defects, so country-scoping would
# not help either - and country is not even in scope here (see below).
#
# THE FIX BELONGS AT THE CALL SITE, NOT IN THE TABLE. `LEET` is a `str.maketrans`
# character->character map, so it structurally cannot express "skip this token" -
# the decision needs the whole token. Confirmed by D087.
#
# NOT COUNTRY-SCOPED, deliberately: `normalize_name` has no `country` parameter
# (normalize.py:285), so a country check is unavailable at this call site. A shape
# guard is also the right shape, since an ordinal is an ordinal in any language.
#
# The guard EXEMPTS rather than extends: 170,314 of 176,142 observed mixed
# occurrences (96.7%) are correct leet expansions and must stay untouched.
# `c1ub`->`club` and `mais0n`->`maison` are the named regression cases.
#
# TOKEN-ANCHORED (`^...$`) on purpose. A substring guard would wrongly swallow
# `b3er`, `p1er` and `x1st`, silently disabling genuine leetspeak. Every LEET key
# is load-bearing: deleting `1` to save `1st` would also break `de1hi`, `denta1`
# and `techno1ogies`; deleting `4` to save `24hr` would break `4l`.
_ORDINAL_RE = re.compile(r"^\d+(?:er|ere|eme|e)$")      # French: 3eme, 1er, 3e
_EN_ORDINAL_RE = re.compile(r"^\d+(?:st|nd|rd|th)$")     # English: 1st, 2nd, 3rd
_HOURS_RE = re.compile(r"^\d+hr$")                      # 24hr, 7hr
_LEET_GUARD_RE = re.compile(
    r"^(?:\d+(?:er|ere|eme|e)|\d+(?:st|nd|rd|th)|\d+hr)$"
)

DBA_RE = re.compile(
    r"\s+(?:doing business as|d\s*/\s*b\s*/\s*a|d\.b\.a\.?|dba|t\s*/\s*a|trading as|a\s*/\s*k\s*/\s*a|aka|"
    r"f\s*/\s*k\s*/\s*a|fka|formerly known as|formerly)\s*:?\s+", re.I)
DOMAIN_RE = re.compile(r"(?:https?://)?(?:www\.)?([a-z0-9][a-z0-9\-]*)\.(?:co\.in|com|net|org|in|fr|co|biz|info|us|io)\b", re.I)


def strip_accents(s: str) -> str:
    s = unicodedata.normalize("NFKD", s)
    return "".join(c for c in s if not unicodedata.combining(c))


_non_alnum = re.compile(r"[^a-z0-9]+")


def _name_tokens(s: str):
    s = s.lower().replace("&", " and ").replace("+", " and ").replace("'", "").replace("’", "")
    s = s.replace(".", "")
    toks = []
    for t in _non_alnum.split(s):
        if not t:
            continue
        if (any(c.isalpha() for c in t) and any(c.isdigit() for c in t)
                and not _LEET_GUARD_RE.match(t)):
            t = t.translate(LEET)
        toks.append(NAME_CANON.get(t, t))
    return toks


def normalize_name(raw: str):
    """Return (full_tokens, core_tokens, alt_core_tokens, flags)."""
    s = translit_text(raw or "")
    s = strip_accents(s)
    is_domain = 0
    doms = DOMAIN_RE.findall(s)
    if doms:
        is_domain = 1
        # remove the domain part(s) from the string, but keep the label as a token
        s2 = DOMAIN_RE.sub(" ", s).replace("|", " ").strip()
        label = doms[0]
        s = (s2 + " " + label) if s2 else label
    s = s.replace("|", " ")
    s = re.sub(r"^\W+", "", s)
    parts = DBA_RE.split(s)
    is_dba = int(len(parts) > 1)
    if is_dba:
        main, alt = parts[-1], parts[0]
    else:
        main, alt = s, ""
    full = _name_tokens(main)
    core = [t for t in full if t not in NAME_STOP]
    alt_core = [t for t in _name_tokens(alt) if t not in NAME_STOP] if alt else []
    return full, core, alt_core, is_domain, is_dba


NUM_RE = re.compile(r"\d+")


def normalize_address(raw: str, country: str):
    """Return dict with tokens (no state), numbers, state code, pin, comps."""
    s = translit_text(raw or "")
    s = strip_accents(s).lower()
    smap = STATE_MAPS.get(country, {})
    canon = dict(ADDR_CANON_COMMON)
    if country == "France":
        canon = {**{k: v for k, v in ADDR_CANON_COMMON.items() if k not in ("st", "ste", "dr", "n", "s", "e", "w")}, **ADDR_CANON_FR}
    comps = [c.strip() for c in s.split(",")]
    state = ""
    toks = []
    nums = []
    pin = ""
    city_comps = []
    for c in comps:
        if not c or c in ("null", "<null>", "n/a", "na", "none"):
            continue
        ck = re.sub(r"[^a-z0-9& ]+", " ", c).replace("&", " and ")
        ck = " ".join(ck.split())
        if ck in smap:
            state = smap[ck]
            continue
        for n in NUM_RE.findall(c):
            if len(n) == 6 and country == "India":
                pin = n
            n2 = n.lstrip("0") or "0"
            nums.append(n2)
        ctoks = []
        for t in _non_alnum.split(c.replace("'", "")):
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
