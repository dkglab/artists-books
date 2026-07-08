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
    catalogs -->|"marc_harvest.py (YAZ)"| refmarc["reference-resources-marc.zip *"]

    %% ---- Stage 2: CONSTRUCT queries (SPARQL-Anything) ----
    csvs --> abrq{{"artists-books.rq<br/>(SPARQL-Anything CONSTRUCT)"}}
    marc --> abrq
    csvs --> refrq{{"reference-works.rq<br/>(SPARQL-Anything CONSTRUCT)"}}
    refmarc -->|"primary creator only *"| refrq

    abrq --> abttl["graph/artists-books.ttl"]
    refrq --> refttl["graph/reference-works.ttl"]

    %% ---- Stage 3: graph store ----
    abttl --> fuseki[["Apache Fuseki<br/>(SPARQL endpoint)"]]
    refttl --> fuseki
    citttl -->|"loaded as-is (no query)"| fuseki

    %% ---- Stage 4: site generation ----
    fuseki --> snowman{{"Snowman<br/>(SELECT queries + Go templates)"}}
    selects["web/queries/*.rq"] --> snowman
    templates["web/templates/*.html"] --> snowman

    %% ---- Output ----
    snowman --> site["Static HTML website (web/site/)<br/>book index + pages · reference index + pages<br/>cross-linked by citations"]

    classDef input fill:#e8f0fe,stroke:#4285f4,stroke-width:2px;
    classDef output fill:#e6f4ea,stroke:#34a853,stroke-width:2px;
    class zotero,catalogs input;
    class site output;
```

`*` `reference-resources-marc.zip` is harvested but only minimally consumed: the
construct query pulls just the primary creator (`100 $a`) from it, joined by
`999 $a`; the rest of the reference graph comes from the CSV, and the remaining
MARC fields (OCLC/WorldCat, secondary creators, …) are still pending.

The citation edges are **frozen**, not constructed (issue #82): `dedup.py` collapses
the three Zotero libraries into the canonical `artists-books.csv` /
`reference-works.csv` lists, and `freeze_citations.py` emits `sources/citations.ttl`
against the canonical URIs — both one-time Phase-0 steps, committed and loaded as-is.
The former live citation match (the `*-crosswalk.csv` fuzzy bridge feeding a
`reference-resources.rq` citation branch) has left the repeatable build.
