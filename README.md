# Artists' Books

A linked data publication pipeline that transforms a curated [Zotero](https://www.zotero.org/) library into a knowledge graph and static website. The collection documents artists' books held at the Joseph C. Sloane Art Library (UNC Chapel Hill), along with citation data tracking how those books appear in reference literature.

> [!IMPORTANT]
> **`sources/zotero/zotero.sqlite` contains three libraries — and the one this site builds from has none of the citation notes.** It aggregates a *personal* library (the curated **1,341-book Sloane holdings** the pipeline builds from) plus two *group* libraries that hold the **"Cited:" citation notes**: an older `Artists_books_critical_index` (frozen 2021) and its live successor **`ABCI`** (use this one). Each book is catalogued once per library under a *different* Zotero item key, so surfacing a book's citations on its page is a cross-library **title/ISBN/OCLC reconciliation**, not an item-key join. See [`sources/zotero/README.md` → Three libraries in one database](sources/zotero/README.md#three-libraries-in-one-database) and issue #55.

## Pipeline overview

See [`PIPELINE.md`](docs/PIPELINE.md) for a rendered (Mermaid) version of this diagram, with each stage linked back to the sections below.

```
Zotero (SQLite database)                 Library catalogs (Z39.50 / SRU)
    │  SQL export + notes_export              │  marc_harvest.py (YAZ)
    ↓                                         ↓
CSVs + notes.xml + crosswalks            MARCXML records
  • artists-books.csv                      • artists-books-marc.xml
  • reference-resources.csv                • reference-resources-marc.xml *
  • notes.xml, *-crosswalk.csv
    └─────────────────┬─────────────────────┘
                      ↓  SPARQL-Anything (two CONSTRUCT queries)
       artists-books.ttl   +   reference-resources.ttl
                      ↓  Apache Fuseki (SPARQL endpoint)
                      ↓  Snowman (static site generator)
              Static HTML website

* reference-resources-marc.xml is harvested but only minimally read so far —
  the construct query pulls just the primary creator from it; the rest of the
  reference graph comes from the CSV + crosswalks (see steps 2–3).
```

The pipeline runs as **two parallel tracks** that meet in the graph stage: the **artists' books** (the 1,341-book collection the site is built from) and the **reference works** that cite them (the 157-item *Reference resources* collection, plus the "Cited:" notes that connect the two). Both tracks are now surfaced on the website: alongside the per-book pages, a **reference works index** and a **per-reference-work page** render the citation relationship, and the two link to each other (a book lists the reference works that cite it; a reference work lists the books it cites). Only reference works that actually cite a book in the collection get a page (43 of the 157 today). The page-number / image-page detail of each citation is still pending (#43/#44).

### 1. Zotero → CSV

The Zotero library is the authoritative source. Export scripts in `sources/zotero/` query the Zotero SQLite database directly using `sqlite3` and produce several CSV files:

| Script | Output | Contents | Used by construct query? |
|---|---|---|---|
| `items_export.sh` | `artists-books.csv` | ~1,341 artists' books, one row per item (title, date, publisher, place, ISBN, language, …) | **Yes** (`artists-books.rq`) |
| `items_export.sh "Reference resources"` | `reference-resources.csv` | 157 reference works that cite the artists' books | **Yes** (`reference-resources.rq`) |
| `notes_export.sh` | `notes.xml` | "Cited:" note paragraphs (one `<p>` per citation), bold page markup preserved | Indirectly — via `citation-crosswalk.csv` |
| `creators_export.sh` | `all-creators.csv`, `all-item_creators.csv` | ~8,385 distinct creator names and their item links | No |
| `publishers_export.sh` | `all-publishers.csv`, `all-item_publishers.csv` | Publisher names and their item links | No |

The SQL queries join across Zotero's internal tables (`items`, `itemData`, `itemDataValues`, `itemCreators`, `creators`, `fields`) to produce flat, structured CSV.

`artists-books.csv` feeds the artists'-book construct query — it supplies the per-book title, publisher, place, date, language, and ISBN. Creators now come from the MARC records (step 2) rather than `all-creators.csv`, and publisher names are read straight from `artists-books.csv`, so the creators/publishers exports (and their hand-reconciled `*-reconciled.csv` variants) are currently auxiliary: kept for reference and reconciliation work, not consumed by the pipeline.

`reference-resources.csv` feeds a **second** construct query (`reference-resources.rq`) for the reference works. The "Cited:" notes that connect references to artists' books don't live on the built collection's records, so a pair of fuzzy-match **crosswalks** (`abc-master-crosswalk.csv`, `citation-crosswalk.csv`) reconcile note → reference-work → artists'-book across the three Zotero libraries. See [`sources/README.md`](sources/README.md) for the full citation data model.

### 2. Library catalogs → MARCXML

For the books that have a UNC bib number, full MARC records are harvested from UNC's catalog over Z39.50 by `sources/marc/marc_harvest.py` (using the YAZ toolkit) and written to `sources/marc/artists-books-marc.xml` — a single MARCXML collection of ~1,340 records, one per item. The harvester stamps each record with a synthetic `999 $a <itemKey>` field so it can be joined back to the corresponding Zotero item.

These records carry richer, more authoritative data than the CSV: cataloguer-supplied creator names with relator roles, real-world-object URIs (VIAF/ISNI in `$1`) and LC name-authority URIs (`$0`), plus the OCLC number (`001`). See [`MARC-RECORDS.md`](docs/MARC-RECORDS.md) for a full analysis of the file.

The same harvester also produces **`sources/marc/reference-resources-marc.xml`** for the reference works. Reference works are mostly *not* UNC bibs, so the harvester searches a chain of **nine** catalogs (UNC, Library of Congress, K10plus, Penn State, LIBRIS, Getty, Clark, NYARC, Harvard) by **ISBN**, then **title + author**, falling back across servers until a record verifies; a few hand-supplied records are merged from `reference-resources-manual.xml`. Result: ~155 of the 157 reference works get a MARC record (joined by `999 $a`, same as the books). The construct query now reads a **basic slice** of this file — just the **primary creator** (`100 $a`) — to demonstrate the join; the rest of the MARC's richer data (OCLC/WorldCat, secondary creators, relator roles, identity URIs, extent/dimensions) isn't in the graph yet (tracked in #40/#51).

### 3. CSV + MARCXML → RDF graph

[SPARQL-Anything](https://sparql-anything.cc/) transforms the sources into RDF using **two** SPARQL CONSTRUCT queries — one per track:

- `queries/artists-books.rq` → `graph/artists-books.ttl` (the artists' books)
- `queries/reference-resources.rq` → `graph/reference-resources.ttl` (the reference works and citations)

Both graphs use [BIBFRAME](https://www.loc.gov/bibframe/) (Library of Congress bibliographic framework) as their primary vocabulary, with a custom `ab:` namespace for collection-specific concepts.

**Artists' books.** Each book is minted a URI from its Zotero item key. Title, publisher, place, date, language, and ISBN come from the CSV; creators (with their VIAF/ISNI/LC identities and LC relator roles), the OCLC number, and the WorldCat URL come from the MARC records, joined to each book through the `999 $a` item key. Books without a MARC record still emit, just without the MARC-derived fields.

**Reference works and citations.** `reference-resources.rq` mints an `ab:ReferenceWork` node (URI `…/reference/<itemKey>`) for each of the 157 reference works, with title/publisher/place/date/language/ISBN from `reference-resources.csv` and the **primary creator** (`100 $a`) joined in from `reference-resources-marc.xml` by the `999 $a` itemKey (a basic MARC slice, like the books' MARC join). It then reads the two crosswalks and emits one **`ab:Citation`** per resolved reference→book link — `ab:citedBy` the reference work, `ab:cites` the artists' book — anchored at `…/reference/<refKey>/citation/<bookKey>`. Currently **433 citations** connect **194 artists' books** to **43 reference works** (paragraphs flagged `review=yes` are held out of the auto-join) — and step 4 renders this both ways, so each book page links to the reference works citing it and each reference page links to the books it cites. Page-number / image-page extraction from the notes is still pending (#43/#44).

```
make graph/artists-books.ttl graph/reference-resources.ttl
```

### 4. RDF graph → website

[Apache Fuseki](https://jena.apache.org/documentation/fuseki2/) loads the Turtle file and exposes it as a local SPARQL endpoint at `http://localhost:3030/artists-books/sparql`.

[Snowman](https://github.com/glaciers-in-archives/snowman) reads `web/views.yaml`, executes the SELECT queries in `web/queries/` against the Fuseki endpoint, and renders the results into HTML using the Go templates in `web/templates/`. The output lands in `web/site/`.

```
make web/site/index.html   # build the site (starts Fuseki automatically)
make serve             # serve at http://127.0.0.1:8080
```

## Tools

All tools are fetched (and, for YAZ, built from source) on first use by the Makefiles in `tools/` — no third-party tool binaries need to be installed system-wide. The only system prerequisites are a JVM and `sqlite3`, plus `make` and a C toolchain (used to compile the vendored [YAZ](https://www.indexdata.com/resources/software/yaz/) toolkit from source). GitHub Codespaces gets these automatically via `.devcontainer/devcontainer.json`.

| Tool | Version | Purpose |
|---|---|---|
| [Apache Jena](https://jena.apache.org/) | 6.1.0 | RDF validation, RDFS reasoning, graph diffing (`riot`, `arq`, `shacl`) |
| [Apache Fuseki](https://jena.apache.org/documentation/fuseki2/) | 6.1.0 | In-process SPARQL endpoint server |
| [SPARQL-Anything](https://sparql-anything.cc/) | 1.1.0 | CSV/MARCXML-to-RDF transformation via SPARQL CONSTRUCT |
| [Snowman](https://github.com/glaciers-in-archives/snowman) | 0.8.0 | SPARQL-driven static site generator |
| [YAZ](https://www.indexdata.com/resources/software/yaz/) | 5.37.3 | `yaz-client`/`yaz-marcdump` — Z39.50/SRU MARC harvest (`sources/marc/marc_harvest.py`); built from source under `tools/yaz-client/` |

## Vocabulary

`docs/vocab.ttl` defines a small custom vocabulary layered on top of BIBFRAME and schema.org:

- `ab:ArtistsBook` — subclass of `schema:Book`
- `ab:ReferenceWork` — a reference work (book, article, webpage) that cites an artists' book
- `ab:Citation` — links a reference work to the artists' book it cites; `ab:cites` → the book, `ab:citedBy` → the reference work
- Creator role properties: `ab:primaryCreator`, `ab:bookArtist`, `ab:photographyBy`, etc.

`ab:ReferenceWork`, `ab:Citation`, `ab:cites`, and `ab:citedBy` are emitted by the construct queries today. The page-level citation properties and the creator-role properties are defined but **not yet emitted** — and `docs/vocab.ttl` still carries the citation terms under a legacy `ex:` prefix pending normalization to `ab:`.

`docs/description.ttl` contains a worked example (Ed Ruscha's *Twentysix Gasoline Stations*) showing how the vocabulary is applied, with links to Wikidata, Getty ULAN, and LC authority records.

## Citation data

The Zotero library also encodes citation data: which artists' books are mentioned in the reference works on book arts (the 157-item *Reference resources* collection; ~73 of them are used often enough to have a short citation-source tag). This is captured three ways in Zotero:

- **Tags** — quick reference labels like `Bury (2015)` or `Drucker (2004)`
- **Notes** — full citation text with page numbers (~7,649 "Cited:" notes)
- **Item relations** — explicit `dc:relation` links (~2,366 connections)

The most-cited source is Moeglin-Delcroix (2012), which cites 1,568 books in the collection. The **notes** are the form the pipeline extracts: the construct query reconciles them (via the crosswalks) into the graph as 433 `ab:Citation`s (step 3). See `sources/README.md` for full documentation of the data model.

## Configuration files

| File | Purpose |
|---|---|
| `Makefile` | Orchestrates the full pipeline |
| `web/snowman.yaml` | Tells Snowman where the SPARQL endpoint is |
| `web/views.yaml` | Maps SELECT queries and templates to output files |

### `Makefile`

The central build file. Key targets:

- `all` — builds `graph/artists-books.ttl` then `web/site/index.html`
- `graph/%.ttl` — runs a CONSTRUCT query through SPARQL-Anything to generate RDF from the CSV and MARCXML sources
- `web/site/index.html` — starts Fuseki, runs Snowman, stops Fuseki; depends on the graph, both YAML files, all SPARQL SELECT queries, and all templates
- `serve` — runs `snowman server` to serve the built site at `http://127.0.0.1:8080`
- `clean` / `superclean` — removes generated files; `superclean` also removes downloaded tool binaries

Fuseki lifecycle is controlled by the `START_FUSEKI` variable (default `true`). Set `START_FUSEKI=false` if you have Fuseki already running.

### `web/snowman.yaml`

Tells Snowman which SPARQL endpoint to query:

```yaml
sparql_client:
  endpoint: "http://localhost:3030/artists-books/sparql"
```

### `web/views.yaml`

Defines one view per output page. Each entry binds a SELECT query to a template and names the output file:

```yaml
views:
  - output: "index.html"
    query: "artists-books.rq"
    template: "index.html"
  - output: "item/{{itemKey}}/index.html"
    query: "artists-books.rq"
    template: "artists-book.html"
  - output: "references.html"
    query: "references.rq"
    template: "references.html"
  - output: "reference/{{itemKey}}/index.html"
    query: "references.rq"
    template: "reference.html"
```

There are **four** views across two query/template pairs — one pair for the artists' books, one for the reference works. Within each pair both views run the same SELECT query, but the second templates a SPARQL variable (`{{itemKey}}`) into its output path, so Snowman writes one file per result row — a detail page per item. Add more entries here to generate additional pages (e.g. per-creator or per-publisher indexes).

## Templates

```
web/templates/
├── layouts/
│   └── base.html         — outer HTML shell (head, body, nav to both indexes)
├── index.html            — collection index, lists every book ("cited by N")
├── artists-book.html     — per-book detail page (one per item/{{itemKey}}/),
│                           with a "Cited by" list of reference works
├── references.html       — reference-works index, lists citing references ("cites N")
└── reference.html        — per-reference detail page (one per reference/{{itemKey}}/),
                            with a "Cites" list of artists' books
```

Templates use Go's [`html/template`](https://pkg.go.dev/html/template) package. See the [Snowman template documentation](https://byabbe.se/snowman-manual/reference/template-syntax/) for how SPARQL results are passed as template data.

## Relevant resources

- [Opening Artists' Books vocabulary](https://oab.lib.utah.edu)
- [Book Arts Research Database](https://researchbookart.uicb.uiowa.edu)
- [Artists' books with authors in Wikidata](https://query.wikidata.org/#SELECT%20DISTINCT%20%3Fauthor%20%3FauthorLabel%20%3Fitem%20%3FitemLabel%20WHERE%20%7B%0A%20%20%3Fitem%20wdt%3AP31%20wd%3AQ1062404%20%3B%20wdt%3AP50%20%3Fauthor%20.%0A%20%20SERVICE%20wikibase%3Alabel%20%7B%20bd%3AserviceParam%20wikibase%3Alanguage%20%22%5BAUTO_LANGUAGE%5D%2Cmul%2Cen%22.%20%7D%0A%7D%0AORDER%20BY%20%3FauthorLabel)
- [Joseph C. Sloane Art Library Collection of Artists' Books and Zines](https://www-jstor-org.libproxy.lib.unc.edu/site/unc-chapel-hill/artists-books/?so=item_title_str_asc)
- [Artists' Books in the Center for Book Arts collection](https://collections.centerforbookarts.org/browse/objects/facet/term_facet/id/18074)
