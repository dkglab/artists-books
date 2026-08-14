#!/usr/bin/env python3
"""Harvest SSID -> IIIF image identifier via the Forum redirect chain (issue #9).

This is the *working* route to the IIIF identifiers. `harvest_iiif.py` asks
`www.jstor.org/content-service/` directly and is refused: that endpoint is gated
against automation, not merely throttled (see `scratch/README.md`). This script
never touches it. Instead it follows the chain that Sloane's own Forum export
publishes in its `Media URL` column:

    forum.jstor.org/assets/<SSID>/representation-view
      -302->  stor.artstor.org/stor/<uuid>                     -- the media UUID
      -302->  ...s3.amazonaws.com/prod.cirrostratus.org/YYYY/MM/DD/HH/<uuid>?...
                                                    |- date partition -|

Neither redirect host is PerimeterX-gated. Only the two `Location` headers are
read -- the S3 URL is **never fetched and never stored**: it is presigned,
expiring, and carries live AWS credentials.

The UUID and the date partition are exactly the two components of the IIIF
identifier that cannot be derived from the SSID:

    /iiif/2016/04/29/16/e31d56f8-4cf7-4053-a74b-033fcb088b79_deflate.tif
          |- date part -| |-------- media UUID --------|    |- codec -|

The codec suffix still varies, so each candidate is confirmed against
`{iiifPath}/info.json` on the open IIIF tier (no headers, unthrottled), which
also yields `width`/`height` for the templates.

Scope: `representation-view` resolves to the record's **first** image, not
necessarily its cover. For most records image 1 is the cover, but where
`imageViewType` is `(Images of the enclosure, cover, & interior)` image 1 is the
slipcase and the real cover is image 2, which this route cannot reach; records
typed `(Interior image[s])` have no cover at all. `imageViewType` is carried
through from the local Forum export so consumers can tell which is which. This
harvests one image per book; interiors still need the gated route.
"""

import argparse
import csv
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

FORUM = "https://forum.jstor.org/assets/{}/representation-view"
STOR = "https://stor.artstor.org/stor/{}"
IIIF = "https://www.jstor.org/iiif/{}/{}{}"
CODECS = ("_deflate.tif", "_jpeg.tif")
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36"
)
FIELDS = [
    "ssid", "uuid", "datePath", "iiifPath", "width", "height",
    "filename", "fileCount", "imageViewType", "status",
]
DONE = {"ok"}


class Blocked(Exception):
    """A limiter tripped. Stop the run rather than escalate it."""


