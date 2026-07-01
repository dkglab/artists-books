# Documentation

Supplementary documentation for the artists' books project. For the project
overview and pipeline diagram see the top-level [`README.md`](../README.md);
for operational and architecture detail see [`CLAUDE.md`](../CLAUDE.md).

## Guides & analyses

- [`PIPELINE.md`](PIPELINE.md) — the build pipeline: the two parallel tracks
  (artists' books and reference works) rendered as a Mermaid diagram, each
  stage linked back to the README.
- [`MARC-RECORDS.md`](MARC-RECORDS.md) — a full analysis of the harvested MARC
  records (`Zotero/artists-books-marc.xml`): fields carried, creator names and
  roles, real-world-object and name-authority URIs, and data-quality notes.
- [`LOCAL_GENRE_TECHNIQUE_TERMS.md`](LOCAL_GENRE_TECHNIQUE_TERMS.md) — the local
  and un-reconciled genre/form (`655`) and topical (`650`) heading terms found
  in the MARC records.
- [`QUERY-PERFORMANCE.md`](QUERY-PERFORMANCE.md) — notes on keeping the
  `queries/` SPARQL-Anything step fast (avoiding the variable-predicate
  blowup when walking Facade-X containers).

## Vocabulary & modeling examples

These are documentation-by-example, not build inputs (the pipeline emits its own
graphs under `graph/`). `make validate` runs Jena's validator over the two `.ttl`
files.

- [`vocab.ttl`](vocab.ttl) — the custom `ab:` vocabulary layered on BIBFRAME and
  schema.org (the citation class/properties, creator-role properties, etc.).
- [`description.ttl`](description.ttl) — a hand-written worked example (Ed Ruscha's
  *Twentysix Gasoline Stations*) demonstrating the full intended graph shape.
- [`website_sources_of_info.xlsx`](website_sources_of_info.xlsx) — spreadsheet of
  the source-of-information notes gathered while designing the website.

## Design mockups

Design-phase artifacts for the website, kept for reference.

- [`website-mockup-jpegs/`](website-mockup-jpegs/) — four-page JPEG mockup of the
  intended website layout, plus [`where_info_comes_from.md`](website-mockup-jpegs/where_info_comes_from.md),
  a Mermaid diagram tracing each page field back to its source (MARC field,
  Zotero CSV, JSTOR, etc.).
