#!/usr/bin/env python3
"""Browser-transport variant of `sources/marc/harvest_iiif.py` (issue #9).

Same job, same output file, same CSV shape -- it *imports* the committed
harvester's parsing and writing logic rather than restating it. The only thing
that differs is the transport: instead of urllib with a junk cookie, the
`content-data` lookups are issued as same-origin `fetch()` calls from inside a
real headed Chrome window that has loaded a `/stable/community.<SSID>` page and
so holds a legitimately-minted session.

Why: from this host, plain urllib got 403 on request #1 of every run, while a
hand-driven browser on the same IP was watched succeeding in the Network tab.
`scratch/results/browser-meta.json`, cited in scratch/README.md as "evidence the
block is IP-wide, not curl-specific", is a single 403 recorded during an
escalated block -- too thin to support that conclusion.

Deliberately NOT passed: `--disable-blink-features=AutomationControlled`. That
flag's only function is to suppress `navigator.webdriver`, the WebDriver spec's
standard "a program is driving me" disclosure. If the harvest needs it, that is
the site declining automated access and is worth knowing, not papering over.

Headed (`headless=False`) is required regardless: the investigation found
headless trips the Fastly JS challenge.

Rate limiting is handled exactly as the committed harvester handles it -- stop
the whole run at the first 403, checkpoint after every record, resume next time.
No browser session state is written to disk.
"""

import argparse
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "sources", "marc"))

from harvest_iiif import (  # noqa: E402  (path set above)
    Blocked,
    read_done,
    read_ssids,
    row,
    rows_for,
    write,
)

from playwright.sync_api import sync_playwright  # noqa: E402

PAGE = "https://www.jstor.org/stable/community.{}"
PATH = "/content-service/content-data/community.{}"

FETCH = """async (ssid) => {
    const res = await fetch('/content-service/content-data/community.' + ssid,
                            {credentials: 'include'});
    return {status: res.status, body: await res.text()};
}"""


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--ssids", default="sources/artstor-ssid.csv")
    p.add_argument("--out", default="sources/ssid-iiif.csv")
    p.add_argument("--limit", type=int, default=0, help="max lookups this run (0 = all)")
    p.add_argument("--delay", type=float, default=8.0, help="seconds between requests")
    p.add_argument("--settle", type=float, default=15.0, help="seconds to let the first page settle")
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
    if not todo:
        return

    stopped = ""
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=False, channel="chrome")
        ctx = browser.new_context(viewport={"width": 1280, "height": 900})
        page = ctx.new_page()

        # One real page load, to clear the challenge and mint a session.
        print(f"opening {PAGE.format(todo[0])} to establish a session...", file=sys.stderr)
        page.goto(PAGE.format(todo[0]), wait_until="domcontentloaded", timeout=90000)
        page.wait_for_timeout(int(args.settle * 1000))

        for i, ssid in enumerate(todo, 1):
            try:
                r = page.evaluate(FETCH, ssid)
            except Exception as e:
                harvested[ssid] = [row(ssid, "", "", "", "", f"error:{str(e)[:60]}")]
                print(f"  {ssid}: error {str(e)[:80]}", file=sys.stderr)
                write(args.out, ssids, harvested)
                time.sleep(args.delay)
                continue

            status, body = r["status"], r["body"]
            if status in (403, 429) or "Client Challenge" in body:
                stopped = f"http:{status} after {i - 1} lookups this run"
                break
            if status != 200:
                harvested[ssid] = [row(ssid, "", "", "", "", f"http:{status}")]
                print(f"  {ssid}: http:{status}", file=sys.stderr)
            else:
                try:
                    import json

                    content = json.loads(body)["content"]
                except (ValueError, KeyError, TypeError):
                    harvested[ssid] = [row(ssid, "", "", "", "", "unparseable")]
                    print(f"  {ssid}: unparseable", file=sys.stderr)
                else:
                    harvested[ssid] = rows_for(ssid, content)

            write(args.out, ssids, harvested)  # checkpoint every record
            if i % 25 == 0:
                print(f"  ...{i}/{len(todo)}", file=sys.stderr)
            time.sleep(args.delay)

        browser.close()

    write(args.out, ssids, harvested)
    images = sum(1 for rs in harvested.values() for r in rs if r["status"] == "ok")
    print(f"{len(harvested)}/{len(ssids)} SSIDs, {images} images -> {args.out}", file=sys.stderr)
    if stopped:
        print(
            f"BLOCKED ({stopped}). Stopping; nothing is lost. Do NOT rerun "
            "immediately -- requesting while blocked extends the penalty.",
            file=sys.stderr,
        )
        raise SystemExit(1)


if __name__ == "__main__":
    main()
