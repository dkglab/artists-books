#!/usr/bin/env python3
"""Build data.json for the subject reconciliation page (#164 follow-up).

The page reviews sources/subjects/pr164-review.csv: the rows where Priya's
subject pass in #164 differs from decisions.csv (Mert's pass and everything
before it). Each row carries both sides, the books that use the heading, and
the concept the heading sits under, so reviewers can pick a side, fix
Priya's values, or settle a concept's label for every heading under it.

Reads only committed sources. Run from the repo root:

  python3 tools/subject-review/build_data.py tools/subject-review/data.json
"""
import csv
import hashlib
import json
import sys
from collections import defaultdict

SHEET = "sources/subjects/pr164-review.csv"
DECISIONS = "sources/subjects/decisions.csv"
OCCURRENCES = "sources/subjects/occurrences.csv"
BOOKS = "sources/artists-books.csv"
FIELDS = ["include", "conceptId", "category", "prefLabel", "exactMatch", "note"]
SITE = "https://dev-artists-books-bdhx.sprites.app"
SAMPLE_BOOKS = 8


def read_csv(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def row_id(cluster):
    """A doc-id-safe key: clusters hold '/', '|', '(' and spaces."""
    return hashlib.sha1(cluster.encode("utf-8")).hexdigest()[:12]


def group(r):
    """The tab a row goes in, from what Priya's pass did with it."""
    if r["priya_include"] != "y":
        return "out"
    head = r["priya_category"].split("-", 1)[0]
    if head == "geographic":
        return "place"
    if head in {"topical", "chronological"}:
        return "topic"
    return "unfinished"


def main(out):
    titles = {r["canonicalKey"]: r["title"] for r in read_csv(BOOKS)}
    books = defaultdict(set)
    for r in read_csv(OCCURRENCES):
        books[r["cluster"]].add(r["canonicalKey"])

    # Concepts as decisions.csv has them now (one label and category each:
    # pr164_review.py checked that), with the headings filed under each.
    concepts = {}
    for r in read_csv(DECISIONS):
        if r["include"] != "y" or not r["conceptId"]:
            continue
        c = concepts.setdefault(r["conceptId"], {"l": r["prefLabel"], "c": r["category"], "k": [], "n": 0})
        c["k"].append([r["cluster"], r["labels"]])
        c["n"] += len(books.get(r["cluster"], ()))

    rows = []
    for r in read_csv(SHEET):
        keys = sorted(books.get(r["cluster"], ()), key=lambda k: titles.get(k, "").casefold())
        rows.append({
            "id": row_id(r["cluster"]),
            "g": group(r),
            "cluster": r["cluster"],
            "labels": r["labels"],
            "changed": r["changed"].split(),
            "flags": r["flags"].split(),
            "head": {f: r[f"head_{f}"] for f in FIELDS},
            "priya": {f: r[f"priya_{f}"] for f in FIELDS},
            "nBooks": len(keys),
            "books": [[k, titles.get(k, k)] for k in keys[:SAMPLE_BOOKS]],
        })
    ids = [r["id"] for r in rows]
    assert len(set(ids)) == len(ids), "row id collision"

    data = {"site": SITE, "rows": rows, "concepts": concepts}
    with open(out, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
    print(f"{out}: {len(rows)} rows, {len(concepts)} concepts")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "tools/subject-review/data.json")
