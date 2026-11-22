#!/usr/bin/env python3
"""How much recall does the harvest's show_n window cost? (issue #98)

Reads an adjudicate_review.py candidates dump -- every candidate a server returns
for its own rejects, fetched at show_n=10 -- and replays select_record's title
logic over it: for each book, the first candidate (probes in precedence order,
records in rank order) that verify_title accepts. A rank of 3 or less means the
harvest itself would have accepted it, so a dump of true rejects should have
none; every acceptance at rank > 3 is recall the show_n=3 window lost.

The band column says why verify accepted: "strong" (full-title ratio >=
TITLE_STRONG) or "weak+year" (weak-band title corroborated by the year). A wider
window gives the weak band more candidates to accept wrongly, so read those rows.
The year column compares the record's year with the CSV's: "agree" (within one
year), "conflict", or "unknown" (either side has none). The strong band takes no
year at all, so on short common titles ("Sans titre", "Climax") a deeper window
mostly surfaces *other works of the same title* -- the conflicts.

Offline: no server is queried.

    python3 measure_show_n.py harvest/scad-residual-candidates.jsonl [--max-rank N]
"""
import argparse
import difflib
import itertools
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import marc_harvest as mh


def first_verified(cfg, d, max_rank):
    row = {"title": d["csv_title"], "date": d["csv_date"],
           "creators": d["csv_creators"]}
    groups = itertools.groupby(d["candidates"],
                               key=lambda c: (c["keytype"], c["probe"]))
    for (keytype, probe), grp in groups:
        for rank, c in enumerate(grp, 1):
            if rank > max_rank:
                break
            if mh.verify_title(cfg, c["marc"].encode("utf-8"), row):
                full = difflib.SequenceMatcher(
                    None, c["title"] or "", mh.norm(d["csv_title"])).ratio()
                band = "strong" if full >= mh.TITLE_STRONG else "weak+year"
                cyear = mh.year_of(d["csv_date"] or "")
                if not (cyear and c["year"]):
                    year = "unknown"
                elif abs(int(cyear) - int(c["year"])) <= 1:
                    year = "agree"
                else:
                    year = "conflict"
                return (keytype, rank, c["hits"], band, year,
                        c["title"], c["year"])
    return None


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("candidates")
    ap.add_argument("--max-rank", type=int, default=10,
                    help="the show_n to simulate (default 10)")
    args = ap.parse_args()

    with tempfile.TemporaryDirectory() as tmp:
        # decode_record needs a scratch state dir; the CSV/out paths are unused.
        cfg = mh.make_cfg(os.path.join(tmp, "x.csv"), os.path.join(tmp, "x.zip"))
        cfg["state"] = tmp
        n, hits = 0, []
        with open(args.candidates) as fh:
            for line in fh:
                d = json.loads(line)
                n += 1
                h = first_verified(cfg, d, args.max_rank)
                if h:
                    hits.append((d["key"], d["csv_title"], d["csv_date"], h))

    within = [h for h in hits if h[3][1] <= 3]
    beyond = [h for h in hits if h[3][1] > 3]
    print(f"rejects={n}  verify at rank<=3: {len(within)}  "
          f"at rank 4-{args.max_rank}: {len(beyond)}")
    tally = {y: sum(1 for h in beyond if h[3][4] == y)
             for y in ("agree", "unknown", "conflict")}
    print("  of which year " + ", ".join(f"{y}={n}" for y, n in tally.items()))
    print("key\trank/hits\tband\tyear\tcsv title (date)\trecord 245 (year)")
    for key, ctitle, cdate, (kt, rank, count, band, year, rtitle, ryear) in within + beyond:
        print(f"{key}\t{rank}/{count}\t{band}\t{year}\t{ctitle} ({cdate})\t{rtitle} ({ryear})")


if __name__ == "__main__":
    main()
