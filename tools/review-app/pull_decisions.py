#!/usr/bin/env python3
"""Merge the review page's shared decisions back into the hand-owned CSVs.

The page (index.html, published as a claude.ai artifact) keeps one document
per item in its `decisions` collection:

  dedup.<lib1Key>  {decision, notes, ...}       -> artists-books-dedup-decisions.csv
  oclc.<groupId>   {nodes: {key: decision}, notes, ...}
                                                -> artists-books-oclc-decisions.csv
                                                   (notes go on every row of the group;
                                                   groupId is an OCLC number or, for a
                                                   same-record group, rec.<server>.<001>, #222)
  xtrack.<abKey>.<rwKey>  {decision, notes, ...}  -> cross-track-decisions.csv (#113)

Save the collection first (Claude: ArtifactData `list` of `decisions` with
`out_dir`), then run from the repo root:

  python3 tools/review-app/pull_decisions.py <out_dir>/decisions

Only rows with a document are touched (plus a new row for a cross-track pair
or OCLC-group node that is in its review sheet but not yet in the overlay);
the page is the source of truth for those, including a decision someone
cleared. Other columns and row order are
kept. Prints what changed.
"""
import csv
import glob
import json
import os
import sys

DEDUP = "sources/artists-books-dedup-decisions.csv"
OCLC = "sources/artists-books-oclc-decisions.csv"
OCLC_REVIEW = "sources/artists-books-oclc-review.csv"  # for a new node's row
XTRACK = "sources/cross-track-decisions.csv"
XTRACK_REVIEW = "sources/cross-track-review.csv"  # for the titles of a new pair's row
VALID = {"dedup": {"", "same", "no", "unsure"},
         "oclc": {"", "same", "no", "wrong-marc", "unsure"},
         "xtrack": {"", "both", "reference", "no", "unsure"}}


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
        d = docs.get("oclc." + r["groupId"])
        if d is None:
            continue
        seen.add("oclc." + r["groupId"])
        dec = ((d.get("nodes") or {}).get(r["canonicalKey"]) or "").strip()
        notes = (d.get("notes") or "").strip()
        if dec not in VALID["oclc"]:
            warnings.append(f"oclc {r['groupId']}/{r['canonicalKey']}: unknown decision {dec!r}, skipped")
            continue
        if (r["decision"], r["notes"]) != (dec, notes):
            changes.append(f"oclc {r['groupId']}/{r['canonicalKey']}: {r['decision'] or '-'} -> {dec or '-'}"
                           + (" (notes changed)" if r["notes"] != notes else ""))
            r["decision"], r["notes"] = dec, notes
    # A group or member found by a later regeneration of the review sheet (a
    # record group's membership moves with every re-harvest, #222) has no
    # overlay row yet, so add one for each such node rather than drop it.
    with open(OCLC_REVIEW, newline="", encoding="utf-8") as f:
        review = {(r["groupId"], r["canonicalKey"]): r for r in csv.DictReader(f)}
    have = {(r["groupId"], r["canonicalKey"]) for r in rows}
    for gid, key in sorted(review.keys() - have):
        d = docs.get("oclc." + gid)
        if d is None:
            continue
        seen.add("oclc." + gid)
        dec = ((d.get("nodes") or {}).get(key) or "").strip()
        notes = (d.get("notes") or "").strip()
        if dec not in VALID["oclc"]:
            warnings.append(f"oclc {gid}/{key}: unknown decision {dec!r}, skipped")
            continue
        if not (dec or notes):
            continue
        rows.append({c: "" for c in cols} | {
            "groupId": gid, "canonicalKey": key,
            "zoteroTitle": review[(gid, key)]["zoteroTitle"], "decision": dec, "notes": notes})
        changes.append(f"oclc {gid}/{key}: new row, {dec or '-'}" + (" (notes)" if notes else ""))
    save(OCLC, cols, rows)

    cols, rows = load(XTRACK)
    for r in rows:
        pair = f"{r['abKey']}.{r['rwKey']}"
        d = docs.pop("xtrack." + pair, None)
        if d is None:
            continue
        dec, notes = (d.get("decision") or "").strip(), (d.get("notes") or "").strip()
        if dec not in VALID["xtrack"]:
            warnings.append(f"xtrack {pair}: unknown decision {dec!r}, skipped")
            continue
        if (r["decision"], r["notes"]) != (dec, notes):
            changes.append(f"xtrack {pair}: {r['decision'] or '-'} -> {dec or '-'}"
                           + (" (notes changed)" if r["notes"] != notes else ""))
            r["decision"], r["notes"] = dec, notes
    # A pair found by a later regeneration of cross-track-review.csv has no
    # overlay row yet (--seed-decisions runs once), so add one for it here
    # rather than drop the decision.
    with open(XTRACK_REVIEW, newline="", encoding="utf-8") as f:
        review = {f"{r['abKey']}.{r['rwKey']}": r for r in csv.DictReader(f)}
    for k in sorted(k for k in docs if k.startswith("xtrack.")):
        pair = k[len("xtrack."):]
        if pair not in review:
            continue  # left in docs, so it is warned about below
        d = docs.pop(k)
        dec, notes = (d.get("decision") or "").strip(), (d.get("notes") or "").strip()
        if dec not in VALID["xtrack"]:
            warnings.append(f"xtrack {pair}: unknown decision {dec!r}, skipped")
            continue
        if not (dec or notes):
            continue
        rv = review[pair]
        rows.append({c: "" for c in cols} | {
            "abKey": rv["abKey"], "rwKey": rv["rwKey"], "abTitle": rv["abTitle"],
            "rwTitle": rv["rwTitle"], "decision": dec, "notes": notes})
        changes.append(f"xtrack {pair}: new row, {dec or '-'}" + (" (notes)" if notes else ""))
    save(XTRACK, cols, rows)

    for k in sorted(set(docs) - seen):
        warnings.append(f"{k}: no matching CSV row, ignored")
    for line in changes:
        print(line)
    for line in warnings:
        print("warning:", line, file=sys.stderr)
    print(f"{len(changes)} row(s) changed", file=sys.stderr)


if __name__ == "__main__":
    main(sys.argv[1])
