# Overview

The `sources/` tree holds every raw input the pipeline transforms, split by
provenance:

- [`zotero/`](zotero/README.md) — the Zotero export track: `zotero.sqlite` (55MB
  SQLite database, Zotero's main metadata store) and its `storage/` attachments,
  the `*_export.{sh,sql}` scripts, and the CSVs / `notes.xml` they produce. Its
  README documents the database itself — the three-library structure, contents,
  tags, collections, fields, and the note export.
- [`marc/`](marc/README.md) — the Z39.50 MARC-harvest track: `marc_harvest.py`,
  the harvested `*-marc.zip` archives, the hand-supplied
  `reference-works-manual.xml`, and `reference-works-unresolved.csv`.
  Resumable harvest state lives under `marc/harvest/` (gitignored). Also
  `resolve_artstor.py`, which mines the harvested 856 links for the JSTOR
  crosswalk below, and `harvest_iiif.py`, which takes that crosswalk's SSIDs the
  rest of the way to IIIF image identifiers.
- root (this file) — the committed graph inputs the construct queries read: the
  canonical `artists-books.csv` and `reference-works.csv` (the deduplicated
  lib 1 ∪ 2 ∪ 3 lists) and the frozen `citations.ttl`, plus loose external
  reference data (the JSTOR collection dumps and `google_books_ids.csv`) and the
  regeneration `Makefile`.

## Canonical key scheme (issue #82, Phase 0)

> [!IMPORTANT]
> The three Zotero libraries are **frozen** (see
> [Three libraries in one database](zotero/README.md#three-libraries-in-one-database)).
> Under #82 the authoritative artists'-book set is **lib 1 ∪ lib 2 ∪ lib 3,
> deduplicated** — the same work catalogued once per library collapses to **one
> canonical node**. This section fixes the identity of that node. It is the
> first Phase-0 decision because everything downstream (the frozen
> `sources/citations.ttl`, the MARC harvest, every minted URI) hangs off it, and
> the frozen citations must point at keys that never move again.

**The canonical key is an existing Zotero item key — never a freshly minted
one — chosen per work by this precedence:**

| # | Prefer the key from… | Because | Applies to |
|---|---|---|---|
| 1 | **lib 3** (group 2352415, *ABCI*) | The newest, richest citation index, maintained latest, and the library the **`Cited:` notes live in**. Choosing it means citation edges anchor on lib-3 keys with **zero bridging** — this is what dissolves the crosswalk. | Any work present in lib 3 |
| 2 | **lib 2** (group 262987) | The older frozen index; use its key only for works that never migrated to lib 3 (no lib-3 successor). | Works in lib 2 but not lib 3 |
| 3 | **lib 1** (personal, user 5818691) | The Sloane physical holdings; use its key only for held works that were never indexed in either group library. | Works in lib 1 only (~290 of the 1,341 held books) |

The precedence is essentially **forced by the data**, not a free choice: lib 3
supersedes lib 2 (10,677 `owl:sameAs` links point lib-3 records back to lib-2
predecessors), and only ~290 held books exist in no group library at all.

**The non-canonical keys are kept as provenance, not discarded.** Each canonical
node records the source item(s) it was deduplicated from — the losing
lib-N keys — as `owl:sameAs` to their Zotero item URIs
(`http://zotero.org/groups/<gid>/items/<key>` or
`http://zotero.org/users/5818691/items/<key>`). The dedup step (Phase-0 task 2)
emits these alongside the canonical key.

**Held flag, not a separate graph.** UNC's physical holdings stay special only
because we have *images* of them. Membership in lib 1's `Artists' Books
Collection` (1,341) is recorded as a **property on the canonical node** (a held
flag), *not* as a distinct held-books graph.

### URI consequences

Minted URIs use the canonical key: `…/item/<canonicalKey>` for artists' books,
`…/reference/<canonicalKey>` for reference works (see CLAUDE.md "URI minting").

- **Reference works are unaffected.** The `Reference resources` collection (157)
  lives in **lib 3**, so `…/reference/<itemKey>` URIs already use lib-3 keys.
- **Artists'-book URIs migrate.** The site historically built from lib 1, so
  today's book URIs carry **lib-1** keys. Under lib-3-precedence the ~1,051 held
  books that also exist in a group library move to their **lib-3** (or lib-2)
  canonical key; only the ~290 held-only books keep a lib-1 key. This is an
  accepted one-time break — the whole point of #82 is to make every cited book a
  first-class node keyed the same way the citations already reference it.

**Ordering constraint:** mint canonical AB/RW identity (Phase-0 task 2)
**before** freezing `sources/citations.ttl` (task 3), or the citation edges point
at keys that later move.

### The dedup generator

`tools/fuzzy-match/dedup.py` mints that canonical identity. It is one-time
throwaway tooling (run once, review, commit; archived with the rest of
`tools/fuzzy-match/` after Phase 0) and reads `zotero/zotero.sqlite` **directly**
— no intermediate export CSVs, since the whole tool is about to be retired. It
clusters records into one node per work using signals in **descending order of
authority**, so a weaker signal never overrides a stronger one:

| # | Signal | Scope | Why it's trusted at this rank |
|---|---|---|---|
| 1 | `owl:sameAs` | all libs | Editorially asserted in Zotero; the dense lib 3 → lib 2 bridge (10,677 links) that supersession is built on. |
| 2 | ISBN (10/13 cross-checked) | all libs | A work-level identifier; near-zero false collisions. Catches duplicates `sameAs` missed — e.g. two lib-2 records of one work where only one carries the lib-3 link. |
| 3 | OCLC | all libs | Same, from the `extra` field. |
| 4 | title + author + **year** | all libs | The no-ISBN fallback. Year keeps distinct **editions** apart (the 1980–2016 editions of *A Humument*; Moeglin-Delcroix 1985 vs 2012) — they collapse only if #1–#3 link them. High-precision default for a frozen set, where a wrong merge is harder to undo than a missed one. |
| 5 | fuzzy title (rapidfuzz), author+year re-ranked | lib 1 → lib 2/3 only | Reused from `match.py`. Only lib-1 books with no exact twin reach here; every attach is written to the review CSV, low-confidence ones flagged `review=yes`, and the hand-owned decisions overlay can veto the merge (`no`/`unsure`). |

Signals 1–4 run globally over all three libraries (the fix that makes it a true
three-way dedup, not the old pairwise lib-1 → lib-3 bridge). Signal 5 exists only
because lib 1 carries almost no `sameAs` (just 7 of its 1,341 books).

**Outputs** (committed; the librarian reviews them before they seed the build):

- `artists-books.csv` — the authoritative artists'-book list (~7.9k canonical
  works), scoped to lib 1's *Artists' Books Collection* ∪ lib 2's *Master list* ∪
  lib 3's *Artists' books*/*ABCI*, **plus any lib-3 record carrying a `Cited:`
  note** (≈63 cited books sit in no collection, but every cited book must be a
  first-class node or its citation has nothing to attach to).
- `reference-works.csv` — the authoritative reference-work list (155 works),
  scoped to lib 3's *Reference resources* (157 records; 2 duplicate pairs
  collapse).
- `artists-books-dedup-review.csv` — the **generated** review surface: one row per
  **fuzzy** lib-1 attach (`lib1Key, twinKey, twinLib, method, confidence, review,
  lib1Title, twinTitle`), `review=yes` on the uncertain (< 0.93) ones. Rewritten
  on every dedup run, so it holds no human input.
- `artists-books-dedup-decisions.csv` — the **hand-owned** overlay recording the
  outcome of reviewing those attaches (`lib1Key, lib1Title, twinTitle, decision,
  notes`; `decision` ∈ `same` / `no` / `unsure`, blank = not yet reviewed). Keyed
  by `lib1Key`; the titles carry the match context. Edited by a person and **not**
  regenerated by make — same split as `construction/decisions.csv` and
  `subjects/decisions.csv` — so a dedup re-run never clobbers the decisions.
  `dedup.py` reads it back to **gate the fuzzy merge**: a lib-1 key marked `no`
  (distinct work) or `unsure` (unconfirmed) is left as its own canonical node
  rather than collapsing into its twin; `same` and unreviewed keys attach as
  before. This is the conservative default for a frozen set — a wrong merge is
  harder to undo than a missed one.

Both authoritative lists share the schema `canonicalKey, canonicalLib, held,
sourceKeys, <bibliographic fields…>`. `canonicalLib` is the library the chosen
key came from; `held` is `true` when any source record is a Sloane physical
holding (lib-1 *Artists' Books Collection* membership); `sourceKeys` lists every
deduplicated record as `libN:KEY` tokens (canonical first), preserving the lib-2/
lib-1 provenance the canonical key demotes to `sameAs`.

**Regenerate:**

```sh
make -C tools/fuzzy-match                 # build the rapidfuzz venv (one time)
make -C sources -B artists-books.csv      # -> artists-books.csv, reference-works.csv, review CSV
```

### Frozen citations (`citations.ttl`)

With canonical identity minted, the citation edges are frozen **once** into
`sources/citations.ttl` instead of recomputed every build — the corpus is dead,
so there is no living source to re-export, and emitting Turtle deletes a whole
construct stage (there is no `citations.rq`). `tools/fuzzy-match/freeze_citations.py`
reads the Zotero `Cited:` notes (`zotero/notes.xml`) and, for each citation
paragraph, resolves **both ends to their canonical URI**:

- the **citing reference work** — matched from the paragraph text by the verified
  substring / `<em>` / fuzzy matcher (`cite_match.py`, ported from #79) against
  `reference-works.csv`;
- the **cited artist's book** — the note's lib-3 itemKey mapped through
  `artists-books.csv`'s `sourceKeys` to the canonical node.

Page numbers come straight from the note markup (#43/#44): a page inside
`<strong>` is an image of the book (`ab:imagesOnPageNumber`), the rest are
passing mentions (`ab:onPageNumber`). Each citation is
`reference/<refKey>/citation/<bookKey>` with `ab:citedBy`, `ab:cites`, an
`rdfs:label` (the verbatim reference string), and its page triples — the same
shape the old construct query emitted, now against canonical keys and with pages.

Only confident, fully-resolved paragraphs are emitted; the uncertain (generic
short titles like *Artists books*), unmatched, and orphaned ones go to
`citations-review.csv` for a human to bless. Current: **5,022 citation edges**
linking **3,896 artists' books** to **54 reference works**; 117 held for review,
1 orphan (a work that is both a reference work and a cited book — it stays a
reference node). `citations.ttl` is committed and loaded into Fuseki alongside
the two constructed graphs (wired in task 4); `graph/` is build output only, so
the frozen graph lives here under `sources/`.

**Regenerate:**

```sh
make -C sources -B citations.ttl          # -> citations.ttl, citations-review.csv
```

## Artstor → JSTOR SSID crosswalk (`artstor-ssid.csv`, issue #9)

Cover images live in JSTOR Forum, whose "Export Records" spreadsheet
(`Jstor_Artists__book_records.csv`) is keyed by **SSID**. Our catalogue records
have no SSID: their MARC 856 `$u` links carry a *patron-side Artstor asset ID*
(`SS33469_33469_<n>`), a numbering JSTOR retired in 2024 and no longer exports.
That missing key is what blocked #9 — title matching is fuzzy and the export's
call number covers only ~60% of our records.

The old URLs still redirect, and the redirect target *is* the key:

```
https://library.artstor.org/public/SS33469_33469_42526770
  -> 301 https://www.jstor.org/stable/community.14183099
```

The number after `community.` is exactly the Forum SSID. `marc/resolve_artstor.py`
walks the MARC archive, fetches each asset ID's redirect (headers only — the
captcha is on the rendered JSTOR page, which is never requested), and writes one
row per 856 link: `canonicalKey, assetId, ssid, status`.

Current: **1,165 of 1,166 links resolved**, covering **1,145 books** and 1,127
distinct SSIDs; 1,156 of those SSIDs are present in the Forum export (the other
9 are presumably assets added to Forum after that export was taken). The single
failure is a cataloguing typo — `URPYB2MG`'s third 856 has a nine-digit asset ID
(`SS33469_33469_425301913`) that resolves to *artstor-page-not-found*; the same
record's other three links resolve, so no book loses coverage.

Two shapes to be aware of when consuming this file:

- **A book may have several assets** (cover, interior, multi-volume): 1,166 links
  over 1,145 books, so do not assume one row per book. (An earlier note here said
  to pick the asset whose Forum `Filename` ends in `1`/`001`; that rule does not
  hold — see `ssid-iiif.csv` below for what actually identifies the cover.)
- **33 SSIDs are shared by more than one canonical key.** Most are dedup misses
  from #82 — *Boundless* under three keys, *Money* under two — so this file
  doubles as a signal for that review. One (SSID 23249420) is shared by four
  records with genuinely different titles and needs a human look.

**Regenerate:**

```sh
make -C sources artstor-ssid.csv                                  # resumable; skips resolved
python3 marc/resolve_artstor.py --limit 250 --delay 1             # or chunk it, from sources/
```

## SSID → IIIF images (`ssid-iiif.csv`, issue #9)

The second half of the cover-image lookup: SSID → the IIIF identifiers of that
record's images. It is a real lookup, not string manipulation — the identifier is
a date-partitioned S3 path with a varying codec suffix, so nothing in it can be
derived from the SSID:

```
/iiif/2016/04/29/16/e31d56f8-4cf7-4053-a74b-033fcb088b79_deflate.tif
      └ upload time ┘ └────── media UUID ──────┘        └ codec ┘
```

> [!IMPORTANT]
> **Not harvested — `ssid-iiif.csv` is not in the tree, and a different route is
> probably needed.** The harvester and its make target are in place and correct,
> but a full attempt from a residential connection (2026-08-13) harvested **0 of
> 1,127 SSIDs**: every run was refused with a 403 at its *first* lookup.
>
> This is **not** a wait-and-retry situation. The block is on automation, not
> merely on the IP. While the script was being refused, a hand-driven browser on
> the same laptop and IP was succeeding; a headed real Chrome with a legitimate
> session, driven by a script, was refused at request #1 and then served a
> CAPTCHA. Solving that to unlock a bulk harvest would be circumvention, so the
> attempt was stopped. Repeated attempts also degrade the IP's standing to where
> ordinary browsing gets challenged.
>
> Because every run died at lookup 0, **`--delay` was never the operative
> variable and its sustainable value is still unmeasured** — raising it cannot
> help when request #1 is refused.
>
> The likeliest way forward is to **ask Artstor/JSTOR for SSID → media
> identifiers directly** rather than to harvest them; see `scratch/README.md`
> § "What the harvest attempt found" for the full sequence, the untested
> UUID-vs-`community.<SSID>` question, and the alternatives.

`marc/harvest_iiif.py` makes one request per distinct SSID in `artstor-ssid.csv`
(1,127 of them) to
`https://www.jstor.org/content-service/content-data/community.<SSID>`, and writes
one row per image: `ssid, pageIndex, iiifPath, pageCount, imageViewDescription,
status`. It is keyed on `ssid` alone — it joins back to books through
`artstor-ssid.csv`, so the canonical key is not duplicated into it.

```
ssid,pageIndex,iiifPath,pageCount,imageViewDescription,status
14183099,0,/iiif/2016/04/29/16/e31d56f8-…_deflate.tif,2,(Cover & interior images),ok
14183099,1,/iiif/2022/09/21/13/0f370719-…_deflate.tif,2,(Cover & interior images),ok
```

`iiifLinks` is ordered and `len(iiifLinks) == pageCount`, so `pageIndex` 0 is
page 1. But **page 1 is not always the cover**, and the file name does not say
which one is (`strip_tease_cover2.tif` and `presente_cover3.tif` are both
covers). `imageViewDescription` — the Forum *Image View Description* field — is
what carries that:

| `imageViewDescription`                          | cover is        |
| ----------------------------------------------- | --------------- |
| `(Cover & interior images)`                      | `pageIndex` 0   |
| `(Images of the enclosure, cover, & interior)`   | `pageIndex` 1 (page 1 is the slipcase) |
| `(Interior image)`, `(Open)`                     | no cover in this record |

It is recorded verbatim and deliberately not interpreted here: `ab:coverImage`
is not yet in `docs/vocab.ttl` and the no-cover fallback policy is undecided.

Once the identifiers are known the images need no crosswalk and no credentials —
`https://www.jstor.org{iiifPath}/info.json` and
`…/full/full/0/default.jpg` (or `…/full/,400/0/default.jpg`) are open Cantaloupe
IIIF Image API 2.1 level-2 endpoints that take **no headers at all** and are not
rate-limited. Masters are 2400px on the long edge. This tier was re-confirmed
healthy during the 2026-08-13 attempt (`info.json` → 200 + JSON, `full/,400/0/`
→ 200 `image/jpeg`) at the same moment the metadata API was refusing everything:
only step 1 is gated.

**The one-time harvest is the constrained part.** `/content-service/` is
rate-limited per IP, the penalty *escalates* when you keep requesting through a
block, and — per the attempt written up in `scratch/README.md` — it also refuses
scripted clients outright regardless of pacing. So `harvest_iiif.py`:

- defaults to `--delay 8` (~1,127 SSIDs ≈ 2.5 h) — an estimate of a sustainable
  rate, never a measured one, and **still unmeasured**: no run has yet completed
  a single lookup, so no value of `--delay` has been shown to work;
- **stops the entire run at the first 403** and exits cleanly rather than
  retrying, because retrying while blocked is what extends the block;
- rewrites the CSV after every record, so an interrupted run loses nothing;
- resumes by skipping SSIDs already recorded `ok`/`no-images`, and retries any
  other status. SSIDs not yet attempted have no rows at all.

Before harvesting from a new host, run `bash scratch/scripts/probe_egress.sh`
there: three requests, and it distinguishes a temporary rate limit (403 *JSTOR:
Access Check*) from a fatal IP-reputation block (200 + a Fastly *Client
Challenge* page).

But treat a passing probe as necessary, not sufficient: on 2026-08-13 the probe
returned 200 and the harvest was refused at lookup 0 seconds later, the probe's
own request apparently having consumed the allowance. A probe that passes and a
harvest that then fails at its first request is the *expected* shape of this
gate, not a new problem.

**Regenerate:**

```sh
make -C sources ssid-iiif.csv                                     # resumable; skips harvested
python3 marc/harvest_iiif.py --limit 100 --delay 8                # or chunk it, from sources/
```
