SHELL := /usr/bin/env bash
.SHELLFLAGS := -O extglob -c

.PHONY: all clean

all: rdflib

clean:
	rm -rf !(Makefile)

rdflib:
	python3 -m venv .
	./bin/pip install --upgrade pip
	./bin/pip install rdflib
