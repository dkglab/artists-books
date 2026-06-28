.PHONY: all clean

# Build an isolated venv with rapidfuzz for the ABC <-> cited-record crosswalk
# (issue #55). Only the committed files (this Makefile, match.py,
# requirements.txt, README.md) survive `clean`; the venv is regenerated.
all: venv/bin/python

clean:
	rm -rf venv

# The venv lives in venv/ (not the dir root) so its auto-generated `.gitignore`
# (`*`) does not mask the committed scripts alongside it.
venv/bin/python:
	python3 -m venv venv
	./venv/bin/pip install --upgrade pip
	./venv/bin/pip install -r requirements.txt
