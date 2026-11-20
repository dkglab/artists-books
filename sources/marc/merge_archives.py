#!/usr/bin/env python3
"""Additively merge per-record MARC stores (#81) into one.

A store is a directory of <key>.xml files (the committed form) or a zip of them
(the form scratch harvests under harvest/ take); any mix can be merged.

Why this exists: marc_harvest.py's combine() rebuilds an archive wholly from the
local harvest state under harvest/<csv-stem>/, which is gitignored. So pointing a
new server's run at the committed archive with --out would *replace* it with just
that run's hits, silently dropping every previously harvested record. Adding a
new server's reach to the committed archive is therefore a merge of archives, not
a re-combine.

Each record carries its own join key in 999 $a and each entry is <key>.xml, so
merging is a union keyed by entry name. Later --add archives win on a collision;
collisions are reported, since for a residual harvest (a run targeting only the
books still missing MARC) the expected overlap is zero and anything else is worth
a look before committing.

Output goes through marc_harvest.write_records, so record serialization is
identical to what the harvester writes -- a merge that changes nothing produces
no git churn.

Run (from sources/):
    python3 marc/merge_archives.py --base marc/artists-books-marc \
        --add marc/harvest/scad-residual.zip --out marc/artists-books-marc
"""
import argparse
import sys
import xml.etree.ElementTree as ET

from marc_harvest import MARC_NS, iter_record_files, record_key, write_records


def read_archive(path):
    """{entry name: record Element} for one per-record store (directory or zip)."""
    out = {}
    for name, data in iter_record_files(path):
        root = ET.fromstring(data)
        rec = (root if root.tag == f"{{{MARC_NS}}}record"
               else root.find(f"{{{MARC_NS}}}record"))
        if rec is not None:
            out[name] = rec
    return out


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base", required=True, help="store (directory or .zip) to merge into")
    ap.add_argument("--add", required=True, action="append",
                    help="store whose records to add (repeatable; later wins)")
    ap.add_argument("--out", required=True, help="output store: a directory, or a .zip (may equal --base)")
    args = ap.parse_args()

    merged = read_archive(args.base)
    print(f"{args.base}: {len(merged)} records")

    for path in args.add:
        add = read_archive(path)
        clash = sorted(set(merged) & set(add))
        merged.update(add)
        print(f"{path}: {len(add)} records, {len(clash)} already present")
        for name in clash[:20]:
            print(f"    overwrites {name}")
        if len(clash) > 20:
            print(f"    ... and {len(clash) - 20} more")

    # Every record is already in memory, so --out == --base is safe: a zip is
    # written whole, and a directory is built beside the target and swapped in.
    # Refuse before writing anything if a record lacks its join key.
    no_key = sum(1 for rec in merged.values() if record_key(rec) is None)
    if no_key:
        print(f"FATAL: {no_key} records have no 999 $a join key", file=sys.stderr)
        sys.exit(3)
    n, _ = write_records(list(merged.values()), args.out)
    print(f"wrote {args.out}: {n} records")


if __name__ == "__main__":
    main()
