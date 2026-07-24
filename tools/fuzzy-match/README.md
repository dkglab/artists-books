# fuzzy-match

Bibliographic reconciliation tooling for the Phase-0 dedup (issue #82) and the
frozen citation graph.

- **`dedup.py`** collapses the same work catalogued across the three Zotero
  libraries (lib 1 ∪ 2 ∪ 3) into one **canonical node**, reading `zotero.sqlite`
  directly and emitting `sources/artists-books.csv`,
  `sources/reference-works.csv`, and `sources/artists-books-dedup-review.csv`.
- **`match.py`** is the matching library `dedup.py` imports — OCLC / ISBN
  expansion, accent-folded title/author normalizers, a year extractor, and an
  author+year agreement score.
- **`cite_match.py`** is the reference-work matcher `freeze_citations.py` imports:
  `match_all()` reconciles each "Cited:" note paragraph to a canonical reference
  work (verbatim-title substring → `<em>`-exact → fuzzy).
- **`freeze_citations.py`** builds the frozen `sources/citations.ttl` — one
  `ab:Citation` per (reference work, artist's book) against the canonical URIs.

Fuzzy matching uses [`rapidfuzz`](https://pypi.org/project/rapidfuzz/), installed
into an isolated venv here. Everything except this
README, `Makefile`, the `*.py` scripts, and `requirements.txt` is generated and
gitignored.

> The earlier standalone ABC ↔ cited-record and citation ↔ reference-resource
> **crosswalk builders** (issues #55/#42) were retired under #82: the canonical
> dedup subsumes the ABC bridge, and citations are frozen once by
> `freeze_citations.py`. `match.py`/`cite_match.py` survive only as the matching
> libraries those two live tools import.

## Use

```sh
make -C tools/fuzzy-match                 # build the venv (one time)
make -C sources artists-books.csv         # run the dedup (also emits reference-works.csv + review)
make -C sources -B citations.ttl          # freeze the citation graph
```

Each script prints a coverage/summary report to stderr.
