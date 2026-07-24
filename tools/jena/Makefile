SHELL := /usr/bin/env bash
.SHELLFLAGS := -O extglob -o pipefail -c
JENA_HOST := https://dlcdn.apache.org/jena/binaries
JENA_VERSION := 6.1.0

# The extracted tree records no version of its own, and the download rule's
# target (bin/riot) exists whatever version installed it -- so a bump to
# JENA_VERSION above would otherwise be ignored on any machine that already
# built once. Gate the download on a version-stamped file instead: bumping the
# version orphans the old stamp, and remaking it wipes the directory (jars from
# two Jena versions sharing lib/ would poison the classpath) and re-downloads.
STAMP := version-$(JENA_VERSION)

# A half-finished download must not be left behind as a target Make then
# considers up to date (an interrupted fetch once left a truncated
# fuseki-server.jar in place, and a 404 leaves a 0-byte binary).
.DELETE_ON_ERROR:

.PHONY: all clean

all: bin/riot

clean:
	rm -rf !(Makefile)

# tar -m stamps the extracted files with the extraction time. Without it they
# keep the mtimes Apache built the release with, which are older than the
# version stamp this rule depends on -- so every single make would see the
# target as out of date and re-download 48MB.
bin/riot: $(STAMP)
	curl --fail $(JENA_HOST)/apache-jena-$(JENA_VERSION).tar.gz \
	| tar zxvf - -m --strip-components 1

$(STAMP):
	$(MAKE) clean
	touch $@
