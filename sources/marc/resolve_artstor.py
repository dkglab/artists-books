#!/usr/bin/env python3
"""Resolve the Artstor asset IDs in MARC 856 $u to JSTOR Forum SSIDs (issue #9).

The catalogue's 856 links point at library.artstor.org with a patron-side asset
ID (SS33469_33469_<n>). Those IDs were retired in 2024 and are not exportable
from JSTOR Forum, which is why no shared key with the Forum "Export Records"
spreadsheet could be found by inspection. But the old URLs still redirect:

    https://library.artstor.org/public/SS33469_33469_42526770
      -> 301 https://www.jstor.org/stable/community.14183099

and the number after `community.` is exactly the Forum SSID. So the redirect
*is* the crosswalk. Only the redirect is fetched (no page body, no captcha).

Two 856 URL shapes carry the same asset ID -- `/public/<id>` and
`/#/asset/<id>`. The fragment form is rewritten to the `/public/` form before
fetching, since a fragment is never sent to the server.

Resumable: already-resolved asset IDs are read back from --out and skipped, so
the run can be chunked with --limit. Hitting an external server, so it is
deliberately polite (--delay between requests, backoff on 429/5xx).
"""

import argparse
import csv
import re
import sys
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
import zipfile

ASSET_RE = re.compile(r"(SS\d+_\d+_\d+)")
SSID_RE = re.compile(r"community\.(\d+)")
PUBLIC_URL = "https://library.artstor.org/public/{}"
USER_AGENT = (
    "artists-books-crosswalk/1.0 "
    "(https://github.com/dkglab/artists-books; UNC Sloane Art Library)"
)
FIELDS = ["canonicalKey", "assetId", "ssid", "status"]


class NoRedirect(urllib.request.HTTPRedirectHandler):
    """Capture the Location header instead of following it."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def read_pairs(archive):
    """(canonicalKey, assetId) for every Artstor 856 $u in the MARC archive."""
    pairs = []
    with zipfile.ZipFile(archive) as z:
        for name in sorted(z.namelist()):
            if not name.endswith(".xml"):
                continue
            root = ET.fromstring(z.read(name))
            key, ids = None, []
            for df in root.iter():
                if df.tag.split("}")[-1] != "datafield":
                    continue
                if df.get("tag") == "999":
                    for sf in df:
                        if sf.get("code") == "a":
                            key = sf.text
                elif df.get("tag") == "856":
                    for sf in df:
                        if sf.get("code") != "u" or not sf.text:
                            continue
                        if "artstor" not in sf.text:
                            continue
                        m = ASSET_RE.search(sf.text)
                        if m:
                            ids.append(m.group(1))
            for asset in dict.fromkeys(ids):  # dedupe, keep record order
                pairs.append((key, asset))
    return pairs


def read_resolved(path):
    """asset ID -> (ssid, status) from a previous run, if any."""
    resolved = {}
    try:
        with open(path, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                if row["status"] == "ok":
                    resolved[row["assetId"]] = (row["ssid"], row["status"])
    except FileNotFoundError:
        pass
    return resolved


def resolve(opener, asset, timeout, retries, delay):
    """Fetch the redirect for one asset ID -> (ssid, status)."""
    url = PUBLIC_URL.format(asset)
    last = "retries exhausted"
    for attempt in range(retries):
        try:
            opener.open(urllib.request.Request(url, method="HEAD"), timeout=timeout)
            return "", "no-redirect"  # 200 without a Location: not a live asset
        except urllib.error.HTTPError as e:
            if e.code in (301, 302, 303, 307, 308):
                loc = e.headers.get("Location", "")
                m = SSID_RE.search(loc)
                return (m.group(1), "ok") if m else ("", f"unexpected:{loc[:60]}")
            if e.code == 429 or e.code >= 500:
                time.sleep(delay * (2**attempt) * 5)
                continue
            return "", f"http:{e.code}"
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            time.sleep(delay * (2**attempt) * 5)
            last = str(e)[:60]
    return "", f"error:{last}"


def write(path, pairs, resolved):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        for key, asset in pairs:
            ssid, status = resolved.get(asset, ("", "unresolved"))
            w.writerow(
                {
                    "canonicalKey": key,
                    "assetId": asset,
                    "ssid": ssid,
                    "status": status,
                }
            )


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--archive", default="marc/artists-books-marc.zip")
    p.add_argument("--out", default="artstor-ssid.csv")
    p.add_argument("--limit", type=int, default=0, help="max lookups this run (0 = all)")
    p.add_argument("--delay", type=float, default=1.0, help="seconds between requests")
    p.add_argument("--timeout", type=float, default=30.0)
    p.add_argument("--retries", type=int, default=3)
    args = p.parse_args()

    pairs = read_pairs(args.archive)
    resolved = read_resolved(args.out)
    todo = [a for a in dict.fromkeys(a for _, a in pairs) if a not in resolved]
    if args.limit:
        todo = todo[: args.limit]

    print(
        f"{len(pairs)} links / {len({a for _, a in pairs})} assets; "
        f"{len(resolved)} already resolved; {len(todo)} to fetch",
        file=sys.stderr,
    )

    opener = urllib.request.build_opener(NoRedirect)
    opener.addheaders = [("User-Agent", USER_AGENT)]
    for i, asset in enumerate(todo, 1):
        ssid, status = resolve(opener, asset, args.timeout, args.retries, args.delay)
        resolved[asset] = (ssid, status)
        if status != "ok":
            print(f"  {asset}: {status}", file=sys.stderr)
        if i % 25 == 0:
            write(args.out, pairs, resolved)
            print(f"  ...{i}/{len(todo)}", file=sys.stderr)
        time.sleep(args.delay)

    write(args.out, pairs, resolved)
    ok = sum(1 for a in {a for _, a in pairs} if resolved.get(a, ("", ""))[1] == "ok")
    print(f"resolved {ok}/{len({a for _, a in pairs})} assets -> {args.out}", file=sys.stderr)


if __name__ == "__main__":
    main()
