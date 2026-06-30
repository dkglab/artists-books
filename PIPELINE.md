# Build pipeline

The build runs as two parallel tracks — the **artists' books** and the **reference works** that cite them — that meet at the RDF graph stage and flow into a single static website. See [`README.md`](README.md) for prose and [`CLAUDE.md`](CLAUDE.md) for operational detail.

```mermaid
flowchart TD
    %% ---- Inputs ----
    zotero[("Zotero library<br/>(zotero.sqlite — 3 libraries)")]
    catalogs[("Library catalogs<br/>(Z39.50 / SRU — 9 servers)")]

    %% ---- Stage 1: source extraction ----
    zotero -->|"SQL export scripts"| csvs["artists-books.csv<br/>reference-resources.csv"]
    zotero -->|"notes_export.sh"| notes["notes.xml<br/>('Cited:' note paragraphs)"]
    notes -->|"fuzzy-match"| crosswalks["citation-crosswalk.csv<br/>abc-master-crosswalk.csv"]

    catalogs -->|"marc_harvest.py (YAZ)"| marc["artists-books-marc.xml"]
    catalogs -->|"marc_harvest.py (YAZ)"| refmarc["reference-resources-marc.xml *"]

    %% ---- Stage 2: CONSTRUCT queries (SPARQL-Anything) ----
    csvs --> abrq{{"artists-books.rq<br/>(SPARQL-Anything CONSTRUCT)"}}
    marc --> abrq
    csvs --> refrq{{"reference-resources.rq<br/>(SPARQL-Anything CONSTRUCT)"}}
    crosswalks --> refrq
    refmarc -.->|"harvested, not yet read *"| refrq

    abrq --> abttl["graph/artists-books.ttl"]
    refrq --> refttl["graph/reference-resources.ttl"]

    %% ---- Stage 3: graph store ----
    abttl --> fuseki[["Apache Fuseki<br/>(SPARQL endpoint)"]]
    refttl --> fuseki

    %% ---- Stage 4: site generation ----
    fuseki --> snowman{{"Snowman<br/>(SELECT queries + Go templates)"}}
    selects["queries/select/*.rq"] --> snowman
    templates["templates/*.html"] --> snowman

    %% ---- Output ----
    snowman --> site["Static HTML website<br/>(site/)"]

    %% ---- Clickable links to the README sections that document each stage ----
    click csvs "README.md#1-zotero--csv" "README §1: Zotero → CSV"
    click notes "README.md#1-zotero--csv" "README §1: Zotero → CSV"
    click crosswalks "README.md#1-zotero--csv" "README §1: Zotero → CSV"
    click marc "README.md#2-library-catalogs--marcxml" "README §2: Library catalogs → MARCXML"
    click refmarc "README.md#2-library-catalogs--marcxml" "README §2: Library catalogs → MARCXML"
    click abrq "README.md#3-csv--marcxml--rdf-graph" "README §3: CSV + MARCXML → RDF graph"
    click refrq "README.md#3-csv--marcxml--rdf-graph" "README §3: CSV + MARCXML → RDF graph"
    click abttl "README.md#3-csv--marcxml--rdf-graph" "README §3: CSV + MARCXML → RDF graph"
    click refttl "README.md#3-csv--marcxml--rdf-graph" "README §3: CSV + MARCXML → RDF graph"
    click fuseki "README.md#4-rdf-graph--website" "README §4: RDF graph → website"
    click snowman "README.md#4-rdf-graph--website" "README §4: RDF graph → website"
    click site "README.md#4-rdf-graph--website" "README §4: RDF graph → website"

    classDef input fill:#e8f0fe,stroke:#4285f4,stroke-width:2px;
    classDef output fill:#e6f4ea,stroke:#34a853,stroke-width:2px;
    class zotero,catalogs input;
    class site output;
```

`*` `reference-resources-marc.xml` is harvested but not yet consumed by a construct
query — the reference graph is currently built from the CSV plus the crosswalks
(tracked in #40 / #46 / #51).
