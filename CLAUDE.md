# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

See `README.md` for the project overview and pipeline diagram. This file captures the operational details and non-obvious architecture that aren't in the README.

## Common commands

```
make all          # full pipeline: graph/artists-books.ttl + graph/reference-works.ttl, then web/site/index.html
make serve        # build if needed, then snowman server on port 8080
make validate     # run Jena riot --validate on docs/vocab.ttl + docs/description.ttl
make clean        # remove generated files (graph/, web/site/, web/.snowman/)
make superclean   # also remove downloaded tool binaries under tools/
```

The Makefile auto-fetches all tools (Jena, Fuseki, SPARQL-Anything, Snowman) into `tools/<tool>/` on first use — no system installs beyond a JVM and `sqlite3`.

### Iterating on queries and templates

`web/site/index.html`'s Make recipe depends on every yaml, every `web/queries/*.rq`, every `web/templates/*.html`, every `web/templates/layouts/*.html`, and every `web/templates/includes/*.html`. Editing any of these triggers a rebuild on the next `make`. The recipe starts Fuseki, `cd`s into `web/` and runs `snowman build` there (Snowman locates its config/queries/templates in the current directory), then stops Fuseki — driven by `START_FUSEKI=true` (set `START_FUSEKI=false` if Fuseki is already running externally).

The `snowman server` process is *not* a watcher — it only serves what's in `web/site/`. After editing, you must kill the running server, re-run `make serve` (which rebuilds), and the new server will pick up the rebuilt files.

The build log is captured at `web/.snowman/build_log.txt`.

### Editing the construct queries

There are **two** construct queries, each producing its own graph, plus one **frozen** graph loaded as-is (no query):

