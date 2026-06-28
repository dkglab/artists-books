#!/usr/bin/env bash
# Export the lib-3 citation-index records that carry a "Cited:" note (issue #55).
#
# These are the candidate target set the ABC <-> cited-record crosswalk matches
# against. Selection is by note presence + libraryID = 3 (NOT by collection --
# see cited_records_export.sql), so there is no collection parameter.
#
# Usage:
#   ./cited_records_export.sh > cited-records.csv

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DB="$SCRIPT_DIR/zotero.sqlite"
SQL="$SCRIPT_DIR/cited_records_export.sql"

sqlite3 -header -csv "$DB" < "$SQL"
