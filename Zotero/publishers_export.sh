#!/usr/bin/env bash
# Export Zotero publishers to two CSV files:
#   publishers.csv       — unique publisher names
#   item_publishers.csv  — item-publisher relations (one row per item with a publisher)
#
# Usage:
#   ./publishers_export.sh [collection name] [output prefix]
#
# Examples:
#   # All publishers
#   ./publishers_export.sh
#
#   # Single collection
#   ./publishers_export.sh "To be photographed"
#
#   # Single collection with custom output prefix
#   ./publishers_export.sh "To be photographed" to_be_photographed
#
# Output files: <prefix>-publishers.csv and <prefix>-item_publishers.csv
# Default prefix is "all".

COLLECTION="${1:-}"
PREFIX="${2:-all}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DB="$SCRIPT_DIR/zotero.sqlite"

sqlite3 \
    -cmd ".parameter set :collection \"${COLLECTION//\"/\\\"}\"" \
    -header -csv \
    "$DB" < "$SCRIPT_DIR/publishers_export.sql" > "${PREFIX}-publishers.csv"

sqlite3 \
    -cmd ".parameter set :collection \"${COLLECTION//\"/\\\"}\"" \
    -header -csv \
    "$DB" < "$SCRIPT_DIR/item_publishers_export.sql" > "${PREFIX}-item_publishers.csv"

echo "Written: ${PREFIX}-publishers.csv and ${PREFIX}-item_publishers.csv"
