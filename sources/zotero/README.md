# Zotero export track

`zotero/` holds the Zotero side of the pipeline: `zotero.sqlite` (Zotero's main
metadata store), its `storage/` attachment snapshots, the `*_export.{sh,sql}`
scripts, and the CSVs / `notes.zip` they produce. This document describes the
database itself — its three-library structure, contents, tags, collections, and
fields — and the note export drawn from it.

For the crosswalk pipeline that bridges these exports to the MARC harvest see
[`../README.md`](../README.md); for the MARC harvest itself see
[`../marc/README.md`](../marc/README.md).

## Three libraries in one database

> [!IMPORTANT]
> `zotero.sqlite` is **not one library** — it aggregates **three** (see the `libraries` / `groups` tables), and the citation **"Cited:" notes live in the group libraries, *not* in the collection the website is built from.**

| `libraryID` | Library | What it is | Holds (big collections) | "Cited:" notes |
|---|---|---|---|---|
| **1** | personal (user `5818691`) | The Sloane Art Library's curated **physical holdings**, actively maintained (edited through Nov 2025). **This is what the pipeline builds from.** | `Artists' Books Collection` (1,341) + `Zines Collection` (488) | **none** |
| **2** | group `262987` — *Artists_books_critical_index* | The **older** citation index. **Frozen since Nov 2021.** | `Master list…` (7,023) + `ABCI` (3,370) | 3,650 items |
| **3** | group `2352415` — *ABCI (Artists' Books Critical Index)* | The **newer** citation index — successor to lib 2 (**10,676 of its 12,052 items carry an `owl:sameAs` back to a lib‑2 item**). Live through Nov 2025. | `Artists' books` (7,117) + `ABCI` (3,929) | 4,008 items |

Consequences:

- **lib 3 (ABCI) supersedes lib 2.** It is richer and still maintained while lib 2 is frozen; only ~3 of the built collection's books are cited *only* in lib 2. Treat **lib 3 as the authoritative citation index**.
- **The built collection (lib 1) has no citation notes**, so the website's "cited-by" model depends on joining notes from lib 3 onto lib‑1 pages.
- **The same work is catalogued once per library under a different item key** — e.g. Ruth Laxson, *(Ho + go)² = it* (ISBN `0-932526-10-1`) is `HKGS8WHZ` in lib 2 and `GURAG9JG` in lib 3, with its own lib‑1 record. So that join is a **title / ISBN / OCLC reconciliation**, not an item-key match — and only **7 of 1,341** lib‑1 books carry an explicit `owl:sameAs` to lib 3.

