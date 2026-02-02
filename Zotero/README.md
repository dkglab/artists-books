# Overview

- `zotero.sqlite` — 55MB SQLite database (Zotero's main metadata store)
- `storage/` — 1,299 subdirectories (8-char hash names)

## What's in the storage directories

Almost all 1,299 directories are complete web snapshots of pages from
the UNC Chapel Hill Libraries catalog, specifically records from the
Art Library's Artists' Book Collection. Each directory is a
self-contained capture of a single catalog page with all its assets.

Typical directory contents (~50-60 files each):

```text
┌─────────────────────────────────┬─────────────────────────────────────────┐
│              Type               │               Description               │
├─────────────────────────────────┼─────────────────────────────────────────┤
│ search.html / index.aspx        │ The main catalog page HTML              │
├─────────────────────────────────┼─────────────────────────────────────────┤
│ .js files (~17k total)          │ jQuery, analytics, UI scripts           │
├─────────────────────────────────┼─────────────────────────────────────────┤
│ .css files                      │ Stylesheets for the catalog UI          │
├─────────────────────────────────┼─────────────────────────────────────────┤
│ .gif, .jpg, .png, .ico          │ UI icons, logos, backgrounds            │
├─────────────────────────────────┼─────────────────────────────────────────┤
│ status_api.php                  │ Library availability API responses      │
├─────────────────────────────────┼─────────────────────────────────────────┤
│ books                           │ Google Books API responses (JSON/JSONP) │
├─────────────────────────────────┼─────────────────────────────────────────┤
│ ISBN*&callback=ProcessListHathi │ HathiTrust API responses                │
└─────────────────────────────────┴─────────────────────────────────────────┘
```

  The important data files:

- `.zotero-ft-cache` (296 dirs) — Plain text extracted from the page,
  already indexed by Zotero for full-text search
- `.zotero-ft-unprocessed` (973 dirs) — JSON containing extracted text
  awaiting indexing
- These contain the bibliographic records: titles, authors,
  publishers, ISBNs, OCLC numbers, call numbers, subject headings,
  physical descriptions, and notes about binding/printing methods