- `make graph/artists-books.ttl` runs `queries/artists-books.rq` over the canonical artists'-book list `sources/artists-books.csv` (lib 1 ∪ 2 ∪ 3, deduplicated — issue #82) and the per-record MARC archive `sources/marc/artists-books-marc.zip` (#81: one `<key>.xml` per record, read via nested Archive→XML triplifiers). Book URIs are minted from the **canonical** key; `ab:heldBySloane true` flags the ~1,300 Sloane holdings. Since #84 the MARC carries the **canonical** key in `999 $a`, so the creator/OCLC/extent join is directly on `?canonical_key` (read from the record data, not the entry filename). `sources/marc/artists-books-marc.zip` is built by merging the ~1,286 already-harvested **held** records (re-keyed lib-1 → canonical, frozen in `sources/marc/artists-books-held-marc.xml` by `sources/marc/rekey_held.py`) with a fresh Z39.50/SRU harvest of the ~6,619 **non-held** works (`marc_harvest.py --premerged`; see `sources/marc/README.md`). The non-held harvest is a large, slow, resumable external job run separately — until it completes, non-held books exist as nodes but carry no MARC enrichment.
- `make graph/reference-works.ttl` runs `queries/reference-works.rq` over `sources/reference-works.csv` (the canonical reference-work list) to emit the `ab:ReferenceWork` nodes. It also reads a **basic slice** of the per-record MARC archive `sources/marc/reference-works-marc.zip` (#81) — just the primary creator (`100 $a`), joined by `999 $a` like the books' MARC — emitted as a `bflc:PrimaryContribution` (#46). The rest of the reference MARC (OCLC/WorldCat, secondary creators, roles, identity URIs, extent/dimensions) is still pending (#40/#51).
- `sources/citations.ttl` is the **frozen** citation graph (issue #82, Phase 0): 5,022 `ab:Citation` edges (`ab:cites`/`ab:citedBy`/`rdfs:label` + `ab:onPageNumber`/`ab:imagesOnPageNumber`) against the canonical `item/`/`reference/` URIs, generated once by `tools/fuzzy-match/freeze_citations.py` and committed. It has **no construct query** — Fuseki just loads it alongside the two constructed graphs. The old live citation build (the `citation-crosswalk.csv`/`abc-master-crosswalk.csv` fuzzy bridge and the second `UNION` branch of the former `reference-resources.rq`) has been removed entirely; its `match.py`/`cite_match.py` matchers survive only as the libraries `dedup.py`/`freeze_citations.py` import.

The two construct queries are pure source-to-RDF transforms — they do **not** touch Fuseki. To regenerate the frozen citations after a source change, run `make -C sources -B citations.ttl` (a one-time Phase-0 generator; see `sources/README.md`).

Before changing how the query walks the MARC, read `docs/QUERY-PERFORMANCE.md` — traversing Facade-X containers with a variable predicate (`?s ?var ?o`) instead of `fx:anySlot` is the difference between a 6-second and a 5-minute build. The MARC is now a per-record zip archive read via nested Archive→XML triplifiers (#81), so the archive recipe passes `-Dlog4j2.statusLoggerLevel=OFF` (the archive triplifier otherwise trips Log4j's StatusLogger onto stdout and corrupts the Turtle).

## Architecture notes beyond the README

### Two SPARQL stages, two query directories

- `queries/` — runs against raw CSVs and the per-record MARC zip archives (#81) via SPARQL-Anything's `x-sparql-anything:` SERVICE (the MARC read is a nested Archive→XML triplifier: an outer `fx:archive.matches` listing + an inner per-record `fx:location ?file` + `fx:from-archive`). Two queries (`artists-books.rq`, `reference-works.rq`) produce two graphs (`graph/artists-books.ttl`, `graph/reference-works.ttl`); each only runs when its `.ttl` is regenerated. The citation edges are **not** constructed here — they are the frozen `sources/citations.ttl`.
- `web/queries/` — runs against Fuseki (which loads **all three** graphs: the two constructed graphs + frozen `sources/citations.ttl`, merged into one dataset). One per Snowman view; results feed into Go templates. Two SELECT queries today: `artists-books.rq` (book index + per-book pages) and `references.rq` (reference index + per-reference pages, #63). Both join across the graphs to render the citation relationship in each direction — `references.rq` requires the citation join so only reference works that cite an in-collection book get a page (54 of 155); `artists-books.rq` joins it `OPTIONAL` for the per-book "Cited by" list. Because Fuseki merges the three files into a single default graph, the web queries need no change to reach the citation graph — the joins resolve across the union.

### URI minting

Book URIs are minted from the **canonical** key (issue #82; mostly a lib-3 Zotero `itemKey`): `https://dkglab.github.io/ns/artists-books/item/<canonicalKey>`. Related per-book resources use suffixed paths (`/publication`, `/identifier`, `/oclc`, `/contribution/<creatorKey>`). The title is *not* a sub-resource — it's emitted as a plain `rdfs:label` on the book node (#11). Creators are identified by their real-world-object URI — VIAF, else ISNI (from MARC `$1`); only when neither exists is an `ab:creator/<creatorKey>` URI minted, where `creatorKey` is the LC name-authority id (MARC `$0`) or, failing that, a slug of the name. This is done via `fx:entity(...)` `BIND` calls in the construct query. The per-book sub-resource URIs (`/oclc`, `/extent`, `/contribution/…`) are minted **inline** inside the MARC `OPTIONAL`: since #84 the MARC joins on `?canonical_key`, which is therefore bound within the `OPTIONAL`, so each mint is simply guarded by `BOUND(...)` and a book with no MARC match emits no dangling sub-resource node.

`reference-works.rq` mints parallel URIs for the reference track: each reference work is `…/reference/<canonicalKey>` (with `/publication`, `/identifier` sub-resources). The citations that link them live in the frozen `sources/citations.ttl`: each is `…/reference/<refKey>/citation/<bookKey>` — keyed by the (reference work, artists' book) pair, so multiple note paragraphs citing the same book from the same work collapse to one `ab:Citation`.

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

The graphs emit BIBFRAME directly (`bf:contribution`, `bf:provisionActivity`, `bf:identifiedBy`, etc.; the book title is a plain `rdfs:label`, not `bf:title` — #11) plus a growing `ab:` namespace: `ab:ArtistsBook`/`ab:itemKey`/`ab:heldBySloane` (artists-books.rq), `ab:ReferenceWork` (reference-works.rq), and `ab:Citation`, `ab:cites`, `ab:citedBy` plus the page-level `ab:onPageNumber`/`ab:imagesOnPageNumber` (#43/#44) — all now emitted in the frozen `sources/citations.ttl`. Still **not yet emitted**: the creator-role properties (`ab:bookArtist`, etc.). `docs/vocab.ttl` and `docs/description.ttl` were normalized off the legacy `ex:` (`http://example.org/`) placeholder prefix onto `ab:` in #115, so the vocabulary now names the terms the graphs actually emit; `ab:heldBySloane` is still missing from `docs/vocab.ttl`. `docs/description.ttl` is a hand-written worked example (Ed Ruscha's *Twentysix Gasoline Stations*) demonstrating the full intended shape.

### `sources/` directory

`sources/` holds the raw inputs, split by provenance: `sources/zotero/` (the Zotero export track), `sources/marc/` (the Z39.50 MARC-harvest track), and — at the `sources/` root — the committed graph inputs the construct queries read: the canonical `artists-books.csv` and `reference-works.csv` (the deduplicated lib 1 ∪ 2 ∪ 3 lists, issue #82) and the frozen `citations.ttl`. (The legacy lib-1 ↔ lib-3 `*-crosswalk.csv` bridge was removed once the canonical dedup subsumed it.) `sources/Makefile` regenerates these (run it as `make -C sources <target>`, with paths subdir-qualified — e.g. `make -C sources artists-books.csv` or `make -C sources marc/reference-works-marc.zip`).

`sources/zotero/zotero.sqlite` is the authoritative source. The `*_export.sh` scripts (in `sources/zotero/`) run `*_export.sql` against it to produce the CSVs the construct queries read; `notes_export.sh` emits `notes.xml`, and `sources/marc/marc_harvest.py` produces the `*-marc.xml` collections (with resumable state under `sources/marc/harvest/`, gitignored). The `tools/fuzzy-match/` matchers turn those into the `*-crosswalk.csv` files. The `-reconciled.csv` variants have been manually cleaned (e.g. mapped to Wikidata/ULAN IDs). See `sources/README.md` for the crosswalk pipeline (with `sources/zotero/README.md` for the Zotero database and citation data model, and `sources/marc/README.md` for the MARC harvest).
