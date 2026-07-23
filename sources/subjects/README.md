# Subject-terms concept scheme

This folder builds `sources/subject-terms.ttl` — a local
[SKOS](https://www.w3.org/TR/skos-primer/) concept scheme of the **topical** and
**geographic** subject headings (MARC `650`/`651`) in the artists'-book records:
what each book is *about*. It is the exact parallel of the construction &
production methods scheme in `../construction/` (issue #86/#103), built by the
same three-role pipeline; issue #105 has the rationale.

The two schemes **partition** the heading space. `../construction/` mines the
genre/form (`655`), material (`340`), and non-plain topical (`650`) headings —
how a book is *made*. This folder mines the complement: plain topical `650` and
geographic `651` — what it is *about*. A heading that turns out to be a
construction method is simply marked `include=n` here (note `→ construction`).

## Why a concept scheme, instead of matching text

Same reason as construction (see `../construction/README.md`): the subject
headings come from many vocabularies — LCSH, FAST, MeSH, RVM, GND, local — and
the *same* concept appears in some records with a `$0` authority URI and in
others as a bare heading. The defining problem for subjects is that **many
headings carry no `$0` at all**, so we can't key on the URI alone. Instead we
build one concept per idea that records **all** of it:

- every **variant heading** seen in the MARC (`skos:altLabel`), plus a normalized
  `ab:matchKey` for each — this is how a bare heading with no `$0` still matches;
- every **authority URI** seen (`skos:exactMatch`), plus a manually-assigned one
  (the `exactMatch` decision column) for a concept whose records carried none;
- one **preferred label** and a **category** — `topical` or `geographic`
  (`skos:broader`), the two `skos:topConceptOf` the scheme.

A heading is the ordered subfields **`$a $x $y $z $v` joined with ` -- `** (e.g.
`Prisons -- Italy -- Livorno -- History`); the vocabulary comes from `$2`
(lower-cased) else the `650` second indicator; the authority URI from `$0`.

## The files

| file | what it is | who maintains it |
|------|------------|------------------|
| `candidates.csv` | every `650`/`651` heading mined from the MARC, aggregated one row per concept cluster — the raw list to review | generated (`make`) |
| `occurrences.csv` | the same headings un-aggregated: one row per (book, cluster, heading, authority) occurrence — the machine-side extract everything else joins against | generated (`make`) |
| `decisions.csv` | the curation: which headings are subjects, their label/category, and how variants group | **edited by hand** |
| `../subject-terms.ttl` | the finished SKOS scheme | generated (`make`) |

`mine-candidates.rq`, `mine-occurrences.rq` and `build-scheme.rq` are the SPARQL
queries that do the mining and the building.

`occurrences.csv` exists so the MARC archive is read **exactly once**. Joining
the tiny `decisions.csv` directly to the large MARC makes ARQ re-read the whole
archive once per decision row (a ~60x blow-up, confirmed with `--explain`);
extracting the occurrences to a flat CSV first turns every downstream step into a
cheap CSV-to-CSV join. (See `docs/QUERY-PERFORMANCE.md`.) Assembling the ordered
heading is the one place we walk Facade-X members with a variable predicate
(`?df ?p ?sf`) to recover subfield position, but the walk is anchored on an
already-bound, already-`650`/`651`-filtered datafield inside the per-record inner
graph, so it stays a few seconds.

## The pipeline

```
   MARC records
      │  ① make -C sources -B subjects/candidates.csv subjects/occurrences.csv
      ▼
   candidates.csv ──②  reviewed/edited by hand  ──▶  decisions.csv
   occurrences.csv ─────────────────────────────────────┐  │
                                                         │  │ ③ make -C sources subject-terms.ttl
                                                         ▼  ▼
                                                  ../subject-terms.ttl
```

### ① Mine the candidates (and occurrences)

```
make -C sources -B subjects/candidates.csv subjects/occurrences.csv
```

`candidates.csv` lists every `650`/`651` heading, one row per concept "cluster,"
sorted by how many records use it. `occurrences.csv` is the same pool
un-aggregated, one row per (book, heading) occurrence. The `-B` forces a rebuild
(run it after a MARC re-harvest to pick up new headings).

### ② Curate — edit `decisions.csv` by hand

Each row is one candidate cluster. The **`labels`** column (right after
`cluster`) is a read-only review aid — the raw heading text mined for that
cluster, copied from `candidates.csv` so a reviewer can tell what a bare cluster
URI/slug actually is without leaving the file. Don't edit it; it's ignored by the
build (`build-scheme.rq` reads columns by name and only touches `include=y`
rows). After a re-mine, re-copy the `labels` column across for any new/changed
clusters. Fill in the rest by hand:

- **include** — `y` if this heading is a subject; `n` otherwise (a construction
  method → note `→ construction`, or noise/duplicate).
- **conceptId** — a short slug naming the concept (e.g. `deserts`, `los-angeles`).
  **Give two rows the *same* conceptId to merge them into one concept** — this is
  how you fold a bare heading into its authority twin, or unify FAST / LCSH /
  local variants of one idea.
- **category** — `topical` (from `650`) or `geographic` (from `651`); the one
  axis not carried by a tag, so the site can group them. Auto-seeded from the tag.
- **prefLabel** — the preferred display label for the concept.
- **exactMatch** — an authority URI you hand-assign to a cluster that carried no
  `$0` in any record (the reconciliation work). Leave blank when the occurrences
  already supply one.
- **note** — free text; flag borderline calls, `→ construction`, etc.

Rows left `include=n` need no other columns.

> The committed `decisions.csv` is an **auto-seeded draft**: every row starts at
> `include=y` with a suggested `conceptId`/`prefLabel` and its `note` flags it for
> review (mirroring construction's draft pre-fill). Curation means flipping the
> non-subjects to `include=n`, merging twins by sharing a `conceptId`, and
> correcting the preferred labels.

### ③ Build the scheme

```
make -C sources subject-terms.ttl
```

Joins your `decisions.csv` to `occurrences.csv` and writes
`../subject-terms.ttl`: one `skos:Concept` per `conceptId`, carrying its
`skos:prefLabel`, every `skos:altLabel` variant, an `ab:matchKey` for each variant
(the lower-cased, punctuation-stripped matching form), and a `skos:exactMatch` to
every authority URI that heading was seen with (plus any manual `exactMatch`).
Two category concepts — `topical` and `geographic` — sit above them as
`skos:topConceptOf` the scheme.

## After a MARC re-harvest

Re-run ① to refresh `candidates.csv` and `occurrences.csv`, then `git diff`
`candidates.csv`: new headings show up as new rows. Add a decision for each new
row in `decisions.csv` (existing decisions carry forward untouched), re-copy the
`labels` column for new/changed clusters, then re-run ③. Only *new* headings ever
need a decision.

## Using the scheme in the site (#105)

Wired up, mirroring construction (#103): `queries/artists-books.rq` joins each
book's heading occurrences (`occurrences.csv`, keyed by canonical key) to
`decisions.csv` and emits `ab:hasSubject <concept>`; Fuseki loads
`../subject-terms.ttl` alongside the other graphs (`tools/fuseki/Makefile`); the
web query `web/queries/subjects.rq` resolves each concept's `rdfs:label` and
category, the per-book template renders a "Subjects" section, and there is a
`/subjects.html` index plus per-subject book-list pages
(`/subject/<conceptKey>/`). `ab:hasSubject` is documented in `docs/vocab.ttl`.

Note: with the current auto-seeded draft `decisions.csv` (every row `include=y`),
the index lists ~4,900 subjects — the seed already merges clusters that share an
identical `prefLabel`+`category` into one `conceptId` (so the FAST/LCSH/local
variants of e.g. *Toy and movable books* collapse). Curation — flipping
non-subjects to `include=n` and merging the remaining differently-spelled/worded
twins — brings that down to the real subject set.
