all-items.csv: items_export.sh items_export.sql
	./items_export.sh > $@

artists-books.csv: items_export.sh items_export.sql
	./items_export.sh "Artists' Books Collection" > $@

reference-resources.csv: items_export.sh items_export.sql
	./items_export.sh "Reference resources" > $@

# Harvest full MARC records from UNC's Z39.50 server for the items in a CSV.
# Resumable harvest state lives under marc/<csv-stem>/ (gitignored); only the
# committed <stem>-marc.xml is the build product. Requires the YAZ toolkit
# (yaz-client, yaz-marcdump). Hits an external server, so it only reruns when
# the source CSV changes.
%-marc.xml: %.csv marc_harvest.py
	python3 marc_harvest.py --csv $< --out $@
