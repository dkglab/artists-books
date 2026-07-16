SHELL := /usr/bin/env bash
.SHELLFLAGS := -O extglob -c
YAZ_HOST := https://ftp.indexdata.com/pub/yaz
YAZ_VERSION := 5.37.3

.PHONY: all clean

# yaz-client and yaz-marcdump (used by ../../sources/marc/marc_harvest.py) are part of
# Index Data's YAZ toolkit, which ships as C source only -- no prebuilt binaries
# like the Java/Go tools. So we fetch the tarball into src/ and build it,
# installing into this directory (bin/, lib/, share/) via --prefix.
# zoomfetch is our own ~200-line Z39.50 driver (../../sources/marc/zoomfetch.c,
# issue #85), linked against the libyaz we just built via its ZOOM C API.
all: bin/yaz-client bin/zoomfetch

clean:
	rm -rf !(Makefile)

bin/yaz-client: src/configure
	cd src && ./configure --prefix=$(CURDIR)
	$(MAKE) -C src
	$(MAKE) -C src install

# Compile zoomfetch against the freshly built libyaz. yaz-config emits the exact
# include/lib flags, so this is portable across Ubuntu and macOS. The rpath lets
# the binary find the built shared libyaz at runtime (required on macOS, harmless
# on Linux); linking the static libyaz.a would be the alternative.
ZOOMFETCH_SRC := ../../sources/marc/zoomfetch.c
bin/zoomfetch: $(ZOOMFETCH_SRC) bin/yaz-client
	$(CC) $(shell $(CURDIR)/bin/yaz-config --cflags) $< \
	      $(shell $(CURDIR)/bin/yaz-config --libs) \
	      -Wl,-rpath,$(CURDIR)/lib -o $@

src/configure:
	mkdir -p src
	curl -s -L $(YAZ_HOST)/yaz-$(YAZ_VERSION).tar.gz \
	| tar zxvf - --strip-components 1 -C src
