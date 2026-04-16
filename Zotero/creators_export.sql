-- Export unique Zotero creators
-- Each row is one unique creator (person or organization).
-- fieldMode: 0 = two-field name (firstName + lastName), 1 = single-field (lastName only, used for institutions)
--
-- Optional parameter: :collection (collection name to filter by)
-- If unset or empty, all creators are exported.
-- Usage via wrapper: ./creators_export.sh "Artists' Books Collection"
-- Usage via sqlite3:
--   sqlite3 -cmd ".parameter set :collection 'My Collection'" -header -csv zotero.sqlite < creators_export.sql

SELECT DISTINCT
    c.creatorID,
    CASE
        WHEN c.fieldMode = 1 THEN c.lastName
        WHEN c.firstName = '' THEN c.lastName
        WHEN c.lastName = '' THEN c.firstName
        ELSE c.firstName || ' ' || c.lastName
    END AS name
FROM creators c
JOIN itemCreators ic ON c.creatorID = ic.creatorID
JOIN items i ON ic.itemID = i.itemID
JOIN itemTypes it ON i.itemTypeID = it.itemTypeID
WHERE it.typeName NOT IN ('attachment', 'note', 'annotation')
  AND (
    :collection IS NULL
    OR :collection = ''
    OR EXISTS (
        SELECT 1
        FROM collectionItems ci
        JOIN collections col ON ci.collectionID = col.collectionID
        WHERE ci.itemID = ic.itemID AND col.collectionName = :collection
    )
  )
ORDER BY c.creatorID;
