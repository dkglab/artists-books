# MARC records overview — `Zotero/artists-books-marc.xml`

An analysis of the full MARC records harvested from UNC's catalog (see
`Zotero/marc_harvest.py`), written with an eye toward turning them into linked
data. **1340 records**, one per artists'-book item that has a UNC bib number.

## The file at a glance

- A single MARCXML `<collection xmlns="http://www.loc.gov/MARC21/slim">` with
  1340 `<record>` children. Well-formed; UTF-8 (`leader/09 = a`).
- Each record carries a synthetic **`999 $a <itemKey> $b <bibnum>`** stamped by
  the harvester — this is the join key back to the Zotero items / the
  `item/<itemKey>` URIs. (`999 $a SY5RIFMP $b b11859007`)
- Records are real OCLC/cataloging records: `001` is the **OCLC number**, `003`
  is `OCoLC`. The UNC bib number is *not* otherwise present — hence the `999`.

## Querying it

Tools installed: `xmlstarlet`, `xmllint`. Everything is namespaced, so register
the MARC slim namespace:

```sh
NS=http://www.loc.gov/MARC21/slim

# count records
xmlstarlet sel -N m=$NS -t -v "count(//m:record)" Zotero/artists-books-marc.xml

# dump one field's subfields ($code=value)
xmlstarlet sel -N m=$NS -t \
  -m "(//m:datafield[@tag='650'])[1]/m:subfield" \
  -o "  \$" -v @code -o "=" -v . -n Zotero/artists-books-marc.xml

# pretty-print / validate
xmllint --format Zotero/artists-books-marc.xml | less
```

For aggregation, Python's `xml.etree.ElementTree` over the same file is often
easier than chained XPath.

## Tag usage distribution

Across 1340 records. **occ** = total occurrences, **recs%** = share of records
with the tag at least once. (Long tail of <1% tags omitted; see the file.)

| tag | occ | recs% | what |
|-----|----:|------:|------|
| **Control** | | | |
| 001 | 1340 | 100% | OCLC control number |
| 003 | 979 | 73% | control-number source (`OCoLC`) |
| 005 | 1338 | 100% | latest transaction timestamp |
| 008 | 1340 | 100% | fixed-length data (date, place, language…) |
| 006/007 | 13/14 | 1% | additional material / physical description |
| **Numbers & codes** | | | |
| 010 | 123 | 9% | LCCN |
| 019 | 411 | 31% | superseded OCLC numbers |
| 020 | 1038 | 44% | ISBN |
| 035 | 1083 | 81% | system control number `(OCoLC)…` |
| 040 | 1340 | 100% | cataloging source |
| 041 | 177 | 13% | language code (multilingual works) |
| 042 | 149 | 11% | authentication (`pcc`) |
| 043 | 542 | 40% | geographic area code |
| 049/050 | 881/847 | 66%/56% | local holdings code / **LC call no.** |
| 082 | 149 | 11% | Dewey number |
| **Title & edition** | | | |
| 245 | 1340 | 100% | title statement |
| 246 | 395 | 23% | variant title |
| 250 | 233 | 17% | edition statement |
| 264 | 1763 | 100% | production/publication/copyright |
| **Physical / RDA** | | | |
| 300 | 1341 | 100% | physical description |
| 336/337/338 | ~1.3k each | 100% | RDA content/media/carrier type |
| 340 | 1349 | 90% | physical medium (RDA) |
| 490/830 | 171/157 | 13%/11% | series statement / series added entry |
| **Creators** (see below) | | | |
| 100 | 1256 | 94% | main creator |
| 700 | 820 | 35% | added personal creator |
| 710 | 673 | 43% | added corporate creator |
| 110/711 | 10/10 | 1% | main corporate / meeting |
| **Subjects & genre** (see below) | | | |
| 650 | 5267 | 82% | topical subject |
| 651 | 743 | 32% | geographic subject |
| 600/610/630 | 1248/72/33 | 47%/3%/1% | personal/corporate/title subject |
| 647/648 | 39/259 | 2%/11% | named event / chronological |
| 655 | 5191 | 99% | **genre/form** (heavily used) |
| **Notes** (see below) | | | |
| 500 | 3145 | 92% | general note |
| 520 | 195 | 14% | summary/abstract |
| 546/505/504 | 132/85/63 | 10%/6%/5% | language / contents / bibliography |
| 563/590 | 25/32 | 2% | binding / local note |
| **Linking** | | | |
| 856 | 1169 | 86% | **electronic location (ArtStor)** |
| 880 | 87 | 2% | vernacular / alternate-script |
| **Local (Innopac/UNC, 9xx)** | | | |
| 915 | 3982 | 100% | local processing note (MARS/authority control) |
| 949 | 541 | 39% | local item / call no. / barcode |
| 994/998 | 538/1339 | 40%/100% | local system fields |
| 791/690/090 | 259/63/87 | local added entries / subjects / call no. |
| **999** | 1340 | 100% | **injected: `$a` itemKey, `$b` bibnum** |

