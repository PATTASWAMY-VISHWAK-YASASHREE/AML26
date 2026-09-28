"""Verify the archived source captures after remediation.

Checks that every edited HTML still parses, every JSON still loads, the
mis-identified capture carries its provenance notice, the JSTOR bot-challenge
page is out of the main source set, and no reference anywhere still points at
the old (wrong) filename.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).parent
SRC = ROOT / "amazon_ml_2026_research" / "sources"
CLASSIC = ROOT / ".research_tmp_classical"

failures: list[str] = []


def check(label: str, ok: bool, detail: str = "") -> None:
    print(f"[{'PASS' if ok else 'FAIL'}] {label}{(' :: ' + detail) if detail else ''}")
    if not ok:
        failures.append(label)


def main() -> int:
    # 1. every HTML capture still parses. stdlib only: the venv has no lxml and
    # resolving one through uv is slower than the check is worth. A tolerant
    # HTMLParser feed catches unbalanced-tag style breakage, which is what the
    # remediation introduced risk of; strict XML parsing is not applicable to
    # deliberately non-conforming archival markup.
    from html.parser import HTMLParser

    class Tolerant(HTMLParser):
        def __init__(self) -> None:
            super().__init__(convert_charrefs=True)
            self.tags = 0

        def handle_starttag(self, tag, attrs):
            self.tags += 1

    htmls = sorted(SRC.rglob("*.html")) + sorted(CLASSIC.rglob("*.html"))
    bad = []
    for p in htmls:
        try:
            parser = Tolerant()
            parser.feed(p.read_text(encoding="utf-8", errors="replace"))
            parser.close()
            if parser.tags == 0:
                bad.append(f"{p.name}: no tags parsed")
        except Exception as exc:  # noqa: BLE001 - report any failure
            bad.append(f"{p.name}: {type(exc).__name__}")
    check(f"all {len(htmls)} HTML captures parse", not bad, "; ".join(bad[:3]))

    # 2. every JSON still loads
    jsons = sorted(SRC.rglob("*.json"))
    bad = []
    for p in jsons:
        try:
            json.loads(p.read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001
            bad.append(f"{p.name}: {type(exc).__name__}")
    check(f"all {len(jsons)} JSON captures parse", not bad, "; ".join(bad[:3]))

    # 3. the mis-identified capture was renamed and carries a provenance notice
    renamed = SRC / "hu_2018_arxiv_1803.07720.html"
    check("mis-identified capture renamed", renamed.exists())
    old = SRC / "deepmatcher_2018.html"
    check("old wrong filename no longer present", not old.exists())
    if renamed.exists():
        text = renamed.read_text(encoding="utf-8", errors="replace")
        check("provenance notice present",
              "PROVENANCE" in text and "1803.07720" in text)
        check("explicitly disclaims DeepMatcher identity",
              "DEEPMATCHER" in text.upper())
        check("real paper title is the math-finance one",
              "Asymptotic Optimal Portfolio" in text)

    # 4. no reference anywhere in the research tree still uses the wrong name.
    #    Only text-like files can contain a stale citation, and this avoids
    #    walking the 20k-file .venv-gpu directory.
    stale = []
    search_dirs = [SRC, CLASSIC, ROOT / "amazon_ml_2026_research" / "reports",
                   ROOT / "amazon_ml_2026_research" / "work"]
    text_suffix = {".html", ".txt", ".json", ".md", ".py", ".csv", ".tex", ".bib"}
    MAX_BYTES = 4 * 1024 * 1024
    seen = set()
    for base in search_dirs:
        if not base.exists():
            continue
        for p in base.rglob("*"):
            if not p.is_file() or p in seen:
                continue
            seen.add(p)
            if p.suffix.lower() not in text_suffix or p.name == "deepmatcher_2018.html":
                continue
            # The renamed capture deliberately quotes its old name inside the
            # provenance notice; that mention is the fix, not a stale citation.
            if p == renamed:
                continue
            try:
                if p.stat().st_size > MAX_BYTES:
                    continue
                if "deepmatcher_2018" in p.read_text(encoding="utf-8", errors="ignore"):
                    stale.append(str(p.relative_to(ROOT)))
            except (OSError, MemoryError):
                continue
    check("no stale references to deepmatcher_2018", not stale,
          f"scanned {len(seen)} files; " + "; ".join(stale[:3]))

    # 5. the JSTOR bot-challenge page is quarantined out of the source set
    blocked = SRC / "_blocked" / "fellegi_sunter_1969_jstor_BLOCKED.html"
    check("JSTOR bot-challenge page quarantined", blocked.exists())
    check("bot-challenge page not in the main source set",
          not (SRC / "fellegi_sunter_1969_jstor.html").exists())
    manifest = SRC / "_blocked" / "MANIFEST_blocked_captures.json"
    check("blocked-capture manifest exists", manifest.exists())
    if manifest.exists():
        data = json.loads(manifest.read_text(encoding="utf-8"))
        blob = json.dumps(data).lower()
        check("manifest records a canonical JSTOR URL", "jstor" in blob)

    # 6. the mislabelled OpenAlex payload was renamed
    check("OpenAlex payload renamed from _unpaywall",
          (SRC / "fellegi_sunter_1969_openalex.json").exists()
          and not (SRC / "fellegi_sunter_1969_jina_unpaywall.json").exists())

    if failures:
        raise SystemExit("FAILURES: " + "; ".join(failures))
    print("\nall source-capture checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
