OS := $(shell uname -sm)
SM_HOST := https://github.com/glaciers-in-archives/snowman/releases/download
SM_VERSION := 0.8.0

ifeq ($(OS),Darwin x86_64)
        SM_BIN := snowman-darwin-amd64
else ifeq ($(OS),Darwin arm64)
        SM_BIN := snowman-darwin-arm64
else ifeq ($(OS),Linux x86_64)
        SM_BIN := snowman-linux-amd64
else ifeq ($(OS),Linux arm64)
        SM_BIN := snowman-linux-arm64
endif

# The binary's filename records no version, so a bump to SM_VERSION above was
# ignored on any machine that already built once: the 0.4.0 -> 0.8.0 bump in
# 7f88b24 left 0.4.0 binaries in place, which then failed the site build on
# --cache-sparql (a flag 0.4.0 spells --cache). Gate the download on a
# version-stamped file instead: bumping the version orphans the old stamp, and
# remaking it wipes the old binary and re-downloads.
STAMP := version-$(SM_VERSION)

# A half-finished download must not be left behind as a target Make then
# considers up to date (an interrupted fetch once left a truncated
# fuseki-server.jar in place, and a 404 leaves a 0-byte binary).
.DELETE_ON_ERROR:

.PHONY: all clean

all: snowman

clean:
	rm -f snowman version-*

snowman: $(STAMP)
	curl -L --fail $(SM_HOST)/$(SM_VERSION)/$(SM_BIN) > $@
	chmod +x $@

$(STAMP):
	$(MAKE) clean
	touch $@
