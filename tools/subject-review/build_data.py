#!/usr/bin/env python3
"""Build data.json for the subject review page (#108, #164).

Three queues, all read from committed sources (run from the repo root):

  pairs    the 1,113 headings in sources/subjects/pr164-review.csv, where
           Priya's pass in #164 differs from decisions.csv (Mert's pass and
           everything before it). Split into four groups by what Priya did.
  draft    the geographic headings still noted 'auto-seeded draft; review' in
           decisions.csv (#108's definition of done), less those in `pairs`,
           which are settled there.
  overlap  sources/subjects/construction-overlap-review.csv (#108): headings
           that may be construction methods rather than subjects, or both.
           Group 3 (Screen prints) is already settled. A heading also in
           `pairs` has its subject side decided there; here it gets only its
           construction side.

Each row carries the books that use the heading and the concept it sits
under. The subject and construction concepts as decisions.csv has them go
along, so the page can merge, check labels and suggest concepts.

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
OVERLAP = "sources/subjects/construction-overlap-review.csv"
CONSTRUCTION = "sources/construction/decisions.csv"
OLD = "sources/subjects/decisions_old.csv"
BOOKS = "sources/artists-books.csv"
FIELDS = ["include", "conceptId", "category", "prefLabel", "exactMatch", "note"]
SITE = "https://dev-artists-books-bdhx.sprites.app"
SAMPLE_BOOKS = 8
DRAFT = "auto-seeded draft; review"
# construction/build-scheme.rq's category table, in its rank order
CONSTRUCTION_CATEGORIES = [
    ["material", "Materials"], ["process-technique", "Process/Technique"],
    ["hand-papermaking-traditions", "Hand Papermaking Traditions"],
    ["structure-physical-format", "Structure/Physical Format"],
    ["enclosure", "Enclosure"], ["genre-form", "Genre/Form"],
]


def read_csv(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def doc_id(queue, cluster):
    """A doc-id-safe key: clusters hold '/', '|', '(' and spaces."""
    key = cluster if queue == "pairs" else f"{queue}|{cluster}"
    return hashlib.sha1(key.encode("utf-8")).hexdigest()[:12]


def pair_group(r):
    """The tab a #164 row goes in, from what Priya's pass did with it."""
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

    def with_books(row, cluster):
        keys = sorted(books.get(cluster, ()), key=lambda k: titles.get(k, "").casefold())
        row["nBooks"] = len(keys)
        row["books"] = [[k, titles.get(k, k)] for k in keys[:SAMPLE_BOOKS]]
        return row

    dec = read_csv(DECISIONS)
    by_cluster = {r["cluster"]: r for r in dec}
    concepts = {}
    for r in dec:
        if r["include"] != "y" or not r["conceptId"]:
            continue
        c = concepts.setdefault(r["conceptId"], {"l": r["prefLabel"], "c": r["category"], "k": [], "n": 0})
        c["k"].append([r["cluster"], r["labels"]])
        c["n"] += len(books.get(r["cluster"], ()))

    cons = read_csv(CONSTRUCTION)
    cons_by_cluster = {r["cluster"]: r for r in cons}
    cons_concepts = {}
    for r in cons:
        if r["include"] == "y" and r["conceptId"]:
            c = cons_concepts.setdefault(r["conceptId"], {"l": r["prefLabel"], "c": r["category"], "n": 0})
            c["n"] += 1

    # Mert's earlier pass left these places out; the merge in #154 put them back.
    old = {r["cluster"]: r for r in read_csv(OLD)}
    left_out_by_mert = {k for k, r in old.items() if r["include"] == "n"
                        and by_cluster.get(k, {}).get("include") == "y"
                        and by_cluster[k]["category"] == "geographic"}

    rows, pair_ids = [], {}
    for r in read_csv(SHEET):
        flags = r["flags"].split()
        if r["cluster"] in left_out_by_mert:
            flags.append("left-out-by-mert")
        row = {"q": "pairs", "id": doc_id("pairs", r["cluster"]), "g": pair_group(r),
               "cluster": r["cluster"], "labels": r["labels"], "flags": flags,
               "head": {f: r[f"head_{f}"] for f in FIELDS},
               "priya": {f: r[f"priya_{f}"] for f in FIELDS}}
        pair_ids[r["cluster"]] = row["id"]
        rows.append(with_books(row, r["cluster"]))

    for r in dec:
        if r["note"] == DRAFT and r["category"] == "geographic" and r["cluster"] not in pair_ids:
            row = {"q": "draft", "id": doc_id("draft", r["cluster"]), "g": "draft",
                   "cluster": r["cluster"], "labels": r["labels"], "flags": [],
                   "head": {f: r[f] for f in FIELDS}}
            rows.append(with_books(row, r["cluster"]))

    for r in read_csv(OVERLAP):
        if r["group"] == "3":
            continue
        k = r["cluster"]
        s = by_cluster.get(k, {f: "" for f in FIELDS})
        c = cons_by_cluster.get(k)
        row = {"q": "overlap", "id": doc_id("overlap", k), "g": "overlap", "group": r["group"],
               "cluster": k, "labels": r["labels"], "flags": [],
               "head": {f: s.get(f, "") for f in FIELDS},
               "cons": {f: (c or {}).get(f, "") for f in ["include", "conceptId", "category", "prefLabel", "note"]},
               "matches": [m for m in r["matching_construction_concepts"].split() if m],
               "prefill": c["conceptId"] if c and c["note"].startswith("pre-filled") and c["include"] == "y" else ""}
        if k in pair_ids:
            row["pair"] = pair_ids[k]
        rows.append(with_books(row, k))

    ids = [r["id"] for r in rows]
    assert len(set(ids)) == len(ids), "row id collision"
    data = {"site": SITE, "rows": rows, "concepts": concepts,
            "consConcepts": cons_concepts, "consCategories": CONSTRUCTION_CATEGORIES}
    with open(out, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
    n = defaultdict(int)
    for r in rows:
        n[r["g"]] += 1
    print(f"{out}: {len(rows)} rows ({dict(n)}), {len(concepts)} subject and {len(cons_concepts)} construction concepts")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "tools/subject-review/data.json")
