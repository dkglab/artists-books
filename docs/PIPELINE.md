# Build pipeline

The build runs as two parallel tracks — the **artists' books** and the **reference works** that cite them — that meet at the RDF graph stage and flow into a single static website. See [`README.md`](../README.md) for prose and [`CLAUDE.md`](../CLAUDE.md) for operational detail.

```mermaid
flowchart TD
    %% ---- Inputs ----
    zotero[("Zotero library<br/>(zotero.sqlite — 3 libraries)")]
    catalogs[("Library catalogs<br/>(Z39.50 / SRU — 9 servers)")]

    %% ---- Stage 1: source extraction ----
    zotero -->|"SQL export scripts"| csvs["artists-books.csv<br/>reference-resources.csv"]
    zotero -->|"notes_export.sh"| notes["notes.zip<br/>('Cited:' note HTML, one file per note)"]
    csvs -->|"fuzzy-match (match.py)"| crosswalk["abc-master-crosswalk.csv"]

    catalogs -->|"marc_harvest.py (YAZ)"| marc["artists-books-marc.xml"]
    catalogs -->|"marc_harvest.py (YAZ)"| refmarc["reference-resources-marc.xml *"]

    %% ---- Stage 2: CONSTRUCT queries (SPARQL-Anything) ----
    csvs --> abrq{{"artists-books.rq<br/>(SPARQL-Anything CONSTRUCT)"}}
    marc --> abrq
    csvs --> refrq{{"reference-resources.rq<br/>(SPARQL-Anything CONSTRUCT)"}}
    crosswalk --> refrq
    notes -->|"citation match in SPARQL"| refrq
    refmarc -->|"primary creator only *"| refrq

    abrq --> abttl["graph/artists-books.ttl"]
    refrq --> refttl["graph/reference-resources.ttl"]

    %% ---- Stage 3: graph store ----
    abttl --> fuseki[["Apache Fuseki<br/>(SPARQL endpoint)"]]
    refttl --> fuseki

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

`*` `reference-resources-marc.xml` is harvested but only minimally consumed: the
construct query pulls just the primary creator (`100 $a`) from it, joined by
`999 $a`; the rest of the reference graph comes from the CSV plus the crosswalks,
and the remaining MARC fields (OCLC/WorldCat, secondary creators, …) are still
pending.