This is also *why* the four big book collections look like "two non-overlapping pairs" (see [Main book collections](#main-book-collections)): each pair is simply one group library, and items in different libraries can never share an item key.

The reconciliation itself — how the lib-3 Cited notes are joined onto lib-1 ABC
pages via the fuzzy-match crosswalks — is documented in
[`../README.md`](../README.md).

### How these libraries came to be

The three-library shape is an artifact of the project's history, not a
deliberate design. It traces to Josh, who first kept a **private** Zotero
library to track the books he taught with — and, again privately, began
recording the citations he found for those books in published reference works.
When that private teaching list was **promoted to seed the larger shared
(group) library**, its contents carried over as the base. From there the work
opened up: students worked through an exhibition catalog or reference work and
added every artists' book it cited, along with the `Cited:` notes. The shared
index then evolved across the two group libraries (lib 2 froze; lib 3 succeeded
it).

One visible consequence: **some reference works carry no citations at all.**
Those are largely holdovers from Josh's original private teaching list — carried
into the shared library when it was seeded, before the student-driven
citation-indexing workflow existed — rather than gaps in data entry. See
[The "Reference resources" collection](#the-reference-resources-collection).

## SQLite database

The database is the primary source of value. It contains structured
metadata for the full collection — far more than what's in the storage
directories.

### Key tables

```
items                → master record for every item (books, articles, attachments, notes)
itemData / fields /
  itemDataValues     → field-value metadata (title, date, publisher, ISBN, place, etc.)
itemCreators /
  creators           → authors, editors, and other creator roles
itemTags / tags      → subject tags
itemNotes            → rich-text notes (citations, annotations)
itemAttachments      → links attachments to their parent items and to storage dirs
collections /
  collectionItems    → user-created folder organization
```

### Item counts

| Type            | Count  |
|-----------------|--------|
| book            | 19,211 |
| note            | 7,980  |
| attachment      | 1,300  |
| journalArticle  | 51     |
| webpage         | 13     |
| manuscript      | 3      |
| bookSection     | 2      |
| thesis          | 1      |

### How items relate to storage directories

Each item has a `key` column (8-char hash). Attachments are separate
items in the `items` table with their own key. The attachment's key
**is the storage directory name**.

Example:

```
Book item  HKGS8WHZ  →  "(Ho + go)² = it" by Ruth Laxson (Nexus Press, 1986)
  └─ Attachment item  EINGQSS4  →  path: storage:search.html
     └─ maps to  sources/zotero/storage/EINGQSS4/search.html
```

Only 1,297 of the 19,211 books have a corresponding storage snapshot.
The remaining 17,915 books exist only as structured metadata in the
database.

## Citation data

This database was compiled by a library manager and book artist at the Sloane Art Library to
record citation relationships among artists' books. For each book in
the collection, they recorded which published reference works discuss
it — effectively building a reverse citation index.

Citation data is stored in two parallel forms:

### Tags — citation source shorthand

Tags like `Bury (2015)`, `Drucker (2004)`, `Moeglin-Delcroix (2012)`
identify which reference works cite a given book. There are ~73
distinct citation-source tags. A book can carry many — e.g. Ed
Ruscha's *Every building on the Sunset Strip* has 12, meaning it
appears in 12 different reference works.

The most frequently used citation sources:

| Tag                       | Books cited |
|---------------------------|-------------|
| Moeglin-Delcroix (2012)  | 1,568       |
| Bury (2015)              | 1,214       |
| Lyons (2009)             | 877         |
| Drucker (2004)           | 615         |
| Phillpot (2013)          | 477         |
| Moeglin-Delcroix (1985)  | 438         |
| NRA Shakespeare (1985)   | 430         |
| Lauf (1998)              | 364         |
| Lyons (1985)             | 354         |

### Notes — full citation details

7,649 of the 7,978 notes are **"Cited:" notes** containing the full
bibliographic references with page numbers. All of a book's citations
are typically combined into a single note, e.g.:

```
Cited:
Bury, Stephen. Artists' Books... London, 2015. pp.17, 38, **45**, 178.
Drucker, Johanna. The Century of Artists' Books. 2nd ed. NYC, 2004. pp.178, **179**, 276.
```

Bold page numbers indicate the entry contains a photograph of the artist book.

The tags and notes encode the same information in parallel: the tag
`Drucker (2004)` on a book corresponds to the Drucker citation line
in that book's note, but the note adds the full bibliographic string
and specific page numbers.

### Notes — HTML structure (the styling is meaningful)

Notes are stored as HTML in `itemNotes.note`, wrapped in Zotero's
`<div class="zotero-note znv1">` (`znv1` = note schema version 1). For
`Cited:` notes the inline tags carry semantics — they are not
decorative:

```html
<div class="zotero-note znv1">
  <p><strong>Cited:</strong></p>
  <p>Chen, Julie, et. al.&nbsp; <em>Reading the object: three decades of books.&nbsp; </em>Oakland: Flying Fish Press, 2016. pp. 20, 22, <strong>23</strong>, <strong>30,</strong> 31, <strong>74-79 (foldout)</strong>,&nbsp;103.<strong> </strong></p>
  <p>Ruben, Robert J. <em>Beyond the Text: Artists' Books from the Collection of Robert J. Ruben</em>. New York: Grolier Club, 2010. pp.48, <strong>49</strong>.</p>
</div>
```

| Element | Meaning |
|---|---|
| `<p><strong>Cited:</strong></p>` | section heading — marks this as a reference-list note |
| each subsequent `<p>` | **one citation** = `Author. <em>Title</em>. Place: Publisher, Year. pp.…` |
| `<em>…</em>` | the **title** of the citing work (the only reliable title delimiter) |
| `<strong>` on a page number | **principal reference** — the page(s) where this book is illustrated/photographed, vs. merely listed |

So in `pp. 20, 22, **23**, **30,** 31, **74-79 (foldout)**, 103` only
the bolded pages (23, 30, the 74–79 foldout) are the substantive
appearances; the rest are passing mentions.

**Caveats for any parser** — the markup is meaningful but sloppily
applied:

- Bold bleeds onto punctuation and whitespace: `<strong>30,</strong>`,
  `205<strong>.</strong>`, and empty trailing `<strong> </strong>`.
  Detect the *digits*, then trim.
- Page ranges and annotations live inside the bold:
  `<strong>74-79 (foldout)</strong>`.
- Entity encoding is inconsistent across (and within) records — the
  same corpus mixes literal Unicode and HTML entities: `Artists'`
  vs. `Artists&rsquo;`, `Esthétique` vs. `Esth&eacute;tique`, `à`
  vs. `&agrave;`.
- `&nbsp;` appears mid-sentence and inside `<em>`; normalize
  whitespace *after* stripping tags.
- Page prefix varies: `pp. 20`, `pp.48`, `p.190` (space optional,
  `p` vs. `pp`).

### Notes — full breakdown

The 7,978 notes break down as follows:

**Citation notes (96%)**

| Variant | Count |
|---|---|
| `Cited:` (standard format) | 7,649 |
| `<strong>Cited</strong>` (bold, no colon) | 7 |
| `Citation:` (alternate keyword) | 2 |
| **Subtotal** | **7,658** |

**OCLC catalog record pastes (144)** — Full WorldCat catalog records
pasted into notes on reference resource items, including class
descriptors, named persons/corps, LC/Dewey numbers, and OCLC provider
metadata. These contain structured bibliographic data not captured
elsewhere in the Zotero fields.

**Indexing workflow notes (63)** — Who performed indexing (`Indexed by
XX`), QC credits (`QC by JH`), and completion markers (`Fully indexed
for Sloane`).

**Descriptive notes (~40)**

- Edition/colophon details (18) — printing method, edition size, paper
- Language notes (7) — e.g. "Text in English and German"
- Condition notes (4) — e.g. "library markings, in protective enclosure"
- Additional WorldCat records (4) — links to alternate OCLC records
- Rarity notes (4) — e.g. "RARE - Johanna Drucker has it"
- Contents/TOC (2) — tables of contents
- Miscellaneous — title source, exhibition context, etc.

**Empty notes (35)** — Blank or whitespace-only.

### The "Reference resources" collection

The citing reference works themselves are also cataloged in the
database, organized into a **"Reference resources" collection** of
157 items. These include the major surveys, exhibition catalogs,
bibliographies, and journals used as citation sources:

- Bury, *Artists' books: the book as a work of art 1963-2000* (2015)
- Drucker, *The century of artists' books* (2004)
- Moeglin-Delcroix, *Esthétique du livre d'artiste 1960/1980* (2012)
- Phillpot, *Booktrek: selected essays on artists' books* (2013)
- Wasserman, *The book as art* (2007)
- Lyons, *Artists' books: Visual Studies Workshop Press* (2009)
- Hamady, *Two decades of Hamady and the Perishable Press Limited* (1984)
- Bodman, *Creating artists' books* (2005)
- and ~149 others

Each citing work is tagged with its own citation-source tag (e.g.
Bury's book is tagged `Bury (2015)`) and carries workflow tags like
`Indexed, needs QC` or `Completed`, which library staff used to track
indexing progress.

Not every reference work here has any citations pointing at it. That is
expected: many are holdovers from Josh's original private teaching list, carried
into the shared library when it became the base and never run through the
student citation-indexing workflow (see
[How these libraries came to be](#how-these-libraries-came-to-be)). A reference
work with no `Cited:` notes is therefore often a provenance artifact, not
missing data.

## Notes export — surfacing "Cited:" notes on ABC pages

The "Cited:" notes are exported so the construct query can read them directly and
match each paragraph to the reference work it cites (the title-substring match runs
live in SPARQL — see [`../README.md`](../README.md)); the cited paragraph is then
attached to the ABC page via `abc-master-crosswalk.csv`. These render on the site:
each ABC book page lists the reference works that cite it, and each reference-work
page lists the ABC books it cites — the two ends of the `ab:Citation` joined back
across the graphs by the Snowman SELECT queries.

`notes_export.sh` (`= notes_export.sql | notes_export.py`) emits **`notes.zip`**,
one `<itemKey>.html` file per lib-3 cited note (selection scope identical to
`cited-records.csv`; entries sorted with fixed mtimes so an unchanged database
gives byte-identical output). Zotero note HTML is messy — entities (`&nbsp;`,
`&rsquo;`), malformed nesting (`<em>…<em>.</em></em>`), and walls of inline-styled
`<span>`s — so `notes_export.py` (stdlib `html.parser`, no venv) parses it
leniently and re-emits only what the citation model needs, as clean HTML:

- one `<p>` per citation paragraph (the `Cited:` header and empty paragraphs
  dropped; the ~4 notes using a CSL `<div class="csl-entry">` bibliography are
  handled too);
- `<em>` kept — the only reliable delimiter of the citing work's title, and the
  signal for the `<em>`-exact fallback match;
- **bold canonicalized to `<strong>`** whether the source used `<strong>`/`<b>`
  or an inline `font-weight: bold` span (`font-weight: normal` spans are cruft,
  not bold) — `<strong>` page numbers are the image-page signal;
- each `<p>` carries `n="…"` (per-item paragraph index). The flattened reference
  string is *not* stored as an attribute — the query reads it straight off the
  `<p>`'s HTML `#innerText`, which the SPARQL-Anything HTML triplifier exposes.

≈4,006 notes / ≈5,170 citation paragraphs. The page-number split is
left to those issues — the markup that feeds them is preserved here.

## Tags beyond citations

The database contains 2,912 distinct tags. Beyond the ~73 citation-source
tags and workflow tags, there are several other categories.

### Course tags

Books were tagged for pull lists for workshops in the library for university courses:
`ARTH 285` (67), `EDUC 567` (62), `ENGL 123` (30), `ARTS 409` (29),
`ARTS 322` (25), `INLS 749` (29), `ARTS 364` (11). Some include
instructor names, e.g. `Instructor: Truong (Lien)`.

### Zines of the Week (ZotW)

Dozens of tags like `ZotW 7/18/22`, `ZotW 9/19/22` (typically 8-10
items each) — a recurring feature highlighting which books were displayed that week as part of the Zines of the Week on-going display.

### Monthly ABBC

`ABBC` (192) plus monthly tags like `March 2019 ABBC`,
`Feb. 2018 ABBC` — likely related to the defunct Artist Book Book Club. 

### Physical and production descriptors

- **Binding:** `Pamphlet binding` (56), `Accordion fold` (8),
  `Smyth sewing` (8), `Perfect binding` (11)
- **Production:** `Offset` (25), `Photocopy` (9),
  `Hand drawing, inking, or painting` (11), `Commercial production` (7)
- **Format:** `Miniature books` (32), `Flip books` (11),
  `Toy and movable books` (8), `Cartonera books` (17),
  `Web-to-print exemplar` (17)

### Subject and genre tags

`Photography, Artistic` (84), `Poetry` (30), `Narrative` (26),
`Feminism` (12), `Conceptual art` (6), `Mail art` (10), `Zines` (12),
`Collage` (18), `Walking art` (11), etc.

### Geographic/cultural tags

`United States` (48), `Mexico` (9), `Cuba -- Matanzas` (6),
plus Library of Congress-style headings for Argentina, Chile, and
others.

### Workflow/QC tags

`Needs to be photographed` (229), `Re-photograph` (42),
`Check citation - Re-search WC with more info` (23),
`Check citation - WC discrepancy` (14), `Completed` (20),
`Indexed, needs QC` (11), `Canonical works` (8).

### Library of Congress Subject Headings

2,099 singleton tags are LCSH subject headings imported from catalog
records — e.g. `AIDS (Disease) and art`, `African American women
artists`, `Aging in art`.

## Collections

```
ABCI (3,929)
ABCI (3,370)
Artists' books (7,117)
Master list of artists' books with or without citations (7,023)
Peripherals/Precedents (2)
Pull lists (1)
├── ARTS 364 - Walking art (18)
├── Collage class - slavick 2019 (65)
├── EDUC 567 - 2020 (36)
├── EDUC 567 - 2021 (37)
├── ENGL 123 - Intro to Fiction Writing (30)
├── Fall 2020 A.b. instruction (0)
│   ├── ARTH 551 (10)
│   ├── CMPL 260 (43)
│   └── ECU Book Arts class (0)
├── Fall 2021 display -- Care and Wellness (26)
├── How to Haiku references (9)
├── INLS 749 (31)
├── Portrait photography (32)
├── Way out West pop-up list (25)
└── Wilson Exhibition Spring 2023 (0)
    ├── 2000-07 (249)
    ├── 2008-15 (22)
    └── 2016-present (0)
Ref resources -- completed (21)
Ref resources -- indexed, need qc (11)
Reference resources (157)
Reference resources to index (115)
Sloane Special Collections (1)
├── Artists' Books Collection (1,341)
│   └── To be photographed (141)
└── Zines Collection (488)
    └── To be scanned (0)
To Be Photographed (0)
├── Jstor Artist Books (45)
│   ├── Done (3)
│   └── done not in master list (0)
└── Jstor Zines (38)
```

### Main book collections

There are four large top-level collections that partition the books
into two non-overlapping pairs — **one pair per group library** (see
[Three libraries in one database](#three-libraries-in-one-database),
which explains *why* the pairs never overlap):

- **lib 3** (group *ABCI*): **ABCI (3,929)** overlaps with **Artists'
  books (7,117)** — ABCI stands for "Artists' Book Citation Index"
- **lib 2** (group *Artists_books_critical_index*): **ABCI (3,370)**
  overlaps with **Master list ... with or without citations (7,023)**

No items appear in both pairs (they live in different libraries).
Together the four collections cover ~14,000 of the 19,211 books; 2,229
books belong to no collection.

### Reference resource workflow

Four collections track indexing progress for the citing reference
works. Items appear to move between them as work proceeds:

- **Reference resources** (157) — the main catalog of citing works
- **Reference resources to index** (115) — not yet indexed
- **Ref resources -- completed** (21) — fully indexed
- **Ref resources -- indexed, need qc** (11) — indexed, awaiting review

### Pull lists

Course reading lists and exhibition selections, organized under a
single parent collection. Includes lists for ARTS, EDUC, ENGL, INLS,
ARTH, and CMPL courses, plus themed displays and exhibitions. Placing items in this folder went alongside and sometimes replaced tagging the items with the course number.

### Sloane Special Collections

Represents the physical holdings of the Sloane Art Library, split into
**Artists' Books Collection** (1,341) and **Zines Collection** (488),
with photography and scanning workflow sub-collections. Created in 2026 to replace the practice of using tags to track photographing/scanning workflow since tag upkeep had been abandoned at an unknown date.

## Item fields

### Metadata fields (books only, out of 19,211)

| Field | Count | % | Notes |
|---|---|---|---|
| title | 19,196 | 99.9 | Near-universal |
| date | 18,233 | 94.9 | |
| publisher | 16,762 | 87.3 | |
| place | 16,115 | 83.9 | Place of publication |
| extra | 6,875 | 35.8 | Freetext; contains OCLC numbers, VCU IDs, physical descriptions |
| language | 6,802 | 35.4 | English (4,774), Spanish (638), French (411), German (405), etc. |
| url | 6,150 | 32.0 | UNC catalog, WorldCat, or other URLs |
| libraryCatalog | 5,201 | 27.1 | Mostly "Open WorldCat" (4,904) |
| ISBN | 3,443 | 17.9 | |
| numPages | 3,252 | 16.9 | |
| shortTitle | 2,171 | 11.3 | |
| callNumber | 1,857 | 9.7 | LC call numbers |
| archiveLocation | 1,576 | 8.2 | Nearly all "Art Library" |
| abstractNote | 1,296 | 6.7 | |
| edition | 916 | 4.8 | |
| accessDate | 176 | 0.9 | |
| series | 127 | 0.7 | |
| numberOfVolumes | 13 | 0.1 | |
| volume | 9 | | |
| seriesNumber | 8 | | |
| rights | 3 | | |

### Creators (books only)

| Role | Books | % | Total assignments |
|---|---|---|---|
| author | 18,674 | 97.2 | 27,255 |
| editor | 219 | 1.1 | 437 |
| contributor | 16 | 0.1 | 49 |
| translator | 5 | | 6 |

- **18,883 books** (98.3%) have at least one creator; 328 have none
- **8,365** distinct creator names
- 72% of books have 1 creator; 16% have 2; the rest have 3+

### Creator identifiers

There are **no globally unique creator identifiers** in the database —
no VIAF, ISNI, ORCID, Wikidata QIDs, or LC authority numbers. Creators
are identified by name strings only.

What is available for future identity resolution:

- **Life dates** — 610 creators have birth/death years embedded in name
  fields (e.g. `firstName: "Tom Phillips"`, `lastName: "1937-"`), useful
  for disambiguation against authority files
- **Named Person entries** — 26 OCLC catalog pastes in notes contain
  library authority-style name forms (e.g. `Phillips, Tom, 1937-`), but
  only for subjects of reference works, not creators generally
- **Role prefixes** — Some VCU-sourced names embed roles via pipe
  delimiters (e.g. `publisher|miCielo Ediciones`)

Creator identity resolution will need to be done externally by matching
name strings (plus life dates where available) against VIAF, Wikidata,
or LC Name Authority Files.

## Identifiers

### Global identifiers

| Identifier | Location | Count | Notes |
|---|---|---|---|
| OCLC number | `extra` field or WorldCat URL | 3,819 | 1,641 in `extra` as `OCLC: nnnnn`; 2,896 in `worldcat.org/oclc/` URLs; some overlap |
| ISBN | `ISBN` field | 3,443 | Mix of ISBN-10 (2,153) and ISBN-13 (1,290); 1,134 contain multiple ISBNs; 223 have noise (prices, "pbk." etc.) |
| ISSN | `ISSN` field | 10 | Journals/serials only |

### Institutional identifiers

| Identifier | Location | Count | Notes |
|---|---|---|---|
| UNC bib ID | URL field (`UNCb` numbers) | 2,174 | UNC Chapel Hill catalog; almost no overlap with OCLC |
| VCU ALMA ID | `extra` field | 2,669 | Virginia Commonwealth University catalog |
| LC call number | `callNumber` field | 1,857 | Not unique but useful for subject grouping |
| Zotero key | `items.key` | 19,211 | Internal 8-char hash; unique within this DB only |

### Coverage

- **6,462 books (34%)** have at least one global identifier (ISBN or OCLC)
- **12,749 books (66%)** have no global identifier

Records come from three main sources: UNC catalog (~2,174), VCU
catalog (~2,669), and WorldCat (~2,911). The ISBN data needs cleanup
(multiple values per field, embedded prices and format notes). OCLC
numbers are the cleanest global identifiers and the best starting
point for linking to external knowledge graphs.

### Note on duplicates

Many books appear 2-4 times in the database with slightly different
title forms. The main cause is the **three-library structure** (see
[Three libraries in one database](#three-libraries-in-one-database)):
the same work is catalogued independently in the personal library and
in each group library, so a single book commonly has one record per
library under different item keys. For citation work, lib 3 (*ABCI*)
holds the authoritative copies.

## Item relations

The `itemRelations` table contains 13,401 entries with three predicate
types:

### `owl:sameAs` (11,027)

Links between items and their counterparts in the two group libraries
(see [Three libraries in one database](#three-libraries-in-one-database)):

- **Group 262987**: "Artists_books_critical_index" (10,677 links) —
  almost all *from* lib 3, pointing each newer *ABCI* record back to its
  predecessor in the older library (this is the evidence that lib 3
  supersedes lib 2)
- **Group 2352415**: "ABCI (Artists' Books Critical Index)" (189 links)
  — mostly from the personal library; only 7 of them are on
  `Artists' Books Collection` books, so they are **not** a usable
  crosswalk for the build

The account (`sloane-art`, user 5818691) syncs with these groups,
meaning the data also exists online at `zotero.org/groups/262987`
and `zotero.org/groups/2352415`.

### `dc:relation` (2,366)

Explicit item-to-item links connecting books to the reference works
that cite them — a **third parallel encoding of the citation data**
(alongside tags and notes). The top targets:

| Reference work | Links |
|---|---|
| Lyons, *Artists' books: VSW Press* | 386 |
| Bury, *Artists' books* | 328 |
| Drucker, *The century of artists' books* | 275 |
| Lyons, *Artists' books: a critical anthology* | 151 |

These are a subset of the tag-based citations (~1,045 items linked
vs ~7,000+ tagged). Nearly all items with a `dc:relation` also carry
the corresponding citation tag.

### `dc:replaces` (6)

A handful of item version replacements.

## Other data

### abstractNote (1,296 items)

A mix of physical descriptions with dimensions (669),
colophon/edition details (230), and descriptive text (509). Many
artists' books have unusual physical forms, so this data is
valuable for the knowledge graph.

### Physical descriptions in extra field

845 `extra` field entries contain dimensions (cm/mm), separate from
the OCLC and VCU identifiers that also appear in this field.

### Fulltext index

1,269 attachment snapshots indexed by Zotero with 11,175 distinct
words and 100,643 word-item associations. This is Zotero's internal
search index for the HTML catalog snapshots.

### Deleted items

95 items in the trash (50 books, 44 notes, 1 bookSection).

## What's in the storage directories

Almost all 1,299 directories are complete web snapshots of pages from
the UNC Chapel Hill Libraries catalog, specifically records from the
Art Library's Artists' Book Collection. Each directory is a
self-contained capture of a single catalog page.

Typical directory contents:

| File                            | Description                        |
|---------------------------------|------------------------------------|
| `search.html` / `index.aspx`   | The main catalog page HTML         |
| `status_api.php`                | Library availability API responses |
| `books`                         | Google Books API responses (JSONP) |
| `ISBN*&callback=ProcessListHathi` | HathiTrust API responses         |

Web snapshot assets (JS, CSS, images) and Zotero's full-text index
state (`.zotero-ft-cache`, `.zotero-ft-unprocessed`) have been removed
from version control — the assets were duplicated UI chrome and the
full-text state is machine-regenerable, neither with research value.
See `.gitignore` for the exclusion patterns.