## Linked-data assets — the headline

**Every record (1340/1340) contains URLs.** They cluster in three roles:

| subfield | role | count | example |
|----------|------|------:|---------|
| `$0` | authority record URI | 19,583 | `http://id.loc.gov/authorities/names/no2017165764` |
| `$1` | real-world-object URI | 5,393 | `http://viaf.org/viaf/15151431616256302424` |
| `$u` | web resource | 1,169 | `https://library.artstor.org/asset/SS33469_33469_42525467` |

URIs by domain (occurrences):

| count | domain | what |
|------:|--------|------|
| 7640 | id.loc.gov | LC subjects, names, genre forms, classification |
| 5804 | id.worldcat.org | FAST headings |
| 5792 | rdaregistry.info | RDA content/media/carrier/illustration types |
| 3110 | viaf.org | VIAF person/org clusters |
| 2250 | isni.org | ISNI identifiers |
| 1210 | library.artstor.org | **ArtStor digital images** |
| 306 | vocab.getty.edu | Getty AAT / ULAN |
| 50 | homosaurus.org | Homosaurus LGBTQ+ vocabulary |
| (tail) | wsworkshop.org, printedmatter.org, vampandtramp.com, getty, … | publisher / dealer pages |

### ⚠️ Trailing-period corruption on `$0`/`$1` URIs — fix before use

End-of-field punctuation leaked into the last subfield, so a large share of the
authority URIs end in a literal `.`:

| subfield | URIs | with trailing `.` |
|----------|-----:|------------------:|
| `$0` | 19,583 | **15,029 (77%)** |
| `$1` | 5,393 | **3,110 (58%)** |
| `$u` (856) | 1,169 | 0 (clean) |

e.g. `http://id.worldcat.org/fast/892873.` and `…/isni/0000000498955015.`
**Strip a single trailing `.` from `$0`/`$1` when minting URIs** — otherwise the
links don't dereference. `$u` web links are clean and need no fix.

## Subjects & genre/form (6xx)

The richest part of these records. Genre/form (`655`) appears in 99% of records
and topical subjects (`650`) in 82%. Headings come from several vocabularies,
flagged by `ind2` (`0` = LCSH) or, when `ind2=7`, by `$2`:

| tag | vocab (`$2` / ind2) | n | with `$0`/`$1` |
|-----|---------------------|--:|---------------:|
| 650 | fast | 2631 | 2631 (100%) |
| 650 | LCSH (ind2=0) | 2552 | 1462 (57%) |
| 655 | fast | 2013 | 2013 (100%) |
| 655 | lcgft | 1364 | 1364 (100%) |
| 655 | aat (Getty) | 296 | 294 |
| 651 | fast | 535 | 535 (100%) |
| 600 | fast | 530 | 530 (100%) |
| 600 | LCSH (ind2=0) | 718 | 555 |
| 650 | homoit (Homosaurus) | 51 | 51 (100%) |

Examples:

```
650 $a Dictators. | $2 fast | $0 http://id.worldcat.org/fast/892873.
650 $a Ecofeminism. | $2 homoit | $0 https://homosaurus.org/v4/homoit0000387.
655 $a Shirts (main garments) | $2 aat | $0 http://vocab.getty.edu/aat/300212499.
```

**`$2` value quirk:** the same vocabulary often appears both clean and with a
trailing period — `fast` (5804) vs `fast.` (266), `aat` (308) vs `aat.` (625),
`rbmscv` (177) vs `rbmscv.` (413), `lcgft` (1366) vs `lcgft.` (144). The
period-suffixed variants **generally lack `$0` links**. See the next section for
what's behind this and the genuinely local schemes.

## Local & un-reconciled headings

