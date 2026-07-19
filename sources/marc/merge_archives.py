#!/usr/bin/env python3
"""Additively merge per-record MARC archives (#81) into one archive.

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

Output goes through marc_harvest.write_record_zip, so entry serialization and the
reproducible-bytes discipline (sorted entries, fixed 1980 mtimes) are identical to
what the harvester writes -- a merge that changes nothing produces no git churn.

Run (from sources/):
    python3 marc/merge_archives.py --base marc/artists-books-marc.zip \
        --add marc/harvest/scad-residual.zip --out marc/artists-books-marc.zip
"""
import argparse
import os
import sys
import xml.etree.ElementTree as ET
import zipfile

from marc_harvest import MARC_NS, write_record_zip


def read_archive(path):
    """{entry name: record Element} for one per-record archive."""
    out = {}
    with zipfile.ZipFile(path) as zf:
        for name in zf.namelist():
            root = ET.fromstring(zf.read(name))
            rec = (root if root.tag == f"{{{MARC_NS}}}record"
                   else root.find(f"{{{MARC_NS}}}record"))
            if rec is not None:
                out[name] = rec
    return out


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base", required=True, help="archive to merge into")
    ap.add_argument("--add", required=True, action="append",
                    help="archive whose records to add (repeatable; later wins)")
    ap.add_argument("--out", required=True, help="output archive (may equal --base)")
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

    # Write via a temp path first so --out == --base cannot truncate the base
    # archive if the write fails partway.
    tmp = args.out + ".tmp"
    n, no_key = write_record_zip(list(merged.values()), tmp)
    if no_key:
        print(f"FATAL: {no_key} records have no 999 $a join key", file=sys.stderr)
        os.unlink(tmp)
        sys.exit(3)
    os.replace(tmp, args.out)
    print(f"wrote {args.out}: {n} records")


if __name__ == "__main__":
    main()
