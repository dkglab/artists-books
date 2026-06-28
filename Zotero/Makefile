all-items.csv: items_export.sh items_export.sql
	./items_export.sh > $@

artists-books.csv: items_export.sh items_export.sql
	./items_export.sh "Artists' Books Collection" > $@

reference-resources.csv: items_export.sh items_export.sql
	./items_export.sh "Reference resources" > $@

# The lib-3 citation-index records carrying a "Cited:" note -- the candidate
# target set for the ABC <-> cited-record crosswalk (issue #55).
cited-records.csv: cited_records_export.sh cited_records_export.sql
	./cited_records_export.sh > $@

# Zotero "Cited:" notes normalized to well-formed XHTML for SPARQL-Anything
# (issue #53). The construct query joins these onto ABC pages via the crosswalk.
notes.xml: notes_export.sh notes_export.sql notes_export.py
	./notes_export.sh > $@

# ABC <-> cited-record crosswalk (issue #55). Reconciles each ABC book to the
# lib-3 record(s) describing the same work (OCLC -> ISBN -> title -> fuzzy), so
# the Cited notes living on those records can be joined onto ABC pages. The
# matcher runs in an isolated venv built under tools/fuzzy-match/.
#
# artists-books.csv and artists-books-marc.xml are committed inputs maintained
# by their own targets (the MARC harvest hits an external Z39.50 server), so
# they are read by the recipe but deliberately NOT prerequisites here -- we do
# not want a crosswalk rebuild to trigger a re-harvest.
FUZZY := ../tools/fuzzy-match
abc-master-crosswalk.csv: cited-records.csv $(FUZZY)/match.py | $(FUZZY)/venv/bin/python
	$(FUZZY)/venv/bin/python $(FUZZY)/match.py \
		--abc artists-books.csv \
		--marc artists-books-marc.xml \
		--cited cited-records.csv \
		--out $@

# Build the fuzzy-match venv on demand (order-only prerequisite above).
$(FUZZY)/venv/bin/python:
	$(MAKE) -C $(FUZZY)

# Harvest full MARC records from UNC's Z39.50 server for the items in a CSV.
# Resumable harvest state lives under marc/<csv-stem>/ (gitignored); only the
# committed <stem>-marc.xml is the build product. Requires the YAZ toolkit
# (yaz-client, yaz-marcdump). Hits an external server, so it only reruns when
# the source CSV changes.
%-marc.xml: %.csv marc_harvest.py
	python3 marc_harvest.py --csv $< --out $@
