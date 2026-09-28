"""Official Amazon ML Challenge 2026 output contract utilities.

The pasted brief is treated as the authoritative contract for this module.
The parsing/validation helpers are pure; ``write_tsv`` creates parent
directories and replaces its target file atomically, so a failure mid-write
never leaves a partial file at the submission path. The module is stdlib-only
so it can be copied into the final submission package without dependency
surprises.
"""
from __future__ import annotations

import csv
import os
import tempfile
from pathlib import Path
from typing import Iterable, Mapping, Sequence

MATCHING_HEADER = ("source1_entity_id", "matched_entity_ids")
CANDIDATE_HEADER = ("source1_entity_id", "candidate_entity_ids")
TARGET_PREFIXES = ("S2-", "S3-")
OFFICIAL_HEADERS = (MATCHING_HEADER, CANDIDATE_HEADER)


def parse_id_list(value: str | None) -> list[str]:
    text = (value or "").strip()
    return [part.strip() for part in text.split(",") if part.strip()]


def validate_id_list(ids: Iterable[str], valid_targets: set[str], *, label: str) -> list[str]:
    errors: list[str] = []
    values = list(ids)
    if len(values) != len(set(values)):
        errors.append(f"{label}: duplicate target IDs")
    for value in values:
        if not value.startswith(TARGET_PREFIXES):
            errors.append(f"{label}: target ID lacks S2-/S3- prefix: {value}")
        elif value not in valid_targets:
            errors.append(f"{label}: target ID is absent from test targets: {value}")
    return errors


def validate_outputs(
    s1_ids: Iterable[str],
    target_ids: Iterable[str],
    matching_rows: Iterable[Sequence[str]],
    candidate_rows: Iterable[Sequence[str]],
) -> list[str]:
    """Validate both TSV row sets after parsing, without scoring them."""
    s1 = set(s1_ids)
    targets = set(target_ids)
    errors: list[str] = []
    parsed_matching = list(matching_rows)
    parsed_candidates = list(candidate_rows)
    for name, rows in (("matching_results", parsed_matching), ("candidate_pairs", parsed_candidates)):
        if any(len(row) != 2 for row in rows):
            errors.append(f"{name}: every row must contain exactly two tab-separated fields")
    def index_rows(rows: Sequence[Sequence[str]], name: str) -> dict[str, list[str]]:
        result: dict[str, list[str]] = {}
        for row in rows:
            if len(row) != 2:
                continue
            entity, value = row[0].strip(), row[1].strip()
            if entity in result:
                errors.append(f"{name}: duplicate source1_entity_id row: {entity}")
            result[entity] = parse_id_list(value)
        return result
    matching = index_rows(parsed_matching, "matching_results")
    candidates = index_rows(parsed_candidates, "candidate_pairs")
    for name, mapping in (("matching_results", matching), ("candidate_pairs", candidates)):
        missing = s1 - set(mapping)
        extra = set(mapping) - s1
        if missing:
            errors.append(f"{name}: missing {len(missing)} Source 1 entities")
        if extra:
            errors.append(f"{name}: contains {len(extra)} unknown Source 1 IDs")
    for entity, ids in matching.items():
        errors.extend(validate_id_list(ids, targets, label=f"matching_results[{entity}]"))
        not_candidates = set(ids) - set(candidates.get(entity, ()))
        if not_candidates:
            errors.append(f"matching_results[{entity}]: {len(not_candidates)} final IDs absent from candidate_pairs")
    for entity, ids in candidates.items():
        errors.extend(validate_id_list(ids, targets, label=f"candidate_pairs[{entity}]"))
    return errors


def write_tsv(path: Path, header: tuple[str, str], rows: Mapping[str, Iterable[str]]) -> None:
    """Atomically write ``rows`` to ``path`` under an official header.

    The data is serialised into a temporary file in the destination directory
    and moved into place with :func:`os.replace` only after the whole write
    succeeds, so a mid-serialisation failure can never leave a half-written file
    at the official submission path.
    """
    if tuple(header) not in OFFICIAL_HEADERS:
        raise ValueError(
            f"header must be one of the official headers "
            f"{[list(h) for h in OFFICIAL_HEADERS]}, got {list(header)!r}"
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=str(path.parent), prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle, delimiter="\t", lineterminator="\n", quoting=csv.QUOTE_NONE)
            writer.writerow(header)
            for entity, ids in rows.items():
                writer.writerow((entity, ",".join(ids)))
        os.replace(tmp_name, path)
    except BaseException:
        # Never leave the partial temp file behind, and let the error propagate.
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise
