# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

See `README.md` for the project overview and pipeline diagram. This file captures the operational details and non-obvious architecture that aren't in the README.

## Common commands

```
make all          # full pipeline: graph/artists-books.ttl + graph/reference-resources.ttl, then web/site/index.html
make serve        # build if needed, then snowman server on port 8080
make validate     # run Jena riot --validate on docs/vocab.ttl + docs/description.ttl
make clean        # remove generated files (graph/, web/site/, web/.snowman/)
make superclean   # also remove downloaded tool binaries under tools/
```

The Makefile auto-fetches all tools (Jena, Fuseki, SPARQL-Anything, Snowman) into `tools/<tool>/` on first use — no system installs beyond a JVM and `sqlite3`.

### Iterating on queries and templates

`web/site/index.html`'s Make recipe depends on every yaml, every `web/queries/select/*.rq`, every `web/templates/*.html`, every `web/templates/layouts/*.html`, and every `web/templates/includes/*.html`. Editing any of these triggers a rebuild on the next `make`. The recipe starts Fuseki, `cd`s into `web/` and runs `snowman build` there (Snowman locates its config/queries/templates in the current directory), then stops Fuseki — driven by `START_FUSEKI=true` (set `START_FUSEKI=false` if Fuseki is already running externally).

The `snowman server` process is *not* a watcher — it only serves what's in `web/site/`. After editing, you must kill the running server, re-run `make serve` (which rebuilds), and the new server will pick up the rebuilt files.

The build log is captured at `web/.snowman/build_log.txt`.

### Editing the construct queries

There are **two** construct queries, each producing its own graph:

- `make graph/artists-books.ttl` runs `queries/construct/artists-books.rq` over the CSVs and `Zotero/artists-books-marc.xml`.
- `make graph/reference-resources.ttl` runs `queries/construct/reference-resources.rq` over `Zotero/reference-resources.csv` and the two crosswalks (`citation-crosswalk.csv`, `abc-master-crosswalk.csv`) to emit the `ab:ReferenceWork` nodes and `ab:Citation`s. It also reads a **basic slice** of `Zotero/reference-resources-marc.xml` — just the primary creator (`100 $a`), joined by `999 $a` like the books' MARC — emitted as a `bflc:PrimaryContribution` (#46). The rest of the reference MARC (OCLC/WorldCat, secondary creators, roles, identity URIs, extent/dimensions) is still pending (#40/#51).

Both are pure source-to-RDF transforms — they do **not** touch Fuseki. The crosswalk CSVs are committed inputs to the graph build (like the `-marc.xml` files), so after regenerating them (`make -C Zotero …`) rebuild the graph explicitly with `make -B graph/reference-resources.ttl`, then re-run `make` to rebuild the site.

Before changing how the query walks the MARC XML, read `docs/QUERY-PERFORMANCE.md` — traversing Facade-X containers with a variable predicate (`?s ?var ?o`) instead of `fx:anySlot` is the difference between a 6-second and a 5-minute build.

## Architecture notes beyond the README

### Two SPARQL stages, two query directories

- `queries/construct/` — runs against raw CSVs/MARCXML via SPARQL-Anything's `x-sparql-anything:` SERVICE. Two queries (`artists-books.rq`, `reference-resources.rq`) produce two graphs (`graph/artists-books.ttl`, `graph/reference-resources.ttl`); each only runs when its `.ttl` is regenerated.
- `web/queries/select/` — runs against Fuseki (which loads **both** constructed graphs). One per Snowman view; results feed into Go templates. Two SELECT queries today: `artists-books.rq` (book index + per-book pages) and `references.rq` (reference index + per-reference pages, #63). Both join across the two graphs to render the citation relationship in each direction — `references.rq` requires the citation join so only reference works that cite an in-collection book get a page (43 of 157); `artists-books.rq` joins it `OPTIONAL` for the per-book "Cited by" list.

### URI minting

Book URIs are minted from the Zotero `itemKey` field: `https://dkglab.github.io/ns/artists-books/item/<itemKey>`. Related per-book resources use suffixed paths (`/title`, `/publication`, `/identifier`, `/oclc`, `/contribution/<creatorKey>`). Creators are identified by their real-world-object URI — VIAF, else ISNI (from MARC `$1`); only when neither exists is an `ab:creator/<creatorKey>` URI minted, where `creatorKey` is the LC name-authority id (MARC `$0`) or, failing that, a slug of the name. This is done via `fx:entity(...)` `BIND` calls in the construct query.

`reference-resources.rq` mints parallel URIs for the reference track: each reference work is `…/reference/<itemKey>` (with `/publication`, `/identifier` sub-resources), and each citation is `…/reference/<refKey>/citation/<bookKey>` — keyed by the (reference work, artists' book) pair, so multiple note paragraphs citing the same book from the same work collapse to one `ab:Citation`.

### `web/views.yaml` and per-row output expansion

Each entry in `web/views.yaml` ties a SELECT query to a template + output path. When the output path templates a SPARQL variable (e.g. `item/{{itemKey}}/index.html`), Snowman writes one file per query result row, substituting that row's value. The template receives that row's bindings as its data context (accessible as `.itemKey`, `.title`, etc., matching the SELECT variable names exactly).

This means per-item SELECT queries should return **one row per output file**. For multi-valued fields (e.g. multiple creators per book), aggregate with `GROUP_CONCAT(DISTINCT ?x; separator="; ")` and `GROUP BY` so the rows collapse — otherwise you get duplicate output files.

The index view uses the same row set but iterates with `{{ range . }}` in the template.

Two non-obvious Snowman behaviours bite here (both learned building the reference views):

- **A *bound* binding is always truthy under `{{ with }}` — even `0` or `""` from an `IF`/aggregate.** Only a genuinely *unbound* variable is hidden. An empty `GROUP_CONCAT` comes back unbound (so `{{ with .isbns }}` correctly hides it), but `COUNT(...)` of zero comes back as a bound `0` and would render. To hide a zero count, leave it unbound — compute it in an inner aggregate subquery, then `BIND(IF(?n > 0, STR(?n), ?sentinel) AS ?count)` in an outer non-aggregate scope (a bare unbound var is illegal in an aggregate projection). The reference index sidesteps this entirely: `references.rq` requires the citation join so the count is always ≥ 1, and the book index derives its "cited by N" with `len (split .citedBy "\n")` over a field that's absent when empty.
- **To render multi-valued fields as *links*, not just text, pack `key`+`label` into each `GROUP_CONCAT` token and split in the template.** SPARQL aggregation flattens a row, losing the pairing needed for per-item hrefs. The citation lists emit `GROUP_CONCAT(DISTINCT CONCAT(?key, "\t", ?label); separator="\n")`, then the template does `{{ range (split . "\n") }}{{ $p := split . "\t" }}<a href="/…/{{ index $p 0 }}">{{ index $p 1 }}</a>{{ end }}`. Snowman's `split` is `split(string, sep)` and `index` is the Go builtin.

### Templates

`web/templates/layouts/base.html` defines a `base` template with `title` and `content` blocks; page templates start with `{{ template "base" . }}` and `{{ define "content" }}...{{ end }}`. Go `html/template` syntax. SPARQL bindings are accessed by lowercase variable name (`.title`, not `.Title`). There are four page templates: `index.html` + `artists-book.html` (books) and `references.html` + `reference.html` (reference works); the two families cross-link via the citation relationship.

### Vocabulary status

The constructed graphs emit BIBFRAME directly (`bf:title`, `bf:contribution`, `bf:provisionActivity`, etc.) plus a growing `ab:` namespace: `ab:ArtistsBook`/`ab:itemKey` (artists-books.rq) and `ab:ReferenceWork`, `ab:Citation`, `ab:cites`, `ab:citedBy` (reference-resources.rq). Still **not yet emitted**: the page-level citation properties (`ab:onPageNumber`/`ab:imagesOnPageNumber`, #43/#44) and the creator-role properties (`ab:bookArtist`, etc.). Note a divergence — `docs/vocab.ttl` still defines the citation class/properties under a legacy `ex:` prefix (`ex:Citation`, `ex:cites`, …) while the construct query emits them under `ab:`; the vocabulary needs normalizing to match. `docs/description.ttl` is a hand-written worked example (Ed Ruscha's *Twentysix Gasoline Stations*) demonstrating the full intended shape.

### Zotero subdirectory

`Zotero/zotero.sqlite` is the authoritative source. The `*_export.sh` scripts run `*_export.sql` against it to produce the CSVs the construct queries read; `notes_export.sh` emits `notes.xml`, and `marc_harvest.py` produces the `*-marc.xml` collections. The `tools/fuzzy-match/` matchers turn those into the `*-crosswalk.csv` files. The `-reconciled.csv` variants have been manually cleaned (e.g. mapped to Wikidata/ULAN IDs). See `Zotero/README.md` for the citation data model and the reference-works pipeline.
