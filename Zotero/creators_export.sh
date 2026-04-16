#!/usr/bin/env bash
# Export Zotero creators to two CSV files:
#   creators.csv       — unique creators (one row per person/organization)
#   item_creators.csv  — item-creator relations (one row per item-creator link)
#
# Usage:
#   ./creators_export.sh [collection name] [output prefix]
#
# Examples:
#   # All creators
#   ./creators_export.sh
#
#   # Single collection
#   ./creators_export.sh "To be photographed"
#
#   # Single collection with custom output prefix
#   ./creators_export.sh "To be photographed" to_be_photographed
#
# Output files: <prefix>-creators.csv and <prefix>-item_creators.csv
# Default prefix is "all".

COLLECTION="${1:-}"
PREFIX="${2:-all}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DB="$SCRIPT_DIR/zotero.sqlite"

sqlite3 \
    -cmd ".parameter set :collection \"${COLLECTION//\"/\\\"}\"" \
    -header -csv \
    "$DB" < "$SCRIPT_DIR/creators_export.sql" > "${PREFIX}-creators.csv"

sqlite3 \
    -cmd ".parameter set :collection \"${COLLECTION//\"/\\\"}\"" \
    -header -csv \
    "$DB" < "$SCRIPT_DIR/item_creators_export.sql" > "${PREFIX}-item_creators.csv"

echo "Written: ${PREFIX}-creators.csv and ${PREFIX}-item_creators.csv"
