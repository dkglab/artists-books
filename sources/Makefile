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

# Zotero "Cited:" notes normalized to one HTML file per note, packed into a zip
# for SPARQL-Anything (issue #53). The construct query reads these directly and
# computes the citation join in SPARQL (reference-resources.rq) -- no crosswalk.
zotero/notes.zip: zotero/notes_export.sh zotero/notes_export.sql zotero/notes_export.py
	./zotero/notes_export.sh $@

# ABC <-> cited-record crosswalk (issue #55). Reconciles each ABC book to the
# lib-3 record(s) describing the same work (OCLC -> ISBN -> title -> fuzzy), so
# the Cited notes living on those records can be joined onto ABC pages. The
# matcher runs in an isolated venv built under tools/fuzzy-match/.
#
# zotero/artists-books.csv and marc/artists-books-marc.xml are committed inputs
# maintained by their own targets (the MARC harvest hits an external Z39.50
# server), so they are read by the recipe but deliberately NOT prerequisites
# here -- we do not want a crosswalk rebuild to trigger a re-harvest.
FUZZY := ../tools/fuzzy-match
abc-master-crosswalk.csv: zotero/cited-records.csv $(FUZZY)/match.py | $(FUZZY)/venv/bin/python
	$(FUZZY)/venv/bin/python $(FUZZY)/match.py \
		--abc zotero/artists-books.csv \
		--marc marc/artists-books-marc.xml \
		--cited zotero/cited-records.csv \
		--out $@

# NOTE (#42): the citation <-> reference-resource match used to be precomputed here
# by tools/fuzzy-match/cite_match.py into citation-crosswalk.csv. It is now computed
# live in SPARQL by queries/reference-resources.rq, which reads the note HTML
# (zotero/notes.zip) and substring-matches the reference title against each
# paragraph. The crosswalk and cite_match.py were removed.

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
marc/%-marc.xml: zotero/%.csv | marc/marc_harvest.py $(YAZ)/bin/yaz-client
	python3 marc/marc_harvest.py --csv $< --out $@

# Build the YAZ toolkit on demand (order-only prerequisite above). The same
# make invocation produces yaz-marcdump alongside yaz-client.
$(YAZ)/bin/yaz-client:
	$(MAKE) -C $(YAZ)
