#!/usr/bin/env python3
"""Merge the subject reconciliation page's decisions into decisions.csv.

The page (index.html, published as a claude.ai artifact) keeps two
collections in its shared database:

  rows/<id>       one per heading in pr164-review.csv: {cluster, take, final,
                  fine, notes, ...}. take is head (keep decisions.csv as it
                  is), priya or edit (write `final`), or unsure.
  concepts/<id>   a label and category set for a whole concept: every
                  include=y row of decisions.csv under that concept gets it.

Save both collections first (Claude: ArtifactData `list` of `rows` and of
`concepts` with `out_dir`), then run from the repo root:

  python3 tools/subject-review/pull_decisions.py <out_dir>

It checks what it writes the way the page does (a slug concept ID, a
topical/geographic category, a label, and one label and category per
concept across the whole file) and writes nothing if any check fails.
Row order, columns and line endings are kept. Prints what changed.
"""
import collections
import csv
import glob
import io
import json
import os
import re
import sys

DECISIONS = "sources/subjects/decisions.csv"
SHEET = "sources/subjects/pr164-review.csv"
SLUG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
CATEGORIES = {"topical", "geographic"}
FIELDS = ["include", "conceptId", "category", "prefLabel", "exactMatch", "note"]


def docs(folder):
    out = []
    for path in sorted(glob.glob(os.path.join(folder, "*.json"))):
        with open(path, encoding="utf-8") as f:
            out.append(json.load(f))
    return out


def main(out_dir):
    rows = docs(os.path.join(out_dir, "rows"))
    concepts = {d["id"]: d for d in docs(os.path.join(out_dir, "concepts"))}
    with open(DECISIONS, newline="", encoding="utf-8") as f:
        raw = f.read()
    reader = csv.DictReader(io.StringIO(raw, newline=""))
    cols, dec = reader.fieldnames, list(reader)
    by_key = {r["cluster"]: r for r in dec}
    labels = {r["cluster"]: r["labels"] for r in csv.DictReader(open(SHEET, newline="", encoding="utf-8"))}

    errors, changed = [], []
    takes = collections.Counter(d.get("take") or "todo" for d in rows)
    for d in rows:
        if d.get("take") not in {"priya", "edit"}:
            continue
        k = d["cluster"]
        new = {f: (d.get("final") or {}).get(f, "").strip() for f in FIELDS}
        if new["include"] != "y":
            new.update(include="n", conceptId="", category="", prefLabel="")
        else:
            o = concepts.get(new["conceptId"])
            if o:
                new.update(prefLabel=o["prefLabel"], category=o["category"])
            if not SLUG.match(new["conceptId"]):
                errors.append(f"{k}: concept ID {new['conceptId']!r} isn't a slug")
            if new["category"] not in CATEGORIES:
                errors.append(f"{k}: category {new['category']!r}")
            if not new["prefLabel"]:
                errors.append(f"{k}: no label")
        r = by_key.get(k)
        if r is None:
            r = {c: "" for c in cols}
            r.update(cluster=k, labels=labels.get(k, ""))
            dec.append(r)
            by_key[k] = r
        before = {f: r[f] for f in FIELDS}
        r.update(new)
        if before != new:
            changed.append(f"{k}: " + ", ".join(f"{f} {before[f]!r} -> {new[f]!r}" for f in FIELDS if before[f] != new[f]))

    relabelled = 0
    for cid, o in concepts.items():
        for r in dec:
            if r["include"] == "y" and r["conceptId"] == cid and (r["prefLabel"], r["category"]) != (o["prefLabel"], o["category"]):
                r["prefLabel"], r["category"] = o["prefLabel"], o["category"]
                relabelled += 1

    seen = collections.defaultdict(set)
    for r in dec:
        if r["include"] == "y":
            seen[r["conceptId"]].add((r["prefLabel"], r["category"]))
    for cid, ls in sorted(seen.items()):
        if len(ls) > 1:
            errors.append(f"concept {cid}: several labels/categories {sorted(ls)}")
    if errors:
        print("\n".join(errors), file=sys.stderr)
        sys.exit(f"{len(errors)} problems; {DECISIONS} not written")

    le = "\r\n" if "\r\n" in raw else "\n"
    with open(DECISIONS, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, cols, lineterminator=le)
        w.writeheader()
        w.writerows(dec)
    print("\n".join(changed))
    print(f"{len(changed)} row(s) changed, {relabelled} relabelled by {len(concepts)} concept label(s)")
    print("decisions on the page: " + ", ".join(f"{k} {n}" for k, n in takes.most_common()))


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
