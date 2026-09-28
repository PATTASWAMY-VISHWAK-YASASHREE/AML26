"""Deep field-level + script profile: one bounded streaming pass per source TSV.

Extends build_profile.py, which stays the canonical profile producer. This adds
the layers the first profile could not answer: name-side completeness,
char/token length histograms, character-class density, Unicode script
detection, legal-suffix and noise-token inventories, address component
parsing, postal-format audit, and exact-duplicate rate.

DESIGN CONSTRAINTS (this box has ~0.36 GB free RAM, 24.2M rows, 2.4 GB of TSV):
  * plain line reader + csv with QUOTE_NONE; nothing is ever collected whole
  * token counters are pruned periodically so they cannot grow unbounded
  * duplicate detection spills int64 hashes to a scratch file and sorts them
    afterwards, so peak RAM is one 8-byte-per-row array, not a Python set
  * READ-ONLY on the dataset. Writes only analysis_out/profile2/ plus a
    scratch dir that is removed at the end.

Output: analysis_out/profile2/{split}_s{src}.json
"""
from __future__ import annotations

import csv
import json
import os
import re
import sys
import time
from collections import Counter

import numpy as np

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(ROOT, "amazon_ml_2026_research", "student_resource", "dataset")
OUT = os.path.join(ROOT, "analysis_out", "profile2")
SCRATCH = os.path.join(ROOT, "analysis_out", ".scratch_dup")

os.makedirs(OUT, exist_ok=True)
os.makedirs(SCRATCH, exist_ok=True)

CHUNK = 60_000
PRUNE_EVERY = 8
CAP = 120_000          # hard ceiling on any single counter
TOPN = 3000
TOKEN_RE = re.compile(r"[^\W_]+", re.UNICODE)

# --- script detection: regex is C-speed, a per-char Python loop is not ------
LATIN_RE = re.compile(r"[A-Za-z\u00C0-\u024F\u1E00-\u1EFF]")
SCRIPTS = {
    "latin": LATIN_RE,
    "devanagari": re.compile(r"[\u0900-\u097F]"),
    "cyrillic": re.compile(r"[\u0400-\u04FF]"),
    "greek": re.compile(r"[\u0370-\u03FF]"),
    "arabic": re.compile(r"[\u0600-\u06FF]"),
    "hebrew": re.compile(r"[\u0590-\u05FF]"),
    "cjk": re.compile(r"[\u4E00-\u9FFF]"),
    "thai": re.compile(r"[\u0E00-\u0E7F]"),
}
PUNCT_RE = re.compile(r"[^\w\s]", re.UNICODE)
WS_RE = re.compile(r"\s+")
# whitespace deleted entirely -- used ONLY for char counts and the dup key,
# never for tokenisation (see the comment at the collapse site in stream_source)
NOWS_RE = re.compile(r"\s")
DIG5_RE = re.compile(r"(?<!\d)\d{5}(?!\d)")
DIG6_RE = re.compile(r"(?<!\d)\d{6}(?!\d)")
DIG3_RE = re.compile(r"(?<!\d)\d{3}(?!\d)")
ANYDIG_RE = re.compile(r"\d")
COMMA_RE = re.compile(r"[,;]")
LEAD_JUNK_RE = re.compile(r"^[^0-9A-Za-z\u00C0-\u024F]+")
TRAIL_JUNK_RE = re.compile(r"[^0-9A-Za-z\u00C0-\u024F]+$")
HOUSENO_RE = re.compile(r"^\s*(\d+[A-Za-z]?(?:[-/]\d+)?)\b")

# Legal-form tokens. Not a normalizer -- an inventory whose frequencies tell you
# which forms actually earn their place in a dictionary.
LEGAL_FORMS = {
    "llc", "l.l.c", "llp", "l.l.p", "ltd", "ltd.", "limited", "inc", "inc.",
    "incorporated", "corp", "corp.", "corporation", "co", "co.", "company",
    "pvt", "pvt.", "private", "plc", "gmbh", "ag", "sa", "sas", "sarl", "srl",
    "spa", "bv", "nv", "ab", "as", "oy", "asa", "aps", "oyj", "pte", "pty",
    "kk", "k.k.", "sro", "sp", "z.o.o", "ooo", "zao", "jsc", "ojsc", "pjsc",
    "a.e", "aep", "anpartsselskab", "kg", "mbh", "ug", "sp.z.o.o", "s.p.a",
}
MULTIWORD_FORMS = [("private", "limited"), ("pvt", "ltd"), ("p", "vt"),
                   ("private", "ltd"), ("and", "sons"), ("and", "brothers"),
                   ("and", "co"), ("sons", "and")]


