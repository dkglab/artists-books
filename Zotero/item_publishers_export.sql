-- Export Zotero item-publisher relations
-- Each row links one item to its publisher name.
-- Join with publishers_export.sql output on publisher to get unique publishers.
--
-- Optional parameter: :collection (collection name to filter by)
-- If unset or empty, all items are exported.
-- Usage via wrapper: ./publishers_export.sh "Artists' Books Collection"
-- Usage via sqlite3:
--   sqlite3 -cmd ".parameter set :collection 'My Collection'" -header -csv zotero.sqlite < item_publishers_export.sql

SELECT
    i.itemID,
    i.key AS itemKey,
    idv.value AS publisher
FROM items i
JOIN itemTypes it ON i.itemTypeID = it.itemTypeID
JOIN itemData id ON i.itemID = id.itemID
JOIN fieldsCombined f ON id.fieldID = f.fieldID
JOIN itemDataValues idv ON id.valueID = idv.valueID
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
ORDER BY i.itemID;
