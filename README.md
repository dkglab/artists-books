# Artists' Books

A linked data publication pipeline that transforms a curated [Zotero](https://www.zotero.org/) library into a knowledge graph and static website. The collection documents artists' books held at the Joseph C. Sloane Art Library (UNC Chapel Hill), along with citation data tracking how those books appear in reference literature.

## Pipeline overview

```
Zotero (SQLite database)
    ↓  SQL export scripts
CSV files
    ↓  SPARQL-Anything (CONSTRUCT query)
RDF graph (Turtle)
    ↓  Apache Fuseki (SPARQL endpoint)
    ↓  Snowman (static site generator)
Static HTML website
```

### 1. Zotero → CSV

The Zotero library is the authoritative source. Export scripts in `Zotero/` query the Zotero SQLite database directly using `sqlite3` and produce several CSV files:

| Script | Output | Contents |
|---|---|---|
| `items_export.sh` | `artists-books.csv` | ~1,342 artists' books from the collection |
| `creators_export.sh` | `all-creators.csv` | ~8,385 distinct creator names |
| `publishers_export.sh` | `all-publishers.csv` | Publisher names |

The SQL queries join across Zotero's internal tables (`items`, `itemData`, `itemDataValues`, `itemCreators`, `creators`, `fields`) to produce flat, structured CSV.

### 2. CSV → RDF graph

[SPARQL-Anything](https://sparql-anything.cc/) reads the CSV files and transforms them into RDF using a SPARQL CONSTRUCT query (`queries/construct/artists-books.rq`).

The resulting graph uses [BIBFRAME](https://www.loc.gov/bibframe/) (Library of Congress bibliographic framework) as its primary vocabulary, with a custom `ab:` namespace for collection-specific concepts. Each book is minted a URI from its Zotero item key and described with properties for title, creator, publisher, place, date, language, and ISBN.

```
make graph/artists-books.ttl
```

### 3. RDF graph → website

[Apache Fuseki](https://jena.apache.org/documentation/fuseki2/) loads the Turtle file and exposes it as a local SPARQL endpoint at `http://localhost:3030/artists-books/sparql`.

[Snowman](https://github.com/glaciers-in-archives/snowman) reads `views.yaml`, executes the SELECT queries in `queries/select/` against the Fuseki endpoint, and renders the results into HTML using the Go templates in `templates/`. The output lands in `site/`.

```
make site/index.html   # build the site (starts Fuseki automatically)
make serve             # serve at http://127.0.0.1:8000
```

## Tools

All tools are downloaded on first use by the Makefiles in `tools/` — no system-level installs required beyond a JVM and `sqlite3`.

| Tool | Version | Purpose |
|---|---|---|
| [Apache Jena](https://jena.apache.org/) | 6.1.0 | RDF validation, RDFS reasoning, graph diffing (`riot`, `arq`, `shacl`) |
| [Apache Fuseki](https://jena.apache.org/documentation/fuseki2/) | 6.1.0 | In-process SPARQL endpoint server |
| [SPARQL-Anything](https://sparql-anything.cc/) | 1.1.0 | CSV-to-RDF transformation via SPARQL CONSTRUCT |
| [Snowman](https://github.com/glaciers-in-archives/snowman) | 0.4.0 | SPARQL-driven static site generator |

## Vocabulary

`vocab.ttl` defines a small custom vocabulary layered on top of BIBFRAME and schema.org:

- `ab:ArtistsBook` — subclass of `schema:Book`
- `ab:ReferenceBook` — reference works that cite artists' books
- `ab:Citation` — links a reference book to the artists' book it cites, with page-level granularity
- Creator role properties: `ab:primaryCreator`, `ab:bookArtist`, `ab:photographyBy`, etc.

`description.ttl` contains a worked example (Ed Ruscha's *Twentysix Gasoline Stations*) showing how the vocabulary is applied, with links to Wikidata, Getty ULAN, and LC authority records.

## Citation data

The Zotero library also encodes citation data: which of the ~1,342 artists' books are mentioned in ~73 reference works on book arts. This is captured three ways in Zotero:

- **Tags** — quick reference labels like `Bury (2015)` or `Drucker (2004)`
- **Notes** — full citation text with page numbers (~7,649 "Cited:" notes)
- **Item relations** — explicit `dc:relation` links (~2,366 connections)

The most-cited source is Moeglin-Delcroix (2012), which cites 1,568 books in the collection. See `Zotero/README.md` for full documentation of the data model.

## Configuration files

| File | Purpose |
|---|---|
| `Makefile` | Orchestrates the full pipeline |
| `snowman.yaml` | Tells Snowman where the SPARQL endpoint is |
| `views.yaml` | Maps SELECT queries and templates to output files |

### `Makefile`

The central build file. Key targets:

- `all` — builds `graph/artists-books.ttl` then `site/index.html`
- `graph/%.ttl` — runs a CONSTRUCT query through SPARQL-Anything to generate RDF from CSV
- `site/index.html` — starts Fuseki, runs Snowman, stops Fuseki; depends on the graph, both YAML files, all SPARQL SELECT queries, and all templates
- `serve` — runs `snowman server` to serve the built site at `http://127.0.0.1:8000`
- `clean` / `superclean` — removes generated files; `superclean` also removes downloaded tool binaries

Fuseki lifecycle is controlled by the `START_FUSEKI` variable (default `true`). Set `START_FUSEKI=false` if you have Fuseki already running.

### `snowman.yaml`

Tells Snowman which SPARQL endpoint to query:

```yaml
sparql_client:
  endpoint: "http://localhost:3030/artists-books/sparql"
```

### `views.yaml`

Defines one view per output page. Each entry binds a SELECT query to a template and names the output file:

```yaml
views:
  - output: "index.html"
    query: "select/artists-books.rq"
    template: "index.html"
```

Add more entries here to generate additional pages (e.g. per-creator or per-publisher indexes).

## Relevant resources

- [Opening Artists' Books vocabulary](https://oab.lib.utah.edu)
- [Book Arts Research Database](https://researchbookart.uicb.uiowa.edu)
- [Artists' books with authors in Wikidata](https://query.wikidata.org/#SELECT%20DISTINCT%20%3Fauthor%20%3FauthorLabel%20%3Fitem%20%3FitemLabel%20WHERE%20%7B%0A%20%20%3Fitem%20wdt%3AP31%20wd%3AQ1062404%20%3B%20wdt%3AP50%20%3Fauthor%20.%0A%20%20SERVICE%20wikibase%3Alabel%20%7B%20bd%3AserviceParam%20wikibase%3Alanguage%20%22%5BAUTO_LANGUAGE%5D%2Cmul%2Cen%22.%20%7D%0A%7D%0AORDER%20BY%20%3FauthorLabel)
- [Joseph C. Sloane Art Library Collection of Artists' Books and Zines](https://www-jstor-org.libproxy.lib.unc.edu/site/unc-chapel-hill/artists-books/?so=item_title_str_asc)
- [Artists' Books in the Center for Book Arts collection](https://collections.centerforbookarts.org/browse/objects/facet/term_facet/id/18074)