def new_slice() -> dict:
    """Zeroed per-(split, source, country) accumulator.

    Keys are grouped by the roadmap section they answer, so the write-up can
    cite them directly.
    """
    return {
        "rows": 0,
        # --- section 1: completeness ---
        "name_empty": 0, "name_ws_only": 0, "addr_empty": 0, "addr_ws_only": 0,
        "both_empty": 0, "name_empty_addr_present": 0,
        "name_dup_ws": 0, "addr_dup_ws": 0,
        # --- section 1: lengths ---
        "name_chars": 0, "addr_chars": 0, "name_tokens": 0, "addr_tokens": 0,
        "name_len_hist": {}, "addr_len_hist": {},
        "name_tok_hist": {}, "addr_tok_hist": {},
        "name_len_min": 10**9, "name_len_max": 0,
        "addr_len_min": 10**9, "addr_len_max": 0,
        "name_len_1": 0, "name_len_le3": 0, "name_len_ge100": 0,
        "addr_len_le10": 0, "addr_len_ge80": 0,
        # --- section 1: character classes ---
        "non_ascii_name": 0, "non_ascii_addr": 0,
        "ascii_name_chars": 0, "nonascii_name_chars": 0,
        "ascii_addr_chars": 0, "nonascii_addr_chars": 0,
        "digit_chars_name": 0, "digit_chars_addr": 0,
        "punct_chars_name": 0, "punct_chars_addr": 0,
        "upper_chars_name": 0, "name_has_upper": 0, "name_all_lower": 0,
        "name_has_punct": 0, "addr_has_punct": 0,
        # --- section 6: postal / address structure ---
        "dig3": 0, "dig5": 0, "dig6": 0, "any_digit_addr": 0,
        "alpha_only_addr": 0, "postcode_at_end": 0,
        "addr_comps": 0, "addr_comp_hist": {},
        "addr_housenum": 0, "addr_comp0_numeric": 0,
        "addr_trailing_comma": 0, "addr_one_word": 0,
        "addr_has_landmark": 0, "addr_trunc_heuristic": 0,
        "addr_ends_numeric": 0, "addr_no_postal": 0,
        # --- section 2: scripts ---
        "script_counts": Counter(), "script_mix_name": 0,
        "script_combo_name": Counter(), "nonascii_only_name": 0,
        "latin_only_name": 0, "no_latin_name": 0, "devanagari_only_name": 0,
        # --- section 3: legal forms and noise ---
        "legal_first": Counter(), "legal_last": Counter(), "legal_any": Counter(),
        "legal_pos_first": 0, "legal_pos_last": 0, "legal_pos_mid": 0,
        "legal_rows": 0,
        "noise_lead": Counter(), "noise_trail": Counter(),
        "noise_lead_rows": 0, "noise_trail_rows": 0, "noise_any_rows": 0,
        # --- section 3: case / diacritic variance ---
        "name_has_diacritic": 0, "name_allcaps_token": 0,
    }


LANDMARK_RE = re.compile(
    r"\b(near|beside|opposite|behind|next to|adjacent|by the|"
    r"opp|nearest|in front of)\b", re.I)
DIACRITIC_RE = re.compile(r"[\u00C0-\u024F\u1E00-\u1EFF]")

COUNTER_KEYS = ("legal_first", "legal_last", "legal_any",
                "noise_lead", "noise_trail")


def classify_scripts(s: str) -> list:
    """Names of the Unicode scripts present in the string, in fixed order."""
    return [k for k, rx in SCRIPTS.items() if rx.search(s)]


def prune_counters(S: dict) -> None:
    """Bound memory: drop hapax entries from any inventory past CAP."""
    for s in S.values():
        for key in COUNTER_KEYS:
            cnt = s[key]

