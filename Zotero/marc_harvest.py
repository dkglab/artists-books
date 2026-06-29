#!/usr/bin/env python3
"""Harvest full MARC records for the items in a Zotero CSV from UNC's Z39.50 server.

Strategy (see Zotero/README.md):
  * Search keys : per item, tried in order, first hit wins --
                    1. Innopac bib number from the catalog URL (.../UNCb<digits>),
                       queried as  @attr 1=12 b<digits>  (unique).
                    2. each ISBN from the ISBN column, as  @attr 1=7 <isbn>.
                  Bib numbers dominate the artist's books; ISBN reaches the many
                  reference works UNC holds but cataloged without a UNCb URL.
                  (OCLC is not used -- UNC's INNOPAC does not index it.)
  * Join key    : the Zotero itemKey. We know which itemKey we queried for, so
                  each retrieved record is stamped with a synthetic
                  999 $a <itemKey> $b <value> $c <keytype>  -- no content join.
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

# YAZ is built under tools/yaz-client/ (see tools/yaz-client/Makefile), not
# installed system-wide. Resolve the binaries from there so the harvest uses our
# self-contained build rather than whatever happens to be on $PATH.
YAZ_BIN     = os.path.normpath(os.path.join(HERE, os.pardir, "tools", "yaz-client", "bin"))
YAZ_CLIENT  = os.path.join(YAZ_BIN, "yaz-client")
YAZ_MARCDUMP = os.path.join(YAZ_BIN, "yaz-marcdump")

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
        "manifest": os.path.join(state, "manifest.tsv"),   # itemKey keytype value status (retrieval order)
        "missing": os.path.join(state, "missing.tsv"),     # itemKey value reason
        "review": os.path.join(state, "review.tsv"),       # itemKey keytype value: query matched >1 holding
    }


def clean_isbns(raw):
    """Split an ISBN field into clean 10/13-digit tokens (hyphens/price noise removed)."""
    out = []
    for tok in (raw or "").split():
        t = re.sub(r"[^0-9Xx]", "", tok)
        if len(t) in (10, 13):
            out.append(t.upper())
    return out


def read_targets(cfg):
    """Return [(itemKey, [(keytype, attr, value), ...])] and [(itemKey, reason)].

    Each target carries an ordered list of search keys; harvest tries them in
    order and keeps the first hit. Precedence: the UNC Innopac bib number
    (1=12, unique) first, then each ISBN (1=7). OCLC is intentionally omitted --
    UNC's INNOPAC does not index OCLC numbers (verified: 0 hits for 1=1007/7/12).
    """
    targets, skipped = [], []
    with open(cfg["csv"], newline="") as fh:
        for row in csv.DictReader(fh):
            keys = []
            m = re.search(r"/UNCb(\d+)", row["url"])
            if m:
                keys.append(("bib", "1=12", "b" + m.group(1)))
            for isbn in clean_isbns(row.get("ISBN", "")):
                keys.append(("isbn", "1=7", isbn))
            if keys:
                targets.append((row["itemKey"], keys))
            else:
                skipped.append((row["itemKey"], "no bib number or ISBN"))
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


def split_records(blob):
    """Split a binary MARC blob into individual records (each ends with 0x1D)."""
    recs, start = [], 0
    for i, byte in enumerate(blob):
        if byte == 0x1D:
            recs.append(blob[start:i + 1])
            start = i + 1
    return recs


def run_batch(cfg, batch):
    """Query a batch over one connection, trying each target's keys until one hits.

    batch is [(itemKey, [(keytype, attr, value), ...]), ...]. Returns
    (results, stdout) where results is one tuple per target, in order:
        (itemKey, status, keytype, value, record_bytes_or_None, review)
    status is "ok"/"miss"; on "ok" keytype/value/record describe the FIRST key
    that hit, and review is True when that query matched >1 holding (so `show 1`
    picked one of several -- a possible wrong-edition pick worth checking).

    Returns (None, stdout) if the server output can't be aligned to the probes
    (hit-line count or record count off), so the caller can retry per target.
    """
    tmp = os.path.join(cfg["state"], "_batch.marc")
    if os.path.exists(tmp):
        os.remove(tmp)

    # One probe per (target, key); probes for a target are contiguous, in order.
    probes = []  # (keytype, attr, value)
    cmds = ["format usmarc", "querytype prefix"]
    for _key, keys in batch:
        for keytype, attr, value in keys:
            probes.append((keytype, attr, value))
            cmds.append(f"find @attr {attr} {value}")
            cmds.append("show 1")
            cmds.append(f"sleep {QUERY_SLEEP}")
    cmds.append("quit")
    proc = subprocess.run(
        [YAZ_CLIENT, "-m", tmp, SERVER],
        input="\n".join(cmds) + "\n",
        capture_output=True, text=True, timeout=60 + len(probes) * 10,
    )

    counts = [int(n) for n in re.findall(r"Number of hits:\s*(\d+)", proc.stdout)]
    if len(counts) != len(probes):
        return None, proc.stdout  # parsing slipped -- let caller retry per target

    records = split_records(open(tmp, "rb").read() if os.path.exists(tmp) else b"")
    if len(records) != sum(1 for c in counts if c > 0):
        return None, proc.stdout  # show/hit misalignment -- retry per target

    # Re-attach each hitting probe's record (probes that missed get None).
    rec_iter = iter(records)
    probe_rec = [next(rec_iter) if c > 0 else None for c in counts]

    results, i = [], 0
    for key, keys in batch:
        chosen = None  # (keytype, value, record, count) of the first key that hit
        for _ in range(len(keys)):
            keytype, _attr, value = probes[i]
            if probe_rec[i] is not None and chosen is None:
                chosen = (keytype, value, probe_rec[i], counts[i])
            i += 1
        if chosen:
            results.append((key, "ok", chosen[0], chosen[1], chosen[2],
                            chosen[3] > 1))
        else:
            results.append((key, "miss", "", "", None, False))
    return results, proc.stdout


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

    pending = [(k, keys) for (k, keys) in targets if k not in done]
    if limit:
        pending = pending[:limit]
    print(f"targets={len(targets)} already_done={len(done)} "
          f"this_run={len(pending)} no_id={len(skipped)}")

    for start in range(0, len(pending), BATCH_SIZE):
        batch = pending[start:start + BATCH_SIZE]
        results, _log = run_batch(cfg, batch)

        if results is None:
            print(f"  !! batch at {start}: server output unalignable; "
                  f"retrying per target", file=sys.stderr)
            results = []
            for one in batch:
                r, _ = run_batch(cfg, [one])
                if r is None:
                    print(f"  !! {one[0]}: still unalignable, deferring to next "
                          f"run", file=sys.stderr)  # no manifest row -> retried
                else:
                    results.extend(r)

        data = b"".join(rec for _k, st, _kt, _v, rec, _rv in results if st == "ok")
        n_hit = sum(1 for _k, st, *_ in results if st == "ok")
        if count_records(data) != n_hit:
            print(f"  !! batch at {start}: {count_records(data)} records but "
                  f"{n_hit} hits -- ABORT to avoid misaligned itemKeys",
                  file=sys.stderr)
            sys.exit(2)

        with open(cfg["combined"], "ab") as fh:
            fh.write(data)
        with open(cfg["manifest"], "a") as mf, \
                open(cfg["missing"], "a") as miss, \
                open(cfg["review"], "a") as rev:
            for key, st, keytype, value, _rec, review in results:
                mf.write(f"{key}\t{keytype}\t{value}\t{st}\n")
                if st != "ok":
                    miss.write(f"{key}\t\tnot found on server\n")
                elif review:
                    rev.write(f"{key}\t{keytype}\t{value}\t"
                              f"matched >1 holding; show 1 picked one\n")

        n_done = len(results)
        print(f"  batch {start // BATCH_SIZE}: {n_done} queried, "
              f"{n_hit} found, {n_done - n_hit} missing")
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
        [YAZ_MARCDUMP, "-l", "9=97", "-i", "marc", "-o", "marcxml", cfg["combined"]],
        capture_output=True, text=True,
    ).stdout

    ET.register_namespace("", MARC_NS)
    root = ET.fromstring(raw)
    records = root.findall(f"{{{MARC_NS}}}record")

    # Manifest ok rows, in retrieval order, as (itemKey, keytype, value).
    # New format is 4 cols (itemKey, keytype, value, status); tolerate the old
    # 3-col bib-only format (itemKey, bibnum, status) so a pre-existing harvest
    # state (e.g. artists-books') re-combines correctly.
    ok_rows = []
    for line in open(cfg["manifest"]):
        cols = line.rstrip("\n").split("\t")
        if cols[-1] != "ok":
            continue
        if len(cols) >= 4:
            ok_rows.append((cols[0], cols[1], cols[2]))
        else:  # legacy: itemKey, bibnum, status
            ok_rows.append((cols[0], "bib", cols[1]))
    if len(ok_rows) != len(records):
        print(f"FATAL: {len(records)} records vs {len(ok_rows)} ok manifest rows; "
              f"refusing to stamp itemKeys", file=sys.stderr)
        sys.exit(3)

    for rec, (key, keytype, value) in zip(records, ok_rows):
        df = ET.SubElement(rec, f"{{{MARC_NS}}}datafield")
        df.set("tag", "999"); df.set("ind1", " "); df.set("ind2", " ")
        # $a join key (itemKey), $b resolving search value, $c its key type.
        for code, val in (("a", key), ("b", value), ("c", keytype)):
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
