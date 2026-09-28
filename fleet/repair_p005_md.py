"""Reassemble the P005 deliverable, which was written with its sections spliced.

The file on disk has the right content but in the wrong ORDER, so it reads as if
parts were deleted:

  line  75  ... | Mean name tokens/row | 3.6569 | ...
  line  76  (blank)                      <- section 3 table ends early
  line 301  | Address digits/row | ...   <- two orphaned rows of that same table
  line 304  The two mean-address ...     <- their explanatory paragraphs
  line 178  ### 7. Relation to the two REFUTED findings   <- heading, EMPTY
  line 285  - **REFUTED-1 ...**          <- that section's body, at the file end
  line 215  - **No `n_comps` ... This is the   <- sentence cut mid-clause
  line 264    single largest blind spot ...      <- its continuation, at the end
  line 310  **Consistency check on the histogram** <- belongs to section 4

This script reorders those fragments into the order the headings imply, using
1-indexed inclusive line ranges against the CURRENT file, and refuses to run if
any anchor line does not contain the expected text. Read-only on the profile;
rewrites only the P005 .md, and leaves the .json sidecar untouched.
"""
from __future__ import annotations

import os

ROOT = os.path.dirname(os.path.abspath(__file__))
DOC = os.path.join(ROOT, "analysis_out", "findings", "P005_US_test_s2_shape.md")

# (start, end) inclusive, 1-indexed, of each block in the CURRENT file, in the
# order the finished document needs them.
BLOCKS = [
    (1, 75),      # title, headline, findings 1-2, section 3 heading + table
    (301, 302),   # orphaned section-3 table rows
    (304, 308),   # their explanatory paragraphs
    (77, 95),     # section 4, name-length histogram
    (310, 314),   # the histogram consistency check
    (96, 177),    # sections 5-6, sampling power and the comma invariant
    (178, 178),   # section 7 heading (its body is a separate block below)
    (285, 299),   # section 7 body: relation to the two REFUTED findings
    (181, 214),   # interpretation
    (215, 215),   # the first half of the truncated n_comps gap
    (264, 283),   # its continuation, plus the remaining gap bullets
    (217, 262),   # recommendations and the confidence-marker table
]

# Lines that must contain this text, or the script aborts rather than silently
# reassembling a file it no longer understands.
ANCHORS = {
    75: "Mean name tokens/row",
    77: "### 4. Name-length histogram",
    178: "### 7. Relation to the two REFUTED findings",
    181: "## Interpretation",
    204: "## Gaps",
    215: "No `n_comps`",
    217: "## Recommendations",
    247: "## Confidence markers",
    262: "Component order is inconsistent",
    264: "single largest blind spot",
    283: "unique-business count is derivable",
    285: "REFUTED-1",
    298: "but it corrects a number",
    299: "file-independent",
    301: "Address digits/row",
    310: "Consistency check on the histogram",
}

# Every line must be consumed exactly once: no dropped prose, no duplication.
SEEN: list[int] = []
CONTENT_LINES = 314  # 315 is the empty string after the trailing newline


def main() -> None:
    with open(DOC, encoding="utf-8") as fh:
        src = fh.read().split("\n")

    for lineno, needle in ANCHORS.items():
        if lineno > len(src):
            raise SystemExit(f"ABORT: file has {len(src)} lines, expected {lineno}")
        if needle not in src[lineno - 1]:
            raise SystemExit(f"ABORT: line {lineno} does not contain {needle!r}\n"
                             f"  found: {src[lineno - 1]!r}")

    # Any line the blocks do not claim must be blank, or prose is being dropped.
    claimed = {n for start, end in BLOCKS for n in range(start, end + 1)}
    orphans = [n for n in range(1, CONTENT_LINES + 1)
               if n not in claimed and src[n - 1].strip()]
    if orphans:
        raise SystemExit(f"ABORT: unclaimed non-blank lines {orphans}")

    out: list[str] = []
    for start, end in BLOCKS:
        block = src[start - 1:end]
        SEEN.extend(range(start, end + 1))
        if not out or (out[-1].strip() and block[0].strip()):
            out.append("")          # exactly one blank line between blocks
        out.extend(block)

    if sorted(SEEN) != sorted(claimed) or len(SEEN) != len(set(SEEN)):
        dupes = sorted({n for n in SEEN if SEEN.count(n) > 1})
        raise SystemExit(f"ABORT: duplicated={dupes}")

    with open(DOC, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(out).rstrip("\n") + "\n")

    rejoined = unwrap_bullet(out)

    with open(DOC, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(rejoined).rstrip("\n") + "\n")

    print(f"reassembled {DOC}")
    print(f"  {len(src)} lines in, {len(rejoined)} lines out, "
          f"{len(claimed)} source lines placed, 0 dropped")


def unwrap_bullet(lines: list[str]) -> list[str]:
    """Rejoin a bullet that was cut in half by the splice.

    The truncated `n_comps` gap arrived as two blocks, and the blank line that
    separated them survived into the middle of one sentence. A blank line between
    a line ending mid-sentence and an indented continuation is dropped.
    """
    out: list[str] = []
    for i, line in enumerate(lines):
        is_split = (line == "" and out and out[-1].rstrip().endswith("is the")
                    and i + 1 < len(lines)
                    and lines[i + 1].startswith("  "))
        if not is_split:
            out.append(line)
    return out


if __name__ == "__main__":
    main()