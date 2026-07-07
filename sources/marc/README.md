# MARC harvest track

`marc/` holds the Z39.50 MARC-harvest track: `marc_harvest.py`, the harvested
`*-marc.xml` collections, the hand-supplied `reference-resources-manual.xml`,
and `reference-resources-unresolved.csv`. Resumable harvest state lives under
`marc/harvest/` (gitignored; only the committed `*-marc.xml` is a build product).

Each record is stamped with a synthetic `999 $a <key>` join key: for the
artists' books this is the **canonical** key (the deduped lib 1∪2∪3 identity,
#82/#84); for the reference works it is the lib-3 `itemKey` (already canonical).
The graph queries join MARC to their CSV rows on this key. See
[`../zotero/README.md`](../zotero/README.md) for the database and
[`../README.md`](../README.md) for the crosswalk pipeline. For a field-level
analysis of the harvested artists'-book records see
[`../../docs/MARC-RECORDS.md`](../../docs/MARC-RECORDS.md).

## Artists'-book MARC harvest (canonical, #84)

The books harvest is keyed to the **canonical** artists'-book list at the
`sources/` root (`sources/artists-books.csv`, `canonicalKey` column), not the
per-library `zotero/` export, so it has its own explicit Makefile target (not the
`marc/%-marc.xml` pattern rule). The ~1,286 books UNC already holds were
harvested under the old lib-1 keys; rather than re-harvest them, `rekey_held.py`
rewrites their `999 $a` from the lib-1 itemKey to the canonical key (via the CSV
`sourceKeys` map) into the frozen `artists-books-held-marc.xml`. `marc_harvest.py`
then merges that file with `--premerged` (its keys skipped during harvest, its
records merged on `--combine`) and harvests only the ~6,619 **non-held** works.
Because the non-held tail mostly lacks a UNC bib number and ISBN, it falls to
verified title / title-author matching — a large, slow, resumable external run
with a real miss rate; until it completes the committed `artists-books-marc.xml`
is the held baseline only.

```sh
# from sources/:
make -C sources -B marc/artists-books-marc.xml   # -B: force the (slow) harvest
# regenerate the frozen held re-key (one-time, from the pre-#84 lib-1 MARC):
python3 marc/rekey_held.py --in-marc marc/artists-books-marc.xml \
    --csv artists-books.csv --out marc/artists-books-held-marc.xml
```

## Reference-work MARC harvest

`marc_harvest.py` also harvests the reference works — `zotero/reference-resources.csv`
→ **`reference-resources-marc.xml`** — via the generic Makefile pattern rule
`marc/%-marc.xml: zotero/%.csv` (the books track has its own target, above). Each
record is stamped with a synthetic `999 $a <itemKey>` so it joins back to its
Zotero item, and harvest state (resumable) lives under `harvest/<csv-stem>/`
(gitignored; only the `<stem>-marc.xml` product is committed).

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
make -C sources marc/reference-resources-marc.xml
# or directly (also run from sources/):
python3 marc/marc_harvest.py --csv zotero/reference-resources.csv --out marc/reference-resources-marc.xml
```

> **Minimally wired into the graph.** `reference-works.rq` builds the
> `ab:ReferenceWork` nodes from the canonical `reference-works.csv`, and now also
> reads a **basic slice** of `reference-resources-marc.xml` — just the primary
> creator (`100 $a`), joined by `999 $a` — emitted as a `bflc:PrimaryContribution`.
> The rest of the MARC's richer data (OCLC/WorldCat, secondary creators,
> relator roles, identity URIs, extent/dimensions) isn't in the graph yet.
