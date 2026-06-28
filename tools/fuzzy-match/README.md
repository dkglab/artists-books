# fuzzy-match

Reconciliation tooling for the **ABC ↔ cited-record crosswalk** (issue #55).

`match.py` matches each book in the personal-library *Artists' Books Collection*
(ABC, lib 1 — what the website builds from) to the lib-3 citation-index
record(s) describing the same work, so the "Cited:" notes that live on those
records can be joined onto ABC pages. It tries, in precedence order, **OCLC →
ISBN → exact normalized title → fuzzy author+title+year** and writes
`Zotero/abc-master-crosswalk.csv`.

Fuzzy matching uses [`rapidfuzz`](https://pypi.org/project/rapidfuzz/), installed
into an isolated venv here (mirrors `tools/rdflib`). Everything except this
README, `Makefile`, `match.py`, and `requirements.txt` is generated and
gitignored.

## Use

```sh
make -C tools/fuzzy-match            # build the venv (one time)
make -C Zotero abc-master-crosswalk.csv   # build cited-records.csv + the crosswalk
```

Or run the matcher directly:

```sh
tools/fuzzy-match/venv/bin/python tools/fuzzy-match/match.py \
    --abc   Zotero/artists-books.csv \
    --marc  Zotero/artists-books-marc.xml \
    --cited Zotero/cited-records.csv \
    --out   Zotero/abc-master-crosswalk.csv
```

A coverage summary (matches by method) is printed to stderr.
