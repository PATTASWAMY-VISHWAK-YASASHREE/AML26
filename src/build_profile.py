"""Single streaming pass over the 7 raw TSVs -> compact profile artifacts.

Designed for a machine with <1 GB free RAM: nothing is loaded whole, no
intermediate parquet is written, and token counters are pruned periodically so
they cannot grow without bound.

Outputs land in analysis_out/profile/ as small CSV/JSON files (target: <40 MB).
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
from collections import Counter

import polars as pl

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(ROOT, "amazon_ml_2026_research", "student_resource", "dataset")
OUT = os.path.join(ROOT, "analysis_out", "profile")
os.makedirs(OUT, exist_ok=True)

CHUNK = 60_000          # rows per streaming chunk
PRUNE_EVERY = 8         # prune count==1 tokens this often
TOPN = 4000
TOKEN_RE = re.compile(r"[a-z0-9]+")
DIG5 = re.compile(r"(?<!\d)\d{5}(?!\d)")
DIG6 = re.compile(r"(?<!\d)\d{6}(?!\d)")
ADDR_SPLIT = re.compile(r"[,;]")


def log(*a):
    print(*a, flush=True)


def write(name, obj):
    p = os.path.join(OUT, name)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
    log(f"  wrote {name} ({os.path.getsize(p) / 1024:.0f} KB)")


def prune(c: Counter, keep_min=1):
    """Space bound: drop hapax tokens periodically."""
    for k in [k for k, v in c.items() if v <= keep_min]:
        del c[k]


def stream_source(path, split, src):
    """Stream one source file with a plain line reader.

    Deliberately NOT polars/pandas: the machine has <1 GB free RAM and a
    collect() over a 480 MB TSV was being OOM-killed. Files are unquoted
    tab-separated, so csv.reader is exact and costs nothing.
    """
    import csv
    name_tokens: dict[str, Counter] = {}
    addr_tokens: dict[str, Counter] = {}
    country_rows: Counter = Counter()
    stats: dict[str, dict] = {}
    n = 0
    t0 = time.time()
    cols: list[str] = []
    with open(path, "r", encoding="utf-8", errors="replace", newline="") as fh:
        rd = csv.reader(fh, delimiter="\t", quoting=csv.QUOTE_NONE)
        try:
            cols = next(rd)
        except StopIteration:
            return {"split": split, "source": src, "cols": [], "rows": 0,
                    "by_country": {}, "country_rows": {},
                    "name_tokens": {}, "addr_tokens": {}}
        idx = {c: i for i, c in enumerate(cols)}
        i_eid = idx.get("entity_id", 0)
        i_bn = idx.get("business_name", 1)
        i_ba = idx.get("business_address", 2)
        i_c = idx.get("country", 3)
        for rec in rd:
            n += 1
            c = (rec[i_c] if len(rec) > i_c else "").strip()
            country_rows[c] += 1
            s = stats.get(c)
            if s is None:
                s = stats[c] = {
                    "rows": 0, "name_empty": 0, "addr_empty": 0,
                    "name_chars": 0, "addr_chars": 0, "name_tokens": 0,
                    "num_digits": 0, "has_digit_name": 0, "has_comma": 0,
                    "prefix_bad": 0, "dig5": 0, "dig6": 0, "alpha_only_addr": 0,
                    "len_hist": {},
                }
            s["rows"] += 1
            eid = (rec[i_eid] if len(rec) > i_eid else "").strip()
            if not eid.startswith(f"S{src}-"):
                s["prefix_bad"] += 1
            bn = (rec[i_bn] if len(rec) > i_bn else "").strip()
            ba = (rec[i_ba] if len(rec) > i_ba else "").strip()
            if not bn:
                s["name_empty"] += 1
            if not ba:
                s["addr_empty"] += 1
            s["name_chars"] += len(bn)
            s["addr_chars"] += len(ba)
            lk = str(len(bn) // 10 * 10)
            s["len_hist"][lk] = s["len_hist"].get(lk, 0) + 1
            if any(ch.isdigit() for ch in bn):
                s["has_digit_name"] += 1
            if "," in ba:
                s["has_comma"] += 1
            bnl = bn.lower()
            bnt = TOKEN_RE.findall(bnl)
            s["name_tokens"] += len(bnt)
            bal = ba.lower()
            s["num_digits"] += sum(ch.isdigit() for ch in ba)
            s["dig5"] += len(DIG5.findall(bal))
            s["dig6"] += len(DIG6.findall(bal))
            if ba and not any(ch.isdigit() for ch in ba):
                s["alpha_only_addr"] += 1
            nt = name_tokens.get(c)
            if nt is None:
                nt = name_tokens[c] = Counter()
            at = addr_tokens.get(c)
            if at is None:
                at = addr_tokens[c] = Counter()
            nt.update(bnt)
            for comp in ADDR_SPLIT.split(bal):
                at.update(TOKEN_RE.findall(comp))
            if n % CHUNK == 0:
                if (n // CHUNK) % PRUNE_EVERY == 0:
                    for cc in name_tokens:
                        prune(name_tokens[cc])
                    for cc in addr_tokens:
                        prune(addr_tokens[cc])
                if (n // CHUNK) % 40 == 0:
                    log(f"  {split} s{src}: {n:,} rows, {len(stats)} countries, "
                        f"{time.time() - t0:.0f}s")
    return {
        "split": split, "source": src, "cols": cols, "rows": n,
        "by_country": stats, "country_rows": dict(country_rows),
        "name_tokens": {c: nt.most_common(TOPN) for c, nt in name_tokens.items()},
        "addr_tokens": {c: at.most_common(TOPN) for c, at in addr_tokens.items()},
    }


def main():
    log(f"streaming profile -> {OUT}")
    for split in ("train", "test"):
        for src in (1, 2, 3):
            p = os.path.join(DATA, split, f"{split}_source{src}.tsv")
            if not os.path.exists(p):
                log(f"MISSING {p}")
                continue
            r = stream_source(p, split, src)
            write(f"{split}_s{src}.json", r)
            log(f"{split} s{src}: {r['rows']:,} rows  countries={list(r['country_rows'])}")
    log("done")


if __name__ == "__main__":
    main()
