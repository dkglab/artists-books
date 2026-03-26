all-items.csv: items_export.sh items_export.sql
	./items_export.sh > $@

artists-books.csv: items_export.sh items_export.sql
	./items_export.sh "Artists' Books Collection" > $@

reference-resources.csv: items_export.sh items_export.sql
	./items_export.sh "Reference resources" > $@
