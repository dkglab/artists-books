# Artists' Books

A linked data publication pipeline that transforms a curated
[Zotero](https://www.zotero.org/) library into a knowledge graph and
static website. The collection documents artists' books held at the
Joseph C. Sloane Art Library (UNC Chapel Hill), along with citation
data tracking how those books appear in reference literature.

## Pipeline

The pipeline runs as **two parallel tracks** that meet at the graph
stage: the **artists' books** (the 1,341-book collection the site is
built from) and the **reference works** that cite them (the 157-item
*Reference resources* collection, plus the "Cited:" notes connecting
the two). Both are surfaced on the website and cross-linked — a book
lists the reference works citing it, a reference work lists the books
it cites. Only reference works that actually cite an in-collection
book get a page (43 of the 157 today).

See [`docs/PIPELINE.md`](docs/PIPELINE.md) for a useful diagram, and
[`docs/README.md`](docs/README.md) for an index of the supplementary
documentation.

The stages, and where each is documented in depth:

1. **Zotero → CSV/notes.** `dedup.py` collapses the three Zotero
   libraries into the canonical book (~7.9k) and reference-work lists;
   `notes_export.sh` emits the "Cited:" note paragraphs; and
   `freeze_citations.py` reconciles those paragraphs to reference works
   and freezes the citation edges into `sources/citations.ttl`. Both
   fuzzy steps are gated by a **hand-owned decisions overlay** — a
   person's `same`/`no`/`unsure` calls in
   `sources/artists-books-dedup-decisions.csv` (per lib-1 key) and
   `yes`/`no`/`unsure` calls in `sources/citations-decisions.csv` (per
   reference-work × book pair). These are read back but never rewritten
   by `make`, so a re-run never clobbers them; each step also emits a
   generated `*-review.csv` surfacing the uncertain matches to curate. →
   [`sources/zotero/README.md`](sources/zotero/README.md) (database,
   notes, citation data model),
   [`sources/README.md`](sources/README.md) (canonical dedup + frozen
   citations).
2. **Library catalogs → MARCXML.** `marc_harvest.py` (YAZ) harvests
   full MARC records over Z39.50/SRU — books from UNC's catalog,
   reference works from a chain of nine catalogs by ISBN then
   title+author — each stamped with a synthetic `999 $a <itemKey>` to
   join back to its Zotero item. →
   [`sources/marc/README.md`](sources/marc/README.md) (harvest),
   [`docs/MARC-RECORDS.md`](docs/MARC-RECORDS.md) (field-level
   analysis).