Not every heading is a clean link to a standard authority. The "local-looking"
headings fall into **four distinct groups**, which matter differently for linked
data.

### 1. Standard vocabularies, just un-reconciled (the period variants)

These are real, well-known vocabularies whose terms were entered as text but
never given a `$0` URI — flagged by a trailing-period `$2`. Their clean-`$2`
twins *do* carry URIs, and the values overlap heavily, so most are **recoverable
by string-matching the period variant to its linked twin**.

| un-reconciled `$2` | n | reconciled twin (n) | twin links to |
|--------------------|--:|---------------------|---------------|
| `rbmscv.` | 413 | `rbmscv` (177) | `id.loc.gov/vocabulary/rbmscv/cv…` |
| `aat.` | 625 | `aat` (308) | `vocab.getty.edu/aat/…` |
| `lcgft.` | 144 | `lcgft` (1366) | `id.loc.gov/authorities/genreForms/…` |
| `fast.` | 266 | `fast` (5804) | `id.worldcat.org/fast/…` |

Shared values, e.g. *Artists' books, Limitation statements, Handmade papers,
Slipcases*, appear in both `rbmscv` and `rbmscv.`. **Caveat:** `fast.` is almost
entirely **`648` chronological** FAST (*"21st century", "1900-2099", "Since
1990"*) — FAST temporal headings are simply not URI-linked here, unlike topical
/geographic/genre FAST.

### 2. Genuinely local genre/technique vocabularies (no standard source)

No authority URIs exist for these — they're artists'-book-specific descriptors
and would need a **locally minted `ab:` vocabulary** (the kind of term `vocab.ttl`
is meant to hold):

- **`abo.org.`** (113, all `655`) — Artists' Books Online structural/narrative
  terms: *Appropriated text, Visual narrative, Photographic sequence*. Contains
  typos (*"Visiual narrative"*).
- **`local.`** (35) — UNC's own genre/technique terms: *Conceptual bookworks,
  Stab binding, Asemic writing, Graduated fore-edges, Corrugated paperboard
  bindings, Altered books*.

### 3. `690` — a local people/peoples index ("UNCProject")

All 63 `690`s are ethnonyms with **variant spellings deliberately grouped** —
e.g. *Hñahñu / Nahnu / Othomi* (Otomi), *Glebo / Grebo / Gweabo / Krebo* (Grebo),
*American aborigines / American Indians / First Nations / Indians of North
America*. This is a project-built index of peoples represented in the books,
capturing name variants. The `$2` scheme label is itself inconsistent —
`UNCProject.` (51), `UNC Project.` (9), `UNCProjec.` (1), and 2 with none — so it
needs normalizing before use, and carries **no `$0`**.

### 4. `791` — acquisition funds, *not* subjects

The 259 `791` fields are **library endowment / donor funds** —
*Hanes Family Library Fund, Howard Holsenbeck Library Fund, William A. Whitaker
Foundation Library Fund* — i.e. **acquisition provenance** (who paid for the
book), not content. Model these separately (or exclude); don't treat them as
headings.

### Normalization notes for these headings

- Strip a trailing `.` from `$2` **and** normalize spacing/spelling variants
  (`UNCProject.` ↔ `UNC Project.`).
- For groups 1–2, prefer the linked twin's `$0` where it exists; otherwise the
  string is the only identifier.
- Subfield-delimiter loss is **rare** — essentially one genuine case
  (`Artists' bookszUnited States.`, a lost `$z` before "United States"), not a
  systemic problem.

## Creators & contributors (1xx / 7xx)

Excellent entity coverage — these are ready-made links to people and
organizations:

| tag | n | `$0` (LC name) | `$1` (VIAF/ISNI) |
|-----|--:|---------------:|-----------------:|
| 100 (main) | 1256 | 1164 (93%) | 1162 |
| 700 (added person) | 820 | 644 | 639 |
| 710 (added corp.) | 673 | 593 | 592 |
| 110/711 | 10/10 | most | most |

Roles are in `$e` (relator term). Top roles map directly onto the project's
intended `ab:` creator roles:

> artist (330), author (269), publisher (186), photographer (111),
> **book artist (105)**, book designer (70), illustrator (59), editor (56),
> printer (41), translator (30), host institution (15), contributor (12)

```
100 $a Goldstein, Bob, | $d 1967- | $e artist. |
    $0 http://id.loc.gov/authorities/names/no2017165764 |
    $1 http://viaf.org/viaf/15151431616256302424 |
    $1 http://isni.org/isni/0000000498955015.
```

(Note the multiple `$1` per creator — VIAF *and* ISNI — and the trailing-period
issue on the last one.)

## ArtStor image links (856)

1169 `856` fields; **1161 point to `library.artstor.org`**, across **1142 of
1340 records (85%)**. These are the digitized photos of each book.

- Indicators are almost all `ind1=4 ind2=2` (HTTP access, "related resource").
- **Every 856 has a `$3`** describing the images (e.g. *"Photos of the artist's
  book's cover and interior."*); none use `$z`.
- ArtStor asset IDs look like `SS33469_33469_42525467` (the `SS33469…`
  collection is UNC's shared-shelf artists' books set). **Two URL shapes appear**
  — `library.artstor.org/asset/<id>` and `library.artstor.org/#/asset/<id>`;
  the stable part is the asset ID.
- The handful of non-ArtStor `$u`: publisher/artist/dealer pages
  (levisherman.com, printedmatter.org, vampandtramp.com, youtube.com, issuu.com…).

## Free-text notes (5xx)

These hold the descriptive prose. `500` dominates (3145 notes across 1234
records — colophons, edition statements, signature notes, etc.).

| tag | meaning | occ |
|-----|---------|----:|
| 500 | general note | 3145 |
| 520 | summary / abstract | 195 |
| 546 | language note | 132 |
| 505 | formatted contents | 85 |
| 504 | bibliography/refs | 63 |
| 590 | local note | 32 |
| 563 | **binding information** | 25 |
| 588 | source of description | 11 |
| 545 | biographical/historical | 8 |
| 586 / 585 / 561 | awards / exhibitions / provenance | 2 / 1 / 1 |

`500` is free-form and high-volume; expect colophon/edition/technique text there.
`520` (summary) and `563` (binding) are especially relevant to artists' books.

## Other notable structure

- **RDA type fields (336/337/338)** are fully present and `$0`-linked to
  `rdaregistry.info` — clean controlled vocab for content/media/carrier type
  (e.g. "text", "still image", "unmediated", "volume").
- **Classification:** `050` (LC call number) is `$0`-linked to
  `id.loc.gov/authorities/classification` in 843/847 cases; `082` (Dewey) and
  `090` (local) carry no `$0`.
- **Vernacular / non-Latin script (880):** 87 fields in 29 records, paralleling
  romanized fields via `$6` linkage — mostly `245` (20), `246` (16), `100` (13),
  `264` (7), `700`/`710`/`500` — i.e. Chinese, Korean, Cherokee, etc. titles and
  names. Join `880` to its base field through the `$6` occurrence number.
- **Local 9xx (Innopac/UNC):** `915` (3982 — MARS/authority-control processing
  notes), `949` (item-level call number + barcode `$i`), `090` (local call no.),
  `994`/`998` (system fields). These are UNC-specific provenance, generally not
  for public linked data. (`690` local subjects and `791` acquisition funds are
  covered under [Local & un-reconciled headings](#local--un-reconciled-headings).)

## Recommendations for the SPARQL-Anything step

1. **Join on `999 $a`** → the Zotero `itemKey` → existing `item/<itemKey>` URIs.
2. **Sanitize URIs:** strip a single trailing `.` from `$0`/`$1` (77% / 58% are
   affected). `$u` is clean.
3. **Normalize `$2`:** strip a trailing `.` before bucketing vocabularies; treat
   the period-suffixed variants as the un-reconciled/local headings.
4. **Prefer `$0`/`$1` over text** for subjects, genres, and creators — coverage
   is high (FAST, LCGFT, RDA, LC names all ~100%; LCSH ~57%) and gives real
   linked-data targets (id.loc.gov, FAST, VIAF, ISNI, Getty, Homosaurus).
5. **Creators:** map `$e` relator terms to `ab:` roles (`book artist` →
   `ab:bookArtist`, etc.); carry both `$1` VIAF and ISNI.
6. **Images:** model the `856`→`library.artstor.org` link (with its `$3` caption)
   as a depiction/related-resource of the book.
7. **Notes:** surface `520` (summary), `500` (general/colophon), and `563`
   (binding) as descriptive literals; the rest are lower-volume.
