#!/usr/bin/env python3
"""Convert a MARCXML <collection> into a reproducible per-record zip archive (#81).

A one-time migration helper: the MARC harvest used to emit one big <collection>
file per CSV; #81 switches to a per-record archive (one <key>.xml per record) read
by the construct queries via SPARQL-Anything's nested Archive -> XML triplifiers.
Going forward marc_harvest.py's combine() writes the archive directly; this script
converts an already-committed collection file to the same archive without a
re-harvest (it reuses marc_harvest.write_record_zip, so the entry serialization
and reproducible-bytes discipline are identical to the harvester's).

The queries take the join key from each record's 999 $a, not the entry filename,
so the <key>.xml naming is only a stable, debuggable layout.

Run (from sources/):
    python3 marc/marc_to_archive.py --in marc/reference-resources-marc.xml \
        --out marc/reference-resources-marc.zip
"""
import argparse
import sys
import xml.etree.ElementTree as ET

from marc_harvest import MARC_NS, write_record_zip


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--in", dest="in_xml", required=True, help="MARCXML <collection>")
    ap.add_argument("--out", required=True, help="output zip of per-record <key>.xml")
    args = ap.parse_args()

    records = ET.parse(args.in_xml).getroot().findall(f"{{{MARC_NS}}}record")
    n_written, n_no_key = write_record_zip(records, args.out)
    print(f"wrote {args.out}: {n_written} records "
          f"({n_no_key} without 999 $a skipped)")
    if n_no_key:
        print(f"  WARNING: {n_no_key} records had no 999 $a and were dropped",
              file=sys.stderr)


if __name__ == "__main__":
    main()
