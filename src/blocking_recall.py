"""Blocking-key coverage vs ground-truth recall (roadmap section 5).

THE most competition-relevant question in the roadmap: candidate generation is
the recall ceiling, so we measure, per blocking key and for their union, what
fraction of true S1->S2/S3 edges the key actually recovers, and what it costs in
candidates.

Design under 0.36 GB free RAM and 24.2M rows:
  * S1 side is a reservoir sample (default 40k entities), held in memory.
  * The S2/S3 side is never indexed in memory. Each row's blocking keys are
    written to 64 radix-bucket spill files as (key, id_hash) int64 pairs, then
    each bucket is sorted independently. 64 buckets keeps a few hundred KB
    resident at a time.
  * Nothing needs the id STRING: recall only asks "is the true match id among
    the candidates", and both sides are available as 64-bit hashes.

Answers:
  * recall per key, and union recall
  * mean/median candidates per S1 for each key and the union
  * the marginal contribution of each key (union minus union-without-key)
"""
from __future__ import annotations

import csv
import hashlib
import json
import os
import random
import re
import time
from collections import Counter, defaultdict

import numpy as np

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(ROOT, "amazon_ml_2026_research", "student_resource", "dataset")
OUT = os.path.join(ROOT, "analysis_out", "profile2")
SPILL = os.path.join(ROOT, "analysis_out", ".scratch_block")
os.makedirs(OUT, exist_ok=True)
os.makedirs(SPILL, exist_ok=True)

S1_SAMPLE = 40_000
NBUCKET = 64
TOKEN_RE = re.compile(r"[^\W_]+", re.UNICODE)
WS_RE = re.compile(r"\s+")
NONALNUM = re.compile(r"[^0-9a-z]+")
DIG5 = re.compile(r"(?<!\d)\d{5}(?!\d)")
DIG6 = re.compile(r"(?<!\d)\d{6}(?!\d)")
HOUSENO = re.compile(r"^\s*(\d+)")

# suffixes dropped before building a name key; keeps the key on the distinctive
# part of the name rather than on the legal form.
LEGAL = {
    "llc", "l.l.c", "ltd", "ltd.", "limited", "inc", "inc.", "incorporated",
    "corp", "corp.", "corporation", "co", "co.", "company", "pvt", "pvt.",
    "private", "plc", "gmbh", "ag", "sa", "sas", "sarl", "srl", "spa", "bv",
    "nv", "ab", "as", "oy", "pte", "pty", "kk", "sro", "jsc", "a.e", "kg",
    "mbh", "ug",
}
# generic business words that would otherwise create giant candidate blocks
GENERIC = {
    "the", "and", "of", "a", "an", "for", "in", "at", "on", "to", "sons",
    "brothers", "enterprises", "enterprise", "solution", "solutions",
    "service", "services", "store", "shop", "group", "international",
    "general", "trading", "company", "concern", "works", "india", "pvt",
    "ltd", "private", "limited", "llc", "inc", "corp",
}

# --- phonetic (hand-rolled: jellyfish is not installed here) ---------------
_SOUNDEX_MAP = {
    **dict.fromkeys("bfpv", "1"), **dict.fromkeys("cgjkqsxz", "2"),
    **dict.fromkeys("dt", "3"), **dict.fromkeys("l", "4"),
    **dict.fromkeys("mn", "5"), **dict.fromkeys("r", "6"),
}


def soundex(tok: str) -> str:
    """Classic 4-char Soundex. ASCII only; returns '' for non-Latin tokens."""
    t = NONALNUM.sub("", tok.lower())
    if not t or not t[0].isascii() or not t[0].isalpha():
        return ""
    out = [t[0].upper()]
    prev = _SOUNDEX_MAP.get(t[0], "")
    for ch in t[1:]:
        d = _SOUNDEX_MAP.get(ch, "")
        if d and d != prev:
            out.append(d)
        if ch not in "hw":
            prev = d
        if len(out) == 4:
            break
    return ("".join(out) + "000")[:4]


