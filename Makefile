START_FUSEKI ?= true

.PHONY: all clean superclean validate serve
.DEFAULT_GOAL := all

all: graph/artists-books.ttl graph/reference-works.ttl web/site/index.html

clean:
	rm -f inferred.ttl diff.txt *.png docs/*.png
	rm -rf graph site .snowman web/site web/.snowman

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

serve: web/site/index.html | tools/snowman/snowman
	cd web && ../tools/snowman/snowman server --port 8080

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

graph/%.ttl: queries/%.rq | tools/sparql-anything/sparql-anything.jar
	@mkdir -p graph
	# -Dlog4j2.statusLoggerLevel=OFF: the SPARQL-Anything archive triplifier (the
	# per-record MARC zip read, #81) trips Log4j's StatusLogger onto stdout, which
	# would corrupt the Turtle. Silence it so only the RDF reaches $@.
	java -Dlog4j2.statusLoggerLevel=OFF -jar tools/sparql-anything/sparql-anything.jar -q $< > $@

# The construct query reads these source files (its x-sparql-anything SERVICEs);
# rebuild the graph when any of them changes. The MARC is a per-record zip archive
# (#81), read via nested Archive -> XML triplifiers.
graph/artists-books.ttl: \
sources/artists-books.csv \
sources/marc/artists-books-marc.zip

graph/reference-works.ttl: \
sources/reference-works.csv \
sources/marc/reference-works-marc.zip

# sources/citations.ttl is a committed frozen graph (issue #82, task 3) — no
# recipe; Fuseki loads it alongside the two constructed graphs, so the site
# rebuilds when it changes.
web/site/index.html: \
graph/artists-books.ttl \
graph/reference-works.ttl \
sources/citations.ttl \
$(wildcard web/*.yaml) \
$(wildcard web/queries/*.rq) \
$(wildcard web/templates/*.html) \
$(wildcard web/templates/layouts/*.html) \
$(wildcard web/templates/includes/*.html) \
| tools/fuseki/fuseki-server tools/snowman/snowman
ifeq ($(START_FUSEKI),true)
	$(MAKE) -s -C tools/fuseki start
endif
	mkdir -p web/.snowman
	# --cache-sparql never: Make already gates this recipe on the graph/query/
	# template prerequisites, so always re-query Fuseki. Snowman's default cache
	# is keyed by query text only, so a changed graph (same query) would other-
	# wise serve stale results (e.g. the old lib-1-only book set).
	cd web && ../tools/snowman/snowman build --cache-sparql never 2>&1 | tee .snowman/build_log.txt
ifeq ($(START_FUSEKI),true)
	$(MAKE) -s -C tools/fuseki stop
endif
