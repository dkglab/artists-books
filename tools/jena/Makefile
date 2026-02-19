SHELL := /usr/bin/env bash
.SHELLFLAGS := -O extglob -c
JENA_HOST := https://dlcdn.apache.org/jena/binaries
JENA_VERSION := 6.0.0

.PHONY: all clean

all: jena

clean:
	rm -rf !(Makefile)

jena:
	curl $(JENA_HOST)/apache-jena-$(JENA_VERSION).tar.gz \
	| tar zxvf - --strip-components 1
