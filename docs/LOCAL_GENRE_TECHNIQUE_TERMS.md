# Local genre / technique terms

The genre/form (`655`) and topical (`650`) heading terms in
`sources/marc/artists-books-marc.xml` that come from **genuinely local vocabularies** —
i.e. schemes with no standard authority and **no `$0`/`$1` URIs**. These are the
candidate seed list for a locally minted `ab:` vocabulary. (Standard
vocabularies that merely lack URIs here — `fast.`, `aat.`, `lcgft.`, `rbmscv.` —
are *not* included; see `MARC-RECORDS.md` → "Local & un-reconciled headings".)

Two schemes, **15 distinct terms**, 148 occurrences total. None carry a URI.

- **`abo.org.`** — Artists' Books Online structural/narrative descriptors (4 terms)
- **`local.`** — UNC local genre/technique terms (11 terms)

`occ` = total occurrences; `recs` = distinct records; `tags` = which MARC field(s)
the term appears in (`655` genre/form, `650` topical). Trailing end-of-field
periods have been stripped from the display form.

## `abo.org.` — Artists' Books Online descriptors

| term | occ | recs | tags |
|------|----:|-----:|------|
| Photographic sequence | 44 | 44 | 655, 650 |
| Appropriated text | 43 | 43 | 655, 650 |
| Visual narrative | 25 | 25 | 655, 650 |
| Visiual narrative ⚠️ | 1 | 1 | 655 |

⚠️ **`Visiual narrative`** is a typo for **`Visual narrative`** — merge it
(would bring the canonical term to 26).

## `local.` — UNC local genre / technique terms

| term | occ | recs | tags |
|------|----:|-----:|------|
| Typographic art | 19 | 19 | 655, 650 |
| Asemic writing | 3 | 3 | 650 |
| Artists' books | 2 | 2 | 655 |
| Conceptual art | 2 | 2 | 655 |
| Graduated fore-edges | 2 | 2 | 655 |
| Sales catalogs | 2 | 2 | 650 |
| Altered books | 1 | 1 | 655 |
| Conceptual bookworks | 1 | 1 | 655 |
| Corrugated paperboard bindings | 1 | 1 | 655 |
| Offset printing | 1 | 1 | 650 |
| Stab binding | 1 | 1 | 655 |

## Grouped by what the term describes

**Genre / form — what the work is**
Artists' books · Conceptual art · Conceptual bookworks · Visual narrative ·
Photographic sequence · Appropriated text · Sales catalogs · Altered books ·
Asemic writing · Typographic art

**Technique / physical structure — how it's made**
Stab binding · Corrugated paperboard bindings · Graduated fore-edges ·
Offset printing

## Reconciliation notes

Several `local.` terms **duplicate concepts that already exist in standard
vocabularies** and are therefore reconciliation candidates rather than truly
novel terms — e.g. *Artists' books*, *Conceptual art*, *Sales catalogs*,
*Offset printing*, *Altered books*, *Stab binding*, and the various bindings
(cf. LCGFT, Getty AAT, RBMS controlled vocabularies, which appear elsewhere in
this data with `$0` links). Before minting local URIs for these, check whether
the linked twin already covers them.

The more genuinely artists'-book-specific, likely-novel terms are the `abo.org.`
set (*Photographic sequence*, *Appropriated text*, *Visual narrative*) plus
*Typographic art*, *Conceptual bookworks*, *Graduated fore-edges*, and
*Asemic writing* — these are the strongest candidates for a local `ab:`
vocabulary.