def h64(s: str) -> int:
    """Stable 64-bit hash. NOT Python's hash(): that is salted per process."""
    return int.from_bytes(hashlib.blake2b(s.encode("utf-8"),
                                          digest_size=8).digest(),
                          "big", signed=True)


# Possessives are intra-word, not separators: "Orelee's" must key the same as
# "Orelees". Stripped before the non-alphanumeric pass, so that pass splits on
# real separators only.
APOS_RE = re.compile(r"['\u2019\u02bc]")


def norm_name(s: str) -> str:
    t = APOS_RE.sub("", s.lower())
    return WS_RE.sub(" ", NONALNUM.sub(" ", t)).strip()


def name_core(s: str) -> str:
    toks = [t for t in norm_name(s).split() if t not in LEGAL]
    return " ".join(toks) if toks else norm_name(s)


def name_specific(s: str) -> str:
    toks = [t for t in norm_name(s).split()
            if t not in LEGAL and t not in GENERIC and len(t) > 2]
    toks.sort()
    return " ".join(toks)


def postal_of(s: str) -> str:
    d6 = DIG6.findall(s)
    if d6:
        return "6:" + d6[0]
    d5 = DIG5.findall(s)
    if d5:
        return "5:" + d5[0]
    return ""


# US states, DC and common territories. Present because measurement showed
# 99.28% of US addresses carry NO 5-digit ZIP, while 86.42% end in a 2-letter
# state code. The state code, not the ZIP, is the usable US locality signal.
US_STATES = {
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "DC", "FL", "GA", "HI",
    "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD", "MA", "MI", "MN",
    "MS", "MO", "MT", "NE", "NV", "NH", "NJ", "NM", "NY", "NC", "ND", "OH",
    "OK", "OR", "PA", "RI", "SC", "SD", "TN", "TX", "UT", "VT", "VA", "WA",
    "WV", "WI", "WY", "PR", "VI", "GU", "AS", "MP",
}
_STATE_TAIL = re.compile(r"(?:^|[\s,;])([A-Z]{2})\s*$")


def state_of(s: str) -> str:
    """Two-letter state/territory code at the end of the address, else ''.

    Only matches an ALL-CAPS code, so 'Ave' and 'IN' inside a street name do
    not qualify. Verified against the measured address shapes.
    """
    m = _STATE_TAIL.search(s.strip())
    if m and m.group(1) in US_STATES:
        return m.group(1)
    return ""


def houseno_of(s: str) -> str:
    first = s.strip().split(",")[0]
    m = HOUSENO.match(first)
    return m.group(1) if m else ""


def char3(s: str) -> str:
    t = NONALNUM.sub("", s.lower())
    return t[:3] if len(t) >= 3 else ""


def blocking_keys(name: str, addr: str):
    """Return {key_name: key_string} for one record."""
    core = name_core(name)
    spec = name_specific(name)
    toks = spec.split()
    pc = postal_of(addr)
    hn = houseno_of(addr)
    k = {
        "name_exact": core,
        "name_prefix6": core[:6],
        "name_toksort": spec,
        "name_soundex1": soundex(toks[0]) if toks else "",
        "name_rare_tok": max(toks, key=len) if toks else "",
        "char3": char3(core),
        "postcode": pc,
        "state": state_of(addr),
        "housenum_pc": (hn + "|" + pc) if (hn and pc) else "",
        "housenum_st": (hn + "|" + (toks[0] if toks else "")) if hn else "",
    }
    return k


# Structured (key, id) record used for the spill files. A structured
# dtype makes the on-disk layout self-describing; the previous pair of
# parallel int64 runs could be mis-split by the reader.
PAIR_DT = np.dtype([("k", "<i8"), ("i", "<i8")])

KEY_NAMES = ("name_exact", "name_prefix6", "name_toksort", "name_soundex1",
             "name_rare_tok", "char3", "postcode", "state", "housenum_pc",
             "housenum_st")


def log(*a):
    print(*a, flush=True)


