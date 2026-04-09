# Artists' Books

[Opening Artists’ Books vocabulary](https://oab.lib.utah.edu)

[Book Arts Research Database](https://researchbookart.uicb.uiowa.edu)

[Artists' books with authors in Wikidata](https://query.wikidata.org/#SELECT%20DISTINCT%20%3Fauthor%20%3FauthorLabel%20%3Fitem%20%3FitemLabel%20WHERE%20%7B%0A%20%20%3Fitem%20wdt%3AP31%20wd%3AQ1062404%20%3B%20wdt%3AP50%20%3Fauthor%20.%0A%20%20SERVICE%20wikibase%3Alabel%20%7B%20bd%3AserviceParam%20wikibase%3Alanguage%20%22%5BAUTO_LANGUAGE%5D%2Cmul%2Cen%22.%20%7D%0A%7D%0AORDER%20BY%20%3FauthorLabel)

[Joseph C. Sloane Art Library Collection of Artists’ Books and Zines](https://www-jstor-org.libproxy.lib.unc.edu/site/unc-chapel-hill/artists-books/?so=item_title_str_asc)

[Artists' Books in the Center for Book Arts collection - includes images for all listings](https://collections.centerforbookarts.org/browse/objects/facet/term_facet/id/18074)

## Generate the artists' books graph from CSV

Run `make graph/artists-books.ttl`.

## Create your description and vocabulary

In `vocab.ttl`, translate your classes and properties into RDFS in
Turtle syntax. Each class and property you define should have an
`rdfs:label` giving it a human-readable label and an `rdfs:comment`
giving it a description. Each property you define should also have an
`rdfs:domain`, and an `rdfs:range` (unless it takes a literal value;
see below).

In `description.ttl`, create an example description using your RDFS
vocabulary in Turtle syntax.

Remember that:

* Resource names, including class and property names, cannot have
  spaces or other unusual punctuation in them.
* Class and property names should be in "camel case", e.g.:
  `PropertyManager`, `managesProperty`
* Class names should be capitalized.

### Using literal values

A `publicationDate` should probably just take a literal date value:

```ttl
ex:catch22 rdfs:label "Catch-22" ; ex:publicationDate "1961-10-10"^^xsd:date .
```

If you choose to do that, do not define a `range` for
 `publicationDate` (or whatever the property is that you think should
 take a literal value). You might be tempted to make the range
 `rdfs:Literal`, but if you do and you have a triple like the one
 above, then it will be inferred that:

```ttl
"1961-10-10"^^xsd:date rdf:type rdfs:Literal .
```

… which is true, but since we cannot have literals in the subject
position, this produces invalid RDF.

## Validate your Turtle files

```text
make validate
```

will check that `vocab.ttl` and `description.ttl` are valid Turtle files.

If either file is invalid, look at it in Visual Studio Code. The
invalid parts should have red squiqqles. If you can't figure out how
to fix it, try asking Copilot for help by highlighting the problematic
part, opening the context menu (right-click or Ctrl/⌘-click) and
choosing Copilot → Explain.

## Infer new triples based on your RDFS vocabulary

```text
make inferred.ttl
```

will create a file `inferred.ttl` containing the triples from
`description.ttl` plus any new triples that could be inferred based on
`vocab.ttl`.

```text
make diff.txt
```

will create a file `diff.txt` showing the differences between
`description.ttl` and `inferred.ttl`.

## Visualize any Turtle file as a graph

```text
make vocab.png
```

will create a file `vocab.png` visualizing `vocab.ttl` as a
graph. This will work for any file ending in `.ttl` (for example,
`description.ttl` or `inferred.ttl`).
