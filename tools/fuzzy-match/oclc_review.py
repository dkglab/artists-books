#!/usr/bin/env python3
"""Build the shared-OCLC review sheet for the artists'-book dedup (issue #70).

The canonical dedup (dedup.py, #82) merges on Zotero sameAs/ISBN/title+author
and fuzzy titles, but not on the OCLC number, which only arrives later with the
MARC harvest. So some works still mint two or three ab:ArtistsBook nodes that
share one MARC 001. oclc-groups.rq lists those nodes from the built graph; this
script lays each group out with its Zotero and MARC context for a person to
decide.

A shared OCLC number is not always a duplicate. The harvest's title-author
search sometimes matches a book to the wrong record, so two distinct books end
up carrying the same 001. The decision vocabulary therefore has four values:

  same        a duplicate of the group's other node(s): merge
  no          a distinct work that legitimately shares the record (volume,
              edition, set member): keep separate
  wrong-marc  a distinct work whose MARC record is a bad harvest match: keep
              separate, and fix or drop the record
  unsure      needs another signal

The sheet (--out) is GENERATED and overwritten on every run. The decisions
live in the hand-owned overlay (--decisions), keyed by (oclc, canonicalKey),
and are joined into the sheet read-only, the same split as
artists-books-dedup-review.csv / artists-books-dedup-decisions.csv. Pass
--seed-decisions to create the overlay with a blank row per node; it refuses
to overwrite an existing file.
"""
import argparse
import csv
import os
import re
import sys
import unicodedata
import xml.etree.ElementTree as ET
from collections import Counter, OrderedDict

NS = {"m": "http://www.loc.gov/MARC21/slim"}
DECISIONS = {"", "same", "no", "wrong-marc", "unsure"}
DECISION_COLS = ["oclc", "canonicalKey", "zoteroTitle", "decision", "notes"]
COLS = ["group", "oclc", "hint", "canonicalKey", "held", "zoteroTitle", "zoteroDate",
        "zoteroCreators", "zoteroPublisher", "callNumber", "marcTitle", "marcCreator",
        "marcEdition", "marcImprint", "marcExtent", "matchMethod", "matchServer",
        "matchedOn", "sourceKeys", "url", "decision", "notes"]


def read_groups(path):
    """Read arq's TSV output (?oclc, ?key) into {oclc: [key, ...]}, in order."""
    groups = OrderedDict()
    with open(path, encoding="utf-8") as f:
        header = f.readline().rstrip("\n").split("\t")
        if header[:2] != ["?oclc", "?key"]:
            sys.exit(f"{path}: expected an arq TSV with ?oclc and ?key, got {header}")
        for line in f:
            oclc, key = (v.strip().strip('"') for v in line.rstrip("\n").split("\t")[:2])
            groups.setdefault(oclc, []).append(key)
    return groups


def subfields(rec, tag, codes):
    """One string per `tag` field: its `codes` subfields, space-joined."""
    return [" ".join(sf.text.strip() for sf in df.iterfind("m:subfield", NS)
                     if sf.get("code") in codes and sf.text)
            for df in rec.iterfind(f"m:datafield[@tag='{tag}']", NS)]


def marc_context(marc_dir, key):
    path = os.path.join(marc_dir, f"{key}.xml")
    if not os.path.exists(path):
        return {}
    rec = ET.parse(path).getroot().find("m:record", NS)
    d999 = {sf.get("code"): (sf.text or "")
            for sf in rec.iterfind("m:datafield[@tag='999']/m:subfield", NS)}
    join = "; ".join
    return {
        "marcTitle": join(subfields(rec, "245", "abnp")),
        "marcCreator": join(subfields(rec, "100", "a") + subfields(rec, "110", "a")),
        "marcEdition": join(subfields(rec, "250", "ab")),
        "marcImprint": join(subfields(rec, "264", "abc") or subfields(rec, "260", "abc")),
        "marcExtent": join(subfields(rec, "300", "ac")),
        "matchedOn": d999.get("b", ""),
        "matchMethod": d999.get("c", ""),
        "matchServer": d999.get("d", ""),
    }


def norm_title(t):
    t = unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "", t)


def load_decisions(path):
    if not os.path.exists(path):
        return {}
    out = {}
    with open(path, newline="", encoding="utf-8") as f:
        for n, r in enumerate(csv.DictReader(f), 2):
            d = (r.get("decision") or "").strip()
            if d not in DECISIONS:
                print(f"  warning: {path}:{n}: unknown decision {d!r}", file=sys.stderr)
            out[(r["oclc"], r["canonicalKey"])] = (d, r.get("notes") or "")
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--groups", required=True, help="arq TSV from oclc-groups.rq")
    ap.add_argument("--books", required=True, help="canonical artists-books.csv")
    ap.add_argument("--marc", required=True, help="per-record MARC directory")
    ap.add_argument("--decisions", required=True, help="hand-owned decisions overlay")
    ap.add_argument("--out", required=True, help="generated review sheet")
    ap.add_argument("--seed-decisions", action="store_true",
                    help="create --decisions with a blank row per node (never overwrites)")
    args = ap.parse_args()

    groups = read_groups(args.groups)
    with open(args.books, newline="", encoding="utf-8") as f:
        books = {r["canonicalKey"]: r for r in csv.DictReader(f)}
    decisions = load_decisions(args.decisions)

    rows = []
    for g, (oclc, keys) in enumerate(groups.items(), 1):
        hint = ("same-title" if len({norm_title(books[k]["title"]) for k in keys}) == 1
                else "title-differs")
        for k in keys:
            b = books[k]
            decision, notes = decisions.get((oclc, k), ("", ""))
            rows.append({
                "group": g, "oclc": oclc, "hint": hint, "canonicalKey": k,
                "held": b["held"], "zoteroTitle": b["title"], "zoteroDate": b["date"],
                "zoteroCreators": b["creators"], "zoteroPublisher": b["publisher"],
                "callNumber": b["callNumber"], "sourceKeys": b["sourceKeys"],
                "url": b["url"], "decision": decision, "notes": notes,
                **marc_context(args.marc, k),
            })

    with open(args.out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, COLS, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)

    current = {(r["oclc"], r["canonicalKey"]) for r in rows}
    if args.seed_decisions:
        if os.path.exists(args.decisions):
            sys.exit(f"{args.decisions} exists; refusing to overwrite hand-owned decisions")
        with open(args.decisions, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, DECISION_COLS, extrasaction="ignore", lineterminator="\n")
            w.writeheader()
            w.writerows(rows)
        print(f"  seeded {args.decisions} with {len(rows)} blank rows", file=sys.stderr)
    else:
        missing = current - decisions.keys()
        stale = decisions.keys() - current
        if missing:
            print(f"  {len(missing)} node(s) not in {args.decisions} yet; add them by hand: "
                  + ", ".join(sorted(f"{o}/{k}" for o, k in missing)), file=sys.stderr)
        if stale:
            print(f"  {len(stale)} decision row(s) no longer in a shared-OCLC group: "
                  + ", ".join(sorted(f"{o}/{k}" for o, k in stale)), file=sys.stderr)

    hints = Counter({r["group"]: r["hint"] for r in rows}.values())
    done = Counter(r["decision"] for r in rows)
    print(f"  {len(groups)} shared-OCLC groups, {len(rows)} nodes "
          f"({hints['same-title']} same-title, {hints['title-differs']} title-differs); "
          f"decisions: {dict(done)}", file=sys.stderr)


if __name__ == "__main__":
    main()
