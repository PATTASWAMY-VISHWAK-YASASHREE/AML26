"""Refresh analysis_out/roster_state_manifest.json to match the repaired roster.

The 20:13 manifest described a broken roster (135 files, 133 unique ids, 6
quarantined orphans). build_roster.py has since been repaired and rebuilt, so
that description is now wrong in three ways - most importantly it records D075
as quarantined when that retirement was an error.

This keeps the stale body (renamed to 'stale_2020_13') so the incident history
survives, and prepends a 'CURRENT' section describing verified reality. It writes
CRLF line endings to match every other file in this tree.
"""
from __future__ import annotations

import json
import os

ROOT = os.path.dirname(os.path.abspath(__file__))
PATH = os.path.join(ROOT, "analysis_out", "roster_state_manifest.json")

with open(PATH, encoding="utf-8") as f:
    doc = json.load(f)

stale = {
    "_README": doc.pop("_README", []),
    "roster_state": doc.pop("roster_state", {}),
    **doc,
}

CURRENT: dict = {
    "as_of": "2026-09-26 ~21:10",
    "roster_state": {
        "task_files_on_disk": 127,
        "unique_ids": 127,
        "by_family": {"A-profile": 93, "B-dictionary": 34},
        "note": "no longer capped at 120 - the TASKS[:120] truncation was removed "
                "because it silently dropped the France place-name and "
                "component-order work (now D124-D127)",
    },
    "integrity_checks": {
        "CHECK_1_filename_vs_embedded_id": "PASS - every task file's name equals its id",
        "CHECK_2_id_collisions": "PASS - no id claimed twice (emit() now raises on collision)",
        "CHECK_3_completed_vs_live_roster": "PASS - every completed deliverable maps to a live task",
        "post_write_self_check": "PASS - build_roster.py verifies filename==id and unique "
                                 "deliverables, and aborts the build otherwise",
        "idempotence": "VERIFIED - re-running build_roster.py leaves 127 tasks and a "
                       "byte-identical id_ledger.json",
    },
    "fixes_applied_to_build_roster": [
        "BUG_3 root cause: resolve_id() is now actually called, honouring "
        "id_ledger.json; next_d_id() skips reserved ids so a fresh task can never "
        "land on a pinned number",
        "deliverable paths are built from the RESOLVED id and checked against it, so a "
        "pinned task can no longer declare a filename that does not exist",
        "removed TASKS[:120] truncation (127 tasks now, was 120)",
        "removed stale-generation task files before writing, so a shrinking roster "
        "cannot leave ghosts behind",
        "fixed cross-country task filenames: the loop is 'for s in SOURCES' but the name "
        "interpolated {c}, leaking the previous loop's country into all six (P052-P057 "
        "were all named *_France_*)",
    ],
    "batch1_deliverables": {
        "status": "11 reports in analysis_out/findings/; _upstream verified pristine "
                  "(git status and git diff both empty)",
        "D070_audit_FR_REGIONS": "14 entries over 4 canonical values (hdf,idf,naq,pdl) vs "
                                 "52 US / 37 India. Real defect is conflation of three admin "
                                 "levels, not thinness.",
        "D073_mine_FR_REGIONS_France": "REFUTES the inherited '100% of France rows' claim - "
                                       "it is test_s1-only (15.31% of French rows).",
        "D074_audit_US_STATES": "52 entries, 52 distinct canonical values, zero defects. "
                                "Cleanest dictionary in the file.",
        "D075_mine_US_STATES_US": "US_STATES needs no extension (47/52 keys evidenced; 'del' "
                                  "10,711 and 'penn' 3,084 are LIKELY additions). Found the "
                                  "two-incompatible-state-dialects defect.",
        "D078_audit_IN_STATES": "49 explicit pairs -> 37 distinct canonical values.",
    },
    "quarantined_orphans": {
        "count": 5,
        "location": "analysis_out/findings/deprecated_slots/",
        "meaning": "Completed, legitimate work whose (dictionary, country) slot the DICT_SCOPE "
                   "fix declared out-of-scope. KEPT, NOT DELETED. Valid negative results, not "
                   "missing work - do not count them toward roster completion.",
        "files": ["D071_mine_FR_REGIONS_US", "D072_mine_FR_REGIONS_India",
                  "D076_mine_US_STATES_India", "D077_mine_US_STATES_France",
                  "D079_mine_IN_STATES_US"],
    },
    "corrections_to_the_earlier_manifest": {
        "D075_was_quarantined_in_error":
            "The 20:13 manifest listed 6 orphans including D075_mine_US_STATES_US. That "
            "retirement was WRONG: 'mine US_STATES for US' is a LIVE slot under DICT_SCOPE "
            "(US_STATES: ['US']). The report is restored to analysis_out/findings/ and D075 "
            "is once again a live task. Verified against DICT_SCOPE directly.",
        "task_count": "135 -> 127 files, unique ids 133 -> 127. The old figures counted 4 "
                      "filename/id mismatches and 2 duplicate-id collisions, plus ghosts "
                      "left by the previous generation.",
    },
    "open_data_discrepancy_UNRESOLVED": {
        "id": "FR-STATE-DENOMINATOR",
        "summary": "Two completed reports disagree on how many France rows can resolve a state "
                   "via FR_REGIONS; the difference is methodological, not arithmetic.",
        "D073": "union bound over FR_REGIONS' 14 keys -> at most 1,204,739 of 1,694,445 France "
                "test rows (71.10%) resolvable; >=489,706 (28.90%) provably not. Sound as a "
                "LOWER bound on unresolved.",
        "D077": "counts only rows with no comma in a non-empty address -> 43,411 (2.5620%) "
                "hard no-state, ceiling 97.4380%.",
        "why_they_differ": "D077 tests a necessary STRUCTURAL condition (no comma => no "
                           "component to match); D073 tests a necessary DICTIONARY condition "
                           "(no region token => no match). D073's test is the stronger one, so "
                           "its 28.90% supersedes D077's 2.5620% as the operative figure. Both "
                           "agree the inherited 100% is false.",
        "note_on_D073_own_numbers": "D073's .md states 1,213,296 / 71.60% while its own .json "
                                    "sidecar states 1,204,739 / 71.10%. Recomputed from the "
                                    "profile, the sidecar is internally consistent "
                                    "(457,385+487,902+259,452 = 1,204,739; 1,694,445-1,204,739 = "
                                    "489,706 = 28.90%). The .md figures do not reconcile and "
                                    "should not be quoted.",
        "status": "recorded as provisional in build_roster.py's already_checked block; "
                  "reconciling under one stated criterion is still unowned and high-value",
    },
    "constraints_upheld": {
        "_upstream_pristine": "git status and git diff both empty (re-verified after the rebuild)",
        "dataset_unmodified": "no raw *.tsv opened; analysis reads only analysis_out/profile/",
        "network": "none used",
    },
    "next_step": "Resume dispatch from batch 2. First outstanding task is D080 (mine IN_STATES "
                 "for India); D080-D089 is the natural next batch of 10.",
}

out = {
    "_README": [
        "State manifest. First written 20:13 to record damage done by a build_roster.py re-run;",
        "UPDATED ~21:10 after the generator was repaired and the roster rebuilt.",
        "The stale 20:13 body is retained below under 'stale_2020_13' so the history of the",
        "incident is not lost. Re-checkable any time with reconcile_roster.py.",
    ],
    "CURRENT": CURRENT,
    "stale_2020_13": stale,
}

with open(PATH, "w", encoding="utf-8", newline="\r\n") as f:
    json.dump(out, f, indent=2, ensure_ascii=False)
    f.write("\n")

print(f"updated {PATH}")
print(f"top-level keys: {list(out)}")
print(f"CURRENT sections: {list(CURRENT)}")
