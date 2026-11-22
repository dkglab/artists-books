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
- **`oclc_review.py`** + **`oclc-groups.rq`** build
  `sources/artists-books-oclc-review.csv` (#70): groups of book nodes that may
  be one work, with Zotero and MARC context for review. A group is either books
  that share an OCLC number in the built graph, or (#222) books whose MARC is
  the same catalogue record, by harvest server and `001`, where that `001` is
  the catalogue's own id rather than an OCLC number (group id
  `rec.<server>.<001>`). They use only the standard library and Jena's `arq`,
  not the venv.
- **`marc_oclc.py`** is the Python copy of the construct queries' OCLC rule
  (#222): the `001` is an OCLC number only with an `on`/`ocn`/`ocm` prefix or
  an `OCoLC` `003`, else the first `035 $a (OCoLC)…`, at most 10 digits.
  `oclc_review.py` uses it to name a record group and link its record. If you
  change the rule, change `queries/artists-books.rq`,
  `queries/reference-works.rq` and this file together.

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
make -C sources -B artists-books-oclc-review.csv   # shared-OCLC/record review sheet (needs graph/artists-books.ttl)
```

Each script prints a coverage/summary report to stderr.
