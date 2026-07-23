# Build pipeline

The build runs as two parallel tracks — the **artists' books** and the **reference works** that cite them — that meet at the RDF graph stage and flow into a single static website. See [`README.md`](../README.md) for prose and [`CLAUDE.md`](../CLAUDE.md) for operational detail.

```mermaid
flowchart TD
    %% ---- Inputs ----
    zotero[("Zotero library<br/>(zotero.sqlite — 3 libraries)")]
    catalogs[("Library catalogs<br/>(Z39.50 / SRU — 9 servers)")]

    %% ---- Stage 1: source extraction + one-time Phase-0 freeze (issue #82) ----
    zotero -->|"dedup.py (lib 1 ∪ 2 ∪ 3)"| csvs["artists-books.csv<br/>reference-works.csv<br/>(canonical lists)"]
    zotero -->|"notes_export.sh"| notes["notes.xml<br/>('Cited:' note paragraphs)"]
    notes -->|"freeze_citations.py (one-time)"| citttl["sources/citations.ttl<br/>(frozen citation edges)"]

    catalogs -->|"marc_harvest.py (YAZ)"| marc["artists-books-marc.zip<br/>(per-record MARC archive)"]
    catalogs -->|"marc_harvest.py (YAZ)"| refmarc["reference-works-marc.zip *"]

    %% ---- Construction-methods SKOS vocabulary (mined from the book MARC) ----
    marc -->|"mine-occurrences.rq"| cocc["construction/occurrences.csv<br/>(one row per book heading)"]
    cocc --> cbuild{{"build-scheme.rq"}}
    cdec["construction/decisions.csv<br/>(hand-curated: include? / concept / category)"] --> cbuild
    cbuild --> cmttl["sources/construction-methods.ttl<br/>(SKOS concept scheme)"]

    %% ---- Stage 2: CONSTRUCT queries (SPARQL-Anything) ----
    csvs --> abrq{{"artists-books.rq<br/>(SPARQL-Anything CONSTRUCT)"}}
    marc --> abrq
    cocc -->|"ab:constructedUsing join"| abrq
    cdec --> abrq
    csvs --> refrq{{"reference-works.rq<br/>(SPARQL-Anything CONSTRUCT)"}}
    refmarc -->|"primary creator only *"| refrq

    abrq --> abttl["graph/artists-books.ttl"]
    refrq --> refttl["graph/reference-works.ttl"]

    %% ---- Stage 3: graph store ----
    abttl --> fuseki[["Apache Fuseki<br/>(SPARQL endpoint)"]]
    refttl --> fuseki
    citttl -->|"loaded as-is (no query)"| fuseki
    cmttl -->|"loaded as-is (no query)"| fuseki

    %% ---- Stage 4: site generation ----
    fuseki --> snowman{{"Snowman<br/>(SELECT queries + Go templates)"}}
    selects["web/queries/*.rq"] --> snowman
    templates["web/templates/*.html"] --> snowman

    %% ---- Output ----
    snowman --> site["Static HTML website (web/site/)<br/>book index + pages · reference index + pages<br/>cross-linked by citations"]

    classDef input fill:#e8f0fe,stroke:#4285f4,stroke-width:2px;
    classDef output fill:#e6f4ea,stroke:#34a853,stroke-width:2px;
    class zotero,catalogs,cdec input;
    class site output;
```

`*` `reference-works-marc.zip` is harvested but only minimally consumed: the
construct query pulls just the primary creator (`100 $a`) from it, joined by
`999 $a`; the rest of the reference graph comes from the CSV, and the remaining
MARC fields (OCLC/WorldCat, secondary creators, …) are still pending.

The citation edges are **frozen**, not constructed (issue #82): `dedup.py` collapses
the three Zotero libraries into the canonical `artists-books.csv` /
`reference-works.csv` lists, and `freeze_citations.py` emits `sources/citations.ttl`
against the canonical URIs — both one-time Phase-0 steps, committed and loaded as-is.
The former live citation match (the `*-crosswalk.csv` fuzzy bridge feeding a
`reference-resources.rq` citation branch) has been removed from the repo.

The **construction-methods** track is an enrichment of the book graph, mined
from the same book MARC. `mine-occurrences.rq` extracts every genre/technique/
material heading to `construction/occurrences.csv` (one row per book heading — a
single pass over the archive, so every downstream step is a cheap CSV-to-CSV
join); `construction/decisions.csv` is the hand-curated call for each heading
cluster (include? / concept id / category). `build-scheme.rq` joins the two into
the `sources/construction-methods.ttl` SKOS scheme, and `artists-books.rq` joins
the same two to attach an `ab:constructedUsing` link from each book to the
concepts its headings map to. Fuseki loads the scheme as-is alongside the
constructed graphs, so the site can resolve each linked concept's label. See
[`sources/construction/README.md`](../sources/construction/README.md) for the
mine → curate → build pipeline.
