# Documentation

Supplementary documentation for the artists' books project. For the project
overview and pipeline diagram see the top-level [`README.md`](../README.md);
for operational and architecture detail see [`CLAUDE.md`](../CLAUDE.md).

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
  `queries/construct/` SPARQL-Anything step fast (avoiding the variable-predicate
  blowup when walking Facade-X containers).
