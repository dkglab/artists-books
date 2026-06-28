-- Export Zotero "Cited:" notes for the lib-3 citation index (issue #53).
--
-- The personal-library ABC (lib 1, what the site builds from) has no Cited
-- notes; they live on the lib-3 records (group 2352415, "ABCI"). We export each
-- note's parent itemKey + the raw note HTML; notes_export.py then normalizes the
-- HTML to well-formed XHTML (Zotero/notes.xml). The construct query joins these
-- onto ABC pages through the #55 crosswalk (abcItemKey -> citedItemKey).
--
-- Scope matches cited_records_export.sql: a real bibliographic item in
-- libraryID = 3 whose note text contains "Cited". ~4,008 notes (=1 per item,
-- max 2).
--
-- Usage (via wrapper):  ./notes_export.sh > notes.xml

SELECT
    pi.key AS itemKey,
    n.note AS note
FROM itemNotes n
JOIN items pi ON n.parentItemID = pi.itemID
JOIN itemTypes it ON pi.itemTypeID = it.itemTypeID
WHERE pi.libraryID = 3
  AND it.typeName NOT IN ('attachment', 'note', 'annotation')
  AND n.note LIKE '%Cited%'
ORDER BY pi.key, n.itemID;
