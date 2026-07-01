-- Export unique Zotero publishers
-- Each row is one distinct publisher name.
--
-- Optional parameter: :collection (collection name to filter by)
-- If unset or empty, all publishers are exported.
-- Usage via wrapper: ./publishers_export.sh "Artists' Books Collection"
-- Usage via sqlite3:
--   sqlite3 -cmd ".parameter set :collection 'My Collection'" -header -csv zotero.sqlite < publishers_export.sql

SELECT DISTINCT
    idv.value AS publisher
FROM itemDataValues idv
JOIN itemData id ON idv.valueID = id.valueID
JOIN fieldsCombined f ON id.fieldID = f.fieldID
JOIN items i ON id.itemID = i.itemID
JOIN itemTypes it ON i.itemTypeID = it.itemTypeID
WHERE f.fieldName = 'publisher'
  AND it.typeName NOT IN ('attachment', 'note', 'annotation')
  AND (
    :collection IS NULL
    OR :collection = ''
    OR EXISTS (
        SELECT 1
        FROM collectionItems ci
        JOIN collections col ON ci.collectionID = col.collectionID
        WHERE ci.itemID = i.itemID AND col.collectionName = :collection
    )
  )
ORDER BY idv.value;
