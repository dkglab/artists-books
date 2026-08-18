# scratch/ — SSID → IIIF investigation (issue #9)

Working files from the 2026-08-13 investigation into how to build a public IIIF
image URL for a JSTOR Forum community item starting from a plain SSID.

This is **research scratch**, not part of the build. Nothing here is referenced by
the Makefile or the construct queries. It is committed so the findings can be
re-checked without re-running the browser capture.

> [!IMPORTANT]
> **Superseded — read `sources/README.md` § "SSID → IIIF images" first.** The
> route this investigation pursued (`content-service`) turns out to be closed to
> automation, and the working route came from somewhere else entirely. This file
> is kept for the image-ordering and cover-semantics findings, which are still
> good, and as a record of what not to retry. See
> [Outcome](#outcome-content-service-is-a-dead-end-the-harvest-went-another-way).

The findings are summarised in issue #9. Short version:

1. `GET https://www.jstor.org/content-service/content-data/community.<SSID>`
   → `content.iiifLinks[]`, an **ordered** array of `/iiif/<path>` identifiers.
   Requires a browser-like `User-Agent` **and** a non-empty `Cookie` header
   (`Cookie: x=y` is enough — no real session needed). **Closed to automation**
   in practice — see Outcome below. Described here as it was found, not as a
   route to use.
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
    challenge-cleared browser context. Written as the fallback for when curl is
    blocked; it does **not** work — see Outcome below.
  - `verify.py`, `verify2.py` — end-to-end SSID → info.json → image-bytes check.
    `verify2.py` is the one that produced `results/verify2.json`.
  - `ratetest.py` — throughput probe against real SSIDs from `sources/artstor-ssid.csv`.
  - `poll.py`, `poll2.py` — poll until the rate-limit block clears.
  - `probe_egress.sh` — **run this on any candidate harvester host** (fly.io sprite,
    CI runner, laptop) to find out whether its egress IP can do the step-1 lookup.
    Makes only 3 requests, and distinguishes the three failure modes, which look
    nothing alike: `200` (usable), `403 Access Check` (temporary rate limit), and
    `200` + a Fastly `Client Challenge` page (IP-reputation block, fatal for curl).
    **A passing probe does not mean the harvest will run** — see below: the probe
    passed and the harvest was still refused at request #1.
- `results/`
  - `verify2.json` — the 6-SSID verification (all 200, with dimensions and byte counts).
  - `ratetest-2.0.json` — 40 SSIDs at 2 s spacing; 15 succeeded before the block.
    This is the sample the cover/`Image View Description` analysis is based on.
  - `ratetest-6.0.json` — 30 SSIDs at 6 s spacing, run too soon after a block:
    all 403. Kept as evidence that the limiter **escalates** when probed while blocked.
  - `browser-meta.json` — **one** 403, for a single SSID (639234), recorded from a
    browser context during an escalated block; the run died before reaching the
    other five. It was originally cited here as "evidence the block is IP-wide,
    not curl-specific" — one request is far too thin for that, and the harvest
    attempt below reached the opposite conclusion. Kept as a data point only.
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

## Outcome: `content-service` is a dead end; the harvest went another way

**Do not retry `www.jstor.org/content-service/content-data/…`.** Steps 1 above
describes it accurately as an API, but it is closed to automation and no amount
of pacing opens it. What was tried on 2026-08-13, all refused at the *first*
lookup of the run: `--delay 8` after a 15-minute silence, again after 20 minutes,
and finally a headed real Chrome holding a legitimately minted session (without
`--disable-blink-features=AutomationControlled`, whose only function is to
suppress the `navigator.webdriver` disclosure), which was refused and then served
a CAPTCHA. Solving a CAPTCHA to unlock a bulk harvest is circumvention, so that
line of attack was stopped there.

Consequences worth keeping:

- **`--delay` is not the knob.** It spaces requests *within* a run; every run died
  at lookup 0. Its sustainable value was never measured and never will be here.
- **A passing `probe_egress.sh` is not a green light.** The probe returned 200 and
  the harvest was refused seconds later — the probe's own request appears to
  consume the allowance.
- **Attempts degrade the IP** to where ordinary human browsing gets challenged.
- `browser-meta.json` was once cited as proof the block is IP-wide. It holds a
  single 403. It is not evidence of that, and the claim was wrong: a hand-driven
  browser on the same IP worked fine throughout.

**The route that works** avoids this endpoint completely, using the redirect chain
that Sloane's own Forum export publishes in its `Media URL` column:

```
forum.jstor.org/assets/<SSID>/representation-view
  ──302──▶ stor.artstor.org/stor/<uuid>                        ← the media UUID
  ──302──▶ …s3.amazonaws.com/prod.cirrostratus.org/YYYY/MM/DD/HH/<uuid>?…
                                            └ the date partition ┘
```

Neither host is bot-gated. That yields the two components of the IIIF identifier
that cannot be derived from an SSID. Implemented as `sources/marc/harvest_media.py`
and documented in `sources/README.md` § "SSID → IIIF images" — **read that, not
this file, for how the pipeline actually works.**

Two things this scratch investigation got wrong that the write-up above corrects:
the cover-position metadata (`Image View Description`) was already sitting in the
local Forum export as `Image View Type[4603]`, so the 1,127 API calls were never
needed for it; and the IIIF *image* tier was never auth-walled — it is open,
unthrottled, and CORS-permissive, which is why the site transcludes rather than
rehosts.

`content-service` remains the only known route to a record's **second and later**
images, so the slipcase cases (`(Images of the enclosure, cover, & interior)`)
stay unresolved. That is the one reason to care about it at all.
