-- Export all Zotero items with data fields as columns
-- Each row is an item, each used field becomes a column
--
-- Optional parameter: :collection (collection name to filter by)
-- If unset or empty, all items are exported.
-- Usage via wrapper: ./items_export.sh "Artists' Books Collection"
-- Usage via sqlite3:
--   sqlite3 -cmd ".parameter set :collection 'My Collection'" -header -csv zotero.sqlite < items_export.sql

SELECT
    i.itemID,
    i.key AS itemKey,
    it.typeName AS itemType,
    i.dateAdded,
    i.dateModified,
    MAX(CASE WHEN f.fieldName = 'title' THEN idv.value END) AS title,
    MAX(CASE WHEN f.fieldName = 'abstractNote' THEN idv.value END) AS abstractNote,
    MAX(CASE WHEN f.fieldName = 'date' THEN idv.value END) AS date,
    MAX(CASE WHEN f.fieldName = 'publisher' THEN idv.value END) AS publisher,
    MAX(CASE WHEN f.fieldName = 'place' THEN idv.value END) AS place,
    MAX(CASE WHEN f.fieldName = 'volume' THEN idv.value END) AS volume,
    MAX(CASE WHEN f.fieldName = 'numberOfVolumes' THEN idv.value END) AS numberOfVolumes,
    MAX(CASE WHEN f.fieldName = 'edition' THEN idv.value END) AS edition,
    MAX(CASE WHEN f.fieldName = 'series' THEN idv.value END) AS series,
    MAX(CASE WHEN f.fieldName = 'seriesNumber' THEN idv.value END) AS seriesNumber,
    MAX(CASE WHEN f.fieldName = 'numPages' THEN idv.value END) AS numPages,
    MAX(CASE WHEN f.fieldName = 'pages' THEN idv.value END) AS pages,
    MAX(CASE WHEN f.fieldName = 'ISBN' THEN idv.value END) AS ISBN,
    MAX(CASE WHEN f.fieldName = 'ISSN' THEN idv.value END) AS ISSN,
    MAX(CASE WHEN f.fieldName = 'url' THEN idv.value END) AS url,
    MAX(CASE WHEN f.fieldName = 'accessDate' THEN idv.value END) AS accessDate,
    MAX(CASE WHEN f.fieldName = 'language' THEN idv.value END) AS language,
    MAX(CASE WHEN f.fieldName = 'shortTitle' THEN idv.value END) AS shortTitle,
    MAX(CASE WHEN f.fieldName = 'libraryCatalog' THEN idv.value END) AS libraryCatalog,
    MAX(CASE WHEN f.fieldName = 'callNumber' THEN idv.value END) AS callNumber,
    MAX(CASE WHEN f.fieldName = 'archiveLocation' THEN idv.value END) AS archiveLocation,
    MAX(CASE WHEN f.fieldName = 'rights' THEN idv.value END) AS rights,
    MAX(CASE WHEN f.fieldName = 'extra' THEN idv.value END) AS extra,
    MAX(CASE WHEN f.fieldName = 'publicationTitle' THEN idv.value END) AS publicationTitle,
    MAX(CASE WHEN f.fieldName = 'bookTitle' THEN idv.value END) AS bookTitle,
    MAX(CASE WHEN f.fieldName = 'websiteTitle' THEN idv.value END) AS websiteTitle,
    MAX(CASE WHEN f.fieldName = 'university' THEN idv.value END) AS university,
    (
        SELECT GROUP_CONCAT(c.collectionName, '; ')
        FROM collectionItems ci
        JOIN collections c ON ci.collectionID = c.collectionID
        WHERE ci.itemID = i.itemID
    ) AS collections
FROM items i
JOIN itemTypes it ON i.itemTypeID = it.itemTypeID
LEFT JOIN itemData id ON i.itemID = id.itemID
LEFT JOIN fieldsCombined f ON id.fieldID = f.fieldID
LEFT JOIN itemDataValues idv ON id.valueID = idv.valueID
WHERE it.typeName NOT IN ('attachment', 'note', 'annotation')
  AND (
    :collection IS NULL
    OR :collection = ''
    OR EXISTS (
        SELECT 1
        FROM collectionItems ci2
        JOIN collections c2 ON ci2.collectionID = c2.collectionID
        WHERE ci2.itemID = i.itemID AND c2.collectionName = :collection
    )
  )
GROUP BY i.itemID
ORDER BY i.itemID;
