#!/usr/bin/env bash
# Export Zotero items to CSV.
#
# Usage:
#   ./items_export.sh [collection name]
#
# Examples:
#   # All items
#   ./items_export.sh > items.csv
#
#   # Single collection
#   ./items_export.sh "To be photographed" > to_be_photographed.csv
#
#   # Or directly with sqlite3
#   sqlite3 -cmd ".parameter set :collection 'To be photographed'" \
#           -header -csv zotero.sqlite < items_export.sql
#
# Note: filtered exports still show all collection memberships for each item,
# not just the one used to filter.

COLLECTION="${1:-}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DB="$SCRIPT_DIR/zotero.sqlite"
SQL="$SCRIPT_DIR/items_export.sql"

sqlite3 \
    -cmd ".parameter set :collection '${COLLECTION//\'/\'\'}'" \
    -header -csv \
    "$DB" < "$SQL"