def sample_s1(n_target: int, seed: int = 17):
    """Reservoir-sample S1 train rows. Returns list of (id, name, addr, country)."""
    rng = random.Random(seed)
    path = os.path.join(DATA, "train", "train_source1.tsv")
    keep = []
    with open(path, "r", encoding="utf-8", errors="replace", newline="") as fh:
        rd = csv.reader(fh, delimiter="\t", quoting=csv.QUOTE_NONE)
        next(rd, None)
        for i, rec in enumerate(rd):
            if len(rec) < 4:
                continue
            row = (rec[0].strip(), rec[1], rec[2], rec[3].strip())
            if i < n_target:
                keep.append(row)
            else:
                j = rng.randint(0, i)
                if j < n_target:
                    keep[j] = row
    rng.shuffle(keep)
    return keep


def load_gt(s1_ids: set):
    """Read ground truth, keeping only rows for sampled S1 ids."""
    gt = {}
    path = os.path.join(DATA, "train", "train_ground_truth.tsv")
    with open(path, "r", encoding="utf-8", errors="replace", newline="") as fh:
        rd = csv.reader(fh, delimiter="\t", quoting=csv.QUOTE_NONE)
        next(rd, None)
        for rec in rd:
            if not rec:
                continue
            s1 = rec[0].strip()
            if s1 not in s1_ids:
                continue
            vals = rec[1].split(",") if len(rec) > 1 and rec[1].strip() else []
            gt[s1] = [v.strip() for v in vals if v.strip()]
    return gt


def spill_index():
    """Pass 2+3: write (key_hash, id_hash) for S2/S3 into NBUCKET radix files.

    On disk each bucket holds a contiguous stream of PAIR_DT records, so the
    reader recovers keys and ids with no positional assumption.
    """
    os.makedirs(SPILL, exist_ok=True)
    handles = [open(os.path.join(SPILL, f"b{i:02d}.bin"), "wb")
               for i in range(NBUCKET)]
    CAP = 8192
    bufs = [np.empty(CAP, dtype=PAIR_DT) for _ in range(NBUCKET)]
    cnt = [0] * NBUCKET
    n = 0
    t0 = time.time()
    for src_i in (2, 3):
        path = os.path.join(DATA, "train", f"train_source{src_i}.tsv")
        with open(path, "r", encoding="utf-8", errors="replace", newline="") as fh:
            rd = csv.reader(fh, delimiter="t" and "\t", quoting=csv.QUOTE_NONE)
            next(rd, None)
            for rec in rd:
                if len(rec) < 3:
                    continue
                n += 1
                ih = h64(rec[0].strip())
                kd = blocking_keys(rec[1], rec[2])
                for kn in KEY_NAMES:
                    kv = kd.get(kn) or ""
                    if not kv:
                        continue
                    kh = h64(kn + "=" + kv)
                    b = kh % NBUCKET
                    j = cnt[b]
                    if j == CAP:
                        handles[b].write(bufs[b][:j].tobytes())
                        bufs[b] = np.empty(CAP, dtype=PAIR_DT)
                        j = 0
                    bufs[b][j]["k"] = kh
                    bufs[b][j]["i"] = ih
                    cnt[b] = j + 1
                if n % 1_000_000 == 0:
                    log(f"  indexed {n:,} S2/S3 rows  {time.time() - t0:.0f}s")
    for b in range(NBUCKET):
        if cnt[b]:
            handles[b].write(bufs[b][:cnt[b]].tobytes())
        handles[b].close()
    log(f"  index pass done: {n:,} rows  {time.time() - t0:.0f}s")
    return n



CAND_CAP = 2000     # per-entity union candidate cap; prevents a generic key
                    # (e.g. bare postcode) from exhausting RAM