class NoRedirect(urllib.request.HTTPRedirectHandler):
    """Return 3xx responses as-is; we want the Location header, not the target."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def read_ssids(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(
            dict.fromkeys(
                r["ssid"] for r in csv.DictReader(f) if r["status"] == "ok" and r["ssid"]
            )
        )


def read_export(path):
    """SSID -> the local Forum export row (filename, file count, view type)."""
    with open(path, newline="", encoding="utf-8-sig") as f:
        return {r["SSID"]: r for r in csv.DictReader(f)}


def read_done(path):
    harvested = {}
    try:
        with open(path, newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                if r["status"] in DONE:
                    harvested[r["ssid"]] = r
    except FileNotFoundError:
        pass
    return harvested


def location(opener, url, timeout):
    """The Location header of a single un-followed redirect."""
    try:
        with opener.open(urllib.request.Request(url), timeout=timeout) as r:
            if r.status in (403, 429):
                raise Blocked(f"http:{r.status} at {urllib.parse.urlparse(url).netloc}")
            return r.status, r.headers.get("Location") or ""
    except urllib.error.HTTPError as e:
        # A declined redirect surfaces here, so the Location we want is on the
        # exception rather than on a response object.
        if e.code in (403, 429):
            raise Blocked(f"http:{e.code} at {urllib.parse.urlparse(url).netloc}")
        return e.code, e.headers.get("Location") or ""


def info(url, timeout):
    """`info.json` for a candidate IIIF path.

    Returns `(width, height)` on success, else the HTTP status if there was one.
    A 403 here means the asset itself is access-restricted -- distinct from a 404,
    which just means this codec guess was wrong.
    """
    req = urllib.request.Request(url)  # open tier: deliberately no headers
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            d = json.loads(r.read())
        return d.get("width"), d.get("height")
    except urllib.error.HTTPError as e:
        return e.code
    except (urllib.error.URLError, ValueError, TimeoutError, OSError):
        return None


def date_path(s3_url):
    """`.../prod.cirrostratus.org/YYYY/MM/DD/HH/<uuid>` -> `YYYY/MM/DD/HH`.

    Only the path is touched; the presigned query string is never read or kept.
    """
    parts = urllib.parse.urlparse(s3_url).path.strip("/").split("/")
    return "/".join(parts[-5:-1]) if len(parts) >= 5 else ""


def row(ssid, meta, status, **kw):
    r = {f: "" for f in FIELDS}
    r.update(
        ssid=ssid,
        filename=(meta.get("Filename") or "") if meta else "",
        fileCount=(meta.get("File Count") or "") if meta else "",
        imageViewType=(meta.get("Image View Type[4603]") or "").strip() if meta else "",
        status=status,
    )
    r.update(kw)
    return r


def resolve(opener, ssid, meta, timeout):
    code, loc = location(opener, FORUM.format(ssid), timeout)
    if not loc:
        return row(ssid, meta, f"no-uuid:http:{code}")
    uuid = loc.rstrip("/").rsplit("/", 1)[-1]

    code, s3 = location(opener, STOR.format(uuid), timeout)
    if not s3:
        return row(ssid, meta, f"no-media:http:{code}", uuid=uuid)
    dp = date_path(s3)
    if not dp:
        return row(ssid, meta, "no-datepath", uuid=uuid)

    codes = set()
    for codec in CODECS:
        path = f"/iiif/{dp}/{uuid}{codec}"
        res = info(f"https://www.jstor.org{path}/info.json", timeout)
        if isinstance(res, tuple):
            return row(ssid, meta, "ok", uuid=uuid, datePath=dp, iiifPath=path,
                       width=res[0], height=res[1])
        codes.add(res)
    # Every candidate 403 => the asset is restricted, not a bad codec guess.
    status = "restricted" if codes == {403} else "no-iiif"
    return row(ssid, meta, status, uuid=uuid, datePath=dp)


def write(path, ssids, harvested):
    tmp = f"{path}.tmp"
    with open(tmp, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        for s in ssids:
            if s in harvested:
                w.writerow(harvested[s])
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--ssids", default="artstor-ssid.csv")
    p.add_argument("--export", default="Jstor_Artists__book_records.csv")
    p.add_argument("--out", default="ssid-media.csv")
    p.add_argument("--limit", type=int, default=0, help="max lookups this run (0 = all)")
    p.add_argument("--delay", type=float, default=2.0, help="seconds between records")
    p.add_argument("--timeout", type=float, default=30.0)
    args = p.parse_args()

    ssids = read_ssids(args.ssids)
    export = read_export(args.export)
    harvested = read_done(args.out)
    todo = [s for s in ssids if s not in harvested]
    if args.limit:
        todo = todo[: args.limit]

    print(
        f"{len(ssids)} SSIDs; {len(harvested)} already resolved; {len(todo)} to do "
        f"at {args.delay}s => ~{len(todo) * args.delay / 60:.0f} min",
        file=sys.stderr,
    )

    opener = urllib.request.build_opener(NoRedirect)
    opener.addheaders = [("User-Agent", USER_AGENT)]
    stopped = ""
    for i, ssid in enumerate(todo, 1):
        try:
            r = resolve(opener, ssid, export.get(ssid), args.timeout)
        except Blocked as e:
            stopped = f"{e} after {i - 1} this run"
            break
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            r = row(ssid, export.get(ssid), f"error:{str(e)[:50]}")
        harvested[ssid] = r
        if r["status"] != "ok":
            print(f"  {ssid}: {r['status']}", file=sys.stderr)
        write(args.out, ssids, harvested)
        if i % 50 == 0:
            print(f"  ...{i}/{len(todo)}", file=sys.stderr)
        time.sleep(args.delay)

    write(args.out, ssids, harvested)
    ok = sum(1 for r in harvested.values() if r["status"] == "ok")
    print(f"{len(harvested)}/{len(ssids)} resolved, {ok} with an IIIF path -> {args.out}",
          file=sys.stderr)
    if stopped:
        print(f"BLOCKED ({stopped}). Stopping; nothing is lost. Wait before resuming.",
              file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
