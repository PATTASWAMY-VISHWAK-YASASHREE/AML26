"""DuckDB compatibility probe.

The point of this probe is *semantic* compatibility, not just API survival: each
expression is paired with an expected value, so a DuckDB release that changes the
meaning of an expression (e.g. ``list_slice`` bounds or ``list_intersect``
ordering) is detected rather than silently producing different results.

Exits 0 when every probe matches, 1 when any probe fails or errors.
"""
from __future__ import annotations

import sys

import duckdb

# (label, SQL expression, expected value)
# Values are Python literals; they are compared after normalising list/tuple
# ordering for the probes whose ordering DuckDB does not guarantee.
PROBES: list[tuple[str, str, object]] = [
    ("version-ish scalar", "SELECT 1 + 1", 2),
    ("list literal", "SELECT [1, 2, 3]", [1, 2, 3]),
    ("list_slice closed", "SELECT list_slice([10, 20, 30, 40, 50], 2, 4)", [20, 30, 40]),
    # list_slice has no 2-arg form in DuckDB 1.5; negative bounds are explicit here.
    ("list_slice negative", "SELECT list_slice([10, 20, 30, 40, 50], -2, -1)", [40, 50]),
    ("list_len", "SELECT len([1, 2, 3])", 3),
    ("list_contains", "SELECT list_contains([1, 2, 3], 2)", True),
    ("list_intersect", "SELECT list_sort(list_intersect([1, 2, 3, 4], [3, 4, 5]))", [3, 4]),
    ("list_distinct", "SELECT list_sort(list_distinct([1, 1, 2, 2, 3]))", [1, 2, 3]),
    ("list_concat", "SELECT list_concat([1, 2], [3])", [1, 2, 3]),
    ("list_transform", "SELECT list_transform([1, 2, 3], x -> x * 2)", [2, 4, 6]),
    ("string_split", "SELECT string_split('a,b,c', ',')", ["a", "b", "c"]),
    ("regexp_matches", "SELECT regexp_matches('S1-200000', '^S1-\\d+$')", True),
    ("regexp_replace", "SELECT regexp_replace('a1b2', '\\d', '#', 'g')", "a#b#"),
    ("string_agg", "SELECT string_agg(x, '|' ORDER BY x) FROM (VALUES ('b'), ('a')) t(x)", "a|b"),
    ("struct field", "SELECT {'a': 1, 'b': 2}.b", 2),
    # Struct lists are 1-BASED in DuckDB: [0] and [3] are out of range (NULL),
    # [1] is the first element.  If a release ever changes this, this probe fires.
    ("list of struct first", "SELECT [{'a': 1}, {'a': 2}][1].a", 1),
    ("list of struct second", "SELECT [{'a': 1}, {'a': 2}][2].a", 2),
    ("list of struct out of range", "SELECT [{'a': 1}, {'a': 2}][0].a", None),
    ("date diff", "SELECT date_diff('day', DATE '2026-01-01', DATE '2026-02-01')", 31),
    ("strftime", "SELECT strftime(DATE '2026-03-05', '%Y-%m-%d')", "2026-03-05"),
    ("median of list", "SELECT median(x) FROM (VALUES (1), (2), (3)) t(x)", 2.0),
    ("quantile", "SELECT quantile_cont(x, 0.5) FROM (VALUES (1), (2), (3)) t(x)", 2.0),
    ("array agg order", "SELECT list(x ORDER BY x DESC) FROM (VALUES (1), (2), (3)) t(x)", [3, 2, 1]),
    ("round half up", "SELECT round(2.5)", 3.0),
    ("greatest", "SELECT greatest(1, 9, 5)", 9),
    ("null coalesce", "SELECT coalesce(NULL, 7)", 7),
    # fetchone() yields a scalar for a plain projection, so aggregate to a list
    # to make the expected value an actual list.
    ("group by having", "SELECT list(x ORDER BY x) FROM (VALUES (1), (1), (2)) t(x) GROUP BY x HAVING count(*) > 1", [1, 1]),
]

# Probes whose result order DuckDB does not promise; compare as sorted lists.
UNORDERED = {"list_intersect", "list_distinct"}


def normalise(value: object, unordered: bool) -> object:
    if isinstance(value, (list, tuple)):
        items = list(value)
        return sorted(items, key=repr) if unordered else items
    return value


def equal(got: object, expected: object, unordered: bool) -> bool:
    got, expected = normalise(got, unordered), normalise(expected, unordered)
    if isinstance(expected, float) or isinstance(got, float):
        try:
            return abs(float(got) - float(expected)) < 1e-9
        except (TypeError, ValueError):
            return False
    return got == expected


def run(con: "duckdb.DuckDBPyConnection") -> int:
    failures = 0
    for label, sql, expected in PROBES:
        try:
            got = con.execute(sql).fetchone()[0]
        except Exception as exc:  # noqa: BLE001 - any DuckDB error is a failure
            print(f"FAIL  {label}: raised {type(exc).__name__}: {exc}")
            failures += 1
            continue
        unordered = label in UNORDERED
        if equal(got, expected, unordered):
            print(f"ok    {label}: {got!r}")
        else:
            print(f"FAIL  {label}: got {got!r}, expected {expected!r}")
            failures += 1
    total = len(PROBES)
    print(f"\n{total - failures}/{total} probes passed")
    return failures


def main() -> int:
    con = duckdb.connect()
    try:
        print(f"duckdb {duckdb.__version__}\n")
        failures = run(con)
    finally:
        con.close()
    if failures:
        print(f"probe FAILED: {failures} expression(s) did not match expectations")
        return 1
    print("probe OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
