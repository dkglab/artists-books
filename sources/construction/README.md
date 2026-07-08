# Construction & production methods concept scheme

This folder builds `sources/construction-methods.ttl` — a local
[SKOS](https://www.w3.org/TR/skos-primer/) concept scheme of the construction
techniques, materials, binding/format types, and printing methods named in the
artists'-book MARC records. The per-book construct query uses it to attach an
`ab:constructedUsing` link to each book (that wiring is a separate, still-to-do
step; see the note at the bottom).

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

## The three files

| file | what it is | who maintains it |
|------|------------|------------------|
| `candidates.csv` | every candidate heading mined from the MARC — the raw list to review | generated (`make`) |
| `decisions.csv` | the curation: which headings are construction/production methods, their label, and how variants group | **edited by hand** |
| `../construction-methods.ttl` | the finished SKOS scheme | generated (`make`) |

`mine-candidates.rq` and `build-scheme.rq` are the two SPARQL queries that do
the mining and the building.

## The pipeline

```
   MARC records
      │  ① make -C sources -B construction/candidates.csv
      ▼
   candidates.csv  ──②  reviewed/edited by hand  ──▶  decisions.csv
                                                          │  ③ make -C sources construction-methods.ttl
                                                          ▼
                                                  ../construction-methods.ttl
```

### ① Mine the candidates

```
make -C sources -B construction/candidates.csv
```

Reads the MARC and lists every heading in the candidate pool — `655`
(genre/form), `340` material headings, and `650` (topical) minus the plain
FAST/LCSH subject headings — one row per concept "cluster," sorted by how many
records use it. The `-B` forces a rebuild (you'll run this after a MARC
re-harvest to pick up new headings).

### ② Curate — edit `decisions.csv` by hand

Each row is one candidate cluster. Fill in these columns:

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

Joins your `decisions.csv` back to the MARC and writes
`../construction-methods.ttl`: one `skos:Concept` per `conceptId`, carrying its
`skos:prefLabel`, every `skos:altLabel` variant, an `ab:matchKey` for each
variant (a lower-cased, punctuation-stripped form used for matching), and a
`skos:exactMatch` to every authority URI that heading was seen with. Four
category concepts sit above them as `skos:topConceptOf` the scheme.

## After a MARC re-harvest

Re-run ① to refresh `candidates.csv`, then `git diff` it: new headings show up
as new rows. Add a decision for each new row in `decisions.csv` (existing
decisions carry forward untouched), then re-run ③. Label variants and URIs for
concepts you've already included refresh automatically — you only ever decide
*new* headings.

## Still to do: use the scheme in the site

Building the scheme does **not** yet change the website. Making the per-book
page show a "Construction techniques, materials, and production methods" section
still needs the construct query and the web query/template updated to read this
scheme. See the pull-request discussion for what those edits are.
