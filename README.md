# Artists' Books

## Generate the artists' books graph from CSV

`make graph/artists-books.ttl`

## Generate the artists' books website from the artists' books graph

`make site/index.html`

## Serve the artists' books website at <http://127.0.0.1:8000>

`make serve`

## Relevant resources

[Opening Artists’ Books vocabulary](https://oab.lib.utah.edu)

[Book Arts Research Database](https://researchbookart.uicb.uiowa.edu)

[Artists' books with authors in Wikidata](https://query.wikidata.org/#SELECT%20DISTINCT%20%3Fauthor%20%3FauthorLabel%20%3Fitem%20%3FitemLabel%20WHERE%20%7B%0A%20%20%3Fitem%20wdt%3AP31%20wd%3AQ1062404%20%3B%20wdt%3AP50%20%3Fauthor%20.%0A%20%20SERVICE%20wikibase%3Alabel%20%7B%20bd%3AserviceParam%20wikibase%3Alanguage%20%22%5BAUTO_LANGUAGE%5D%2Cmul%2Cen%22.%20%7D%0A%7D%0AORDER%20BY%20%3FauthorLabel)

[Joseph C. Sloane Art Library Collection of Artists’ Books and Zines](https://www-jstor-org.libproxy.lib.unc.edu/site/unc-chapel-hill/artists-books/?so=item_title_str_asc)

[Artists' Books in the Center for Book Arts collection - includes images for all listings](https://collections.centerforbookarts.org/browse/objects/facet/term_facet/id/18074)
