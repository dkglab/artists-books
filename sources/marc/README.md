# MARC harvest track

`marc/` holds the Z39.50 MARC-harvest track: `marc_harvest.py`, the harvested
`*-marc.zip` archives, the hand-supplied `reference-works-manual.xml`, and
`reference-works-unresolved.csv`. Resumable harvest state lives under
`marc/harvest/` (gitignored; only the committed `*-marc.zip` is a build product).

The harvest product is a **per-record zip archive** (#81), not one big
`<collection>` file: one `<key>.xml` MARCXML document per record, packed with
reproducible bytes (entries sorted, fixed 1980 mtimes) so a re-harvest that
changes one record touches one entry. The construct queries read it with
SPARQL-Anything's nested Archive→XML triplifiers (`marc_to_archive.py` converts a
legacy monolithic `*-marc.xml` to this format without a re-harvest).

Each record is stamped with a synthetic `999 $a <key>` join key: for the
artists' books this is the **canonical** key (the deduped lib 1∪2∪3 identity,
#82/#84); for the reference works it is the canonical key from the deduped
`reference-works.csv` (a lib-3 `itemKey`, which for the reference set is already
canonical).
The graph queries join MARC to their CSV rows on this key (read from the record's
999, not the entry filename). See
[`../zotero/README.md`](../zotero/README.md) for the database and
[`../README.md`](../README.md) for the canonical dedup + citation pipeline. For a field-level
analysis of the harvested artists'-book records see
[`../../docs/MARC-RECORDS.md`](../../docs/MARC-RECORDS.md).

## Fetch transport: the `zoomfetch` ZOOM driver (#85)

Z39.50 records are fetched by **`zoomfetch`**, a ~200-line C driver
(`zoomfetch.c`) built against the libyaz we already compile under
`tools/yaz-client/` — it talks the protocol over YAZ's **ZOOM** C API rather than
scripting the interactive `yaz-client`. It needs no new external dependency (just
a C compiler, already required to build YAZ); the Makefile compiles it with
`yaz-config --cflags/--libs` and installs it as `tools/yaz-client/bin/zoomfetch`
alongside `yaz-marcdump`.

`marc_harvest.py` opens one `zoomfetch` process per server batch (one persistent
`ZOOM_connection`, so the Init handshake is amortised across the batch) and pipes
it one job per line — `id⇥pqf-query⇥maxrecords`. For each job the driver emits
framed, length-prefixed blocks on stdout: `HITS⇥id⇥n`, then a `RECORD⇥id⇥index⇥bytelen`
header followed by exactly `bytelen` **raw ISO 2709 bytes** per record; a
server-side search diagnostic is `ERROR⇥id⇥code⇥msg` (a real miss) and a
connection-level failure is `FATAL⇥id⇥code⇥msg`, after which the driver stops so
the caller **defers** every unanswered job to the next run.

Because every record is tagged with its job `id`, there is no positional
reconstruction — which kills the old **"unalignable"** failure class at the root.
The former positional machinery (the `Number of hits:`/record-count consistency
checks, the batch back-off/retry, the per-item fallback, and UNC's `batch: 10`
workaround) is gone; the only remaining Z39.50 resilience is a subprocess timeout
that defers a hung driver rather than crashing the resumable harvest. The SRU art
libraries (Getty, Clark, NYARC, Harvard) are untouched — they already fetch over
clean HTTP/CQL via `sru_search()`. Encoding is unchanged: `zoomfetch` returns the
server's raw bytes and the UTF-8 / UNC leader-09 handling stays downstream
(`yaz-marcdump -l 9=97`).

## Artists'-book MARC harvest (canonical, #84)

The books harvest is keyed to the **canonical** artists'-book list at the
`sources/` root (`sources/artists-books.csv`, `canonicalKey` column), not the
per-library `zotero/` export, so it has its own explicit Makefile target (not the
`marc/%-marc.zip` pattern rule). The ~1,286 books UNC already holds were
harvested under the old lib-1 keys; rather than re-harvest them, `rekey_held.py`
rewrites their `999 $a` from the lib-1 itemKey to the canonical key (via the CSV
`sourceKeys` map) into the frozen `artists-books-held-marc.xml` (kept as a single
`<collection>` file — it is a `--premerged` input, not a query-facing product).
`marc_harvest.py` then merges that file with `--premerged` (its keys skipped
during harvest, its records merged on `--combine`) and harvests only the ~6,619
**non-held** works. Because the non-held tail mostly lacks a UNC bib number and
ISBN, it falls to verified title / title-author matching — a large, slow,
resumable external run with a real miss rate; until it completes the committed
`artists-books-marc.zip` is the held baseline only.

