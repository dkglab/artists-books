#!/usr/bin/env python3
"""Re-query one server for the review.tsv rows that failed title verification and dump
each candidate's decoded 245/author/year next to the CSV row, so the genuine
false-negatives can be picked out by hand (issue #84, step 3).

Resumable: appends to candidates.jsonl and skips keys already present. Fetches
more candidates per probe than the harvest did (show_n=10 vs 3), since the whole
point is to see the ones verify_title never got to look at.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import marc_harvest as mh

# Harvest state for the run being adjudicated: harvest/<stem>.csv plus the
# gitignored harvest/<stem>/ state dir the run wrote.
HERE = os.path.dirname(os.path.abspath(__file__))
STEM = os.environ.get("STEM", "scad-residual")
SERVER = os.environ.get("SERVER", "scad")
STATE = os.path.join(HERE, "harvest")
OUT = os.path.join(STATE, f"{STEM}-candidates.jsonl")
REVIEW = os.path.join(STATE, STEM, "review.tsv")
CSV = os.path.join(STATE, f"{STEM}.csv")
# Deliberately wider than the harvest's show_n=3: the whole point is to see the
# candidates verify_title never got to look at (one of the 12 SCAD recoveries was
# ranked 4th of 7 hits).
SHOW_N = 10
BATCH = 10


def reject_keys():
    """Keys whose only review reason is a failed title verification -- the true
    rejects. Rows reading "N candidates; verified one" were accepted."""
    keys = []
    with open(REVIEW) as fh:
        for line in fh:
            parts = line.rstrip("\n").split("\t")
            if len(parts) >= 5 and parts[4] == "title hits failed verification":
                keys.append(parts[0])
    return keys


def main():
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else None

    cfg = mh.make_cfg(CSV, os.path.join(STATE, f"{STEM}.zip"))
    rows = mh.read_rows(cfg)
    rowmap = {mh.row_key(r): r for r in rows}
    server = next(s for s in mh.SERVERS if s["name"] == SERVER)

    done = set()
    if os.path.exists(OUT):
        with open(OUT) as fh:
            for line in fh:
                done.add(json.loads(line)["key"])

    wanted = [k for k in reject_keys() if k not in done]
    if limit:
        wanted = wanted[:limit]
    print(f"rejects={len(reject_keys())} done={len(done)} this_run={len(wanted)}",
          flush=True)

    targets = dict(mh.server_targets(rows, server))
    batch = [(k, targets[k]) for k in wanted if k in targets]

    for i in range(0, len(batch), BATCH):
        chunk = batch[i:i + BATCH]
        results = mh.run_zoom(cfg, server, chunk, SHOW_N)
        if results is None:
            print(f"batch {i // BATCH}: driver timeout, stopping", flush=True)
            break
        with open(OUT, "a") as fh:
            for key, probelist in results:
                row = rowmap[key]
                cands = []
                for keytype, value, count, recs in probelist:
                    for rec in recs:
                        title, main, authors, year = mh.decode_record(cfg, rec)
                        cands.append({
                            "keytype": keytype, "probe": value, "hits": count,
                            "title": title, "main": main,
                            "authors": authors, "year": year,
                            "marc": rec.decode("utf-8", "replace"),
                        })
                fh.write(json.dumps({
                    "key": key,
                    "csv_title": row.get("title", ""),
                    "csv_creators": row.get("creators", ""),
                    "csv_date": row.get("date", ""),
                    "csv_publisher": row.get("publisher", ""),
                    "candidates": cands,
                }) + "\n")
        print(f"batch {i // BATCH + 1}/{(len(batch) + BATCH - 1) // BATCH} done",
              flush=True)


if __name__ == "__main__":
    main()
