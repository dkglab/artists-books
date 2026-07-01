START_FUSEKI ?= true

.PHONY: all clean superclean validate serve
.DEFAULT_GOAL := all

all: graph/artists-books.ttl graph/reference-resources.ttl website/site/index.html

clean:
	rm -f inferred.ttl diff.txt *.png docs/*.png
	rm -rf graph site .snowman website/site website/.snowman

superclean: clean
	@$(MAKE) -s -C tools/jena clean
	@$(MAKE) -s -C tools/rdflib clean
	@$(MAKE) -s -C tools/fuseki clean
	@$(MAKE) -s -C tools/snowman clean
	@$(MAKE) -s -C tools/yaz-client clean

tools/jena/bin/riot \
tools/rdflib/bin/rdf2dot \
tools/sparql-anything/sparql-anything.jar \
tools/fuseki/fuseki-server \
tools/snowman/snowman:
	$(MAKE) -s -C $(shell echo $@ | cut -d/ -f1-2)

validate: docs/vocab.ttl docs/description.ttl | tools/jena/bin/riot
	./tools/jena/bin/riot --validate $^
	@echo "docs/vocab.ttl and docs/description.ttl are valid."

serve: website/site/index.html | tools/snowman/snowman
	cd website && ../tools/snowman/snowman server --port 8080

inferred.ttl: docs/vocab.ttl docs/description.ttl | validate
	./tools/jena/bin/riot --formatted=ttl --rdfs $< $(word 2,$^) > $@

diff.txt: docs/description.ttl inferred.ttl | validate
	./tools/jena/bin/riot --validate inferred.ttl
	@echo "inferred.ttl is valid."
	./tools/jena/bin/rdfdiff $^ TTL TTL > $@ ; \
	[ $$? -eq 0 ] \
	&& (echo "\033[1;31mNo triples were inferred!\033[0m" ; rm -f $@) \
	|| echo "Triples were inferred!"

%.png: %.ttl | validate tools/rdflib/bin/rdf2dot
	./tools/rdflib/bin/rdf2dot $< 2>/dev/null | dot -Tpng > $@

graph/%.ttl: queries/construct/%.rq | tools/sparql-anything/sparql-anything.jar
	@mkdir -p graph
	java -jar tools/sparql-anything/sparql-anything.jar -q $< > $@

# The construct query reads these source files (its x-sparql-anything SERVICEs);
# rebuild the graph when any of them changes.
graph/artists-books.ttl: \
Zotero/artists-books.csv \
Zotero/artists-books-marc.xml

graph/reference-resources.ttl: \
Zotero/reference-resources.csv \
Zotero/citation-crosswalk.csv \
Zotero/abc-master-crosswalk.csv

website/site/index.html: \
graph/artists-books.ttl \
graph/reference-resources.ttl \
$(wildcard website/*.yaml) \
$(wildcard website/queries/select/*.rq) \
$(wildcard website/templates/*.html) \
$(wildcard website/templates/layouts/*.html) \
$(wildcard website/templates/includes/*.html) \
| tools/fuseki/fuseki-server tools/snowman/snowman
ifeq ($(START_FUSEKI),true)
	$(MAKE) -s -C tools/fuseki start
endif
	mkdir -p website/.snowman
	cd website && ../tools/snowman/snowman build 2>&1 | tee .snowman/build_log.txt
ifeq ($(START_FUSEKI),true)
	$(MAKE) -s -C tools/fuseki stop
endif
