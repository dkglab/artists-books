SHELL := /usr/bin/env bash
.SHELLFLAGS := -O extglob -c
JENA_HOST := https://dlcdn.apache.org/jena/binaries
JENA_VERSION := 6.1.0
ENDPOINT := http://localhost:3030/artists-books/sparql

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

fuseki-server:
	curl $(JENA_HOST)/apache-jena-fuseki-$(JENA_VERSION).tar.gz \
	| tar zxvf - --strip-components 1
