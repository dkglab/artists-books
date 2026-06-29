SHELL := /usr/bin/env bash
.SHELLFLAGS := -O extglob -c
YAZ_HOST := https://ftp.indexdata.com/pub/yaz
YAZ_VERSION := 5.37.3

.PHONY: all clean

# yaz-client and yaz-marcdump (used by ../../Zotero/marc_harvest.py) are part of
# Index Data's YAZ toolkit, which ships as C source only -- no prebuilt binaries
# like the Java/Go tools. So we fetch the tarball into src/ and build it,
# installing into this directory (bin/, lib/, share/) via --prefix.
all: bin/yaz-client

clean:
	rm -rf !(Makefile)

bin/yaz-client: src/configure
	cd src && ./configure --prefix=$(CURDIR)
	$(MAKE) -C src
	$(MAKE) -C src install

src/configure:
	mkdir -p src
	curl -s -L $(YAZ_HOST)/yaz-$(YAZ_VERSION).tar.gz \
	| tar zxvf - --strip-components 1 -C src
