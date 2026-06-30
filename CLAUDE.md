# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

See `README.md` for the project overview and pipeline diagram. This file captures the operational details and non-obvious architecture that aren't in the README.

## Common commands

```
make all          # full pipeline: graph/artists-books.ttl + graph/reference-resources.ttl, then site/index.html
make serve        # build if needed, then snowman server on port 8080
make validate     # run Jena riot --validate on vocab.ttl + description.ttl
make clean        # remove generated files (graph/, site/, .snowman/)
make superclean   # also remove downloaded tool binaries under tools/
```

The Makefile auto-fetches all tools (Jena, Fuseki, SPARQL-Anything, Snowman) into `tools/<tool>/` on first use — no system installs beyond a JVM and `sqlite3`.

### Iterating on queries and templates

`site/index.html`'s Make recipe depends on every yaml, every `queries/select/*.rq`, every `templates/*.html`, every `templates/layouts/*.html`, and every `templates/includes/*.html`. Editing any of these triggers a rebuild on the next `make`. The recipe starts Fuseki, runs `snowman build`, then stops Fuseki — driven by `START_FUSEKI=true` (set `START_FUSEKI=false` if Fuseki is already running externally).

The `snowman server` process is *not* a watcher — it only serves what's in `site/`. After editing, you must kill the running server, re-run `make serve` (which rebuilds), and the new server will pick up the rebuilt files.

The build log is captured at `.snowman/build_log.txt`.

### Editing the construct queries

There are **two** construct queries, each producing its own graph:

- `make graph/artists-books.ttl` runs `queries/construct/artists-books.rq` over the CSVs and `Zotero/artists-books-marc.xml`.
- `make graph/reference-resources.ttl` runs `queries/construct/reference-resources.rq` over `Zotero/reference-resources.csv` and the two crosswalks (`citation-crosswalk.csv`, `abc-master-crosswalk.csv`) to emit the `ab:ReferenceWork` nodes and `ab:Citation`s. It does **not** yet read `Zotero/reference-resources-marc.xml` (that wiring is pending — #40/#46/#51).

Both are pure source-to-RDF transforms — they do **not** touch Fuseki. The crosswalk CSVs are committed inputs to the graph build (like the `-marc.xml` files), so after regenerating them (`make -C Zotero …`) rebuild the graph explicitly with `make -B graph/reference-resources.ttl`, then re-run `make` to rebuild the site.

Before changing how the query walks the MARC XML, read `QUERY-PERFORMANCE.md` — traversing Facade-X containers with a variable predicate (`?s ?var ?o`) instead of `fx:anySlot` is the difference between a 6-second and a 5-minute build.

## Architecture notes beyond the README

### Two SPARQL stages, two query directories

- `queries/construct/` — runs against raw CSVs/MARCXML via SPARQL-Anything's `x-sparql-anything:` SERVICE. Two queries (`artists-books.rq`, `reference-resources.rq`) produce two graphs (`graph/artists-books.ttl`, `graph/reference-resources.ttl`); each only runs when its `.ttl` is regenerated.
- `queries/select/` — runs against Fuseki (which loads **both** constructed graphs). One per Snowman view; results feed into Go templates. Note: only the artists'-book views exist today — no SELECT query reads the reference graph yet (#63).

### URI minting

Book URIs are minted from the Zotero `itemKey` field: `https://dkglab.github.io/ns/artists-books/item/<itemKey>`. Related per-book resources use suffixed paths (`/title`, `/publication`, `/identifier`, `/oclc`, `/contribution/<creatorKey>`). Creators are identified by their real-world-object URI — VIAF, else ISNI (from MARC `$1`); only when neither exists is an `ab:creator/<creatorKey>` URI minted, where `creatorKey` is the LC name-authority id (MARC `$0`) or, failing that, a slug of the name. This is done via `fx:entity(...)` `BIND` calls in the construct query.

`reference-resources.rq` mints parallel URIs for the reference track: each reference work is `…/reference/<itemKey>` (with `/publication`, `/identifier` sub-resources), and each citation is `…/reference/<refKey>/citation/<bookKey>` — keyed by the (reference work, artists' book) pair, so multiple note paragraphs citing the same book from the same work collapse to one `ab:Citation`.

### `views.yaml` and per-row output expansion

Each entry in `views.yaml` ties a SELECT query to a template + output path. When the output path templates a SPARQL variable (e.g. `item/{{itemKey}}/index.html`), Snowman writes one file per query result row, substituting that row's value. The template receives that row's bindings as its data context (accessible as `.itemKey`, `.title`, etc., matching the SELECT variable names exactly).

This means per-item SELECT queries should return **one row per output file**. For multi-valued fields (e.g. multiple creators per book), aggregate with `GROUP_CONCAT(DISTINCT ?x; separator="; ")` and `GROUP BY` so the rows collapse — otherwise you get duplicate output files.

The index view uses the same row set but iterates with `{{ range . }}` in the template.

### Templates

`templates/layouts/base.html` defines a `base` template with `title` and `content` blocks; page templates start with `{{ template "base" . }}` and `{{ define "content" }}...{{ end }}`. Go `html/template` syntax. SPARQL bindings are accessed by lowercase variable name (`.title`, not `.Title`).

### Vocabulary status

The constructed graphs emit BIBFRAME directly (`bf:title`, `bf:contribution`, `bf:provisionActivity`, etc.) plus a growing `ab:` namespace: `ab:ArtistsBook`/`ab:itemKey` (artists-books.rq) and `ab:ReferenceWork`, `ab:Citation`, `ab:cites`, `ab:citedBy` (reference-resources.rq). Still **not yet emitted**: the page-level citation properties (`ab:onPageNumber`/`ab:imagesOnPageNumber`, #43/#44) and the creator-role properties (`ab:bookArtist`, etc.). Note a divergence — `vocab.ttl` still defines the citation class/properties under a legacy `ex:` prefix (`ex:Citation`, `ex:cites`, …) while the construct query emits them under `ab:`; the vocabulary needs normalizing to match. `description.ttl` is a hand-written worked example (Ed Ruscha's *Twentysix Gasoline Stations*) demonstrating the full intended shape.

### Zotero subdirectory

`Zotero/zotero.sqlite` is the authoritative source. The `*_export.sh` scripts run `*_export.sql` against it to produce the CSVs the construct queries read; `notes_export.sh` emits `notes.xml`, and `marc_harvest.py` produces the `*-marc.xml` collections. The `tools/fuzzy-match/` matchers turn those into the `*-crosswalk.csv` files. The `-reconciled.csv` variants have been manually cleaned (e.g. mapped to Wikidata/ULAN IDs). See `Zotero/README.md` for the citation data model and the reference-works pipeline.
