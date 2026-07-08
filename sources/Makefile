# Regenerates the committed source artifacts under sources/. Run from sources/
# (e.g. `make -C sources <target>`). Two tracks live in subdirs — zotero/ (the
# Zotero DB exports) and marc/ (the Z39.50 MARC harvest) — while the crosswalks
# that bridge them stay at this level.

zotero/all-items.csv: zotero/items_export.sh zotero/items_export.sql
	./zotero/items_export.sh > $@

zotero/artists-books.csv: zotero/items_export.sh zotero/items_export.sql
	./zotero/items_export.sh "Artists' Books Collection" > $@

zotero/reference-resources.csv: zotero/items_export.sh zotero/items_export.sql
	./zotero/items_export.sh "Reference resources" > $@

# The lib-3 citation-index records carrying a "Cited:" note -- the candidate
# target set for the ABC <-> cited-record crosswalk (issue #55).
zotero/cited-records.csv: zotero/cited_records_export.sh zotero/cited_records_export.sql
	./zotero/cited_records_export.sh > $@

# Zotero "Cited:" notes normalized to well-formed XHTML for SPARQL-Anything
# (issue #53). The construct query joins these onto ABC pages via the crosswalk.
zotero/notes.xml: zotero/notes_export.sh zotero/notes_export.sql zotero/notes_export.py
	./zotero/notes_export.sh > $@

# ABC <-> cited-record crosswalk (issue #55). Reconciles each ABC book to the
# lib-3 record(s) describing the same work (OCLC -> ISBN -> title -> fuzzy), so
# the Cited notes living on those records can be joined onto ABC pages. The
# matcher runs in an isolated venv built under tools/fuzzy-match/.
#
# NOTE: this is a legacy Phase-0 target (the abc<->cited crosswalk), retired from
# the repeatable build (citations are now frozen in citations.ttl). match.py reads
# a single-collection marc/artists-books-marc.xml, but #81 replaced that monolith
# with the per-record archive marc/artists-books-marc.zip, so this recipe is no
# longer runnable as-is; the committed abc-master-crosswalk.csv stays as a frozen
# artifact. (zotero/artists-books.csv and the MARC were always read, not
# prerequisites, so a crosswalk rebuild never triggered a re-harvest.)
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
# artists-books.csv/reference-works.csv are committed inputs with their own
# target above, so (like the crosswalks) they are read but not prerequisites.
citations.ttl citations-review.csv &: zotero/notes.xml \
		$(FUZZY)/freeze_citations.py $(FUZZY)/cite_match.py | $(FUZZY)/venv/bin/python
	$(FUZZY)/venv/bin/python $(FUZZY)/freeze_citations.py \
		--notes zotero/notes.xml \
		--refs reference-works.csv \
		--books artists-books.csv \
		--out citations.ttl \
		--review citations-review.csv

abc-master-crosswalk.csv: zotero/cited-records.csv $(FUZZY)/match.py | $(FUZZY)/venv/bin/python
	$(FUZZY)/venv/bin/python $(FUZZY)/match.py \
		--abc zotero/artists-books.csv \
		--marc marc/artists-books-marc.xml \
		--cited zotero/cited-records.csv \
		--out $@

# Citation <-> reference-resource crosswalk (issue #42). Each "Cited:" note
# paragraph (zotero/notes.xml) is a free-text reference to a reference work;
# this reconciles it to a row in zotero/reference-resources.csv (the title
# appears verbatim in the paragraph -> substring match, <em> title + year
# corroborate), so citations can be minted under reference/<refItemKey>/...
# abc-master-crosswalk.csv scopes the paragraphs to the cited records actually
# in use. Runs in the shared fuzzy-match venv; low-confidence/unmatched rows
# carry review=yes and are excluded from the construct query's auto-join.
citation-crosswalk.csv: zotero/notes.xml zotero/reference-resources.csv abc-master-crosswalk.csv \
		$(FUZZY)/cite_match.py | $(FUZZY)/venv/bin/python
	$(FUZZY)/venv/bin/python $(FUZZY)/cite_match.py \
		--notes zotero/notes.xml \
		--refs zotero/reference-resources.csv \
		--abc-crosswalk abc-master-crosswalk.csv \
		--out $@

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
# The canonical artists'-book harvest (issue #84). Unlike the reference track
# (pattern rule below), the canonical AB list lives at the sources/ root with a
# canonicalKey column, so this explicit rule overrides the marc/%-marc.zip
# pattern. The ~1,340 already-harvested held books are NOT re-harvested: they are
# merged from the frozen, re-keyed marc/artists-books-held-marc.xml (a one-time
# artifact of marc/rekey_held.py, so an order-only prerequisite) via --premerged,
# and only the ~6,619 non-held books hit the Z39.50/SRU servers here.
marc/artists-books-marc.zip: artists-books.csv \
		| marc/artists-books-held-marc.xml marc/marc_harvest.py $(YAZ)/bin/yaz-client
	python3 marc/marc_harvest.py --csv $< --out $@ \
		--premerged marc/artists-books-held-marc.xml

marc/%-marc.zip: zotero/%.csv | marc/marc_harvest.py $(YAZ)/bin/yaz-client
	python3 marc/marc_harvest.py --csv $< --out $@

# Build the YAZ toolkit on demand (order-only prerequisite above). The same
# make invocation produces yaz-marcdump alongside yaz-client.
$(YAZ)/bin/yaz-client:
	$(MAKE) -C $(YAZ)