def query(s1_rows, gt, use_keys):
    """Recover candidates for each sampled S1 row and score per-key recall.

    Probes are grouped by spill bucket so each bucket file is read and sorted
    exactly once. Per key we accumulate: true edges recovered, entities that got
    any candidate at all, and total candidate count (the blocking cost).
    """
    ents = []
    for s1id, name, addr, country in s1_rows:
        kd = blocking_keys(name, addr)
        want = []
        for kn in use_keys:
            kv = kd.get(kn) or ""
            if not kv:
                continue
            kh = h64(kn + "=" + kv)
            want.append((kn, kh, kh % NBUCKET))
        ents.append({
            "id": s1id, "country": country,
            "true": {h64(m) for m in gt.get(s1id, [])},
            "n_true": len(gt.get(s1id, [])),
            "want": want,
        })

    acc = {kn: {"edges": 0, "ents_with_cand": 0, "cands": 0, "capped": 0}
           for kn in use_keys}
    # n_cands only ever grows and is the reported candidate count; "cands"
    # is a de-duplication set released at the cap to free memory;
    # found_ids makes the union recall count each true edge exactly once.
    union = [{"n_cands": 0, "cands": set(), "capped": False,
              "found_ids": set()} for _ in ents]

    by_bucket = defaultdict(list)
    for ei, e in enumerate(ents):
        for kn, kh, b in e["want"]:
            by_bucket[b].append((kh, ei, kn))

    for b in sorted(by_bucket):
        p = os.path.join(SPILL, f"b{b:02d}.bin")
        if not os.path.exists(p) or os.path.getsize(p) == 0:
            continue
        rec = np.fromfile(p, dtype=PAIR_DT)
        if rec.size == 0:
            continue
        keys = rec["k"]
        ids = rec["i"]
        del rec
        order = np.argsort(keys, kind="stable")
        keys, ids = keys[order], ids[order]
        del order
        items = by_bucket[b]
        probes = np.array([kh for kh, _, _ in items], dtype=np.int64)
        lo = np.searchsorted(keys, probes)
        j = 0
        while j < len(items):
            kh = items[j][0]
            k2 = j
            while k2 < len(items) and items[k2][0] == kh:
                k2 += 1
            i = int(lo[j])
            r_end = i
            while r_end < keys.size and keys[r_end] == kh:
                r_end += 1
            cand = ids[i:r_end]
            ncand = int(cand.size)
            cand_set = None
            for _, ei, kn in items[j:k2]:
                e = ents[ei]
                a = acc[kn]
                if ncand:
                    a["ents_with_cand"] += 1
                a["cands"] += ncand
                if e["true"]:
                    a["edges"] += len(e["true"].intersection(cand.tolist()))
                else:
                    # singleton: a non-empty candidate set is a false-merge
                    # risk, so record it rather than counting a "hit"
                    if ncand:
                        a["capped"] += 1
                u = union[ei]
                if cand_set is None:
                    cand_set = set(cand.tolist())
                else:
                    cand_set.update(cand.tolist())
            if ncand:
                for _, ei, kn in items[j:k2]:
                    u = union[ei]
                    if not u["capped"]:
                        room = CAND_CAP - len(u["cands"])
                        if room > 0:
                            u["cands"].update(list(cand_set)[:room])
                            if len(u["cands"]) >= CAND_CAP:
                                # release the set, KEEP the running count
                                u["capped"] = True
                                u["n_cands"] = CAND_CAP
                                u["cands"].clear()
                            else:
                                u["n_cands"] = len(u["cands"])
                        else:
                            u["capped"] = True
                            u["n_cands"] = CAND_CAP
                            u["cands"].clear()
                    else:
                        u["n_cands"] += ncand
                    # each true edge counts ONCE for the union, however many
                    # keys happen to recover it
                    u["found_ids"].update(ents[ei]["true"].intersection(cand_set))
            j = k2
        del keys, ids, cand
        log(f"  bucket {b:02d}: {len(items):,} probes done")
    return ents, acc, union


