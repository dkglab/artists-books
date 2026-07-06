#!/usr/bin/env bash
# Export Zotero "Cited:" notes as one HTML file per note, packed into a zip for
# SPARQL-Anything (#53).
#
# notes_export.sql selects each lib-3 cited note (parent itemKey + raw HTML);
# notes_export.py normalizes the messy note HTML and writes a reproducible zip of
# <itemKey>.html files. SQL selects, Python normalizes -- the Python step is
# stdlib-only and testable on its own stdin.
#
# Usage:
#   ./notes_export.sh notes.zip

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DB="$SCRIPT_DIR/zotero.sqlite"
SQL="$SCRIPT_DIR/notes_export.sql"
OUT="${1:?usage: notes_export.sh OUT.zip}"

sqlite3 -header -csv "$DB" < "$SQL" | python3 "$SCRIPT_DIR/notes_export.py" --out "$OUT"
