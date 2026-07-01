# MARC harvest track

`marc/` holds the Z39.50 MARC-harvest track: `marc_harvest.py`, the harvested
`*-marc.xml` collections, the hand-supplied `reference-resources-manual.xml`,
and `reference-resources-unresolved.csv`. Resumable harvest state lives under
`marc/harvest/` (gitignored; only the committed `*-marc.xml` is a build product).

Each record is stamped with a synthetic `999 $a <itemKey>` so it joins back to
its Zotero item, so this track only makes sense alongside the Zotero exports it
keys against — see [`../zotero/README.md`](../zotero/README.md) for the database
and [`../README.md`](../README.md) for the crosswalk pipeline that bridges the
two. For a field-level analysis of the harvested artists'-book records see
[`../../docs/MARC-RECORDS.md`](../../docs/MARC-RECORDS.md).

## Reference-work MARC harvest

`marc_harvest.py` harvests full MARC records for both tracks — `zotero/artists-books.csv`
→ `artists-books-marc.xml` and `zotero/reference-resources.csv` →
**`reference-resources-marc.xml`** — via the generic Makefile pattern rule
`marc/%-marc.xml: zotero/%.csv`. Each record is stamped with a synthetic
`999 $a <itemKey>` so it joins back to its Zotero item, and harvest state
(resumable) lives under `harvest/<csv-stem>/` (gitignored; only the
`<stem>-marc.xml` product is committed).

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

> **Minimally wired into the graph.** `reference-resources.rq` builds the
> `ab:ReferenceWork` nodes from `reference-resources.csv`, and now also reads a
> **basic slice** of `reference-resources-marc.xml` — just the primary creator
> (`100 $a`), joined by `999 $a` — emitted as a `bflc:PrimaryContribution`.
> The rest of the MARC's richer data (OCLC/WorldCat, secondary creators,
> relator roles, identity URIs, extent/dimensions) isn't in the graph yet.
