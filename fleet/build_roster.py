"""Generate the analysis roster (127 tasks, not a fixed 120).

Two deliverable families, per the user's instruction:
  A. data-profile dictionary  (P*) - descriptive statistics of the dataset
  B. dictionary expansion     (D*) - evidence mined from the data to improve
                                   the upstream normalisation dictionaries

Each task is emitted as a standalone JSON work order so any agent can be spawned
with a single self-contained prompt and no shared mutable state.

Agents read ONLY the compact profile in analysis_out/profile/ (575 KB each), never
the 2.4 GB of raw TSVs, because this machine has under 1 GB of free RAM.

ID STABILITY IS LOAD-BEARING. An earlier version numbered every task with a bare
sequential counter, so any change to the task list renumbered the whole B family
and detached ten finished reports from the work orders that produced them. The
ledger in analysis_out/id_ledger.json now pins each completed
(family, kind, dictionary, country) slot to the id its deliverable already uses,
resolve_id() honours it, and next_d_id() skips pinned ids so a fresh task can
never overwrite a finished one. emit() refuses duplicate ids, the pre-write pass
deletes the previous generation's task files, and a post-write self-check fails
the build if any filename disagrees with its id.
"""
from __future__ import annotations

import json
import os

ROOT = os.path.dirname(os.path.abspath(__file__))
OUTDIR = os.path.join(ROOT, "analysis_out", "tasks")
os.makedirs(OUTDIR, exist_ok=True)

COUNTRIES = ["US", "India", "France"]
SOURCES = ["train_s1", "train_s2", "train_s3", "test_s1", "test_s2", "test_s3"]

BASE_RULES = """
HARD CONSTRAINTS
- READ-ONLY on the dataset and on _upstream/. Never modify, move or delete them.
- Read ONLY the compact profile JSON files in analysis_out/profile/. They are small
  (575 KB each) because this machine has under 1 GB of free RAM. Do NOT open the raw
  *.tsv files under amazon_ml_2026_research/student_resource/dataset/ - a 480 MB scan
  was OOM-killed on this box and will kill you too.
- You MAY read _upstream/src/*.py to check what a dictionary actually does.
- You may write exactly two files: your deliverable .md, and a .json sidecar in
  analysis_out/findings/ holding the structured numbers.
- Never fetch anything from the network. The competition prohibits external data
  lookup, with immediate disqualification as the penalty.

EVIDENCE STANDARD
Every number you state must be traceable to a field in the profile JSON. If a field
you need was not collected, say so explicitly and mark the gap - do not estimate and
do not invent a plausible-looking figure. Distinguish clearly between what the data
shows and what you are inferring.
""".strip()

DICT_FILES = {
    "FR_REGIONS": "_upstream/src/normalize.py",
    "US_STATES": "_upstream/src/normalize.py",
    "IN_STATES": "_upstream/src/normalize.py",
    "ADDR_CANON_FR": "_upstream/src/normalize.py",
    "ADDR_CANON_COMMON": "_upstream/src/normalize.py",
    "LEET": "_upstream/src/normalize.py",
    "ADDR_GENERIC": "_upstream/src/keys.py",
    "indic_token_dict": "_upstream/src/resources/indic_token_dict.json",
}