def stream_source(path: str, split: str, src: int) -> dict:
    """Stream one source file; accumulate per-country stats and dup hashes."""
    t0 = time.time()
    cols: list = []
    country_rows: Counter = Counter()
    S: dict = {}
    n = 0
    hash_path = os.path.join(SCRATCH, f"{split}_s{src}.i64")
    hf = open(hash_path, "wb")
    buf = np.empty(CHUNK, dtype=np.int64)
    bi = 0

    with open(path, "r", encoding="utf-8", errors="replace", newline="") as fh:
        rd = csv.reader(fh, delimiter="\t", quoting=csv.QUOTE_NONE)
        try:
            cols = next(rd)
        except StopIteration:
            hf.close()
            return {"split": split, "source": src, "cols": [], "rows": 0,
                    "by_country": {}, "country_rows": {}}
        idx = {c: i for i, c in enumerate(cols)}
        i_bn, i_ba = idx.get("business_name", 1), idx.get("business_address", 2)
        i_c = idx.get("country", 3)

        for rec in rd:
            n += 1
            c = (rec[i_c] if len(rec) > i_c else "").strip()
            country_rows[c] += 1
            s = S.get(c)
            if s is None:
                s = S[c] = new_slice()
            s["rows"] += 1

            bn = rec[i_bn] if len(rec) > i_bn else ""
            ba = rec[i_ba] if len(rec) > i_ba else ""
            # COLLAPSE whitespace to single spaces, never delete it. Deleting
            # it would fuse "B+ Retail Inc" into the single token "B+RetailInc",
            # which silently destroys token counts, legal-form detection,
            # house-number parsing and landmark detection.
            nw = WS_RE.sub(" ", bn).strip()
            aw = WS_RE.sub(" ", ba).strip()
            # whitespace-free forms, used only for char counts and the dup key
            nw_tight = NOWS_RE.sub("", bn)
            aw_tight = NOWS_RE.sub("", ba)
            bn_s, ba_s = bn.strip(), ba.strip()

            # ---- section 1: completeness ----
            if not bn_s:
                s["name_empty"] += 1
            elif not nw:
                s["name_ws_only"] += 1
            if not ba_s:
                s["addr_empty"] += 1
            elif not aw:
                s["addr_ws_only"] += 1
            if not bn_s and not ba_s:
                s["both_empty"] += 1
            if not bn_s and ba_s:
                s["name_empty_addr_present"] += 1
            if bn_s != nw:
                s["name_dup_ws"] += 1
            if ba_s != aw:
                s["addr_dup_ws"] += 1

            # ---- section 1: lengths ----
            # char counts use the whitespace-free form so that mean length
            # measures payload, not layout
            ln, la = len(nw_tight), len(aw_tight)
            s["name_chars"] += ln
            s["addr_chars"] += la
            if ln:
                s["name_len_min"] = min(s["name_len_min"], ln)
                s["name_len_max"] = max(s["name_len_max"], ln)
                if ln == 1:
                    s["name_len_1"] += 1
                if ln <= 3:
                    s["name_len_le3"] += 1
                if ln >= 100:
                    s["name_len_ge100"] += 1
            if la:
                s["addr_len_min"] = min(s["addr_len_min"], la)
                s["addr_len_max"] = max(s["addr_len_max"], la)
                if la <= 10:
                    s["addr_len_le10"] += 1
                if la >= 80:
                    s["addr_len_ge80"] += 1

            ntoks = TOKEN_RE.findall(nw.lower())
            atoks = TOKEN_RE.findall(aw.lower())
            s["name_tokens"] += len(ntoks)
            s["addr_tokens"] += len(atoks)
            for tgt, v in (("name_len_hist", ln), ("addr_len_hist", la),
                           ("name_tok_hist", len(ntoks)),
                           ("addr_tok_hist", len(atoks))):
                b = str(v // 10 * 10)
                s[tgt][b] = s[tgt].get(b, 0) + 1

            # ---- section 1: character classes ----
            an = sum(1 for ch in nw_tight if ord(ch) < 128)
            aa = sum(1 for ch in aw_tight if ord(ch) < 128)
            s["ascii_name_chars"] += an
            s["nonascii_name_chars"] += ln - an
            s["ascii_addr_chars"] += aa
            s["nonascii_addr_chars"] += la - aa
            if ln and an != ln:
                s["non_ascii_name"] += 1
            if la and aa != la:
                s["non_ascii_addr"] += 1
            s["digit_chars_name"] += sum(1 for ch in nw if ch.isdigit())
            s["digit_chars_addr"] += sum(1 for ch in aw if ch.isdigit())
            pn = PUNCT_RE.findall(nw)
            pa = PUNCT_RE.findall(aw)
            s["punct_chars_name"] += len(pn)
            s["punct_chars_addr"] += len(pa)
            if pn:
                s["name_has_punct"] += 1
            if pa:
                s["addr_has_punct"] += 1
            up = sum(1 for ch in nw if ch.isupper())
            s["upper_chars_name"] += up
            if up:
                s["name_has_upper"] += 1
            if ln and nw.islower():
                s["name_all_lower"] += 1
            if any(len(t) > 1 and t.isupper() for t in TOKEN_RE.findall(nw)):
                s["name_allcaps_token"] += 1
            if ln and DIACRITIC_RE.search(nw):
                s["name_has_diacritic"] += 1

            # ---- section 2: scripts ----
            if nw:
                sc = classify_scripts(nw)
                for k in sc:
                    s["script_counts"][k] += 1
                if len(sc) > 1:
                    s["script_mix_name"] += 1
                    s["script_combo_name"]["+".join(sorted(sc))] += 1
                if "latin" not in sc:
                    s["no_latin_name"] += 1
                elif len(sc) == 1:
                    s["latin_only_name"] += 1
                if sc == ["devanagari"]:
                    s["devanagari_only_name"] += 1
                if an == 0 and (ln - an) > 0:
                    s["nonascii_only_name"] += 1

            # ---- section 6: postal and address structure ----
            if aw:
                if ANYDIG_RE.search(aw):
                    s["any_digit_addr"] += 1
                else:
                    s["alpha_only_addr"] += 1
                s["dig3"] += len(DIG3_RE.findall(aw))
                s["dig5"] += len(DIG5_RE.findall(aw))
                s["dig6"] += len(DIG6_RE.findall(aw))
                comps = [x.strip() for x in COMMA_RE.split(aw) if x.strip()]
                tail = comps[-1] if comps else ""
                if ANYDIG_RE.search(tail) and len(tail) <= 12:
                    s["postcode_at_end"] += 1
                s["addr_comps"] += len(comps)
                cb = str(len(comps) // 2 * 2)
                s["addr_comp_hist"][cb] = s["addr_comp_hist"].get(cb, 0) + 1
                if comps and ANYDIG_RE.match(comps[0]):
                    s["addr_comp0_numeric"] += 1
                    if HOUSENO_RE.match(comps[0]):
                        s["addr_housenum"] += 1
                if aw.endswith((",", ";")):
                    s["addr_trailing_comma"] += 1
                if len(comps) == 1 and len(atoks) == 1:
                    s["addr_one_word"] += 1
                if LANDMARK_RE.search(aw):
                    s["addr_has_landmark"] += 1
                # Address-completeness signals. These are DESCRIPTIVE, not a
                # truncation judgement: an earlier "ends on a digit => truncated"
                # heuristic fired on ~88% of US rows because a trailing ZIP is
                # itself digits, so it carried no information.
                #   addr_ends_numeric : last component is a bare number (a ZIP
                #                       or PIN sitting at the end)
                #   addr_no_postal    : no 5- or 6-digit code anywhere, i.e. the
                #                       address has no postal component at all
                #                       (the normal case for France)
                if comps and ANYDIG_RE.fullmatch(comps[-1]):
                    s["addr_ends_numeric"] += 1
                if not DIG5_RE.search(aw) and not DIG6_RE.search(aw):
                    s["addr_no_postal"] += 1

            # ---- section 3: legal forms ----
            if ntoks:
                found = [t for t in ntoks if t.strip(".,") in LEGAL_FORMS]
                if found:
                    s["legal_rows"] += 1
                    for t in set(found):
                        s["legal_any"][t] += 1
                    s["legal_first"][ntoks[0]] += 1
                    s["legal_last"][ntoks[-1]] += 1
                    for t in found:
                        i = ntoks.index(t)
                        if i == 0:
                            s["legal_pos_first"] += 1
                        elif i == len(ntoks) - 1:
                            s["legal_pos_last"] += 1
                        else:
                            s["legal_pos_mid"] += 1

            # ---- section 3: leading/trailing noise punctuation ----
            if nw:
                lm = LEAD_JUNK_RE.match(nw)
                tm = TRAIL_JUNK_RE.search(nw)
                if lm:
                    s["noise_lead_rows"] += 1
                    if len(s["noise_lead"]) < CAP:
                        s["noise_lead"][lm.group(0)] += 1
                if tm:
                    s["noise_trail_rows"] += 1
                    if len(s["noise_trail"]) < CAP:
                        s["noise_trail"][tm.group(0)] += 1
                if lm or tm:
                    s["noise_any_rows"] += 1

            # ---- section 9: exact-duplicate fingerprint ----
            buf[bi] = hash((nw_tight.lower(), aw_tight.lower()))
            bi += 1
            if bi == CHUNK:
                hf.write(buf.tobytes())
                bi = 0

            if n % CHUNK == 0:
                if (n // CHUNK) % PRUNE_EVERY == 0:
                    prune_counters(S)
                if (n // CHUNK) % 40 == 0:
                    print(f"  {split} s{src}: {n:,} rows, {len(S)} countries, "
                          f"{time.time() - t0:.0f}s", flush=True)

    if bi:
        hf.write(buf[:bi].tobytes())
    hf.close()

    # Section 9: exact-duplicate rate, computed out-of-core. peak RAM here is
    # one int64 array (8 bytes/row => ~40 MB for the largest file), not a set.
    dup = {"rows_hashed": 0, "distinct": 0, "dup_excess": 0,
           "dup_excess_rate": None, "largest_group": 0}
    arr = np.fromfile(hash_path, dtype=np.int64)
    os.remove(hash_path)
    if arr.size:
        n_h = int(arr.size)
        uniq, counts = np.unique(arr, return_counts=True)
        rep = counts[counts > 1]
        dup = {
            "rows_hashed": n_h,
            "distinct": int(uniq.size),
            "dup_excess": int(rep.sum() - rep.size) if rep.size else 0,
            "dup_excess_rate": round(float((rep.sum() - rep.size) / n_h), 6)
                               if rep.size else 0.0,
            "largest_group": int(rep.max()) if rep.size else 0,
            "groups_involved": int(rep.size),
        }
        del uniq, counts
    del arr

    out = {"split": split, "source": src, "cols": cols, "rows": n,
           "country_rows": dict(country_rows),
           "dup_exact_name_addr": dup,
           "by_country": {}}
    for cc, s in S.items():
        s["script_counts"] = dict(s["script_counts"])
        s["script_combo_name"] = dict(s["script_combo_name"].most_common(40))
        for key in COUNTER_KEYS:
            s[key] = s[key].most_common(TOPN)
        for k in ("name_len_min", "addr_len_min"):
            if s[k] == 10**9:
                s[k] = None
        out["by_country"][cc] = s
    return out


def main() -> None:
    print(f"deep profile -> {OUT}", flush=True)
    for split in ("train", "test"):
        for src in (1, 2, 3):
            p = os.path.join(DATA, split, f"{split}_source{src}.tsv")
            if not os.path.exists(p):
                print(f"MISSING {p}", flush=True)
                continue
            r = stream_source(p, split, src)
            op = os.path.join(OUT, f"{split}_s{src}.json")
            with open(op, "w", encoding="utf-8") as f:
                json.dump(r, f, ensure_ascii=False, indent=1)
            d = r["dup_exact_name_addr"]
            print(f"{split} s{src}: {r['rows']:,} rows  "
                  f"countries={list(r['country_rows'])}  "
                  f"dup_excess={d['dup_excess']:,} "
                  f"({(d.get('dup_excess_rate') or 0) * 100:.2f}%)  "
                  f"largest_group={d['largest_group']:,}  "
                  f"-> {os.path.getsize(op) / 1024:.0f} KB", flush=True)
    try:
        os.rmdir(SCRATCH)
    except OSError:
        pass
    print("done", flush=True)


if __name__ == "__main__":
    main()
