#!/usr/bin/env python3
"""Harvest full MARC records for the items in a Zotero CSV from UNC's Z39.50 server.

Strategy (see Zotero/README.md):
  * Search key  : the Innopac bib number, taken from the catalog URL
                  (.../UNCb<digits>) and queried as  @attr 1=12 b<digits>.
                  Most rows lack an ISBN but have a bib number.
  * Join key    : the Zotero itemKey. We know which itemKey we queried for, so
                  each retrieved record is stamped with a synthetic
                  999 $a <itemKey> $b <bibnum> field -- no content-based join.
  * Politeness  : one serial connection, reused across a batch of queries, with
                  a `sleep` between each query and a pause between batches.
  * Encoding    : Innopac sends UTF-8 bytes but mislabels leader/09 as MARC-8, so
                  we do NOT transcode (that double-encodes); we only rewrite
                  leader/09 to 'a' so each record is honestly self-describing.
  * Output      : a single MARCXML <collection>. Per-CSV harvest state lives under
                  marc/<csv-stem>/ (combined.marc is append-only and resumable).

Run:
    python3 marc_harvest.py --csv artists-books.csv --out artists-books-marc.xml
    python3 marc_harvest.py --csv artists-books.csv --out artists-books-marc.xml --limit 15
    python3 marc_harvest.py --csv artists-books.csv --out artists-books-marc.xml --combine
"""
import argparse
import csv
import os
import re
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

SERVER      = "tcp:afton.lib.unc.edu:210/INNOPAC"
HERE        = os.path.dirname(os.path.abspath(__file__))
MARC_DIR    = os.path.join(HERE, "marc")  # gitignored harvest state, per-CSV subdir

BATCH_SIZE  = 50      # queries per reused connection
QUERY_SLEEP = 0.4     # seconds between queries within a connection
BATCH_SLEEP = 2       # seconds between batches
MARC_NS     = "http://www.loc.gov/MARC21/slim"


def make_cfg(csv_path, out_xml):
    """Resolve all paths for one CSV; harvest state lives in marc/<csv-stem>/."""
    csv_path = os.path.abspath(csv_path)
    base = os.path.splitext(os.path.basename(csv_path))[0]
    state = os.path.join(MARC_DIR, base)
    return {
        "csv": csv_path,
        "out": os.path.abspath(out_xml),
        "state": state,
        "combined": os.path.join(state, "combined.marc"),  # binary MARC, append-only
        "manifest": os.path.join(state, "manifest.tsv"),   # itemKey bibnum status (retrieval order)
        "missing": os.path.join(state, "missing.tsv"),     # itemKey bibnum reason
    }


def read_targets(cfg):
    """Return [(itemKey, bibnum)] and a list of (itemKey, reason) with no bib number."""
    targets, skipped = [], []
    with open(cfg["csv"], newline="") as fh:
        for row in csv.DictReader(fh):
            m = re.search(r"/UNCb(\d+)", row["url"])
            if m:
                targets.append((row["itemKey"], "b" + m.group(1)))
            else:
                skipped.append((row["itemKey"], "no bib number in url"))
    return targets, skipped


def load_done(cfg):
    """itemKeys already recorded in the manifest (ok or miss) -> resumable."""
    done = set()
    if os.path.exists(cfg["manifest"]):
        with open(cfg["manifest"]) as fh:
            for line in fh:
                parts = line.rstrip("\n").split("\t")
                if parts and parts[0]:
                    done.add(parts[0])
    return done


def run_batch(cfg, batch):
    """Query a batch over one connection. Returns (ordered_hits, marc_bytes, stdout).

    ordered_hits[i] is True/False for batch[i], in order; marc_bytes holds exactly
    one record per True, in the same order.
    """
    tmp = os.path.join(cfg["state"], "_batch.marc")
    if os.path.exists(tmp):
        os.remove(tmp)
    cmds = ["format usmarc", "querytype prefix"]
    for _key, bib in batch:
        cmds.append(f"find @attr 1=12 {bib}")
        cmds.append("show 1")
        cmds.append(f"sleep {QUERY_SLEEP}")
    cmds.append("quit")
    proc = subprocess.run(
        ["yaz-client", "-m", tmp, SERVER],
        input="\n".join(cmds) + "\n",
        capture_output=True, text=True, timeout=60 + len(batch) * 10,
    )
    # A bib number is unique, so each find's hit count is 0 or 1, in query order.
    hits = [int(n) > 0 for n in re.findall(r"Number of hits:\s*(\d+)", proc.stdout)]
    data = open(tmp, "rb").read() if os.path.exists(tmp) else b""
    return hits, data, proc.stdout