```sh
# from sources/:
make -C sources -B marc/artists-books-marc.zip   # -B: force the (slow) harvest
# regenerate the frozen held re-key (one-time, from the pre-#84 lib-1 MARC):
python3 marc/rekey_held.py --in-marc <pre-#84 lib-1 marc.xml> \
    --csv artists-books.csv --out marc/artists-books-held-marc.xml
```

### UW-Madison: a discovery layer as a harvest source (#99)

**UW-Madison's Kohler Art Library keeps a named "Artists' Book Collection"**, and
the UW System catalogue that describes it is reachable — but not as MARC. Its
Alma SRU is unpublished: the institution code is `01UWI_MAD` (readable off any
record's own `location_data`) and the Ex Libris endpoint rejects it, the same
off-by-default wall CARLI/SAIC presents. What *is* open is the catalogue's own
discovery layer at `search.library.wisc.edu`: a fielded advanced search
(`/search/catalog?title=…&names=…&identifiers=…&match=all`) plus a per-record
JSON document at `/catalog/<mms>.json`. Records are therefore **synthesized**
from that JSON, as eHive's are, and stamped `999 $d uwmad`.

It sits second-to-last in the waterfall, ahead of eHive only: a synthesized
record is thinner than real cataloguing, so it must never pre-empt a catalogue
that actually holds the work. It is also a *union* catalogue — confirmed hits
come back held at UW Milwaukee, Stevens Point and La Crosse as well as Madison.

Three things about this source are worth carrying to the next one:

**It makes the OCLC key work — the first target in the chain that does.** #99
measured OCLC retrieval as unreachable through every configured free target: LC
answers `@attr 1=1007` with `[114] Unsupported Use attribute`, and the Alma
tenants' `alma.oclc_control_number` silently matches everything. UW's
`identifiers` index does filter on an OCLC number, which is why `oclc` exists as
a keytype at all — and why it exists **only** here. Of the 713 OCLC-bearing
misses, 50 resolved.

**But its identifier index is relevance-ranked, not an exact key.** Searching
`identifiers=9999999999` — an OCLC number that does not exist — returns one
plausible-looking record (an unrelated Thai children's book) with no diagnostic.
This is the `alma.oclc_control_number` match-all trap in milder and more
dangerous form: milder because it returns one hit rather than the whole
catalogue, more dangerous because one hit *looks like* a successful lookup. So
`uw_confirms()` re-checks every identifier-key candidate against the retrieved
record's own `oclc_ids`/`isbns`, and that confirmation — not the search — is what
earns `oclc` its place in `IDENTIFIER_KEYS`. **A discovery layer's identifier
search is a suggestion; only the record confirms.**

**Search results are truncated; candidates must be re-fetched.** The results page
carries title, author and date and nothing else — publication data, extent,
notes, ISBNs and OCLC numbers all live in the per-record JSON. This is exactly
the lesson eHive taught (its search endpoint drops `publication_date`), now
arriving at a second, unrelated source, which is why it belongs here as a rule
rather than a per-source footnote: **a discovery layer's result list is a
shortlist, never a record.**

What the synthesis maps, and what it does not: `001` (the OCLC control number in
its prefixed `ocm`/`ocn`/`on` form, so the WorldCat link `artists-books.rq` mints
from `001` is correct — unlike eHive, this source has a real one; where it does
not, no `001` is emitted rather than a fabricated one, per #130), `020`,
`100`/`700` with `$0` from `infocard_data`'s LC name-authority ids, `245` split
on ISBD punctuation, `250`/`260`/`264` replayed verbatim from
`display_publication_data` (which is not a rendering but the actual MARC field,
indicators and subfields), `300` reconstructed into `$a`/`$b`/`$c` from the
flattened physical description, and `500` notes. Deliberately **no `520`**: this
catalogue's JSON exposes no summary or abstract field, and `display_notes` are
500-type cataloguer's notes, not a summary of the work. Books resolved here carry
no summary — an honest gap, not a bug.

`robots.txt` allows `/search/catalog` and `/catalog` for `User-agent: *`; the
harvest sends per-title lookups from a residual list, not a crawl, under a
descriptive `User-Agent` (`UW_UA`) so the operator can identify and throttle it.
Note that the same file carries a `User-agent: ClaudeBot / Disallow: /` rule.

```sh
# from sources/: residual -> uwmad run -> additive merge
python3 marc/residual_csv.py --csv artists-books.csv \
    --archive marc/artists-books-marc.zip --out marc/harvest/residual-all.csv
python3 marc/marc_harvest.py --csv marc/harvest/residual-all.csv \
    --out marc/harvest/uwmad-residual.zip --servers uwmad
python3 marc/merge_archives.py --base marc/artists-books-marc.zip \
    --add marc/harvest/uwmad-residual.zip --out marc/artists-books-marc.zip
```

That pass took the committed archive from **5,623 to 5,716** records (71.0% →
72.2% of the 7,920 canonical works): **93 of the 2,289 residual books with a
usable search key** — 50 by OCLC, 41 by verified title-author, 2 by ISBN. At
~1.7 s per book the full residual run is about an hour.

### eHive: the Visual Studies Workshop collection (#99)

The largest single hole in the MARC coverage is **Visual Studies Workshop** —
#99 measures it as more works than the next seven press clusters combined. No
amount of adding library catalogues reaches it, because VSW catalogues its
collection in **eHive**, a museum-collection CMS, not in a Z39.50/SRU library
catalogue. eHive is therefore the last entry in the `SERVERS` waterfall, with its
own `protocol: "ehive"`.

It differs from every other server in the chain in three ways worth knowing:

- **Credentials.** eHive's API needs a clientId/clientSecret/trackingId triple
  (Edit My Profile > API Keys in the eHive account), read from
  `EHIVE_CLIENT_ID`, `EHIVE_CLIENT_SECRET` and `EHIVE_TRACKING_ID`. They are
  secrets and must stay out of the repo. `ehive_client.py` holds the
  authorization dance — a POST that answers **303 with the access grant in a
  response header** (following the redirect loses it), then a GET to the token
  endpoint — and re-authorizes on the 401 that a token expiring mid-harvest
  produces. With no credentials set the server is simply skipped.
- **The account is the search scope.** `conn` is an API path rather than a host:
  every query is scoped to VSW's own account (3931), so a "catalogue" here is one
  institution's holdings. Search is relevance-ranked full text — there is no
  fielded author index to AND against, so the probe is the bare title and
  `verify_title` does the discriminating, exactly as it does for the
  single-common-word titles at SCAD.
- **The records are synthesized, not fetched.** eHive answers JSON objects, so
  `ehive_to_marcxml()` maps its fields onto the tags the construct query reads
  (100/700, 300, 520) plus the 245 that `verify_title` judges. `combine()` stamps
  `999 $d ehive`, so a synthesized record stays distinguishable from real
  cataloguing in the committed archive.

Two properties of eHive's data shape the result:

**Search results are truncated; candidates must be re-fetched.** The account
search endpoint returns only a subset of each record's fields — notably *without*
`publication_date`, `publisher`, `publication_place` or `edition`. Only
`/api/v2/objectrecords/{id}` returns the full record. This is easy to get wrong
in a way that quietly costs recall: a field census run over search results
concludes eHive has no dates (one `date_made` in 977 records), when in fact ~95%
of full records carry a `publication_date`. Since `verify_title`'s weak band
needs the year to corroborate, mapping search hits directly would strand every
weak-band match in `review.tsv`. `ehive_full_record()` does the re-fetch, cached
per run.

`edition` is deliberately **not** mapped to MARC 250. Its values are edition
sizes and copy numbers ("30", "500", "1/31", "/3"), not the edition statement
250 means — routing them there would assert `bf:editionStatement "1/31"` on the
book. An honest home would be a new `ab:` term for edition size (out of scope
for #99).

**Copies are separate records.** VSW catalogues each physical copy as its own
object record ("copy 1" … "copy 13"), so an undeduplicated top-3 can be three
copies of one work with the actually-matching book pushed outside the window —
the same show-depth ceiling #98 describes, reached by a different route.
`ehive_candidates()` collapses on the normalized title (lowest objectRecordId
wins, stable across runs) so `show_n` counts distinct works; `fetch_n` over-fetches
to give it something to collapse.

`residual_csv.py` builds the input — the canonical rows still missing a record,
optionally filtered to a cluster:

```sh
# from sources/:
python3 marc/residual_csv.py --csv artists-books.csv \
    --archive marc/artists-books-marc.zip --publisher 'visual studies' \
    --out marc/harvest/vsw-residual.csv
python3 marc/marc_harvest.py --csv marc/harvest/vsw-residual.csv \
    --out marc/harvest/vsw-ehive.zip --servers ehive
python3 marc/merge_archives.py --base marc/artists-books-marc.zip \
    --add marc/harvest/vsw-ehive.zip --out marc/artists-books-marc.zip
```

Probe the API directly (discovering paging, or reading a record's fields) with:

```sh
python3 marc/ehive_client.py --path /api/v2/accounts/3931/objectrecords \
    --param 'query=year of the cow' --param limit=5
```

Paging is `offset`/`limit`; `page`/`pageSize` are silently ignored, as is
`catalogueType` (the book slice is filtered client-side on `LIBRARY`).

### Adding a server's reach to the committed archive

`combine()` rebuilds an archive wholly from the harvest state under
`harvest/<csv-stem>/`, which is **gitignored** — so running a newly added server
against the residual and pointing `--out` at the committed archive would *replace*
it with only that run's hits, dropping everything harvested before. Adding a
server's reach is therefore an **additive merge of archives**, via
`merge_archives.py`: run the new server against a residual CSV (the books still
missing a record) into its own archive under `harvest/`, then merge that into the
committed one. Every record carries its join key in `999 $a` and every entry is
`<key>.xml`, so the merge is a union keyed by entry name; for a residual run the
expected collision count is zero, and the tool reports any it finds.

That is how the SCAD pass landed: 2,920 non-held books still missing MARC →
**463 verified records** (15.9%), plus **12** hand-adjudicated recoveries merged
from `harvest/scad-residual-manual.xml`, taking the committed archive from 4,985
to **5,460** records. The 12 are title-verify false negatives — the right book
under a cataloguer's variant title (`Iconomics : Money` catalogued as `245 $a
Money` with `246 Iconomics`; `Bob : book number 100` as `Bobby : book nr. 100`) —
recovered by re-querying the `review.tsv` rejects with a wider `show_n` and
reading the candidates by hand, **without** loosening `TITLE_STRONG`/`TITLE_WEAK`.
One of the 12 was ranked 4th of 7 hits, i.e. outside the harvest's `show_n=3`
window: on common-word artist's-book titles the show depth, not just the
threshold, is a real ceiling on recall.

```sh
# from sources/, after harvesting a residual into its own archive:
python3 marc/merge_archives.py --base marc/artists-books-marc.zip \
    --add marc/harvest/scad-residual.zip --out marc/artists-books-marc.zip
```

## Reference-work MARC harvest

`marc_harvest.py` also harvests the reference works — the deduped canonical
`reference-works.csv` (at the `sources/` root, `canonicalKey` column) →
**`reference-works-marc.zip`** — via its own explicit Makefile target, like the
books track (not the `marc/%-marc.zip` pattern rule, which is keyed to the
per-library `zotero/` exports). Each record is stamped with a synthetic
`999 $a <canonicalKey>` so it joins its `reference-works.rq` row directly on
`?canonical_key`, and harvest state (resumable) lives under `harvest/<csv-stem>/`
(gitignored; only the `<stem>-marc.zip` product is committed). Harvesting the
deduped canonical list (rather than the pre-dedup 157-row "Reference resources"
collection) keeps the archive to exactly the 155 canonical works — an earlier
pre-dedup harvest also fetched a couple of losing-key records that then failed to
join any canonical row.

The reference works need a **different keying strategy** than the books: they are
mostly catalogued as *Open WorldCat*, not UNC bibs, so a UNC-bib lookup finds
almost none. The harvester instead tries, per item:

1. **ISBN** (`@attr 1=7` / `alma.isbn`),
2. **title + author** (author surname from the CSV `creators` column, with a
   `verify_title` guard so a coincidental title hit isn't stamped onto the wrong
   key),

across the same server chain the books use — UNC, Library of Congress, K10plus, Penn
State, LIBRIS (Z39.50), then Getty, Clark, NYARC, Emory, Harvard (Alma SRU/CQL),
and SCAD (Z39.50) — falling through to the next server until a record verifies.
(Emory's Rose Library holds the Nexus Press archive and a deep artist's-book
collection, so it is grouped with the art libraries; SCAD absorbed the Atlanta
College of Art and holds the Nexus Press / ACA imprints directly. An earlier note
here held SCAD unreachable — its iii.com-hosted catalogue firewalling datacenter
clients on :210 and :443 — but a 2026-07 re-probe found both the Z39.50 server and
the WebPAC answering, and it is now in the chain.) A handful of
hand-supplied records are merged from `reference-works-manual.xml`. Result:
**153 of the 155** canonical reference works get a record; the residual (two
webpages with no catalogue record) is listed in `reference-works-unresolved.csv`.

```sh
# from sources/:
make -C sources marc/reference-works-marc.zip
# or directly (also run from sources/):
python3 marc/marc_harvest.py --csv reference-works.csv --out marc/reference-works-marc.zip
```

> **Minimally wired into the graph.** `reference-works.rq` builds the
> `ab:ReferenceWork` nodes from the canonical `reference-works.csv`, and now also
> reads a **basic slice** of `reference-works-marc.zip` — just the primary
> creator (`100 $a`), joined by `999 $a` — emitted as a `bflc:PrimaryContribution`.
> The rest of the MARC's richer data (OCLC/WorldCat, secondary creators,
> relator roles, identity URIs, extent/dimensions) isn't in the graph yet.
