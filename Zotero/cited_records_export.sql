-- Export the lib-3 citation-index records that carry a "Cited:" note.
--
-- These are the candidate target set for the ABC <-> cited-record crosswalk
-- (issue #55): the personal library (lib 1, the "Artists' Books Collection"
-- the website builds from) has no Cited notes, so the notes have to be joined
-- in from lib 3 (group 2352415, "ABCI") through a bibliographic crosswalk.
--
-- A record qualifies when it is a real bibliographic item in libraryID = 3 and
-- has at least one child note whose text contains "Cited". `extra` is exported
-- raw; OCLC numbers (`OCLC: <n>`) are parsed downstream in the matcher (SQLite
-- has no regex -- keep SQL = extract, Python = normalize).
--
-- Usage:
--   sqlite3 -header -csv zotero.sqlite < cited_records_export.sql
-- or via the wrapper:
--   ./cited_records_export.sh > cited-records.csv

SELECT
    i.key AS itemKey,
    MAX(CASE WHEN f.fieldName = 'title' THEN idv.value END) AS title,
    MAX(CASE WHEN f.fieldName = 'ISBN'  THEN idv.value END) AS ISBN,
    MAX(CASE WHEN f.fieldName = 'extra' THEN idv.value END) AS extra,
    MAX(CASE WHEN f.fieldName = 'date'  THEN idv.value END) AS date,
    (
        SELECT GROUP_CONCAT(
            CASE WHEN c.firstName IS NULL OR c.firstName = ''
                 THEN c.lastName
                 ELSE c.lastName || ', ' || c.firstName END,
            '; ')
        FROM itemCreators ic
        JOIN creators c ON ic.creatorID = c.creatorID
        WHERE ic.itemID = i.itemID
    ) AS creators
FROM items i
JOIN itemTypes it ON i.itemTypeID = it.itemTypeID
LEFT JOIN itemData id ON i.itemID = id.itemID
LEFT JOIN fieldsCombined f ON id.fieldID = f.fieldID
LEFT JOIN itemDataValues idv ON id.valueID = idv.valueID
WHERE i.libraryID = 3
  AND it.typeName NOT IN ('attachment', 'note', 'annotation')
  AND EXISTS (
    SELECT 1
    FROM itemNotes n
    WHERE n.parentItemID = i.itemID
      AND n.note LIKE '%Cited%'
  )
GROUP BY i.itemID
ORDER BY i.itemID;
