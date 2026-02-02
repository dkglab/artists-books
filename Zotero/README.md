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
