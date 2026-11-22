# review-app

The shared dedup review page for #70, published as a claude.ai artifact
(https://claude.ai/artifact/YGmqzYCbnRdFeBqx5oYkbk). Reviewers decide both
queues on it at once, live:

- **Title matches**: the fuzzy lib-1 attaches in
  `sources/artists-books-dedup-review.csv` → `artists-books-dedup-decisions.csv`.
- **Shared OCLC numbers**: the groups in `sources/artists-books-oclc-review.csv`
  → `artists-books-oclc-decisions.csv`.

Each item shows both Zotero records, the MARC record(s), and links to the dev
site and the catalogues. Decisions live in the artifact's shared database
(`decisions` collection, one document per pair or group), not in the page.

- `build_data.py OUT`: builds `data.json` (gitignored) from the committed
  sources. Rebuild and republish it when the review CSVs change.
- `index.html`: the page.
- `pull_decisions.py DIR`: merges a saved copy of the `decisions` collection
  into the two CSVs, keeping their row order and line endings.
