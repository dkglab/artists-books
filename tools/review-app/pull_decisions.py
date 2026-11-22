#!/usr/bin/env python3
"""Merge the review page's shared decisions back into the hand-owned CSVs.

The page (index.html, published as a claude.ai artifact) keeps one document
per item in its `decisions` collection:

  dedup.<lib1Key>  {decision, notes, ...}       -> artists-books-dedup-decisions.csv
  oclc.<oclc>      {nodes: {key: decision}, notes, ...}
                                                -> artists-books-oclc-decisions.csv
                                                   (notes go on every row of the group)

Save the collection first (Claude: ArtifactData `list` of `decisions` with
`out_dir`), then run from the repo root:

  python3 tools/review-app/pull_decisions.py <out_dir>/decisions

Only rows with a document are touched; the page is the source of truth for
those, including a decision someone cleared. Other columns and row order are
kept. Prints what changed.
"""
import csv
import glob
import json
import os
import sys

DEDUP = "sources/artists-books-dedup-decisions.csv"
OCLC = "sources/artists-books-oclc-decisions.csv"
VALID = {"dedup": {"", "same", "no", "unsure"},
         "oclc": {"", "same", "no", "wrong-marc", "unsure"}}


def load(path):
    with open(path, newline="", encoding="utf-8") as f:
        r = csv.DictReader(f)
        return r.fieldnames, list(r)


def line_ending(path):
    with open(path, "rb") as f:
        return "\r\n" if b"\r\n" in f.readline() else "\n"


def save(path, cols, rows):
    eol = line_ending(path)  # keep the file's own line endings, so diffs stay small
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, cols, lineterminator=eol)
        w.writeheader()
        w.writerows(rows)


def main(folder):
    docs = {}
    for p in glob.glob(os.path.join(folder, "*.json")):
        with open(p, encoding="utf-8") as f:
            docs[os.path.basename(p)[:-5]] = json.load(f)

    changes, warnings = [], []

    cols, rows = load(DEDUP)
    for r in rows:
        d = docs.pop("dedup." + r["lib1Key"], None)
        if d is None:
            continue
        dec, notes = (d.get("decision") or "").strip(), (d.get("notes") or "").strip()
        if dec not in VALID["dedup"]:
            warnings.append(f"dedup {r['lib1Key']}: unknown decision {dec!r}, skipped")
            continue
        if (r["decision"], r["notes"]) != (dec, notes):
            changes.append(f"dedup {r['lib1Key']}: {r['decision'] or '-'} -> {dec or '-'}"
                           + (" (notes changed)" if r["notes"] != notes else ""))
            r["decision"], r["notes"] = dec, notes
    save(DEDUP, cols, rows)

    cols, rows = load(OCLC)
    seen = set()
    for r in rows:
        d = docs.get("oclc." + r["oclc"])
        if d is None:
            continue
        seen.add("oclc." + r["oclc"])
        dec = ((d.get("nodes") or {}).get(r["canonicalKey"]) or "").strip()
        notes = (d.get("notes") or "").strip()
        if dec not in VALID["oclc"]:
            warnings.append(f"oclc {r['oclc']}/{r['canonicalKey']}: unknown decision {dec!r}, skipped")
            continue
        if (r["decision"], r["notes"]) != (dec, notes):
            changes.append(f"oclc {r['oclc']}/{r['canonicalKey']}: {r['decision'] or '-'} -> {dec or '-'}"
                           + (" (notes changed)" if r["notes"] != notes else ""))
            r["decision"], r["notes"] = dec, notes
    save(OCLC, cols, rows)

    for k in sorted(set(docs) - seen):
        warnings.append(f"{k}: no matching CSV row, ignored")
    for line in changes:
        print(line)
    for line in warnings:
        print("warning:", line, file=sys.stderr)
    print(f"{len(changes)} row(s) changed", file=sys.stderr)


if __name__ == "__main__":
    main(sys.argv[1])
