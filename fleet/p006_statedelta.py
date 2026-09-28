"""P006 scratch: attribute the US test_s3 vs test_s2 address-length delta.

Read-only. Loads only the compact profile JSONs plus _upstream/src/normalize.py
(imported read-only, used only for its US_STATES key/value table).
"""
import json
import os
import sys
import traceback

LOG = open("p006_log.txt", "w", encoding="utf-8", buffering=1)


def w(*a):
    LOG.write(" ".join(str(x) for x in a) + "\n")
    LOG.flush()


def P(n):
    with open(os.path.join("analysis_out", "profile", n + ".json"), encoding="utf-8") as f:
        return json.load(f)


try:
    sys.path.insert(0, os.path.join("_upstream", "src"))
    import normalize as N  # noqa: E402
    a = dict(P("test_s3")["addr_tokens"]["US"])
    b = dict(P("test_s2")["addr_tokens"]["US"])
    u3 = P("test_s3")["by_country"]["US"]
    u2 = P("test_s2")["by_country"]["US"]
    N3, N2 = u3["rows"], u2["rows"]
    obs = u3["addr_chars"] / N3 - u2["addr_chars"] / N2
    w("observed mean-addr delta = %.4f chars/row" % obs)
    w("observed mean-name delta = %.4f chars/row"
      % (u3["name_chars"] / N3 - u2["name_chars"] / N2))
    w("")
    d3 = d2 = 0
    det = []
    for full, ab in list(N.US_STATES.items()):
        if full not in a:
            continue
        fa, aa = len(full), len(ab)
        d3 += fa * a[full]
        d2 += aa * b.get(ab, 0)
        det.append((full, ab, a[full], b.get(ab, 0), (fa - aa) * a[full]))
    det.sort(key=lambda r: -r[4])
    w("%-18s%-4s%9s%9s%10s" % ("state", "ab", "t_s3", "t_s2", "chDelta"))
    for r in det[:18]:
        w("%-18s%-4s%9d%9d%10d" % (r[0], r[1], r[2], r[3], r[4]))
    w("%-22s%9d%9d%10d" % ("SUM(all full names)",
                             sum(r[2] for r in det), sum(r[3] for r in det), d3 - d2))
    w("")
    w("predicted mean-addr delta from state spelling alone = %.4f" % ((d3 - d2) / N3))
    w("unexplained residual                                = %.4f" % (obs - (d3 - d2) / N3))
    w("")
    w("states matched=%d  US_STATES=%d IN_STATES=%d FR_REGIONS=%d"
      % (len(det), len(N.US_STATES), len(N.IN_STATES), len(N.FR_REGIONS)))
    w("unit token t_s2=%d t_s3=%d" % (b.get("unit", 0), a.get("unit", 0)))
    w("ADDR_CANON_COMMON['unit']=%r" % N.ADDR_CANON_COMMON.get("unit"))
    w("")
    w("=== MECHANISM: does a spelled-out US state resolve, and does it survive? ===")
    cases = [
        ("123 Main St, Springfield, NY", "US"),
        ("123 Main St, Springfield, New York", "US"),
        ("500 Peachtree St, Atlanta, Georgia", "US"),
        ("500 Peachtree St, Atlanta, GA", "US"),
        ("100 Road St, Raleigh, North Carolina", "US"),
        ("100 Road St, Raleigh, NC", "US"),
        ("7 Rue de la Paix, Bordeaux, Nouvelle Aquitaine", "France"),
        ("7 Rue de la Paix, Bordeaux, Pays de la Loire", "France"),
    ]
    for s, c in cases:
        toks, nums, st, pin, cc = N.normalize_address(s, c)
        w("  %-6s %-46s state=%-5r toks=%s" % (c, s, st, toks))
    w("")
    w("=== MECHANISM: state buried in a longer component (no comma isolation) ===")
    for s in ["123 Main St Springfield Texas", "123 Main St, Springfield Texas 75201"]:
        toks, nums, st, pin, cc = N.normalize_address(s, "US")
        w("  %-46s state=%-5r toks=%s" % (s, st, toks))
    w("")
    w("=== MECHANISM: 'unit' as a token - is it kept or dropped? ===")
    for s in ["123 Main St Unit 5, Dallas, Texas", "123 Main St #5, Dallas, Texas"]:
        toks, nums, st, pin, cc = N.normalize_address(s, "US")
        w("  %-42s toks=%s" % (s, toks))
    w("")
    w("=== COVERAGE: which US states appear spelled-out in each file, and are they all mapped? ===")
    tk3 = a
    tk2 = b
    inv3 = {}
    for full, ab in list(N.US_STATES.items()):
        if ab in inv3:
            continue
        inv3[ab] = full
    seen3 = {k: v for k, v in inv3.items() if v in tk3}
    seen2 = {k: v for k, v in inv3.items() if k in tk2}
    w("  distinct US states seen spelled-out in test_s3 : %d" % len(seen3))
    w("  distinct US states seen abbreviated in test_s2 : %d" % len(seen2))
    w("  states in neither: %s" % sorted(set(inv3) - set(seen3) - set(seen2)))
    w("  all spelled-out forms are keys in US_STATES?   %s"
      % all(v in N.US_STATES for v in seen3.values()))
    w("")
    w("=== COLLISION: state names that are also common US place/street words ===")
    for t in ["washington", "indiana", "missouri", "virginia", "kansas", "delaware",
              "iowa", "wyoming", "nevada", "oregon", "georgia", "florida"]:
        c = tk3.get(t, 0)
        w("    %-12s test_s3_count=%-9d in US_STATES=%s" % (t, c, t in N.US_STATES))
    w("")
    w("=== does a bare 'in' component become Indiana? ===")
    for s in ["123 Main St, Springfield, IN", "123 Main St, in, Springfield"]:
        toks, nums, st, pin, cc = N.normalize_address(s, "US")
        w("    %-34s state=%r" % (s, st))
except Exception:
    w(traceback.format_exc())
LOG.close()


