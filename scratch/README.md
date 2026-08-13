# scratch/ — SSID → IIIF investigation (issue #9)

Working files from the 2026-08-13 investigation into how to build a public IIIF
image URL for a JSTOR Forum community item starting from a plain SSID.

This is **research scratch**, not part of the build. Nothing here is referenced by
the Makefile or the construct queries. It is committed so the findings can be
re-checked without re-running the browser capture.

The findings are summarised in issue #9. Short version:

1. `GET https://www.jstor.org/content-service/content-data/community.<SSID>`
   → `content.iiifLinks[]`, an **ordered** array of `/iiif/<path>` identifiers.
   Requires a browser-like `User-Agent` **and** a non-empty `Cookie` header
   (`Cookie: x=y` is enough — no real session needed). Heavily rate-limited per IP.
2. `https://www.jstor.org{iiifLinks[i]}/info.json` and
   `https://www.jstor.org{iiifLinks[i]}/full/full/0/default.jpg`
   → open Cantaloupe IIIF Image API 2.1 level 2. **No headers of any kind
   required**, and not rate-limited.

The IIIF identifier is a date-partitioned S3 path
(`2016/04/29/16/<uuid>_deflate.tif`) and **cannot be derived from the SSID** —
step 1 is a mandatory lookup. The codec suffix varies (`_deflate.tif`, `_jpeg.tif`).

## Layout

- `scripts/` — the Playwright capture and curl verification scripts.
  - `capture.py`, `capture2.py` — load `/stable/community.<SSID>` in headed Chrome
    and log every network response; `capture2.py` also saves XHR/fetch bodies.
    Headless is detected by the Fastly JS challenge, hence `headless=False`.
  - `capture_browse.py` — same, for the collection browse page.
  - `harvest_browser.py` — fetch `content-data` for N SSIDs from inside a
    challenge-cleared browser context (fallback when curl is blocked).
  - `verify.py`, `verify2.py` — end-to-end SSID → info.json → image-bytes check.
    `verify2.py` is the one that produced `results/verify2.json`.
  - `ratetest.py` — throughput probe against real SSIDs from `sources/artstor-ssid.csv`.
  - `poll.py`, `poll2.py` — poll until the rate-limit block clears.
  - `probe_egress.sh` — **run this on any candidate harvester host** (fly.io sprite,
    CI runner, laptop) to find out whether its egress IP can do the step-1 lookup.
    Makes only 3 requests, and distinguishes the three failure modes, which look
    nothing alike: `200` (usable), `403 Access Check` (temporary rate limit), and
    `200` + a Fastly `Client Challenge` page (IP-reputation block, fatal for curl).
- `results/`
  - `verify2.json` — the 6-SSID verification (all 200, with dimensions and byte counts).
  - `ratetest-2.0.json` — 40 SSIDs at 2 s spacing; 15 succeeded before the block.
    This is the sample the cover/`Image View Description` analysis is based on.
  - `ratetest-6.0.json` — 30 SSIDs at 6 s spacing, run too soon after a block:
    all 403. Kept as evidence that the limiter **escalates** when probed while blocked.
  - `browser-meta.json` — all 403; evidence the block is IP-wide, not curl-specific.
- `api-samples/`
  - `content-data-community.14183099.json` — a full `content-service` response.
    Note `iiifLinks`, `mediaIds`, `pageCount`, `pageNames`, and the `metadata`
    array (`File Name`, `SSID`, `Image View Description`, `Accession Number`).
  - `iiif-info-14183099-page1.json` — a IIIF `info.json` (2400×1800, level 2).
  - `grouped-search-collection-browse.json` — the collection browse search API.
    Checked as a possible bulk route: it carries **no** IIIF links, so it does not
    avoid the per-item lookup.
  - `network-log-14183099.json` — the full response log for one item page.
    AWS presigned query parameters are REDACTED.
- `images/` — sample renderings used to confirm page ordering.
  - `pg-<ssid>-<i>.jpg` — page *i* (0-based) of each verified SSID.
  - `ck-21027692-*.jpg` — the `(Images of the enclosure, cover, & interior)` case:
    page 0 is the slipcase, page 1 is the actual cover.
  - `ck-21034137-*.jpg` — `strip_tease_cover2.tif`: filename ends in `2` but
    page 0 *is* the cover.

## Deliberately not committed

Browser session state (`cookies.txt`, `state.json`) and the multi-MB raw page
HTML dumps and screenshots. Re-run `scripts/capture2.py <SSID>` to regenerate.

## Caveat on the rate-limit numbers

The sustainable request rate was **not** measured — the budget was exhausted
during testing. Observed: blocked after ~15–20 requests; a first block cleared in
90 s; continuing to request while blocked extended it past 25 minutes. Any
harvester must checkpoint and stop completely on the first 403.
