# Regenerates the committed source artifacts under sources/. Run from sources/
# (e.g. `make -C sources <target>`). Two tracks live in subdirs — zotero/ (the
# Zotero DB exports) and marc/ (the Z39.50 MARC harvest) — while the crosswalks
# that bridge them stay at this level.

zotero/all-items.csv: zotero/items_export.sh zotero/items_export.sql
	./zotero/items_export.sh > $@

zotero/artists-books.csv: zotero/items_export.sh zotero/items_export.sql
	./zotero/items_export.sh "Artists' Books Collection" > $@

# (No reference-works export target: the canonical reference-works.csv is built by
# dedup.py straight from zotero.sqlite, so the "Reference resources" collection
# needs no intermediate CSV export.)

# Zotero "Cited:" notes normalized to well-formed XHTML for SPARQL-Anything
# (issue #53). freeze_citations.py reads these to build the frozen citations.ttl.
zotero/notes.xml: zotero/notes_export.sh zotero/notes_export.sql zotero/notes_export.py
	./zotero/notes_export.sh > $@

FUZZY := ../tools/fuzzy-match

# One-time cross-library dedup (issue #82, Phase 0). Collapses the same work
# catalogued across lib 1/2/3 into one canonical node (canonical key by
# precedence lib 3 > lib 2 > lib 1; see README.md "Canonical key scheme") and
# emits the authoritative artists'-book and reference-work lists plus a review
# CSV of the uncertain lib-1 fuzzy attaches. Reads zotero/zotero.sqlite directly
# (no intermediate export CSVs) and runs in the shared fuzzy-match venv. Grouped
# target (&:) -- one recipe run produces all three files.
artists-books.csv reference-works.csv artists-books-dedup-review.csv &: \
		$(FUZZY)/dedup.py $(FUZZY)/match.py | $(FUZZY)/venv/bin/python
	$(FUZZY)/venv/bin/python $(FUZZY)/dedup.py \
		--db zotero/zotero.sqlite \
		--out-books artists-books.csv \
		--out-refs reference-works.csv \
		--review artists-books-dedup-review.csv

# Frozen citations (issue #82, Phase 0, task 3). Reads the Zotero "Cited:" notes
# and emits one ab:Citation per (reference work, artist's book) against the
# canonical URIs from the two dedup lists above, capturing page numbers (#43/#44)
# from the note markup. Generated once, committed, and loaded into Fuseki as-is
# (no citations.rq); the review CSV surfaces the uncertain/unmatched paragraphs.
# The paragraph -> reference-work match reuses cite_match.py's matcher. artists-books.csv
# and reference-works.csv are committed inputs with their own target above, so they
# are read but not listed as prerequisites (a rebuild here doesn't re-run the dedup).
citations.ttl citations-review.csv &: zotero/notes.xml \
		$(FUZZY)/freeze_citations.py $(FUZZY)/cite_match.py | $(FUZZY)/venv/bin/python
	$(FUZZY)/venv/bin/python $(FUZZY)/freeze_citations.py \
		--notes zotero/notes.xml \
		--refs reference-works.csv \
		--books artists-books.csv \
		--out citations.ttl \
		--review citations-review.csv


# Build the fuzzy-match venv on demand (order-only prerequisite above).
$(FUZZY)/venv/bin/python:
	$(MAKE) -C $(FUZZY)

# Harvest full MARC records from UNC's Z39.50 server for the items in a CSV.
# Resumable harvest state lives under marc/harvest/<csv-stem>/ (gitignored);
# only the committed marc/<stem>-marc.xml is the build product. Requires the
# YAZ toolkit (yaz-client, yaz-marcdump), built on demand under tools/yaz-client/.
# Both the harvester script and the YAZ toolkit are order-only prerequisites
# (| ...) so editing marc_harvest.py or rebuilding the toolkit does not by
# itself trigger a re-harvest -- that hits an external server, so it only
# reruns when the source CSV changes.
YAZ := ../tools/yaz-client

# The MARC harvest emits a per-record zip archive (#81) -- one <key>.xml per
# record -- not one big <collection> file; the construct queries read it via
# nested Archive -> XML triplifiers.
#
# Both canonical harvests read a deduped list at the sources/ root (canonicalKey
# column), not a per-library zotero/ export, so they get explicit rules that
# override the marc/%-marc.zip pattern below.
#
# The canonical artists'-book harvest (issue #84). The ~1,340 already-harvested
# held books are NOT re-harvested: they are merged from the frozen, re-keyed
# marc/artists-books-held-marc.xml (a one-time artifact of marc/rekey_held.py, so
# an order-only prerequisite) via --premerged, and only the ~6,619 non-held books
# hit the Z39.50/SRU servers here.
marc/artists-books-marc.zip: artists-books.csv \
		| marc/artists-books-held-marc.xml marc/marc_harvest.py \
		  $(YAZ)/bin/yaz-client $(YAZ)/bin/zoomfetch
	python3 marc/marc_harvest.py --csv $< --out $@ \
		--premerged marc/artists-books-held-marc.xml

# The canonical reference-work harvest. Reads the deduped reference-works.csv (not
# the pre-dedup "Reference resources" collection), so each record is stamped with
# the canonical key -- keeping the archive to exactly the canonical works, with no
# losing-key duplicates. row_key() prefers canonicalKey, and the hand-supplied
# marc/reference-works-manual.xml (derived from the CSV stem) is
# merged for the items no reachable catalogue serves.
marc/reference-works-marc.zip: reference-works.csv | marc/marc_harvest.py \
		$(YAZ)/bin/yaz-client $(YAZ)/bin/zoomfetch
	python3 marc/marc_harvest.py --csv $< --out $@

marc/%-marc.zip: zotero/%.csv | marc/marc_harvest.py \
		$(YAZ)/bin/yaz-client $(YAZ)/bin/zoomfetch
	python3 marc/marc_harvest.py --csv $< --out $@

# Build the YAZ toolkit on demand (order-only prerequisite above). The same
# make invocation produces yaz-marcdump and the zoomfetch driver (issue #85)
# alongside yaz-client.
$(YAZ)/bin/yaz-client $(YAZ)/bin/zoomfetch:
	$(MAKE) -C $(YAZ)