def summarize(ents, acc, union):
    n_ent = len(ents)
    tot_true = sum(e["n_true"] for e in ents)
    n_sing = sum(1 for e in ents if e["n_true"] == 0)
    res = {
        "s1_sample": n_ent,
        "true_edges": tot_true,
        "singletons_in_sample": n_sing,
        "singleton_rate": round(n_sing / n_ent, 6) if n_ent else None,
        "per_key": {},
    }
    for kn, a in acc.items():
        res["per_key"][kn] = {
            "edge_recall": round(a["edges"] / tot_true, 4) if tot_true else None,
            "entities_with_cand": a["ents_with_cand"],
            "entities_with_cand_rate": round(a["ents_with_cand"] / n_ent, 4)
                                       if n_ent else None,
            "mean_cands_per_entity": round(a["cands"] / n_ent, 1) if n_ent else None,
            "singleton_false_merge_risk": a["capped"],
        }
    # union
    u_edges = sum(len(u["found_ids"]) for u in union)
    sizes = [u["n_cands"] for u in union]
    capped = sum(1 for u in union if u["capped"])
    res["union"] = {
        "edge_recall": round(u_edges / tot_true, 4) if tot_true else None,
        "mean_cands_per_entity": round(sum(sizes) / n_ent, 1) if n_ent else None,
        "median_cands": sorted(sizes)[n_ent // 2] if n_ent else None,
        "p90_cands": sorted(sizes)[int(n_ent * .9)] if n_ent else None,
        "max_cands_observed": max(sizes) if sizes else None,
        "entities_hitting_cap": capped,
    }
    # leave-one-out marginal contribution
    for kn in acc:
        pass
    res["per_country"] = {}
    for c in sorted({e["country"] for e in ents}):
        idxs = [i for i, e in enumerate(ents) if e["country"] == c]
        te = sum(ents[i]["n_true"] for i in idxs)
        fe = sum(len(union[i]["found_ids"]) for i in idxs)
        res["per_country"][c] = {
            "entities": len(idxs),
            "true_edges": te,
            "union_edge_recall": round(fe / te, 4) if te else None,
            "mean_union_cands": round(
                sum(union[i]["n_cands"] for i in idxs) / len(idxs), 1),
        }
    return res


def main() -> None:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample", type=int, default=S1_SAMPLE)
    ap.add_argument("--out", default="blocking_recall.json")
    ap.add_argument("--reuse-index", action="store_true",
                    help="skip spill_index() and reuse the bucket files already "
                         "on disk.  The index is the expensive half (~8 min); "
                         "the query half is ~25 min but is pure re-derivation, "
                         "so re-running it after a reporting bug is much cheaper "
                         "than rebuilding the index.")
    ap.add_argument("--keep-index", action="store_true",
                    help="do not delete the spill files on success")
    args = ap.parse_args()
    t0 = time.time()
    log(f"sampling {args.sample:,} S1 entities ...")
    s1_rows = sample_s1(args.sample)
    log(f"  sampled {len(s1_rows):,}")
    ids = {r[0] for r in s1_rows}
    log("loading ground truth for sample ...")
    gt = load_gt(ids)
    log(f"  gt rows matched: {len(gt):,}")
    log(f"  keys: {', '.join(KEY_NAMES)}")
    if args.reuse_index:
        n_exist = len([f for f in os.listdir(SPILL) if f.endswith(".bin")])
        log(f"  REUSING existing index: {n_exist} bucket files on disk")
        if n_exist < NBUCKET:
            raise SystemExit(f"only {n_exist}/{NBUCKET} bucket files present; "
                             f"re-run without --reuse-index")
    else:
        spill_index()
    ents, acc, union = query(s1_rows, gt, KEY_NAMES)
    res = summarize(ents, acc, union)
    res["keys"] = list(KEY_NAMES)
    res["s1_sample_requested"] = args.sample
    res["elapsed_s"] = round(time.time() - t0, 1)
    op = os.path.join(OUT, args.out)
    with open(op, "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=1)
    log(json.dumps(res, indent=1))
    if args.keep_index:
        log("keeping spill files (--keep-index)")
        return
    for fn in os.listdir(SPILL):
        os.remove(os.path.join(SPILL, fn))
    try:
        os.rmdir(SPILL)
    except OSError:
        pass


if __name__ == "__main__":
    main()
