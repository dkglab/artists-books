#!/usr/bin/env python3
"""Harvest the JSTOR IIIF image identifiers for each Forum SSID (issue #9).

`artstor-ssid.csv` gets us from a catalogue record to a JSTOR Forum SSID. This
script takes the next step: SSID -> the IIIF identifiers of that record's images.

That step is a genuine lookup, not string manipulation. The IIIF identifier is a
date-partitioned S3 path whose codec suffix varies:

    /iiif/2016/04/29/16/e31d56f8-4cf7-4053-a74b-033fcb088b79_deflate.tif
          |- upload time -| |------- media UUID -------|   |- codec -|

so nothing in it can be derived from the SSID. One request per SSID:

    GET https://www.jstor.org/content-service/content-data/community.<SSID>
      -> content.iiifLinks[]  -- ordered, one entry per image, [0] is page 1
         content.pageCount    -- == len(iiifLinks) in every record checked
         content.metadata[]   -- carries "Image View Description"

The images themselves (`{iiifPath}/info.json`, `{iiifPath}/full/full/0/default.jpg`)
are open Cantaloupe IIIF Image API 2.1 endpoints needing no headers at all, so
only this one-time metadata harvest is access-constrained.

"Image View Description", *not* the file name, is what says whether page 1 is the
cover: `(Cover & interior images)` -> iiifLinks[0]; `(Images of the enclosure,
cover, & interior)` -> page 1 is the slipcase and the cover is iiifLinks[1];
`(Interior image)` / `(Open)` -> the record has no cover at all. It is recorded
here verbatim; deciding what to do with it is the consumer's job.

Access: the metadata API wants a browser-like User-Agent *and* a non-empty
Cookie header -- that is the whole gate, no session needed. Send junk (`x=y`),
never harvested browser state: a stale PerimeterX `_pxhd` cookie causes a 403.

Rate limiting is the hazard, and it escalates. The API is limited per IP (blocked
after ~15-20 requests during the #9 investigation, at one request every 2s); a
first block cleared in 90s of silence, but continuing to request while blocked
pushed the penalty past 25 minutes. So this script does NOT retry a 403 -- it
stops the whole run at the first one and exits cleanly, leaving the next
invocation to resume. --delay defaults to 8s, which is an untested estimate of a
sustainable rate, not a measurement.

Resumable: SSIDs already recorded as done are read back from --out and skipped,
so the run can be chunked with --limit, and the CSV is rewritten after every
record. Rows whose status is not `ok`/`no-images` are dropped on the next run and
retried; SSIDs never yet attempted have no rows at all (unlike artstor-ssid.csv,
one row per *image* means an unattempted record has no row shape to reserve).
"""

import argparse
import csv
import json
import os
import sys
import time
import urllib.error
import urllib.request

API = "https://www.jstor.org/content-service/content-data/community.{}"
# Browser-like UA + any non-empty cookie: see the access note in the docstring.
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36"
)
COOKIE = "x=y"
VIEW_LABEL = "Image View Description"
FIELDS = ["ssid", "pageIndex", "iiifPath", "pageCount", "imageViewDescription", "status"]
# Statuses that count as a finished lookup; anything else is retried next run.
DONE = {"ok", "no-images"}


class Blocked(Exception):
    """The limiter tripped. Stop the run -- retrying is what escalates it."""


def read_ssids(path):
    """Distinct SSIDs from the artstor crosswalk, in file order."""
    with open(path, newline="", encoding="utf-8") as f:
        return list(
            dict.fromkeys(
                row["ssid"] for row in csv.DictReader(f) if row["status"] == "ok" and row["ssid"]
            )
        )


