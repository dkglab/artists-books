#!/usr/bin/env python3
"""One-time (#82 task 5 / #84): re-key the legacy lib-1 held MARC to canonical keys.

The pre-#84 sources/marc/artists-books-marc.xml carried the *lib-1* itemKey in
each record's 999 $a, because the site historically built only from UNC's held
subset. #82 made the canonical deduped list (sources/artists-books.csv, lib
1∪2∪3) authoritative, keyed by canonicalKey. This script rewrites each legacy
record's 999 $a from its lib-1 itemKey to the canonical key, using the
lib-1 → canonical map carried in the CSV's sourceKeys column (tokens like
"1:Y2MQKHFR; 3:EN42444Z").

The result is committed as artists-books-held-marc.xml -- a frozen input the
canonical harvest merges via marc_harvest.py --premerged, so the ~1,340 already
-harvested held books need no re-harvest (issue #84 maintainer decision:
"re-key held + harvest non-held"). Records whose lib-1 key no longer maps to any
canonical row (folded away by dedup) are dropped and reported.

This is a Phase-0-style one-shot: it reads the pre-#84 committed MARC, and once
the canonical pipeline overwrites artists-books-marc.xml the held file is treated
as frozen (like the *-manual.xml records and sources/citations.ttl). Regenerate
only from the pre-#84 MARC (git history) if the dedup lists change.

Run once (from sources/):
    python3 marc/rekey_held.py --in-marc marc/artists-books-marc.xml \
        --csv artists-books.csv --out marc/artists-books-held-marc.xml
"""
import argparse
import csv
import sys
import xml.etree.ElementTree as ET

MARC_NS = "http://www.loc.gov/MARC21/slim"
NS = f"{{{MARC_NS}}}"


def lib1_to_canonical(csv_path):
    """Map each lib-1 itemKey to its canonical key, read from the sourceKeys column
    (";"-separated "<lib>:<KEY>" tokens; the "1:" token is the lib-1 origin key)."""
    mapping = {}
    with open(csv_path, newline="") as fh:
        for row in csv.DictReader(fh):
            for tok in (row.get("sourceKeys") or "").split(";"):
                tok = tok.strip()
                if tok.startswith("1:"):
                    mapping[tok[2:]] = row["canonicalKey"]
    return mapping


def record_999a(rec):
    """The 999 $a text of a MARC record Element, or None."""
    for df in rec.findall(f"{NS}datafield"):
        if df.get("tag") == "999":
            for sf in df.findall(f"{NS}subfield"):
                if sf.get("code") == "a":
                    return sf
    return None


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--in-marc", required=True, help="legacy lib-1 MARCXML (999 $a = lib-1 key)")
    ap.add_argument("--csv", required=True, help="canonical CSV carrying sourceKeys")
    ap.add_argument("--out", required=True, help="output MARCXML with canonical 999 $a")
    args = ap.parse_args()

    mapping = lib1_to_canonical(args.csv)

    ET.register_namespace("", MARC_NS)
    tree = ET.parse(args.in_marc)
    root = tree.getroot()
    records = root.findall(f"{NS}record")

    rekeyed, dropped, no999, dup = 0, [], 0, 0
    seen = set()  # canonical keys already emitted -- dedup lib-1 records that
    for rec in list(records):        # deduped onto the same canonical work
        sf = record_999a(rec)
        if sf is None:
            no999 += 1
            root.remove(rec)
            continue
        canonical = mapping.get(sf.text)
        if canonical is None:
            dropped.append(sf.text)
            root.remove(rec)
            continue
        if canonical in seen:
            dup += 1
            root.remove(rec)
            continue
        sf.text = canonical  # keep $b/$c/$d provenance; only the join key changes
        seen.add(canonical)
        rekeyed += 1

    tree.write(args.out, encoding="unicode", xml_declaration=True)
    print(f"wrote {args.out}: {rekeyed} re-keyed ({no999} without 999, "
          f"{len(dropped)} unmapped lib-1 keys dropped, {dup} duplicate canonical keys folded)")
    if dropped:
        print("  dropped (no canonical row): " + ", ".join(dropped[:20])
              + (" ..." if len(dropped) > 20 else ""), file=sys.stderr)


if __name__ == "__main__":
    main()
