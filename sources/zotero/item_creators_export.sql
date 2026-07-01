-- Export Zotero item-creator relations
-- Each row links one item to one creator, with role and position.
-- Join with creators_export.sql output on creatorID to get names.
--
-- Optional parameter: :collection (collection name to filter by)
-- If unset or empty, all items are exported.
-- Usage via wrapper: ./creators_export.sh "Artists' Books Collection"
-- Usage via sqlite3:
--   sqlite3 -cmd ".parameter set :collection 'My Collection'" -header -csv zotero.sqlite < item_creators_export.sql

SELECT
    ic.itemID,
    i.key AS itemKey,
    ic.creatorID,
    ic.orderIndex,
    ct.creatorType
FROM itemCreators ic
JOIN items i ON ic.itemID = i.itemID
JOIN itemTypes it ON i.itemTypeID = it.itemTypeID
JOIN creatorTypes ct ON ic.creatorTypeID = ct.creatorTypeID
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
ORDER BY ic.itemID, ic.orderIndex;
