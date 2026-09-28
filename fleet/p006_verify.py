"""Verify the P006 deliverable's arithmetic against the profile, read-only.

Checks the two things this agent can independently recompute exactly:
  - share-of-file percentages
  - the name-length histogram floor/ceiling bound and mean offset
Everything else in the .md is either a raw field copy or a token-mass proxy
whose token set is defined in build_p006_json.py.
"""
import json
import os

OUT = open("p006_verify.txt", "w", encoding="utf-8", buffering=1)


def w(*a):
    OUT.write(" ".join(str(x) for x in a) + "\n")
    OUT.flush()


def P(n):
    with open(os.path.join("analysis_out", "profile", n + ".json"), encoding="utf-8") as f:
        return json.load(f)


d = P("test_s3")
R = d["rows"]
u = d["by_country"]["US"]
N = u["rows"]

w("=== shares (md says US 38.2837, India 47.3180, France 14.3983) ===")
for c in ("US", "India", "France"):
    v = d["country_rows"][c]
    w("  %-7s %9d  %.4f%%" % (c, v, v / R * 100))
w("  sum=%d rows=%d match=%s" % (sum(d["country_rows"].values()), R,
                                 sum(d["country_rows"].values()) == R))
w("")

w("=== histogram bound (md says [38,341,410 , 55,821,110], offset +4.923) ===")
lo = hi = 0
for b, c in sorted(u["len_hist"].items(), key=lambda x: int(x[0])):
    b = int(b)
    lo += b * c
    hi += (b + 9) * c
w("  floor sum = %d" % lo)
w("  ceil  sum = %d" % hi)
w("  measured name_chars = %d" % u["name_chars"])
w("  in-bounds = %s" % (lo <= u["name_chars"] <= hi))
w("  mean offset above floor = %.4f" % ((u["name_chars"] - lo) / N))
w("  md's floor 38,341,410 matches? %s" % (lo == 38341410))
w("  md's ceil  55,821,110 matches? %s" % (hi == 55821110))
w("")

w("=== md section-2 table spot-checks ===")
w("  has_comma identity: rows-addr_empty = %d, has_comma = %d, equal=%s"
  % (N - u["addr_empty"], u["has_comma"], N - u["addr_empty"] == u["has_comma"]))
w("  comma-less rows = %d" % (N - u["addr_empty"] - u["has_comma"]))
w("  alpha_only/nonempty = %.4f%%" % (u["alpha_only_addr"] / (N - u["addr_empty"]) * 100))
w("")

w("=== null-placeholder arithmetic (md: 55,317 + 54,557 = 109,874 = 5.6470%) ===")
tk = dict(d["addr_tokens"]["US"])
nt = tk.get("null", 0)
w("  null token in test_s3 US = %d" % nt)
w("  addr_empty              = %d" % u["addr_empty"])
w("  sum                     = %d" % (nt + u["addr_empty"]))
w("  sum/rows                = %.4f%%" % ((nt + u["addr_empty"]) / N * 100))
w("  France null token       = %d" % dict(d["addr_tokens"]["France"]).get("null", 0))
w("  test_s3 addr_tokens list length = %d (TOPN cap 4000)" % len(d["addr_tokens"]["US"]))
w("  -> is 'null' inside the retained top-4000? %s" % ("null" in tk))
OUT.close()
