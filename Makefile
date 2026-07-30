START_FUSEKI ?= true

.PHONY: all clean superclean validate serve FORCE
.DEFAULT_GOAL := all

all: graph/artists-books.ttl graph/reference-works.ttl web/site/index.html

clean:
	rm -rf graph site .snowman web/site web/.snowman

superclean: clean
	@$(MAKE) -s -C tools/jena clean
	@$(MAKE) -s -C tools/fuseki clean
	@$(MAKE) -s -C tools/snowman clean
	@$(MAKE) -s -C tools/yaz-client clean

# Each version-pinned tool gates its download on a version stamp (see the
# tools/*/Makefile), but Make would never ask: the binary already exists, so
# this rule looks up to date and the sub-make never runs. That is how the
# Snowman 0.4.0 -> 0.8.0 bump in 7f88b24 went unnoticed on machines that had
# already built. Force the delegation; the sub-make is a no-op when the stamp
# matches the pinned version.
tools/jena/bin/riot \
tools/sparql-anything/sparql-anything.jar \
tools/fuseki/fuseki-server \
tools/snowman/snowman: FORCE
	$(MAKE) -s -C $(shell echo $@ | cut -d/ -f1-2)

FORCE:

validate: docs/vocab.ttl docs/description.ttl | tools/jena/bin/riot
	./tools/jena/bin/riot --validate $^
	@echo "docs/vocab.ttl and docs/description.ttl are valid."

serve: web/site/index.html | tools/snowman/snowman
	cd web && ../tools/snowman/snowman server --port 8080

graph/%.ttl: queries/%.rq | tools/sparql-anything/sparql-anything.jar
	@mkdir -p graph
	# -Dlog4j2.statusLoggerLevel=OFF: the SPARQL-Anything archive triplifier (the
	# per-record MARC zip read, #81) trips Log4j's StatusLogger onto stdout, which
	# would corrupt the Turtle. Silence it so only the RDF reaches $@.
	java -Dlog4j2.statusLoggerLevel=OFF -jar tools/sparql-anything/sparql-anything.jar -q $< > $@

# The construct query reads these source files (its x-sparql-anything SERVICEs);
# rebuild the graph when any of them changes. The MARC is a per-record zip archive
# (#81), read via nested Archive -> XML triplifiers.
#
# artists-books.ttl also reads the construction occurrences + decisions CSVs to
# attach ab:constructedUsing (#86), and the subjects occurrences + decisions CSVs
# to attach ab:hasSubject (#105): each occurrences.csv maps a book's canonical key
# to its heading clusters, each decisions.csv maps included clusters to concepts.
# The concept URIs it emits resolve against sources/construction-methods.ttl and
# sources/subject-terms.ttl, which Fuseki loads separately.
graph/artists-books.ttl: \
sources/artists-books.csv \
sources/marc/artists-books-marc.zip \
sources/construction/occurrences.csv \
sources/construction/decisions.csv \
sources/subjects/occurrences.csv \
sources/subjects/decisions.csv

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
sources/construction-methods.ttl \
sources/subject-terms.ttl \
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
