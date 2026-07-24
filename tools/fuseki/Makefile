SHELL := /usr/bin/env bash
.SHELLFLAGS := -O extglob -o pipefail -c
JENA_HOST := https://dlcdn.apache.org/jena/binaries
JENA_VERSION := 6.1.0
ENDPOINT := http://localhost:3030/artists-books/sparql

# The extracted tree records no version of its own, and fuseki-server exists
# whatever version installed it -- so a bump to JENA_VERSION above would
# otherwise be ignored on any machine that already built once. Gate the
# download on a version-stamped file instead: bumping the version orphans the
# old stamp, and remaking it wipes the directory (which also stops a running
# server, via clean's dependency on stop) and re-downloads.
STAMP := version-$(JENA_VERSION)

# A half-finished download must not be left behind as a target Make then
# considers up to date (an interrupted fetch once left a truncated
# fuseki-server.jar in place, and a 404 leaves a 0-byte binary).
.DELETE_ON_ERROR:

.PHONY: all clean start stop

all: fuseki-server

clean: stop
	rm -rf !(Makefile)

start: fuseki-server
	if [ ! -e run/fuseki.pid ]; then \
	mkdir -p run; \
	./fuseki-server --quiet \
	--file=../../graph/artists-books.ttl \
	--file=../../graph/reference-works.ttl \
	--file=../../sources/citations.ttl \
	--file=../../sources/construction-methods.ttl \
	--file=../../sources/subject-terms.ttl /artists-books \
	2> run/fuseki.log \
	& echo $$! \
	> run/fuseki.pid; \
	for i in $$(seq 1 300); do \
	  if ! kill -0 $$(cat run/fuseki.pid) 2> /dev/null; then \
	    echo "fuseki exited during startup; see run/fuseki.log" >&2; \
	    rm -f run/fuseki.pid; exit 1; \
	  fi; \
	  if curl -sf -o /dev/null \
	    --data-urlencode 'query=ASK {}' \
	    '$(ENDPOINT)'; then break; fi; \
	  if [ $$i = 300 ]; then \
	    echo "fuseki not ready after 60s; see run/fuseki.log" >&2; \
	    exit 1; \
	  fi; \
	  sleep 0.2; \
	done; \
	fi

stop:
	if [ -e run/fuseki.pid ]; then \
	kill $$(cat run/fuseki.pid) || true; \
	rm -f run/fuseki.pid; \
	fi

# tar -m stamps the extracted files with the extraction time. Without it they
# keep the mtimes Apache built the release with, which are older than the
# version stamp this rule depends on -- so every single make would see the
# target as out of date and re-download 48MB.
fuseki-server: $(STAMP)
	curl --fail $(JENA_HOST)/apache-jena-fuseki-$(JENA_VERSION).tar.gz \
	| tar zxvf - -m --strip-components 1

$(STAMP):
	$(MAKE) clean
	touch $@
