#!/usr/bin/env python3
"""Emit the residual CSV for a follow-up MARC harvest: the canonical rows that
still have no record in a committed archive.

Adding a newly reachable catalogue's reach (issue #99's lever 3, and the SCAD
pass before it) is a *residual* run: harvest only the books still missing MARC
into their own archive, then fold that in with merge_archives.py. Both halves of
that need the residual list, which until now was produced ad hoc. This makes it
repeatable -- and re-runnable as coverage moves, so the list never goes stale the
way #99's own figures did.

The output carries the input's columns verbatim, so marc_harvest.py consumes it
directly (it reads canonicalKey via row_key). Give it a distinct stem: harvest
state lives in harvest/<csv-stem>/, so vsw-residual.csv gets its own resumable
state rather than colliding with the main artists-books run.

    # every canonical work still missing MARC
    python3 marc/residual_csv.py --csv artists-books.csv \
        --archive marc/artists-books-marc.zip --out marc/harvest/residual.csv

    # just the Visual Studies Workshop cluster (#99 lever 1, the eHive target)
    python3 marc/residual_csv.py --csv artists-books.csv \
        --archive marc/artists-books-marc.zip --publisher 'visual studies' \
        --out marc/harvest/vsw-residual.csv
"""

import argparse
import csv
import os
import re
import sys
import zipfile

# The OCLC key the residual reports on is the same one marc_harvest's uwmad
# server searches with, so they share one definition: a residual that counted
# OCLC-bearing rows differently from the harvest that queries them would report
# a lever nobody could pull.
from marc_harvest import oclc_of


def archive_keys(path):
    """The 999 $a join keys already covered by an archive: one <key>.xml per record."""
    with zipfile.ZipFile(path) as zf:
        return {os.path.splitext(n)[0] for n in zf.namelist() if n.endswith(".xml")}


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--csv", required=True, help="canonical CSV (artists-books.csv)")
    ap.add_argument("--archive", required=True, help="committed *-marc.zip to diff against")
    ap.add_argument("--out", required=True, help="residual CSV to write")
    ap.add_argument("--publisher", help="only rows whose publisher matches this regex")
    ap.add_argument("--held", choices=("true", "false"),
                    help="only rows with this held value")
    args = ap.parse_args()

    have = archive_keys(args.archive)
    with open(args.csv, newline="") as fh:
        reader = csv.DictReader(fh)
        fields = reader.fieldnames
        rows = list(reader)

    residual = [r for r in rows if (r.get("canonicalKey") or r.get("itemKey")) not in have]
    total_missing = len(residual)
    if args.held:
        residual = [r for r in residual if (r.get("held") or "").strip().lower() == args.held]
    if args.publisher:
        pat = re.compile(args.publisher, re.I)
        residual = [r for r in residual if pat.search(r.get("publisher") or "")]

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(residual)

    n_isbn = sum(1 for r in residual if (r.get("ISBN") or "").strip())
    n_oclc = sum(1 for r in residual if oclc_of(r))
    n_none = sum(1 for r in residual if not oclc_of(r) and not (r.get("ISBN") or "").strip())
    print(f"{len(rows)} canonical rows, {len(have)} with MARC, {total_missing} missing")
    print(f"wrote {args.out}: {len(residual)} rows"
          + (f" (filtered from {total_missing})" if len(residual) != total_missing else ""))
    print(f"  keys available: {n_oclc} OCLC, {n_isbn} ISBN, {n_none} neither "
          f"(title/author only -- verification-gated)")
    if not residual:
        print("  nothing residual -- archive already covers the selection", file=sys.stderr)


if __name__ == "__main__":
    main()