def read_done(path):
    """ssid -> its rows, for SSIDs a previous run finished with."""
    harvested = {}
    try:
        with open(path, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                if row["status"] in DONE:
                    harvested.setdefault(row["ssid"], []).append(row)
    except FileNotFoundError:
        pass
    return harvested


def view_description(content):
    for entry in content.get("metadata") or []:
        if entry.get("label") == VIEW_LABEL:
            return "; ".join(entry.get("value") or [])
    return ""


def rows_for(ssid, content):
    """One row per image, or a single no-images row."""
    links = content.get("iiifLinks") or []
    count = content.get("pageCount", "")
    desc = view_description(content)
    if not links:
        return [row(ssid, "", "", count, desc, "no-images")]
    if count != "" and count != len(links):
        print(f"  {ssid}: pageCount {count} != {len(links)} iiifLinks", file=sys.stderr)
    return [row(ssid, i, path, count, desc, "ok") for i, path in enumerate(links)]


def row(ssid, index, path, count, desc, status):
    return {
        "ssid": ssid,
        "pageIndex": index,
        "iiifPath": path,
        "pageCount": count,
        "imageViewDescription": desc,
        "status": status,
    }


def fetch(opener, ssid, timeout, retries, delay):
    """Look up one SSID -> its rows. Raises Blocked on 403/429/JS challenge."""
    last = "retries exhausted"
    for attempt in range(retries):
        try:
            with opener.open(urllib.request.Request(API.format(ssid)), timeout=timeout) as r:
                body = r.read()
        except urllib.error.HTTPError as e:
            if e.code in (403, 429):  # "JSTOR: Access Check" -- the rate limit
                raise Blocked(f"http:{e.code}")
            if e.code >= 500:
                time.sleep(delay * (2**attempt) * 5)
                last = f"http:{e.code}"
                continue
            return [row(ssid, "", "", "", "", f"http:{e.code}")]
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            time.sleep(delay * (2**attempt) * 5)
            last = str(e)[:60]
            continue
        if b"Client Challenge" in body:  # Fastly JS challenge: this IP is blocked
            raise Blocked("js-challenge")
        try:
            content = json.loads(body)["content"]
        except (ValueError, KeyError, TypeError):
            return [row(ssid, "", "", "", "", "unparseable")]
        return rows_for(ssid, content)
    return [row(ssid, "", "", "", "", f"error:{last}")]


def write(path, ssids, harvested):
    """Rewrite the CSV: SSIDs in crosswalk order, images in page order."""
    tmp = f"{path}.tmp"
    with open(tmp, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        for ssid in ssids:
            w.writerows(harvested.get(ssid, ()))
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--ssids", default="artstor-ssid.csv", help="the SSID crosswalk to read")
    p.add_argument("--out", default="ssid-iiif.csv")
    p.add_argument("--limit", type=int, default=0, help="max lookups this run (0 = all)")
    p.add_argument("--delay", type=float, default=8.0, help="seconds between requests")
    p.add_argument("--timeout", type=float, default=30.0)
    p.add_argument("--retries", type=int, default=3)
    args = p.parse_args()

    ssids = read_ssids(args.ssids)
    harvested = read_done(args.out)
    todo = [s for s in ssids if s not in harvested]
    if args.limit:
        todo = todo[: args.limit]

    print(
        f"{len(ssids)} SSIDs; {len(harvested)} already harvested; {len(todo)} to fetch "
        f"at {args.delay}s => ~{len(todo) * args.delay / 60:.0f} min",
        file=sys.stderr,
    )

    opener = urllib.request.build_opener()
    opener.addheaders = [("User-Agent", USER_AGENT), ("Cookie", COOKIE)]
    stopped = ""
    for i, ssid in enumerate(todo, 1):
        try:
            rows = fetch(opener, ssid, args.timeout, args.retries, args.delay)
        except Blocked as e:
            stopped = f"{e} after {i - 1} lookups this run"
            break
        harvested[ssid] = rows
        if rows[0]["status"] != "ok":
            print(f"  {ssid}: {rows[0]['status']}", file=sys.stderr)
        write(args.out, ssids, harvested)  # checkpoint every record
        if i % 25 == 0:
            print(f"  ...{i}/{len(todo)}", file=sys.stderr)
        time.sleep(args.delay)

    write(args.out, ssids, harvested)
    images = sum(1 for rs in harvested.values() for r in rs if r["status"] == "ok")
    print(
        f"{len(harvested)}/{len(ssids)} SSIDs, {images} images -> {args.out}",
        file=sys.stderr,
    )
    if stopped:
        print(
            f"BLOCKED ({stopped}). Stopping; nothing is lost. Do NOT rerun "
            "immediately -- requesting while blocked extends the penalty. Wait "
            "(minutes, not seconds), then rerun to resume.",
            file=sys.stderr,
        )


if __name__ == "__main__":
    main()
