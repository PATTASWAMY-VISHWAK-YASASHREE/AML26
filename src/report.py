"""Render the deep profile JSONs as readable tables.

Usage: & .venv\\Scripts\\python.exe report.py [which]
  which = s1 | s2 | s3 | all  (default all)
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
P2 = os.path.join(ROOT, "analysis_out", "profile2")


def pct(a, b):
    return f"{100 * a / b:.2f}%" if b else "n/a"


def show(split, src):
    p = os.path.join(P2, f"{split}_s{src}.json")
    if not os.path.exists(p):
        print(f"(missing {p})")
        return
    d = json.load(open(p, encoding="utf-8"))
    dup = d["dup_exact_name_addr"]
    print(f"\n{'=' * 78}")
    print(f"{split.upper()} SOURCE {src}   rows={d['rows']:,}   "
          f"cols={d['cols']}")
    print(f"  exact-duplicate name+addr: excess={dup['dup_excess']:,} "
          f"({pct(dup['dup_excess'], dup['rows_hashed'])})  "
          f"largest_group={dup['largest_group']}  "
          f"groups={dup.get('groups_involved', 0):,}")
    for c, s in d["by_country"].items():
        r = s["rows"]
        print(f"\n  --- {c}  rows={r:,} "
              f"({pct(r, d['rows'])} of file) ---")
        print(f"   completeness : name_empty={s['name_empty']:,} "
              f"name_ws_only={s['name_ws_only']:,} "
              f"addr_empty={s['addr_empty']:,} "
              f"addr_ws_only={s['addr_ws_only']:,}")
        print(f"                  both_empty={s['both_empty']:,}  "
              f"name_empty_but_addr={s['name_empty_addr_present']:,}  "
              f"inner_ws_name={s['name_dup_ws']:,}")
        print(f"   name length  : mean={s['name_chars'] / r:.2f}  "
              f"min={s['name_len_min']} max={s['name_len_max']}  "
              f"len1={s['name_len_1']:,} <=3={s['name_len_le3']:,} "
              f">=100={s['name_len_ge100']:,}")
        print(f"   name tokens  : mean={s['name_tokens'] / r:.2f}")
        nh = s["name_len_hist"]
        tot = sum(nh.values()) or 1
        top = sorted(nh.items(), key=lambda kv: -kv[1])[:6]
        print("   name len hist: " + "  ".join(
            f"{k}-{int(k) + 9}:{v:,}({100 * v / tot:.1f}%)" for k, v in top))
        print(f"   addr length  : mean={s['addr_chars'] / r:.2f}  "
              f"min={s['addr_len_min']} max={s['addr_len_max']}  "
              f"<=10={s['addr_len_le10']:,} >=80={s['addr_len_ge80']:,}")
        print(f"   char classes : nonascii_name_rows={s['non_ascii_name']:,} "
              f"({pct(s['non_ascii_name'], r)})  "
              f"nonascii_addr_rows={s['non_ascii_addr']:,} "
              f"({pct(s['non_ascii_addr'], r)})")
        print(f"                  name nonascii_chars="
              f"{s['nonascii_name_chars']:,}/{s['name_chars']:,} "
              f"({pct(s['nonascii_name_chars'], s['name_chars'])})")
        print(f"                  name digit_chars={s['digit_chars_name']:,} "
              f"punct_chars={s['punct_chars_name']:,}  "
              f"has_punct={s['name_has_punct']:,} "
              f"has_upper={s['name_has_upper']:,} "
              f"all_lower={s['name_all_lower']:,}")
        print(f"   scripts      : {s['script_counts']}")
        print(f"                  latin_only={s['latin_only_name']:,} "
              f"no_latin={s['no_latin_name']:,} "
              f"deva_only={s['devanagari_only_name']:,} "
              f"mixed={s['script_mix_name']:,} "
              f"nonascii_only={s['nonascii_only_name']:,}")
        cb = s["script_combo_name"]
        if cb:
            print("   mixed combos : " + "  ".join(
                f"{k}:{v:,}" for k, v in list(cb.items())[:5]))
        print(f"   legal forms  : rows_with_legal={s['legal_rows']:,} "
              f"({pct(s['legal_rows'], r)})  pos first={s['legal_pos_first']:,} "
              f"last={s['legal_pos_last']:,} mid={s['legal_pos_mid']:,}")
        la = s["legal_any"]
        print("   legal top    : " + "  ".join(
            f"{k}:{v:,}" for k, v in la[:8]))
        print(f"   noise        : lead={s['noise_lead_rows']:,} "
              f"trail={s['noise_trail_rows']:,} "
              f"any={s['noise_any_rows']:,} ({pct(s['noise_any_rows'], r)})")
        print("   noise lead   : " + "  ".join(
            repr(k) + f":{v:,}" for k, v in s["noise_lead"][:8]))
        print("   noise trail  : " + "  ".join(
            repr(k) + f":{v:,}" for k, v in s["noise_trail"][:8]))
        print(f"   postal       : dig5={s['dig5']:,} dig6={s['dig6']:,} "
              f"any_digit={s['any_digit_addr']:,} "
              f"({pct(s['any_digit_addr'], r)})  "
              f"alpha_only={s['alpha_only_addr']:,}  "
              f"postcode_at_end={s['postcode_at_end']:,}")
        print(f"   addr struct  : comps_mean={s['addr_comps'] / r:.2f}  "
              f"housenum={s['addr_housenum']:,} "
              f"({pct(s['addr_housenum'], r)})  "
              f"trailing_comma={s['addr_trailing_comma']:,}")
        print(f"                  landmark={s['addr_has_landmark']:,} "
              f"({pct(s['addr_has_landmark'], r)})  "
              f"ends_numeric={s.get('addr_ends_numeric', 0):,} "
              f"({pct(s.get('addr_ends_numeric', 0), r)})  "
              f"no_postal={s.get('addr_no_postal', 0):,} "
              f"({pct(s.get('addr_no_postal', 0), r)})")
        print(f"   case/diacrit : diacritic_names={s['name_has_diacritic']:,} "
              f"({pct(s['name_has_diacritic'], r)})  "
              f"allcaps_token={s['name_allcaps_token']:,}")


def main():
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    for split in ("train", "test"):
        for src in (1, 2, 3):
            if which != "all" and which != f"s{src}":
                continue
            show(split, src)


if __name__ == "__main__":
    main()