ALREADY_CHECKED = """
ALREADY CHECKED AND REFUTED - DO NOT REDO THIS WORK
Two findings from an earlier code review were tested against the real data and
are FALSE. Do not re-derive them; if your evidence appears to support either,
say so explicitly and show the numbers, because that would be significant.

REFUTED-1 "French postal codes are discarded by the pin guard."
  normalize.py captures `pin` only when len(n)==6 and country=="India", so
  France has no postal signal. MEASURED: France dig5/row = 0.004 in test_s1
  (0.005 in test_s2) versus US 0.110. Only 0.413% of the 259,452 France rows in
  test_source1 contain a standalone 5-digit number. French addresses carry house
  numbers ("175 Boulevard du President Franklin Roosevelt"), not postcodes. The
  pin guard is real but its impact is on US source-1 rows, not France.
  ALREADY-COVERED CORRECTION: the pin gap does affect US source-1 (dig6/row
  0.001 there vs 0.013-0.014 in US source-2/3). Do not re-derive the France
  version.

REFUTED-2 - PARTIALLY RE-SCOPED, READ THIS BEFORE RELYING ON IT.
  Original claim: "FR_REGIONS is too thin, so France has no usable state signal."
  MEASURED by replicating normalize_address's exact component matching:
  state resolves for 100.00% of France rows (259,452 / 259,452, zero unmatched).
  The reason given was that this dataset uses only three modern regions - hauts-de-
  france (101,521), nouvelle-aquitaine (85,197), pays de la loire (72,734) - all
  already mapped, plus ~1,100 rows of legacy names.

  *** THAT 100% FIGURE IS A test_source1-ONLY DENOMINATOR. IT IS NOT THE ANSWER
  *** FOR FRANCE AS A WHOLE. TWO AGENTS INDEPENDENTLY MEASURED THIS.

  test_source1 is only 259,452 of 1,694,445 France test rows = 15.31%. The
  arithmetic that produced "100%" (101,521 + 85,197 + 72,734 = 259,452) sums to
  exactly the s1 row count, which is the tell.

  Across all three test sources, at most 1,204,739 of 1,694,445 France rows
  (71.10%) can resolve a state through FR_REGIONS. 489,706 rows (28.90%)
  provably cannot, from a maximal French gazetteer. These are upper bounds
  (union bound over the 14 FR_REGIONS keys), not direct counts - component
  structure is discarded by the profile builder.

  ROOT CAUSE: s1 encodes geography with REGION names, but test_s2 and test_s3
  encode it with DEPARTMENT names, and most of those departments are absent from
  FR_REGIONS. Examples from addr_tokens[France]: gironde 62 (s1) vs 75,104 (s2)
  and 75,621 (s3); nord 200 (s1) vs 75,362 (s2) and 76,449 (s3); atlantique
  253 (s1) vs 63,697 (s2) and 64,398 (s3).

  SO: do NOT re-derive the s1-scoped 100% result, and do NOT treat "France's
  region handling is fine" as settled. The correct statement is that FR_REGIONS
  is adequate for 15.31% of French rows and materially inadequate for the other
  84.69%. If your work touches French geography, measure across s1/s2/s3
  separately and never quote a single-source rate as a France-wide rate.

  *** UNRESOLVED CONTRADICTION - THE 71.10% IS NOT SETTLED. ***
  A second agent (D077) measured the SAME population the other way and got
  2.5620% unresolvable / 97.4380% ceiling, versus 28.90% / 71.10% here. The two
  differ by an order of magnitude on identical input. The most likely cause is
  the RESOLUTION CRITERION (D073 uses a maximal exact gazetteer and takes union
  bounds; D077 appears to apply a looser test), not the data. Until someone
  reconciles them under one stated criterion, BOTH numbers are provisional and
  neither should be used to size a fix. Reconciling them is high-value and
  currently unowned - if you do it, report both figures under your criterion.

  STILL TRUE from the original finding: the missing self-map loop entry
  (normalize.py:252 omits FR_REGIONS) is a real code defect with ZERO measurable
  effect on this dataset, because all 14 canonical values (hdf, idf, naq, pdl)
  occur 0 times as input tokens. NOTE: this "zero effect" statement is about the
  SELF-MAP LOOP only. It is NOT evidence that the s2/s3 department gap is
  harmless, and the two must not be conflated.

WHAT THIS MEANS FOR YOU
Do NOT assume France's region handling is settled - the s2/s3 department gap is
real and still open. But it has now been measured, so do not re-derive the
denominator error either. Work on the parts that remain unexplored:
  - WHICH departments test_s2/test_s3 actually use, and how many FR_REGIONS
    entries would be needed to cover them. Do this across s1/s2/s3 separately.
  - France's CITY distribution (bordeaux, nantes, lille, tourcoing, dunkerque,
    roubaix, calais dominate) and whether city is handled as a feature
  - the ~1,100 legacy-region rows and the 0.42% France rows with no digits
  - whether address COMPONENT ORDER is consistent (French rows put region
    before or after city inconsistently: "Bordeaux, Nouvelle-Aquitaine" vs
    "Nouvelle-Aquitaine, La Teste-de-Buch")
  - anything the profile shows that nobody has asked about yet

A SEPARATE MEASURED FINDING you should not re-derive: ADDR_CANON_FR has no
entries for the French function words de, la, du, des, le, les. Within test_s2
alone they account for 731,158 of the 4,745,780 listed France address-token
mass (15.41%), against 0.37% for US and 0.01% for India - France is ~42x the US
function-word rate. They are unhandled, so they enter the IDF-weighted features
(features.py:120-123) and dilute IDF weighting for every French pair. Note the
s2 share is 15.41%; quoting the per-token counts (de 1,050,023, la 481,231,
du 220,355, des 199,183) against the s2 denominator would be wrong, because
those four counts are summed across all three test files. This is already
established; build on it rather than re-measuring it.
""".strip()