def count_records(marc_bytes):
    """Count records in a binary MARC blob (records end with the 0x1D terminator)."""
    return marc_bytes.count(b"\x1d")


def harvest(cfg, limit=None):
    os.makedirs(cfg["state"], exist_ok=True)
    targets, skipped = read_targets(cfg)
    done = load_done(cfg)

    if skipped and not os.path.exists(cfg["missing"]):
        with open(cfg["missing"], "w") as fh:
            for key, reason in skipped:
                fh.write(f"{key}\t\t{reason}\n")

    pending = [(k, b) for (k, b) in targets if k not in done]
    if limit:
        pending = pending[:limit]
    print(f"targets={len(targets)} already_done={len(done)} "
          f"this_run={len(pending)} no_id={len(skipped)}")

    for start in range(0, len(pending), BATCH_SIZE):
        batch = pending[start:start + BATCH_SIZE]
        hits, data, _log = run_batch(cfg, batch)

        if len(hits) != len(batch):
            print(f"  !! batch at {start}: got {len(hits)} hit-lines for "
                  f"{len(batch)} queries; re-running one-by-one", file=sys.stderr)
            batch_hits, blobs = [], []
            for one in batch:
                h, d, _ = run_batch(cfg, [one])
                ok = bool(h and h[0])
                batch_hits.append(ok)
                if ok:
                    blobs.append(d)
            hits, data = batch_hits, b"".join(blobs)

        n_hit, n_rec = sum(hits), count_records(data)
        if n_rec != n_hit:
            print(f"  !! batch at {start}: {n_rec} records but {n_hit} hits "
                  f"-- ABORT to avoid misaligned itemKeys", file=sys.stderr)
            sys.exit(2)

        with open(cfg["combined"], "ab") as fh:
            fh.write(data)
        with open(cfg["manifest"], "a") as mf, open(cfg["missing"], "a") as miss:
            for (key, bib), ok in zip(batch, hits):
                mf.write(f"{key}\t{bib}\t{'ok' if ok else 'miss'}\n")
                if not ok:
                    miss.write(f"{key}\t{bib}\tnot found on server\n")

        print(f"  batch {start // BATCH_SIZE}: {len(batch)} queried, "
              f"{n_hit} found, {len(batch) - n_hit} missing")
        if start + BATCH_SIZE < len(pending):
            time.sleep(BATCH_SLEEP)

    combine(cfg)


def combine(cfg):
    """Convert combined.marc -> single MARCXML <collection>, stamping itemKeys."""
    if not os.path.exists(cfg["combined"]):
        print("no combined.marc yet -- nothing to combine", file=sys.stderr)
        return
    raw = subprocess.run(
        # No transcode (bytes are already UTF-8); just mark leader/09 'a' (97).
        ["yaz-marcdump", "-l", "9=97", "-i", "marc", "-o", "marcxml", cfg["combined"]],
        capture_output=True, text=True,
    ).stdout

    ET.register_namespace("", MARC_NS)
    root = ET.fromstring(raw)
    records = root.findall(f"{{{MARC_NS}}}record")

    ok_rows = [tuple(l.rstrip("\n").split("\t")[:2])
               for l in open(cfg["manifest"]) if l.rstrip("\n").endswith("\tok")]
    if len(ok_rows) != len(records):
        print(f"FATAL: {len(records)} records vs {len(ok_rows)} ok manifest rows; "
              f"refusing to stamp itemKeys", file=sys.stderr)
        sys.exit(3)

    for rec, (key, bib) in zip(records, ok_rows):
        df = ET.SubElement(rec, f"{{{MARC_NS}}}datafield")
        df.set("tag", "999"); df.set("ind1", " "); df.set("ind2", " ")
        for code, val in (("a", key), ("b", bib)):
            sf = ET.SubElement(df, f"{{{MARC_NS}}}subfield")
            sf.set("code", code); sf.text = val

    ET.ElementTree(root).write(cfg["out"], encoding="unicode", xml_declaration=True)
    print(f"wrote {cfg['out']}: {len(records)} records (itemKey in 999 $a)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--csv", required=True, help="input Zotero CSV")
    ap.add_argument("--out", required=True, help="output MARCXML collection path")
    ap.add_argument("--limit", type=int, help="only process first N pending targets")
    ap.add_argument("--combine", action="store_true",
                    help="just (re)build the output XML from existing harvest state")
    args = ap.parse_args()
    cfg = make_cfg(args.csv, args.out)
    if args.combine:
        combine(cfg)
    else:
        harvest(cfg, limit=args.limit)
