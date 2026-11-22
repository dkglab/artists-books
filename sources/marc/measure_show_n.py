#!/usr/bin/env python3
"""How much recall does the harvest's show_n window cost? (issue #98)

Reads an adjudicate_review.py candidates dump -- every candidate a server returns
for its own rejects, fetched at show_n=10 -- and replays the harvest's title
logic over it. For each book it reports the first candidate (probes in
precedence order, records in rank order) that plain verify_title accepts. A rank
inside the trusted window means the original harvest would have taken it, so a
dump of true rejects should have none; every acceptance below the window is
recall the window lost.

Columns:
  band   why verify_title accepted: "strong" (full-title ratio >= TITLE_STRONG)
         or "weak+year" (a weak-band title corroborated by the year).
  year   the record's year against the CSV's: "agree" (within one year),
         "conflict", or "unknown" (either side has none). The strong band takes
         no year at all, so on short common titles ("Sans titre", "Climax") a
         deeper window mostly surfaces *other works of the same title*.
  guard  what the harvest now does with the book: select_record with the
         server's window, i.e. verify_title inside it and the stricter
         verify_deep below it. "accept @rank: title (year)" names the record it
         keeps, which need not be the one plain verify would have taken first;
         "reject" if none clears.

Offline: no server is queried.

    python3 measure_show_n.py harvest/scad-residual-candidates.jsonl
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


def probes(d, max_rank):
    """[(keytype, probe, hits, [candidate, ...])] in precedence then rank order."""
    out = []
    for (kt, probe), grp in itertools.groupby(
            d["candidates"], key=lambda c: (c["keytype"], c["probe"])):
        grp = list(grp)[:max_rank]
        out.append((kt, probe, grp[0]["hits"], grp))
    return out


def year_agreement(cdate, ryear):
    cyear = mh.year_of(cdate or "")
    if not (cyear and ryear):
        return "unknown"
    return "agree" if abs(int(cyear) - int(ryear)) <= 1 else "conflict"


def replay(cfg, d, max_rank, window):
    """(keytype, rank, hits, band, year, guard, record title, record year) for
    the first candidate plain verify_title accepts, or None."""
    row = {"title": d["csv_title"], "date": d["csv_date"],
           "creators": d["csv_creators"]}
    plist = probes(d, max_rank)
    status, _kt, _v, rec, _n, _review = mh.select_record(
        cfg, d["key"],
        [(kt, p, n, [c["marc"].encode("utf-8") for c in grp])
         for kt, p, n, grp in plist],
        {d["key"]: row}, window=window)
    guard = "reject"
    if status == "ok":
        chosen = next(c for _kt, _p, _n, grp in plist for c in grp
                      if c["marc"].encode("utf-8") == rec)
        rank = next(i for _kt, _p, _n, grp in plist
                    for i, c in enumerate(grp, 1) if c is chosen)
        guard = f"accept @{rank}: {chosen['title']} ({chosen['year']})"
    for kt, _probe, n, grp in plist:
        for rank, c in enumerate(grp, 1):
            if mh.verify_title(cfg, c["marc"].encode("utf-8"), row):
                full = difflib.SequenceMatcher(
                    None, c["title"] or "", mh.norm(d["csv_title"])).ratio()
                band = "strong" if full >= mh.TITLE_STRONG else "weak+year"
                return (kt, rank, n, band, year_agreement(d["csv_date"], c["year"]),
                        guard, c["title"], c["year"])
    return None


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("candidates")
    ap.add_argument("--max-rank", type=int, default=mh.TITLE_SHOW_N,
                    help="the depth to simulate (default TITLE_SHOW_N)")
    ap.add_argument("--window", type=int, default=3,
                    help="the server's trusted show_n (default 3)")
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
                h = replay(cfg, d, args.max_rank, args.window)
                if h:
                    hits.append((d["key"], d["csv_title"], d["csv_date"], h))

    within = [h for h in hits if h[3][1] <= args.window]
    beyond = [h for h in hits if h[3][1] > args.window]
    print(f"rejects={n}  verify at rank<={args.window}: {len(within)}  "
          f"at rank {args.window + 1}-{args.max_rank}: {len(beyond)}")
    tally = {y: sum(1 for h in beyond if h[3][4] == y)
             for y in ("agree", "unknown", "conflict")}
    print("  of which year " + ", ".join(f"{y}={k}" for y, k in tally.items()))
    print(f"  the guarded harvest accepts "
          f"{sum(1 for h in beyond if h[3][5] != 'reject')}")
    print("key\trank/hits\tband\tyear\tguard\tcsv title (date)\trecord 245 (year)")
    for key, ctitle, cdate, (_kt, rank, count, band, year, guard,
                             rtitle, ryear) in within + beyond:
        print(f"{key}\t{rank}/{count}\t{band}\t{year}\t{guard}\t"
              f"{ctitle} ({cdate})\t{rtitle} ({ryear})")


if __name__ == "__main__":
    main()
