# review-app

The shared dedup review page for #214 (which replaced #70), published as a claude.ai artifact
(https://claude.ai/artifact/YGmqzYCbnRdFeBqx5oYkbk). Reviewers decide both
queues on it at once, live:

- **Title matches**: the fuzzy lib-1 attaches in
  `sources/artists-books-dedup-review.csv` → `artists-books-dedup-decisions.csv`.
- **Shared OCLC or record**: the groups in `sources/artists-books-oclc-review.csv`
  (books sharing an OCLC number, or matched to one catalogue's own record, #222)
  → `artists-books-oclc-decisions.csv`.
- **In both lists** (#113): an artists' book beside a reference work that may be
  the same work, from `sources/cross-track-review.csv` →
  `cross-track-decisions.csv` (`both`, `reference`, `no` or `unsure`).

Each item shows both Zotero records, the MARC record(s), and links to the dev
site and the catalogues. When one of its books is also in another pair or
group (two cross-track pairs that share a book, or a pair whose books share an
OCLC number), the item lists those too, so their decisions can be made together. Decisions live in the artifact's shared database
(`decisions` collection, one document per pair or group), not in the page.

- `build_data.py OUT`: builds `data.json` (gitignored) from the committed
  sources. Rebuild and republish it when the review CSVs change.
- `index.html`: the page.
- `pull_decisions.py DIR`: merges a saved copy of the `decisions` collection
  into the three CSVs, keeping their row order and line endings.
