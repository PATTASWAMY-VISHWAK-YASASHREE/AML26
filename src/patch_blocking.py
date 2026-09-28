"""Patch blocking_recall.py: fix the spill-file layout bug.

The writer flushed [4096 keys][4096 ids] repeatedly into each bucket file,
while the reader split every file at its halfway point. The two halves
therefore did not correspond to the key array and the id array, so lookups
matched against garbage and union edge recall came out at 1.3%.

Fix: store a STRUCTURED (key, id) pair stream, so the on-disk layout is
self-describing and the reader cannot misinterpret it. Also derives the
bucket on read instead of trusting a stored bucket field.

Idempotent: safe to run more than once.
"""
import io
import re
import sys

P = "blocking_recall.py"
src = io.open(P, encoding="utf-8").read()

if "PAIR_DT" in src and "def spill_index" in src and "PAIR_DT" in src.split("def query")[0]:
    print("already patched")
    sys.exit(0)

# 1. add the structured dtype next to the module constants
if "PAIR_DT" not in src:
    src = src.replace(
        'ID_SPLIT_RE = re.compile(r"^(S[123])-")',
        'ID_SPLIT_RE = re.compile(r"^(S[123])-")', 1)
    anchor = "KEY_NAMES = ("
    ins = ('# Structured (key, id) record used for the spill files. A structured\n'
           '# dtype makes the on-disk layout self-describing; the previous pair of\n'
           '# parallel int64 runs could be mis-split by the reader.\n'
           'PAIR_DT = np.dtype([("k", "<i8"), ("i", "<i8")])\n\n')
    src = src.replace(anchor, ins + anchor, 1)

# 2. replace the body of spill_index
new_spill = '''def spill_index():
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
            rd = csv.reader(fh, delimiter="t" and "\\t", quoting=csv.QUOTE_NONE)
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
'''

m = re.search(r"^def spill_index\(\):$.*?^    return n$", src, re.S | re.M)
if not m:
    print("could not locate spill_index")
    sys.exit(1)
src = src[:m.start()] + new_spill.rstrip("\n") + src[m.end():]

# 3. fix the reader in query()
old_read = """        raw = np.fromfile(p, dtype=np.int64)
        half = raw.size // 2
        keys, ids = raw[:half], raw[half:]
        del raw
        order = np.argsort(keys, kind="stable")
        keys, ids = keys[order], ids[order]
        del order"""
new_read = """        rec = np.fromfile(p, dtype=PAIR_DT)
        if rec.size == 0:
            continue
        keys = rec["k"]
        ids = rec["i"]
        del rec
        order = np.argsort(keys, kind="stable")
        keys, ids = keys[order], ids[order]
        del order"""
if old_read in src:
    src = src.replace(old_read, new_read, 1)
    print("reader patched")
else:
    print("WARN: reader pattern not found")

io.open(P, "w", encoding="utf-8", newline="\n").write(src)
print("patched", P)
