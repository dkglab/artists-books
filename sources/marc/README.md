# MARC harvest track

`marc/` holds the Z39.50 MARC-harvest track: `marc_harvest.py`, the harvested
`*-marc.zip` archives, the hand-supplied `reference-resources-manual.xml`, and
`reference-resources-unresolved.csv`. Resumable harvest state lives under
`marc/harvest/` (gitignored; only the committed `*-marc.zip` is a build product).

The harvest product is a **per-record zip archive** (#81), not one big
`<collection>` file: one `<key>.xml` MARCXML document per record, packed with
reproducible bytes (entries sorted, fixed 1980 mtimes) so a re-harvest that
changes one record touches one entry. The construct queries read it with
SPARQL-Anything's nested Archive→XML triplifiers (`marc_to_archive.py` converts a
legacy monolithic `*-marc.xml` to this format without a re-harvest).

Each record is stamped with a synthetic `999 $a <key>` join key: for the
artists' books this is the **canonical** key (the deduped lib 1∪2∪3 identity,
#82/#84); for the reference works it is the lib-3 `itemKey` (already canonical).
The graph queries join MARC to their CSV rows on this key (read from the record's
999, not the entry filename). See
[`../zotero/README.md`](../zotero/README.md) for the database and
[`../README.md`](../README.md) for the crosswalk pipeline. For a field-level
analysis of the harvested artists'-book records see
[`../../docs/MARC-RECORDS.md`](../../docs/MARC-RECORDS.md).

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

`marc_harvest.py` also harvests the reference works — `zotero/reference-resources.csv`
→ **`reference-resources-marc.zip`** — via the generic Makefile pattern rule
`marc/%-marc.zip: zotero/%.csv` (the books track has its own target, above). Each
record is stamped with a synthetic `999 $a <itemKey>` so it joins back to its
Zotero item, and harvest state (resumable) lives under `harvest/<csv-stem>/`
(gitignored; only the `<stem>-marc.zip` product is committed).

The reference works need a **different keying strategy** than the books: they are
mostly catalogued as *Open WorldCat*, not UNC bibs, so a UNC-bib lookup finds
almost none. The harvester instead tries, per item:

1. **ISBN** (`@attr 1=7` / `alma.isbn`),
2. **title + author** (author surname from the CSV `creators` column, with a
   `verify_title` guard so a coincidental title hit isn't stamped onto the wrong
   key),

across a chain of **nine catalogues** — UNC, Library of Congress, K10plus, Penn
State, LIBRIS (Z39.50), then Getty, Clark, NYARC, Harvard (Alma SRU/CQL) —
falling through to the next server until a record verifies. A handful of
hand-supplied records are merged from `reference-resources-manual.xml`. Result:
**~155 of the 157** reference works get a record; the residual (e.g. webpages
with no catalogue record) is listed in `reference-resources-unresolved.csv`.

```sh
# from sources/:
make -C sources marc/reference-resources-marc.zip
# or directly (also run from sources/):
python3 marc/marc_harvest.py --csv zotero/reference-resources.csv --out marc/reference-resources-marc.zip
```

> **Minimally wired into the graph.** `reference-works.rq` builds the
> `ab:ReferenceWork` nodes from the canonical `reference-works.csv`, and now also
> reads a **basic slice** of `reference-resources-marc.zip` — just the primary
> creator (`100 $a`), joined by `999 $a` — emitted as a `bflc:PrimaryContribution`.
> The rest of the MARC's richer data (OCLC/WorldCat, secondary creators,
> relator roles, identity URIs, extent/dimensions) isn't in the graph yet.
