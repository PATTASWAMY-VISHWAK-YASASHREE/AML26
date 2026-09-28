"""Fix two metric bugs in blocking_recall.query().

Bug A: union edge recall exceeded 1.0 (reported 4.39).
  `u["found"] += len(true ∩ cand_set)` ran once PER KEY.  A true edge recovered
  by three different keys was therefore counted three times, so the "union"
  was really a sum over keys.  Fix: accumulate the recovered id hashes in a
  SET per entity, so each edge is counted once no matter how many keys find it.

Bug B: union candidate counts were nonsense (median 0, mean 141.9).
  On hitting CAND_CAP the code did `u["cands"].clear()`, discarding the count
  and leaving the entity looking like it had zero candidates -- which is why
  the median was 0 while the mean was high.  Fix: keep a separate integer
  `n_cands` that only ever grows, and use the set purely for de-duplication
  until the cap, after which the set is released to free memory but the
  integer is retained.

Both are metric bugs, not performance issues: the underlying index and lookups
were correct, so only the reported numbers change.
"""
import io
import re
import sys

P = "blocking_recall.py"
src = io.open(P, encoding="utf-8").read()

if "n_cands" in src and "found_ids" in src:
    print("already patched")
    sys.exit(0)

# --- Bug B, part 1: the accumulator needs a count and a set of found ids ----
old_acc = '    union = [{"found": 0, "cands": set(), "capped": False} for _ in ents]'
new_acc = ('    # n_cands only ever grows and is the reported candidate count; "cands"\n'
           '    # is a de-duplication set released at the cap to free memory;\n'
           '    # found_ids makes the union recall count each true edge exactly once.\n'
           '    union = [{"n_cands": 0, "cands": set(), "capped": False,\n'
           '              "found_ids": set()} for _ in ents]')
if old_acc in src:
    src = src.replace(old_acc, new_acc, 1)
    print("accumulator patched")
else:
    print("WARN: accumulator pattern not found")

# --- Bugs A and B, part 2: the accumulation loop ---------------------------
old_loop = '''            if ncand:
                for _, ei, kn in items[j:k2]:
                    u = union[ei]
                    if not u["capped"]:
                        room = CAND_CAP - len(u["cands"])
                        if room > 0:
                            u["cands"].update(list(cand_set)[:room])
                            if len(u["cands"]) >= CAND_CAP:
                                u["capped"] = True
                                u["cands"].clear()
                    u["found"] += len(ents[ei]["true"].intersection(cand_set))'''
new_loop = '''            if ncand:
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
                    u["found_ids"].update(ents[ei]["true"].intersection(cand_set))'''
if old_loop in src:
    src = src.replace(old_loop, new_loop, 1)
    print("accumulation loop patched")
else:
    print("WARN: loop pattern not found")

# --- reporting must read the new fields -----------------------------------
src = src.replace('u_edges = sum(u["found"] for u in union)',
                  'u_edges = sum(len(u["found_ids"]) for u in union)')
src = src.replace('sizes = [len(u["cands"]) for u in union]',
                  'sizes = [u["n_cands"] for u in union]')
src = src.replace('sum(len(union[i]["cands"]) for i in idxs) / len(idxs), 1),',
                  'sum(union[i]["n_cands"] for i in idxs) / len(idxs), 1),')

io.open(P, "w", encoding="utf-8", newline="\n").write(src)
print("patched", P)
