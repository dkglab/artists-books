#!/usr/bin/env python3
"""Merge hand-collected IIIF paths into ssid-media.csv (issue #168).

`harvest_media.py`'s Forum redirect chain started returning 403 for every SSID
in November 2026, and `content-service` is rate-limited, so the 68 bare-SSID
records added in #167 could not be harvested. Their IIIF paths were instead read
by hand off the `www.jstor.org/stable/community.<ssid>` item pages (Claude in
Chrome, slow browsing pace) into the frozen `ssid-iiif-links.csv`:

    ssid,status,iiifLinks
    24509442,ok,/iiif/2019/02/15/13/2ed9...037_deflate.tif|/iiif/2022/05/06/20/ead8..._deflate.tif

`iiifLinks` lists every image of the record in viewer order. As with
`harvest_media.py`, only the **first** is taken (one image per book); the rest
stay in the links file for later use. For each `ok` SSID not already in
`ssid-media.csv` this:

- splits `uuid`/`datePath` out of the first path,
- confirms the path against `{path}/info.json` on the open IIIF tier, which also
  gives the master's `width`/`height`,
- carries `filename`/`fileCount`/`imageViewType` through from the local Forum
  export, and checks the number of links against its `File Count`.

Existing rows are never touched. Output order follows `artstor-ssid.csv`, as
`harvest_media.py` writes it.
"""

import argparse
import csv
import re
import sys
import time

from harvest_media import info, read_export, read_ssids, row, write

PATH = re.compile(r"^/iiif/(\d{4}/\d{2}/\d{2}/\d{2})/([0-9a-f-]{36})_[a-z]+\.tif$")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--links", default="ssid-iiif-links.csv")
    p.add_argument("--ssids", default="artstor-ssid.csv")
    p.add_argument("--export", default="Jstor_Artists__book_records.csv")
    p.add_argument("--out", default="ssid-media.csv")
    p.add_argument("--delay", type=float, default=1.0)
    p.add_argument("--timeout", type=float, default=30.0)
    args = p.parse_args()

    ssids = read_ssids(args.ssids)
    export = read_export(args.export)
    with open(args.out, newline="", encoding="utf-8") as f:
        media = {r["ssid"]: r for r in csv.DictReader(f)}
    with open(args.links, newline="", encoding="utf-8") as f:
        links = [r for r in csv.DictReader(f) if r["status"] == "ok" and r["ssid"] not in media]

    added, failed = 0, 0
    for r in links:
        ssid, paths = r["ssid"], r["iiifLinks"].split("|")
        meta = export.get(ssid)
        m = PATH.match(paths[0])
        if not m:
            print(f"  {ssid}: unparseable path {paths[0]!r}", file=sys.stderr)
            failed += 1
            continue
        if meta and meta.get("File Count") and int(meta["File Count"]) != len(paths):
            print(f"  {ssid}: {len(paths)} links but File Count {meta['File Count']}",
                  file=sys.stderr)
        res = info(f"https://www.jstor.org{paths[0]}/info.json", args.timeout)
        time.sleep(args.delay)
        if not isinstance(res, tuple):
            print(f"  {ssid}: info.json -> {res}", file=sys.stderr)
            failed += 1
            continue
        media[ssid] = row(ssid, meta, "ok", uuid=m[2], datePath=m[1], iiifPath=paths[0],
                          width=res[0], height=res[1])
        added += 1

    known = set(ssids)
    unordered = [s for s in media if s not in known]
    if unordered:
        print(f"  {len(unordered)} rows not in {args.ssids} are dropped: {unordered[:5]}",
              file=sys.stderr)
    write(args.out, ssids, media)
    print(f"{added} added, {failed} failed -> {args.out} ({len(media)} rows)", file=sys.stderr)
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
