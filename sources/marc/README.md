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

across a chain of **ten catalogues** — UNC, Library of Congress, K10plus, Penn
State, LIBRIS (Z39.50), then Getty, Clark, NYARC, Emory, Harvard (Alma SRU/CQL) —
falling through to the next server until a record verifies. (Emory's Rose Library
holds the Nexus Press archive and a deep artist's-book collection, so it is
grouped with the art libraries; SCAD, which also holds Nexus Press, is unreachable
— its iii.com-hosted catalogue firewalls datacenter clients on both :210 and :443.) A handful of
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
