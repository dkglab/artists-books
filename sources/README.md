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

## Canonical key scheme (issue #82, Phase 0)

> [!IMPORTANT]
> The three Zotero libraries are **frozen** (see
> [Three libraries in one database](zotero/README.md#three-libraries-in-one-database)).
> Under #82 the authoritative artists'-book set is **lib 1 ∪ lib 2 ∪ lib 3,
> deduplicated** — the same work catalogued once per library collapses to **one
> canonical node**. This section fixes the identity of that node. It is the
> first Phase-0 decision because everything downstream (the frozen
> `graph/citations.ttl`, the MARC harvest, every minted URI) hangs off it, and
> the frozen citations must point at keys that never move again.

**The canonical key is an existing Zotero item key — never a freshly minted
one — chosen per work by this precedence:**

| # | Prefer the key from… | Because | Applies to |
|---|---|---|---|
| 1 | **lib 3** (group 2352415, *ABCI*) | The newest, richest citation index, maintained latest, and the library the **`Cited:` notes live in**. Choosing it means citation edges anchor on lib-3 keys with **zero bridging** — this is what dissolves the crosswalk. | Any work present in lib 3 |
| 2 | **lib 2** (group 262987) | The older frozen index; use its key only for works that never migrated to lib 3 (no lib-3 successor). | Works in lib 2 but not lib 3 |
| 3 | **lib 1** (personal, user 5818691) | The Sloane physical holdings; use its key only for held works that were never indexed in either group library. | Works in lib 1 only (~290 of the 1,341 held books) |

The precedence is essentially **forced by the data**, not a free choice: lib 3
supersedes lib 2 (10,677 `owl:sameAs` links point lib-3 records back to lib-2
predecessors), and only ~290 held books exist in no group library at all.

**The non-canonical keys are kept as provenance, not discarded.** Each canonical
node records the source item(s) it was deduplicated from — the losing
lib-N keys — as `owl:sameAs` to their Zotero item URIs
(`http://zotero.org/groups/<gid>/items/<key>` or
`http://zotero.org/users/5818691/items/<key>`). The dedup step (Phase-0 task 2)
emits these alongside the canonical key.

**Held flag, not a separate graph.** UNC's physical holdings stay special only
because we have *images* of them. Membership in lib 1's `Artists' Books
Collection` (1,341) is recorded as a **property on the canonical node** (a held
flag), *not* as a distinct held-books graph.

### URI consequences

Minted URIs use the canonical key: `…/item/<canonicalKey>` for artists' books,
`…/reference/<canonicalKey>` for reference works (see CLAUDE.md "URI minting").

- **Reference works are unaffected.** The `Reference resources` collection (157)
  lives in **lib 3**, so `…/reference/<itemKey>` URIs already use lib-3 keys.
- **Artists'-book URIs migrate.** The site historically built from lib 1, so
  today's book URIs carry **lib-1** keys. Under lib-3-precedence the ~1,051 held
  books that also exist in a group library move to their **lib-3** (or lib-2)
  canonical key; only the ~290 held-only books keep a lib-1 key. This is an
  accepted one-time break — the whole point of #82 is to make every cited book a
  first-class node keyed the same way the citations already reference it.

**Ordering constraint:** mint canonical AB/RW identity (Phase-0 task 2)
**before** freezing `graph/citations.ttl` (task 3), or the citation edges point
at keys that later move.

### The dedup generator

`tools/fuzzy-match/dedup.py` mints that canonical identity. It is one-time
throwaway tooling (run once, review, commit; archived with the rest of
`tools/fuzzy-match/` after Phase 0) and reads `zotero/zotero.sqlite` **directly**
— no intermediate export CSVs, since the whole tool is about to be retired. It
clusters records into one node per work using signals in **descending order of
authority**, so a weaker signal never overrides a stronger one:

| # | Signal | Scope | Why it's trusted at this rank |
|---|---|---|---|
| 1 | `owl:sameAs` | all libs | Editorially asserted in Zotero; the dense lib 3 → lib 2 bridge (10,677 links) that supersession is built on. |
| 2 | ISBN (10/13 cross-checked) | all libs | A work-level identifier; near-zero false collisions. Catches duplicates `sameAs` missed — e.g. two lib-2 records of one work where only one carries the lib-3 link. |
| 3 | OCLC | all libs | Same, from the `extra` field. |
| 4 | title + author + **year** | all libs | The no-ISBN fallback. Year keeps distinct **editions** apart (the 1980–2016 editions of *A Humument*; Moeglin-Delcroix 1985 vs 2012) — they collapse only if #1–#3 link them. High-precision default for a frozen set, where a wrong merge is harder to undo than a missed one. |
| 5 | fuzzy title (rapidfuzz), author+year re-ranked | lib 1 → lib 2/3 only | Reused from `match.py`. Only lib-1 books with no exact twin reach here; every attach is written to the review CSV, low-confidence ones flagged `review=yes`. |

Signals 1–4 run globally over all three libraries (the fix that makes it a true
three-way dedup, not the old pairwise lib-1 → lib-3 bridge). Signal 5 exists only
because lib 1 carries almost no `sameAs` (just 7 of its 1,341 books).

**Outputs** (committed; the librarian reviews them before they seed the build):

- `artists-books.csv` — the authoritative artists'-book list (~7.9k canonical
  works), scoped to lib 1's *Artists' Books Collection* ∪ lib 2's *Master list* ∪
  lib 3's *Artists' books*/*ABCI*, **plus any lib-3 record carrying a `Cited:`
  note** (≈63 cited books sit in no collection, but every cited book must be a
  first-class node or its citation has nothing to attach to).
- `reference-works.csv` — the authoritative reference-work list (155 works),
  scoped to lib 3's *Reference resources* (157 records; 2 duplicate pairs
  collapse).
- `artists-books-dedup-review.csv` — the transient review surface: one row per
  **fuzzy** lib-1 attach (`lib1Key, twinKey, twinLib, method, confidence, review,
  lib1Title, twinTitle`), `review=yes` on the uncertain (< 0.93) ones.

Both authoritative lists share the schema `canonicalKey, canonicalLib, held,
sourceKeys, <bibliographic fields…>`. `canonicalLib` is the library the chosen
key came from; `held` is `true` when any source record is a Sloane physical
holding (lib-1 *Artists' Books Collection* membership); `sourceKeys` lists every
deduplicated record as `libN:KEY` tokens (canonical first), preserving the lib-2/
lib-1 provenance the canonical key demotes to `sameAs`.

**Regenerate:**

```sh
make -C tools/fuzzy-match                 # build the rapidfuzz venv (one time)
make -C sources -B artists-books.csv      # -> artists-books.csv, reference-works.csv, review CSV
```

---

The rest of this document describes the citation-crosswalk pipeline as it
stands **today** — the two fuzzy-match reconciliations that bridge lib 1 to
lib 3 so a Zotero `Cited:` note in a group library can be surfaced on the
artists'-book page it refers to. Under #82 this machinery is being replaced:
the canonical-key dedup above **subsumes** `abc-master-crosswalk.csv` (once
every work is one keyed node there is nothing to bridge), and the citation
match becomes the one-time `graph/citations.ttl` generator. The sections below
are retained as reference until that transition lands.
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
