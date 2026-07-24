# Construction & production methods concept scheme

This folder builds `sources/construction-methods.ttl` — a local
[SKOS](https://www.w3.org/TR/skos-primer/) concept scheme of the construction
techniques, materials, binding/format types, and printing methods named in the
artists'-book MARC records. The per-book construct query (`queries/artists-
books.rq`) attaches an `ab:constructedUsing` link from each book to the concepts
its headings map to; the per-book site page renders them (see "Using the scheme
in the site" at the bottom).

## Why a concept scheme, instead of matching text

The construction-relevant headings in the MARC come from many vocabularies —
Getty AAT, the RBMS controlled vocabularies, RDA materials, LC genre/form
(LCGFT), FAST — plus a handful of purely local (`local.`/`abo.org.`) headings.
Most of the reconciled ones already carry an authority URI in subfield `$0`, but
**inconsistently**: the same concept (e.g. *Corrugated board bindings*) appears
in some records with a `$0` and in others as a bare heading, and the local
headings never have one.

So we can't key construction terms on the `$0` URI alone (we'd drop every
bare-heading occurrence), and we don't want to guess by fuzzily matching label
text. Instead we build one concept per idea that records **all** of it:

- every **variant label** seen in the MARC (`skos:altLabel`), plus a normalized
  `ab:matchKey` for each — this is how a record with no `$0` still matches;
- every **authority URI** seen (`skos:exactMatch`) — this matches records that
  *do* carry a `$0`, and future records whose label we haven't seen before;
- one **preferred label** and a **category** (`skos:broader`).

Variant headings that mean the same thing — across vocabularies — collapse into
a single concept. That reconciliation is exactly the point.

## The files

| file | what it is | who maintains it |
|------|------------|------------------|
| `candidates.csv` | every candidate heading mined from the MARC, aggregated one row per concept cluster — the raw list to review | generated (`make`) |
| `occurrences.csv` | the same headings un-aggregated: one row per (book, cluster, label, authority) occurrence — the machine-side extract everything else joins against | generated (`make`) |
| `decisions.csv` | the curation: which headings are construction/production methods, their label, and how variants group | **edited by hand** |
| `../construction-methods.ttl` | the finished SKOS scheme | generated (`make`) |

`mine-candidates.rq`, `mine-occurrences.rq` and `build-scheme.rq` are the SPARQL
queries that do the mining and the building.

`occurrences.csv` exists so the MARC archive is read **exactly once**. Joining
the tiny `decisions.csv` directly to the large MARC makes ARQ re-read the whole
archive once per decision row (a ~60x blow-up, confirmed with `--explain`);
extracting the occurrences to a flat CSV first turns every downstream step —
`build-scheme.rq` and the `ab:constructedUsing` join in
`queries/artists-books.rq` — into a cheap CSV-to-CSV join.

## The pipeline

```
   MARC records
      │  ① make -C sources -B construction/candidates.csv construction/occurrences.csv
      ▼
   candidates.csv ──②  reviewed/edited by hand  ──▶  decisions.csv
   occurrences.csv ─────────────────────────────────────┐  │
                                                         │  │ ③ make -C sources construction-methods.ttl
                                                         ▼  ▼
                                                  ../construction-methods.ttl
```

### ① Mine the candidates (and occurrences)

```
make -C sources -B construction/candidates.csv construction/occurrences.csv
```

`candidates.csv` reads the MARC and lists every heading in the candidate pool —
`655` (genre/form), `340` material headings, and `650` (topical) minus the plain
FAST/LCSH subject headings — one row per concept "cluster," sorted by how many
records use it. `occurrences.csv` is the same pool un-aggregated, one row per
(book, heading) occurrence. The `-B` forces a rebuild (you'll run this after a
MARC re-harvest to pick up new headings).

### ② Curate — edit `decisions.csv` by hand

Each row is one candidate cluster. The **`labels`** column (right after
`cluster`) is a read-only review aid — the raw `$a` heading text mined for that
cluster, copied over from `candidates.csv` so a reviewer can tell what a bare
cluster URI/slug actually is without leaving the file. Don't edit it; it's
ignored by the build (`build-scheme.rq` reads columns by name and only touches
`include=y` rows). It mirrors `candidates.csv`; after a re-mine, re-copy the
`labels` column across for any new/changed clusters. Fill in the rest by hand:

- **include** — `y` if this heading is a construction/production method, `n`
  otherwise (subject matter, literary genre, document type, etc.).
- **conceptId** — a short slug naming the concept (e.g. `accordion-fold`).
  **Give two rows the *same* conceptId to merge them into one concept** — this
  is how you fold a local heading into its authority twin, or unify the same
  idea across AAT/RBMS/LCGFT.
- **category** — one of `material`, `technique`, `binding-format`,
  `production-printing`.
- **prefLabel** — the preferred display label for the concept.
- **note** — free text; used to flag borderline calls for review.

Rows left `include=n` need no other columns. You don't need to touch the label
variants or URIs — those are gathered automatically from the MARC in step ③.

### ③ Build the scheme

```
make -C sources construction-methods.ttl
```

Joins your `decisions.csv` to `occurrences.csv` and writes
`../construction-methods.ttl`: one `skos:Concept` per `conceptId`, carrying its
`skos:prefLabel`, every `skos:altLabel` variant, an `ab:matchKey` for each
variant (a lower-cased, punctuation-stripped form used for matching), and a
`skos:exactMatch` to every authority URI that heading was seen with. Four
category concepts sit above them as `skos:topConceptOf` the scheme.

## After a MARC re-harvest

Re-run ① to refresh `candidates.csv` and `occurrences.csv`, then `git diff`
`candidates.csv`: new headings show up as new rows. Add a decision for each new
row in `decisions.csv` (existing decisions carry forward untouched), then re-run
③. Label variants and URIs for concepts you've already included refresh
automatically — you only ever decide *new* headings.

## Using the scheme in the site

`queries/artists-books.rq` joins each book's heading occurrences
(`occurrences.csv`, keyed by canonical key) to `decisions.csv` on the cluster
key and emits `ab:constructedUsing <concept>` for every included cluster —
minting the same `ab:construction/<conceptId>` URIs this scheme defines. Fuseki
loads `../construction-methods.ttl` alongside the constructed graph, so the web
query (`web/queries/artists-books.rq`) resolves each linked concept's
`rdfs:label` and the per-book template renders a "Construction Techniques,
Materials, and Production Methods" section.
