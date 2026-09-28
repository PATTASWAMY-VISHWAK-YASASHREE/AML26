"""Throughput probe for deep_profile.stream_source.

Runs the real function against the first N rows of a source file (materialised
to a small temp TSV) so we can measure rows/sec and extrapolate the full 24.2M
row cost before committing to it. Also verifies the accumulator is non-degenerate.
"""
import csv
import io
import os
import sys
import time

import deep_profile as dp

LIMIT = int(sys.argv[1]) if len(sys.argv) > 1 else 50_000
SRC = sys.argv[2] if len(sys.argv) > 2 else "train_source1.tsv"
SPLIT = "train"


def head(src_path: str, limit: int) -> str:
    out = io.StringIO()
    with open(src_path, "r", encoding="utf-8", errors="replace", newline="") as fh:
        rd = csv.reader(fh, delimiter="\t", quoting=csv.QUOTE_NONE)
        w = csv.writer(out, delimiter="\t", quoting=csv.QUOTE_NONE,
                       lineterminator="\n")
        for i, rec in enumerate(rd):
            if i > limit:
                break
            w.writerow(rec)
    return out.getvalue()


def main() -> None:
    p = os.path.join(dp.DATA, SPLIT, SRC)
    tmp = os.path.join(dp.SCRATCH, "_bench.tsv")
    os.makedirs(dp.SCRATCH, exist_ok=True)
    txt = head(p, LIMIT)
    with open(tmp, "w", encoding="utf-8", newline="") as f:
        f.write(txt)
    t0 = time.time()
    r = dp.stream_source(tmp, "bench", 1)
    el = time.time() - t0
    n = r["rows"]
    rps = n / el if el else 0
    total = 24_229_173
    print(f"rows={n:,}  elapsed={el:.1f}s  rows/sec={rps:,.0f}")
    print(f"extrapolated full corpus: {total / rps / 3600:.2f} h")
    d = r["dup_exact_name_addr"]
    print("dup:", d)
    for c, s in r["by_country"].items():
        print(f"  {c}: rows={s['rows']:,} name_empty={s['name_empty']} "
              f"scripts={s['script_counts']} "
              f"legal_rows={s['legal_rows']} noise_any={s['noise_any_rows']} "
              f"name_len_mean={s['name_chars'] / max(1, s['rows']):.1f}")
        print(f"     noise_lead top5={s['noise_lead'][:5]}")
        print(f"     legal_last top5={s['legal_last'][:5]}")
    os.remove(tmp)


if __name__ == "__main__":
    main()