3. **CSV + MARCXML → RDF graph.** Two
   [SPARQL-Anything](https://sparql-anything.cc/) CONSTRUCT queries
   (`queries/artists-books.rq`, `queries/reference-works.rq`) emit
   [BIBFRAME](https://www.loc.gov/bibframe/) plus a custom `ab:`
   namespace into `graph/*.ttl`. The citation edges are not constructed
   here — they are the frozen `sources/citations.ttl` (issue #82): 5,022
   citations link 3,896 books to 54 reference works. Two parallel local
   SKOS vocabularies are mined from the book MARC and curated by hand,
   each gated by its own `decisions.csv` overlay (include? / concept /
   category, per heading cluster; hand-edited, never rewritten by
   `make`): construction techniques, materials, binding/format types and
   printing methods (*how* a book is made) in
   `sources/construction/decisions.csv` → `sources/construction-methods.ttl`,
   and topical/geographic subjects (*what* it is about) in
   `sources/subjects/decisions.csv` → `sources/subject-terms.ttl`. Their
   `build-scheme.rq` queries emit the schemes, and `artists-books.rq`
   attaches an `ab:constructedUsing` / `ab:hasSubject` link from each
   book to the concepts its headings map to. → [`CLAUDE.md`](CLAUDE.md)
   (query architecture, URI minting),
   [`sources/construction/README.md`](sources/construction/README.md) and
   [`sources/subjects/README.md`](sources/subjects/README.md)
   (the mine → curate → build vocabulary pipeline),
   [`docs/QUERY-PERFORMANCE.md`](docs/QUERY-PERFORMANCE.md).
4. **RDF graph → website.** [Apache
   Fuseki](https://jena.apache.org/documentation/fuseki2/) loads the two
   constructed graphs, the frozen citations, and the
   `construction-methods.ttl` and `subject-terms.ttl` SKOS schemes, and
   serves a local SPARQL endpoint;
   [Snowman](https://github.com/glaciers-in-archives/snowman) runs the
   SELECT queries in `web/queries/` against it and renders the Go
   templates in `web/templates/` into `web/site/` — including, on each
   book page, the construction-methods and subject sections resolved from
   the schemes. →
   [`CLAUDE.md`](CLAUDE.md) (views, templates, Snowman gotchas).

## Building

```sh
make all       # build graph/*.ttl, then web/site/index.html
make serve     # build if needed, then serve at http://127.0.0.1:8080
```

All tools are fetched (and, for YAZ, built from source) on first use —
no third-party binaries need a system-wide install. The only system
prerequisites are a JVM, `sqlite3`, `make`, and a C toolchain (to
compile the vendored
[YAZ](https://www.indexdata.com/resources/software/yaz/)); GitHub
Codespaces gets these via `.devcontainer/devcontainer.json`. See
[`CLAUDE.md`](CLAUDE.md) for the full target list and build details.

Regenerating the inputs under `sources/` additionally needs **GNU Make
≥ 4.3**, for grouped targets. macOS ships GNU Make 3.81, so there use
`gmake` (`brew install make`) — `make -C sources …` stops with an
explanatory error rather than misbuilding. The `make all` / `make
serve` build above has no such requirement.

| Tool | Version | Purpose |
|---|---|---|
| [Apache Jena](https://jena.apache.org/) | 6.1.0 | RDF validation, RDFS reasoning, graph diffing (`riot`, `arq`, `shacl`) |
| [Apache Fuseki](https://jena.apache.org/documentation/fuseki2/) | 6.1.0 | In-process SPARQL endpoint server |
| [SPARQL-Anything](https://sparql-anything.cc/) | 1.1.0 | CSV/MARCXML-to-RDF transformation via SPARQL CONSTRUCT |
| [Snowman](https://github.com/glaciers-in-archives/snowman) | 0.8.0 | SPARQL-driven static site generator |
| [YAZ](https://www.indexdata.com/resources/software/yaz/) | 5.37.3 | `yaz-client`/`yaz-marcdump` — Z39.50/SRU MARC harvest; built from source |

## Vocabulary & data model

The graphs emit BIBFRAME with a custom `ab:` namespace layered on top
(`ab:ArtistsBook`, `ab:ReferenceWork`, `ab:Citation`,
`ab:cites`/`ab:citedBy`, `ab:constructedUsing`, `ab:hasSubject`,
creator-role properties). The concepts that `ab:constructedUsing` and
`ab:hasSubject` point at live in companion SKOS schemes,
`sources/construction-methods.ttl` and `sources/subject-terms.ttl` —
mined from the book MARC and curated by hand (see
[`sources/construction/README.md`](sources/construction/README.md) and
[`sources/subjects/README.md`](sources/subjects/README.md)).
`docs/vocab.ttl`
defines the vocabulary and `docs/description.ttl` is a hand-written
worked example (Ed Ruscha's *Twentysix Gasoline Stations*); `make
validate` runs Jena's validator over both. Some terms are defined but
not yet emitted, and the citation terms still carry a legacy `ex:`
prefix pending normalization — see [`docs/README.md`](docs/README.md)
and [`CLAUDE.md`](CLAUDE.md) for current status.

The Zotero library encodes the citation data three ways — tags,
"Cited:" notes (~7,649), and `dc:relation` links (~2,366); the
**notes** are the form the pipeline extracts. See
[`sources/zotero/README.md` → Citation
data](sources/zotero/README.md#citation-data) for the full model.

## Relevant resources

- [Opening Artists' Books vocabulary](https://oab.lib.utah.edu)
- [Book Arts Research Database](https://researchbookart.uicb.uiowa.edu)
- [Artists' books with authors in Wikidata](https://query.wikidata.org/#SELECT%20DISTINCT%20%3Fauthor%20%3FauthorLabel%20%3Fitem%20%3FitemLabel%20WHERE%20%7B%0A%20%20%3Fitem%20wdt%3AP31%20wd%3AQ1062404%20%3B%20wdt%3AP50%20%3Fauthor%20.%0A%20%20SERVICE%20wikibase%3Alabel%20%7B%20bd%3AserviceParam%20wikibase%3Alanguage%20%22%5BAUTO_LANGUAGE%5D%2Cmul%2Cen%22.%20%7D%0A%7D%0AORDER%20BY%20%3FauthorLabel)
- [Joseph C. Sloane Art Library Collection of Artists' Books and Zines](https://www-jstor-org.libproxy.lib.unc.edu/site/unc-chapel-hill/artists-books/?so=item_title_str_asc)
- [Artists' Books in the Center for Book Arts collection](https://collections.centerforbookarts.org/browse/objects/facet/term_facet/id/18074)
