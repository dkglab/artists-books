# Overview

- `zotero.sqlite` — 55MB SQLite database (Zotero's main metadata store)
- `storage/` — 1,299 subdirectories (8-char hash names)

## SQLite database

The database is the primary source of value. It contains structured
metadata for the full collection — far more than what's in the storage
directories.

### Key tables

```
items                → master record for every item (books, articles, attachments, notes)
itemData / fields /
  itemDataValues     → field-value metadata (title, date, publisher, ISBN, place, etc.)
itemCreators /
  creators           → authors, editors, and other creator roles
itemTags / tags      → subject tags
itemNotes            → rich-text notes (citations, annotations)
itemAttachments      → links attachments to their parent items and to storage dirs
collections /
  collectionItems    → user-created folder organization
```

### Item counts

| Type            | Count  |
|-----------------|--------|
| book            | 19,211 |
| note            | 7,980  |
| attachment      | 1,300  |
| journalArticle  | 51     |
| webpage         | 13     |
| manuscript      | 3      |
| bookSection     | 2      |
| thesis          | 1      |

### How items relate to storage directories

Each item has a `key` column (8-char hash). Attachments are separate
items in the `items` table with their own key. The attachment's key
**is the storage directory name**.

Example:

```
Book item  HKGS8WHZ  →  "(Ho + go)² = it" by Ruth Laxson (Nexus Press, 1986)
  └─ Attachment item  EINGQSS4  →  path: storage:search.html
     └─ maps to  Zotero/storage/EINGQSS4/search.html
```

Only 1,297 of the 19,211 books have a corresponding storage snapshot.
The remaining 17,915 books exist only as structured metadata in the
database.

## Citation data

This database was compiled by a librarian at the Hanes Art Library to
record citation relationships among artists' books. For each book in
the collection, they recorded which published reference works discuss
it — effectively building a reverse citation index.

Citation data is stored in two parallel forms:

### Tags — citation source shorthand

Tags like `Bury (2015)`, `Drucker (2004)`, `Moeglin-Delcroix (2012)`
identify which reference works cite a given book. There are ~73
distinct citation-source tags. A book can carry many — e.g. Ed
Ruscha's *Every building on the Sunset Strip* has 12, meaning it
appears in 12 different reference works.

The most frequently used citation sources:

| Tag                       | Books cited |
|---------------------------|-------------|
| Moeglin-Delcroix (2012)  | 1,568       |
| Bury (2015)              | 1,214       |
| Lyons (2009)             | 877         |
| Drucker (2004)           | 615         |
| Phillpot (2013)          | 477         |
| Moeglin-Delcroix (1985)  | 438         |
| NRA Shakespeare (1985)   | 430         |
| Lauf (1998)              | 364         |
| Lyons (1985)             | 354         |

### Notes — full citation details

7,649 of the 7,978 notes are **"Cited:" notes** containing the full
bibliographic references with page numbers. All of a book's citations
are typically combined into a single note, e.g.:

```
Cited:
Bury, Stephen. Artists' Books... London, 2015. pp.17, 38, **45**, 178.
Drucker, Johanna. The Century of Artists' Books. 2nd ed. NYC, 2004. pp.178, **179**, 276.
```

Bold page numbers appear to indicate the primary or illustrated entry.

The tags and notes encode the same information in parallel: the tag
`Drucker (2004)` on a book corresponds to the Drucker citation line
in that book's note, but the note adds the full bibliographic string
and specific page numbers.

### The "Reference resources" collection

The citing reference works themselves are also cataloged in the
database, organized into a **"Reference resources" collection** of
156 items. These include the major surveys, exhibition catalogs,
bibliographies, and journals used as citation sources:

- Bury, *Artists' books: the book as a work of art 1963-2000* (2015)
- Drucker, *The century of artists' books* (2004)
- Moeglin-Delcroix, *Esthétique du livre d'artiste 1960/1980* (2012)
- Phillpot, *Booktrek: selected essays on artists' books* (2013)
- Wasserman, *The book as art* (2007)
- Lyons, *Artists' books: Visual Studies Workshop Press* (2009)
- Hamady, *Two decades of Hamady and the Perishable Press Limited* (1984)
- Bodman, *Creating artists' books* (2005)
- and ~148 others

Each citing work is tagged with its own citation-source tag (e.g.
Bury's book is tagged `Bury (2015)`) and carries workflow tags like
`Indexed, needs QC` or `Completed`, which the librarian used to track
indexing progress.

### Note on duplicates

Many books appear 2-4 times in the database with slightly different
title forms, likely from separate catalog imports. The collections
(like "Reference resources") appear to hold the canonical records.

## What's in the storage directories

Almost all 1,299 directories are complete web snapshots of pages from
the UNC Chapel Hill Libraries catalog, specifically records from the
Art Library's Artists' Book Collection. Each directory is a
self-contained capture of a single catalog page.

Typical directory contents:

| File                            | Description                        |
|---------------------------------|------------------------------------|
| `search.html` / `index.aspx`   | The main catalog page HTML         |
| `status_api.php`                | Library availability API responses |
| `books`                         | Google Books API responses (JSONP) |
| `ISBN*&callback=ProcessListHathi` | HathiTrust API responses         |
| `.zotero-ft-cache`              | Plain text extracted from the page (296 dirs) |
| `.zotero-ft-unprocessed`        | JSON with extracted text awaiting indexing (973 dirs) |

Web snapshot assets (JS, CSS, images) have been removed from version
control and from disk — they were duplicated UI chrome with no research
value. See `.gitignore` for the exclusion patterns.
