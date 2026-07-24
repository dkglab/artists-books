SHELL := /usr/bin/env bash
.SHELLFLAGS := -O extglob -c
SA_HOST := https://github.com/SPARQL-Anything/sparql.anything/releases/download
SA_VERSION := v1.1.0

# The jar's filename records no version, so a bump to SA_VERSION above would
# otherwise be ignored on any machine that already built once. Gate the
# download on a version-stamped file instead: bumping the version orphans the
# old stamp, and remaking it wipes the old jar and re-downloads.
STAMP := version-$(SA_VERSION)

# A half-finished download must not be left behind as a target Make then
# considers up to date (an interrupted fetch once left a truncated
# fuseki-server.jar in place, and a 404 leaves a 0-byte binary).
.DELETE_ON_ERROR:

.PHONY: all clean

all: sparql-anything.jar

clean:
	rm -rf !(Makefile)

sparql-anything.jar: $(STAMP)
	curl -s -L --fail $(SA_HOST)/$(SA_VERSION)/sparql-anything-$(SA_VERSION).jar > $@

$(STAMP):
	$(MAKE) clean
	touch $@