TASKS: list[dict] = []
BY_ID: dict[str, dict] = {}

# Which countries each dictionary legitimately applies to. Country-scoped
# tables (STATE_MAPS keys) must NOT be crossed with the wrong country.
DICT_SCOPE = {
    "FR_REGIONS": ["France"],
    "US_STATES": ["US"],
    "IN_STATES": ["India"],
    "indic_token_dict": ["India"],
    "ADDR_CANON_FR": ["France"],
    "ADDR_CANON_COMMON": ["US", "India", "France"],
    "LEET": ["US", "India", "France"],
    "ADDR_GENERIC": ["US", "India", "France"],
}

# ---------------------------------------------------------------------------
# ID STABILITY
# Regenerating the roster must NOT renumber tasks that agents have already
# completed, or every finished deliverable is orphaned from its work order. An
# earlier country-scope fix silently changed 24 B-tasks into 13, which shifted
# every D-id and broke the link between ten completed reports and their tasks.
#
# Rule: an id already on disk is REUSED for the new task that covers the same
# (dictionary, country) slot; only genuinely new slots take fresh ids. The
# ledger in analysis_out/id_ledger.json records the mapping.
# ---------------------------------------------------------------------------
LEDGER = os.path.join(ROOT, "analysis_out", "id_ledger.json")
SLOT2ID: dict[tuple, str] = {}
if os.path.exists(LEDGER):
    with open(LEDGER, encoding="utf-8") as f:
        for slot, tid in json.load(f).items():
            key = tuple(json.loads(slot))
            SLOT2ID[key] = tid

# Every id the ledger has already handed out, whether or not this build re-emits
# it. A quarantined slot's id is still spoken for - reusing it would resurrect a
# number that a completed report already answers to.
RESERVED_IDS: set[str] = set(SLOT2ID.values())


def id_for(slot: tuple) -> str:
    """Stable id for a (family, kind, dictionary, country) slot."""
    if slot in SLOT2ID:
        return SLOT2ID[slot]
    return ""


def next_d_id(default_tid: str) -> str:
    """First unused D-id at or after default_tid.

    Skipping is required, not cosmetic. The ledger pins ids such as D071 to a
    specific finished report, and the sequential counter eventually walks onto
    them. Emitting a second, different task as D071 would give two work orders
    the same number - which is exactly BUG_2, the silent overwrite.
    """
    num = int(default_tid[1:])
    while f"D{num:03d}" in RESERVED_IDS or f"D{num:03d}" in BY_ID:
        num += 1
    return f"D{num:03d}"


