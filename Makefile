START_FUSEKI ?= true

.PHONY: all clean superclean validate serve FORCE

# A failed recipe must not leave its target behind looking up to date: a
# java error half-way through `> $@` would otherwise leave a truncated
# graph/*.ttl that the next `make` happily serves (#178).
.DELETE_ON_ERROR:
.DEFAULT_GOAL := all

all: graph/artists-books.ttl graph/reference-works.ttl graph/publications.ttl web/site/index.html

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
	# -Dlog4j2.statusLoggerLevel=OFF: SPARQL-Anything's Log4j StatusLogger can
	# print onto stdout (first seen with the per-record MARC read, #81), which
	# would corrupt the Turtle. Silence it so only the RDF reaches $@.
	java -Dlog4j2.statusLoggerLevel=OFF -jar tools/sparql-anything/sparql-anything.jar -q $< > $@

# The construct query reads these source files (its x-sparql-anything SERVICEs);
# rebuild the graph when any of them changes. The MARC is a per-record directory
# (#81), one <key>.xml per record, read via nested Folder -> XML triplifiers; it
# is listed file by file (not as the directory), so editing a single record's
# contents -- which leaves the directory's own mtime alone -- still rebuilds.
#
# artists-books.ttl also reads the construction occurrences + decisions CSVs to
# attach ab:constructedUsing (#86), and the subjects occurrences + decisions CSVs
# to attach ab:hasSubject (#105): each occurrences.csv maps a book's canonical key
# to its heading clusters, each decisions.csv maps included clusters to concepts.
# It also reads sources/artstor-ssid.csv + sources/ssid-media.csv to attach the
# JSTOR IIIF imagery (#9), joining canonical key -> SSID -> IIIF identifier.
# The concept URIs it emits resolve against sources/construction-methods.ttl,
# sources/subject-terms.ttl and sources/image-view-types.ttl, which Fuseki loads
# separately. Creator identity comes from sources/creators/agents.csv (#170),
# the corpus-wide authority join table both construct queries read.
graph/artists-books.ttl: \
sources/artists-books.csv \
$(wildcard sources/marc/artists-books-marc/*.xml) \
sources/creators/agents.csv \
sources/construction/occurrences.csv \
sources/construction/decisions.csv \
sources/subjects/occurrences.csv \
sources/subjects/decisions.csv \
sources/titles/740-variant-titles.csv \
sources/artstor-ssid.csv \
sources/ssid-media.csv

graph/reference-works.ttl: \
sources/reference-works.csv \
$(wildcard sources/marc/reference-works-marc/*.xml) \
sources/creators/agents.csv

# The publication statement of both tracks (#21): one query over both
# canonical lists and both MARC directories, so the MARC 264/260 + 008 reading
# and the Zotero fallback are written once.
graph/publications.ttl: \
sources/artists-books.csv \
sources/reference-works.csv \
sources/dates/decisions.csv \
$(wildcard sources/marc/artists-books-marc/*.xml) \
$(wildcard sources/marc/reference-works-marc/*.xml)

# sources/citations.ttl is a committed frozen graph (issue #82, task 3) — no
# recipe; Fuseki loads it alongside the two constructed graphs, so the site
# rebuilds when it changes.
web/site/index.html: \
graph/artists-books.ttl \
graph/reference-works.ttl \
graph/publications.ttl \
sources/citations.ttl \
sources/construction-methods.ttl \
sources/subject-terms.ttl \
sources/image-view-types.ttl \
$(wildcard web/*.yaml) \
$(wildcard web/queries/*.rq) \
$(wildcard web/templates/*.html) \
$(wildcard web/templates/*.json) \
$(wildcard web/templates/layouts/*.html) \
$(wildcard web/templates/includes/*.html) \
$(wildcard web/static/*) \
| tools/fuseki/fuseki-server tools/snowman/snowman
ifeq ($(START_FUSEKI),true)
	$(MAKE) -s -C tools/fuseki start
endif
	mkdir -p web/.snowman
	# --cache-sparql never: Make already gates this recipe on the graph/query/
	# template prerequisites, so always re-query Fuseki. Snowman's default cache
	# is keyed by query text only, so a changed graph (same query) would other-
	# wise serve stale results (e.g. the old lib-1-only book set).
	#
	# Make's /bin/sh has no pipefail, so the pipeline's status is tee's (always
	# 0) and a Snowman failure would pass silently over a partial web/site/
	# (#178). Record Snowman's own status instead, stop Fuseki either way, then
	# fail. The target is removed explicitly: .DELETE_ON_ERROR only deletes a
	# target the recipe has modified, and Snowman may abort before rewriting it.
	cd web && { ../tools/snowman/snowman build --cache-sparql never 2>&1; \
	  echo $$? > .snowman/exit-status; } | tee .snowman/build_log.txt
ifeq ($(START_FUSEKI),true)
	$(MAKE) -s -C tools/fuseki stop
endif
	@status=$$(cat web/.snowman/exit-status); \
	if [ "$$status" != 0 ]; then \
	  echo "snowman build failed (exit $$status); see web/.snowman/build_log.txt" >&2; \
	  rm -f $@; exit $$status; \
	fi
	# The facet indexes are rendered with text/template (views.yaml `unsafe: true`),
	# which leaves JSON escaping to the template: fail the build if it slipped,
	# removing the target so the next `make` rebuilds rather than looking done.
	for f in construction-facet subject-facet; do \
	  python3 -m json.tool web/site/$$f.json > /dev/null || { rm -f $@; exit 1; }; \
	done
