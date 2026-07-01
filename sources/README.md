# Overview

The `sources/` tree holds every raw input the pipeline transforms, split by
provenance:

- [`zotero/`](zotero/README.md) — the Zotero export track: `zotero.sqlite` (55MB
  SQLite database, Zotero's main metadata store) and its `storage/` attachments,
  the `*_export.{sh,sql}` scripts, and the CSVs / `notes.xml` they produce. Its
  README documents the database itself — the three-library structure, contents,
  tags, collections, fields, and the note export.
- [`marc/`](marc/README.md) — the Z39.50 MARC-harvest track: `marc_harvest.py`,
  the harvested `*-marc.xml` collections, the hand-supplied
  `reference-resources-manual.xml`, and `reference-resources-unresolved.csv`.
  Resumable harvest state lives under `marc/harvest/` (gitignored).
- root (this file) — the files that **bridge** the two tracks:
  `abc-master-crosswalk.csv` and `citation-crosswalk.csv`, plus loose external
  reference data (the JSTOR collection dumps and `google_books_ids.csv`) and the
  regeneration `Makefile`.

The rest of this document describes the citation-crosswalk pipeline: the two
fuzzy-match reconciliations that bridge the two tracks so a Zotero "Cited:" note
in a group library can be surfaced on the artists'-book page it refers to.
Filenames below are qualified by track (`zotero/…`, `marc/…`) except the
crosswalks and external data, which live at this level.

## ABC ↔ cited-record crosswalk

Because lib 1 (the ABC the website builds from) has no Cited notes and shares no
item keys with lib 3 (see [Three libraries in one database](zotero/README.md#three-libraries-in-one-database)),
the notes can only reach ABC pages through a **bibliographic
crosswalk**. `tools/fuzzy-match/match.py` reconciles each of the 1,341 ABC books
to the lib-3 record(s) carrying a Cited note, trying signals in precedence order:

| method | signal | confidence | ABC items matched |
|---|---|---|---:|
| `oclc`  | OCLC number agrees | 1.00 | **0** |
| `isbn`  | ISBN agrees (10/13 forms cross-checked) | 1.00 | **31** |
| `title` | exact normalized title agrees | 0.95 | **162** |
| `fuzzy` | rapidfuzz title sim, confirmed by author + year | blended | **11** |
| `none`  | no confident match | 0.00 | **1,137** |

**204 / 1,341 (15.2%) match a cited-note-bearing lib-3 record** — i.e. 204 ABC
books have a citation-carrying twin. The rest have no twin in the lib-3 cited set.

Two findings worth recording:

- **OCLC does not bridge these two sources.** The issue proposed spiking OCLC as
  a high-precision key, but in practice it contributes **0** matches. ABC records
  were (re)cataloged at UNC and carry fresh billion-range OCLC numbers, while only
  747 lib-3 cited records carry *any* OCLC (in `extra` as `OCLC: <n>`), and that
  subset describes different works — the two indexing efforts picked different
  WorldCat records for the same book. ISBN and title carry the load instead.
- **The fuzzy tail is shallow and noisy.** Beyond exact title, most high-title-
  similarity pairs are coincidences (`Metamorfosis` vs `Metamorphosis`, different
  author and year). The matcher therefore only asserts a fuzzy match when the
  title is very close **or** the author is (near-)identical *and* the year matches
  exactly (catching edition/series variants like `South America, 1972.` vs
  `Richard Long : South America, 1972.`). Of the 11 fuzzy matches, **10 are
  flagged `review=yes`** (confidence < 0.93) for manual vetting.

**Output** `sources/abc-master-crosswalk.csv` is a complete census — one row per ABC
item, matched or not — with columns `abcItemKey, citedItemKey, method, confidence,
review, abcTitle, citedTitle`. The `abcTitle`/`citedTitle` columns are for human
review; the note join (below) treats `review=yes` rows as provisional and skips them.

**Regenerate:**

```sh
make -C tools/fuzzy-match                     # build the rapidfuzz venv (one time)
make -C sources zotero/cited-records.csv      # lib-3 candidate set (note presence + libraryID=3)
make -C sources abc-master-crosswalk.csv
```

Fuzzy matching needs [`rapidfuzz`](https://pypi.org/project/rapidfuzz/), installed
into an isolated venv under `tools/fuzzy-match/venv/` (gitignored — only the
scripts are committed). `zotero/cited-records.csv` is produced by
`zotero/cited_records_export.sh`/`.sql`, selecting lib-3 items that have a child note
containing `Cited` (**not** by collection). The crosswalk reads the committed
`zotero/artists-books.csv` (title/ISBN/date) and `marc/artists-books-marc.xml` (OCLC in `001`,
authors in `100`/`700 $a`, joined via `999 $a`).

## Citation ↔ reference-resource crosswalk

Each Cited note paragraph (exported to `zotero/notes.xml` — see
[Notes export](zotero/README.md#notes-export--surfacing-cited-notes-on-abc-pages))
is a *free-text* reference to a reference work; it
carries no key linking it to the **Reference resources** collection
(`zotero/reference-resources.csv`) — `citedItemKey` is the artist's book's lib-3 record,
not the citing work. To anchor citation URIs on the reference resource
(`reference/<refItemKey>/citation/…`), `tools/fuzzy-match/cite_match.py`
reconciles each paragraph to a reference-resources row:

1. **substring** — a reference title (≥ 10 normalized chars) appears verbatim in
   the paragraph; longest title wins, the embedded year boosts confidence. This
   is the dominant signal (the paragraph quotes the full title).  conf 0.95–0.99
2. **em-exact** — the `<em>` title normalizes exactly to a reference title.  0.95
3. **fuzzy** — rapidfuzz on the `<em>` title.  flagged for review below 0.93

Scoped (via `abc-master-crosswalk.csv`) to the lib-3 cited records actually in
use, so it covers the 436 citation paragraphs reachable from ABC books.
**Output** `sources/citation-crosswalk.csv` is one row per paragraph
(`citedItemKey, n, refItemKey, method, confidence, review, refTitle,
citationText`). Generic short titles ("Artists books") and unmatched-but-citation
paragraphs carry `review=yes` and are excluded from the construct query's
auto-join. Current: **433 paragraphs auto-matched** across 46 reference works,
3 held for review (`BEGEG5AI`'s own short-generic-title citations), 3 editorial
annotations recorded as `none`. (Earlier ~50 review-held paragraphs cited
reference works missing from the collection; those were later added — e.g. Lyons,
*Artists' Books: Visual Studies Workshop Press* — and a corrupt note title was
repaired, dropping the review count from ~50 to 3.)

```sh
make -C sources citation-crosswalk.csv
```

**Wired into the build.** Citations are constructed by
`queries/reference-resources.rq` (not `artists-books.rq`), since a
citation belongs to the reference work it appears in. It joins
`citation-crosswalk.csv` (paragraph → `refItemKey` + flattened text, skipping
`review=yes` / empty matches) with `abc-master-crosswalk.csv` (`citedItemKey →
abcItemKey`, skipping `review=yes`) and emits one `ab:Citation` per resolved
paragraph, anchored on the reference resource:

```
reference/<refItemKey>/citation/<abcItemKey>
    a          ab:Citation ;
    ab:citedBy reference/<refItemKey> ;   # the citing reference work
    ab:cites   item/<abcItemKey> ;        # the cited artist's book
    rdfs:label "<flattened reference string>" .
```

Result: **433 citations** linking **194 ABC books** to **43 reference works**;
no `notes.xml` read is needed at graph-build time (the crosswalk already carries
the text). Page-number / image-page extraction is still TODO.

**Regenerate** (the crosswalks are committed inputs to the graph build, like
`artists-books.csv`/`-marc.xml`, so rebuild the graph explicitly):

```sh
make -C sources zotero/notes.xml citation-crosswalk.csv
make -B graph/reference-resources.ttl
```