def resolve_id(default_tid: str, slot: tuple | None = None) -> str:
    """Pin a slot to its ledger id, else take the next free sequential id.

    The deliverable filename embeds the id, so callers must resolve the id
    BEFORE building the deliverable path and use the resolved value in both.
    Otherwise a pinned task still declares a filename that does not exist.
    """
    if slot:
        pinned = id_for(slot)
        if pinned:
            return pinned
    if default_tid.startswith("D"):
        return next_d_id(default_tid)
    return default_tid


def emit(tid, family, title, question, inputs, deliverable):
    if tid in BY_ID:
        raise ValueError(
            f"id collision: {tid!r} already emitted for "
            f"{BY_ID[tid]['deliverable']!r}; cannot also emit {deliverable!r}. "
            f"Add the slot to id_ledger.json or rename the duplicate."
        )
    task = {
        "id": tid, "family": family, "title": title, "question": question,
        "inputs": inputs, "deliverable": deliverable,
        "base_rules": BASE_RULES, "already_checked": ALREADY_CHECKED,
    }
    TASKS.append(task)
    BY_ID[tid] = task
    return task


def build():
    n = 0

    # ------------- Family A: data-profile dictionary -------------
    for c in COUNTRIES:                      # A1 shape, per country x source
        for s in SOURCES:
            n += 1
            emit(f"P{n:03d}", "A-profile",
                 f"[{c}] {s}: shape, null rates, length distribution",
                 "Report row counts, empty-name and empty-address rates, mean name and address "
                 "length, the name-length histogram, digit-in-name rate, comma-in-address rate, "
                 "and entity_id prefix validity for this slice. State what share of the file this "
                 "country is, and whether the slice is large enough to conclude from.",
                 [f"{s}.json"], f"analysis_out/findings/P{n:03d}_{c}_{s}_shape.md")

    for c in COUNTRIES:                      # A2 numeric / digit structure
        for s in SOURCES:
            n += 1
            emit(f"P{n:03d}", "A-profile",
                 f"[{c}] {s}: digit structure and address-number behaviour",
                 "The France-postcode hypothesis is already refuted, so do not re-test it. Instead "
                 "characterise what the digits actually ARE. For each slice report dig5/row, dig6/row, "
                 "total digit density, the share of addresses with no digits, and how digit density "
                 "differs between source 1 and sources 2/3 (this asymmetry is the real pin finding). "
                 "Quantify how many France addresses begin with a house number, and whether the house "
                 "number appears in a consistent position relative to the street word. State whether "
                 "house number is a reliable matching key or a noise source, and justify it.",
                 [f"{s}.json"], f"analysis_out/findings/P{n:03d}_{c}_{s}_numeric.md")

    for s in ["train_s1", "test_s1", "test_s2"]:   # A2b France-specific digit forensics
        n += 1
        emit(f"P{n:03d}", "A-profile",
             f"France digit forensics ({s}): what the numbers are",
             "France is the only country in the test set and is absent from training, so this is the "
             "highest-value profile work. Using the digit-density and alpha_only_addr fields, "
             "characterise precisely what numeric content French addresses carry. The known sample "
             "is house numbers (175, 30, 5 bis, 21 Chemin) plus a small tail of genuine 5-digit "
             "codes. Quantify: what share of France rows have a leading house number, what share have "
             "a 'bis'/'ter' suffix on it, and what share have no number at all. Then say which of "
             "these would be a useful blocking key and which would be actively harmful as one.",
             [f"{s}.json"], f"analysis_out/findings/P{n:03d}_fr_digits_{s}.md")

    for c in COUNTRIES:                      # A3 address component vocabulary
        for s in ["train_s1", "test_s1"]:
            n += 1
            emit(f"P{n:03d}", "A-profile",
                 f"[{c}] {s}: address component vocabulary",
                 "From addr_tokens, take the most frequent tokens and classify them as street-type "
                 "words, directionals, city/place words, numeric tokens, or noise. Report what "
                 "share of total token mass the top 100 account for, and whether the vocabulary is "
                 "country-distinct enough that country-scoped keys avoid cross-country collisions.",
                 [f"{s}.json"], f"analysis_out/findings/P{n:03d}_{c}_{s}_addr_vocab.md")

    for c in COUNTRIES:                      # A4 name vocabulary
        n += 1
        emit(f"P{n:03d}", "A-profile",
             f"[{c}] business-name vocabulary and structure",
             "From name_tokens, report the top tokens, the token-length distribution, and the "
             "share of mass in legal-suffix tokens (llc, inc, pvt, ltd, sarl, sa, sprl, bv, gmbh "
             "and equivalents). Identify tokens safe to drop in normalisation, and flag any that "
             "carry real signal and must not be dropped.",
             [f"{s}.json" for s in SOURCES],
             f"analysis_out/findings/P{n:03d}_{c}_name_vocab.md")

    for c in COUNTRIES:                      # A5 train/test shift, per country
        n += 1
        emit(f"P{n:03d}", "A-profile",
             f"[{c}] train vs test distribution shift",
             "Compare the same statistics between train and test slices for this country. Report "
             "any shift in null rates, length distributions, digit density or vocabulary "
             "distribution. This is the most important risk measurement in the analysis, because "
             "the test set is scored on a country absent from training.",
             [f"{s}.json" for s in SOURCES],
             f"analysis_out/findings/P{n:03d}_{c}_shift.md")

    for s in SOURCES:                        # A5 cross-country, per source
        n += 1
        emit(f"P{n:03d}", "A-profile",
             f"cross-country shift: {s}",
             "Compare this file's per-country distributions against each other. Quantify how "
             "different France is from US and India on every measured axis, and state plainly which "
             "axes France looks similar on and which it does not.",
             [f"{s}.json"], f"analysis_out/findings/P{n:03d}_{s}_crosscountry.md")

    for c in COUNTRIES:                      # A6 token tails
        for axis in ("name_tokens", "addr_tokens"):
            for s in ["train_s1", "test_s1"]:
                n += 1
                emit(f"P{n:03d}", "A-profile",
                     f"[{c}] {axis} tail analysis ({s})",
                     "Examine the tail past the top 4000 tokens. Estimate how much token mass "
                     "lives there, identify recurring patterns (typos, transliteration variants, "
                     "compound forms), and say whether current normalisation addresses them.",
                     [f"{s}.json"],
                     f"analysis_out/findings/P{n:03d}_{c}_{s}_{axis}_tail.md")

    for dname, path in DICT_FILES.items():        # B1 current-state audit
        n += 1
        tid = resolve_id(f"D{n:03d}", ("B", "audit", dname, None))
        emit(tid, "B-dictionary",
             f"audit current {dname}",
             f"Read {path} and report exactly what {dname} contains today: entry count, distinct "
             "canonical values, and structural defects (missing self-maps, empty values, overlaps, "
             "country scoping). Quote the source lines. Do not propose changes yet - this task "
             "establishes ground truth for the tasks that follow.",
             [path], f"analysis_out/findings/{tid}_audit_{dname}.md")

        # B2 evidence mining, per country.
        # FIX (n4 refused D079 as structurally impossible): the original loop
        # crossed every dictionary with every country, producing nonsense such as
        # "extend IN_STATES for US". STATE_MAPS is keyed strictly by country, so
        # a country-scoped table can only be mined for its OWN country. Each
        # dictionary now declares the countries it legitimately applies to.
        for c in DICT_SCOPE.get(dname, COUNTRIES):
            n += 1
            tid = resolve_id(f"D{n:03d}", ("B", "mine", dname, c))
            emit(tid, "B-dictionary",
                 f"mine evidence to extend {dname} for {c}",
                 f"Mine the profile for evidence about what {dname} should contain for {c}. For "
                 "region/state tables, look for frequent address tokens resembling region, "
                 "department or state names that are currently unhandled. For abbreviation "
                 "tables, look for token pairs that both occur often where one is plausibly an "
                 "abbreviation of the other. For leetspeak, look for digits or symbols inside "
                 "otherwise-alphabetic words. Rank candidates in a table with supporting "
                 "frequency, each marked CONFIRMED / LIKELY / SPECULATIVE.",
                 [f"{s}.json" for s in SOURCES],
                 f"analysis_out/findings/{tid}_mine_{dname}_{c}.md")

    for c in COUNTRIES:                      # A7 name-vs-address balance
        for s in SOURCES:
            n += 1
            emit(f"P{n:03d}", "A-profile",
                 f"[{c}] {s}: name-vs-address informativeness balance",
                 "For this slice, compare how much identifying signal the name carries versus the "
                 "address, using token counts and empty rates. Report whether records with an "
                 "empty address are still matchable by name alone, and estimate what share of rows "
                 "are name-only. This decides whether the name-only blocking fallback in "
                 "CAPS_NOADDR (keys.py) is adequate.",
                 [f"{s}.json"], f"analysis_out/findings/P{n:03d}_{c}_{s}_balance.md")

    for c in COUNTRIES:                      # A8 short/edge-length audit
        for s in ["train_s1", "test_s1"]:
            n += 1
            emit(f"P{n:03d}", "A-profile",
                 f"[{c}] {s}: short-name and edge-case audit",
                 "Using the length histogram and empty rates, quantify how many business names are "
                 "0-3 characters and how many addresses are near-empty. Short names are the main "
                 "source of false blocking collisions. State whether the token filters in keys.py "
                 "(min length 2, MAX_NT 4) would drop or mishandle them.",
                 [f"{s}.json"], f"analysis_out/findings/P{n:03d}_{c}_{s}_edge.md")

    for dname, path in DICT_FILES.items():   # B3 what still needs fixing
        n += 1
        tid = resolve_id(f"D{n:03d}", ("B", "gaps", dname, None))
        emit(tid, "B-dictionary",
             f"remaining gaps in {dname}",
             f"The earlier audit of {dname} in {path} produced claims that have since been REFUTED "
             "against real data - read the already_checked block before starting. Your job is to "
             "determine what, if anything, is STILL actually wrong with this dictionary, now that "
             "the France-postcode and France-region hypotheses are dead. Concretely: which entries "
             "are never or almost never fired by this dataset (dead weight), which tokens appear in "
             "the profile that this dictionary does NOT handle but should, and which entries could "
             "collide across countries. If the honest answer is 'this dictionary is fine for this "
             "dataset, the defect is theoretical only', say exactly that. A clean bill of health "
             "is a valid and useful result.",
             [f"{s}.json" for s in SOURCES],
             f"analysis_out/findings/{tid}_gaps_{dname}.md")

    for axis in ("name_tokens", "addr_tokens"):   # B4 city / place-name analysis
        n += 1
        tid = resolve_id(f"D{n:03d}", ("B", "fr_places", axis, None))
        emit(tid, "B-dictionary",
             f"France {axis}: city and place-name coverage",
             "France is the only scored country and is absent from training. The known French city "
             "distribution is extremely concentrated: bordeaux, nantes, lille, tourcoing, dunkerque, "
             "roubaix, calais, saint-nazaire, pessac, la teste-de-buch. Using the France {axis}, "
             "determine (a) the exact top-30 places and their shares, (b) what share of all French "
             "rows fall inside the top 10 places, and (c) whether the places are cleanly separable "
             "from street words. Then assess the risk: if many distinct businesses share one city "
             "and a street, does that create blocking collisions, and should city be a blocking key "
             "at all given France is one country in the index?",
             ["test_s1.json", "test_s2.json", "test_s3.json"],
             f"analysis_out/findings/{tid}_fr_places_{axis}.md")

    for dname in ("FR_REGIONS", "ADDR_CANON_FR"):   # B5 the real France work
        n += 1
        tid = resolve_id(f"D{n:03d}", ("B", "fr_order", dname, None))
        emit(tid, "B-dictionary",
             f"France: component-order robustness for {dname}",
             "French addresses put the region in inconsistent positions: the data contains both "
             "'Bordeaux, Nouvelle-Aquitaine' and 'Nouvelle-Aquitaine, La Teste-de-Buch' and "
             "'Nouvelle-Aquitaine, 3 Rue de Campeyraut'. Determine how normalize_address handles "
             "position-dependent logic, whether any code path assumes a fixed order, and whether "
             "reordering breaks or preserves matching. Also check the 'bis'/'ter' house-number "
             "suffixes (e.g. '5 bis Rue Pierre Dignac', '20 bis RUE jules lefebvre') against "
             "ADDR_CANON_FR and LEET: are they tokenised as street words, numbers, or noise? "
             "This is a concrete, unexamined France-specific risk.",
             ["test_s1.json", "test_s2.json", "test_s3.json"],
             f"analysis_out/findings/{tid}_fr_order_{dname}.md")

    # NO hard cap on the roster. A previous `TASKS[:120]` sliced 7 tasks off the
    # end with no warning, and those 7 were the highest-value France work in the
    # whole roster: D124/D125 city and place-name coverage, and D126/D127
    # component-order robustness (the `bis`/`ter` house-number risk called out in
    # AGENT_PROMPT.md as unexamined). A silent cap that preferentially eats the
    # best work is worse than no cap. plan_batches.py now sizes batches from
    # whatever this returns, so the fleet grows to cover the roster.
    tasks = list(TASKS)

    # Clear stale task files BEFORE writing. Without this, a rebuild leaves
    # behind the previous generation's files, so analysis_out/tasks/ accumulates
    # two rosters at once - which is how 135 files with 133 unique ids and two
    # colliding ids arose in the first place. Only *.json in OUTDIR is touched.
    keep = {f"{t['id']}.json" for t in tasks}
    removed = 0
    for fn in os.listdir(OUTDIR):
        if fn.endswith(".json") and fn not in keep:
            os.remove(os.path.join(OUTDIR, fn))
            removed += 1
    if removed:
        print(f"removed {removed} stale task file(s) from a previous generation")

    for t in tasks:
        # A task whose declared deliverable is already claimed by another id is
        # the exact failure that produced BUG_2; refuse to write it.
        with open(os.path.join(OUTDIR, f"{t['id']}.json"), "w", encoding="utf-8") as f:
            json.dump(t, f, indent=1, ensure_ascii=False)

    # Post-write self-check: filename == id, and no deliverable claimed twice.
    by_deliv: dict[str, str] = {}
    problems: list[str] = []
    for t in tasks:
        stem = os.path.splitext(os.path.basename(t["deliverable"]))[0]
        if not stem.startswith(t["id"] + "_"):
            problems.append(f"  {t['id']}: deliverable stem {stem!r} does not start with its id")
        prev = by_deliv.get(t["deliverable"])
        if prev:
            problems.append(f"  deliverable {t['deliverable']} claimed by both {prev} and {t['id']}")
        by_deliv[t["deliverable"]] = t["id"]
    if problems:
        raise SystemExit("roster self-check FAILED:\n" + "\n".join(problems))

    fams: dict[str, int] = {}
    for t in tasks:
        fams[t["family"]] = fams.get(t["family"], 0) + 1
    print(f"wrote {len(tasks)} task files to {OUTDIR}")
    print("by family:", fams)
    print("self-check: PASS (filenames match ids, no duplicate deliverables)")
    return tasks


if __name__ == "__main__":
    build()
