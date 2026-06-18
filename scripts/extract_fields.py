#!/usr/bin/env python3
"""Extract every field-tracking row from website_sources_of_info.xlsx into JSON.

One JSON record per data row (skipping each sheet's header). The XLSX columns
differ per sheet, so we map each sheet's headers onto a single normalized schema
and copy every non-empty cell verbatim -- nothing is summarized or dropped. The
resulting scripts/website_sources_of_info.json is a faithful, diffable backup of
the spreadsheet and the input to create_field_issues.py.

Usage: python scripts/extract_fields.py
"""

import json
from pathlib import Path

import openpyxl

REPO = Path(__file__).resolve().parent.parent
XLSX = REPO / "website_sources_of_info.xlsx"
OUT = REPO / "scripts" / "website_sources_of_info.json"

# Normalized schema -> the set of header strings (lowercased, stripped) that map
# to it across the various sheets. Headers not in any of these sets are still
# captured under an "extra" map so we can never silently drop a column.
HEADER_MAP = {
    "field": {"page info"},
    "vocab": {"term in abci vocabulary", "in vocab", "in vocabulary"},
    "acceptable_source": {"acceptable source for input"},
    "source": {"source of info", "source"},
    "item_name": {"item name in source"},
    "questions": {"questions"},
    "notes": {"notes"},
    "description": {"description"},
}


def norm(s):
    return "" if s is None else str(s).strip()


def header_to_key(header, col_idx, seen):
    """Map a header cell to a normalized key.

    The reference-page sheet has a blank header over its purpose/description
    column; treat a trailing blank-header column as 'description' if that slot
    isn't already filled, otherwise stash it as extra_<col>.
    """
    h = header.lower()
    for key, names in HEADER_MAP.items():
        if h in names:
            return key
    if header == "":
        if "description" not in seen:
            return "description"
        return f"extra_{col_idx}"
    return f"extra_{col_idx}"


def main():
    wb = openpyxl.load_workbook(XLSX, data_only=True)
    records = []
    for ws in wb.worksheets:
        rows = list(ws.iter_rows(values_only=True))
        if not rows:
            continue
        headers = [norm(c) for c in rows[0]]
        # Resolve each column index to a normalized key.
        seen = set()
        keys = []
        for i, h in enumerate(headers):
            k = header_to_key(h, i, seen)
            seen.add(k)
            keys.append(k)
        for r_i, row in enumerate(rows[1:], start=2):
            cells = [norm(c) for c in row]
            if not any(cells):
                continue
            rec = {"page": ws.title, "sheet_row": r_i}
            for k in HEADER_MAP:
                rec[k] = ""
            for col_i, (k, val) in enumerate(zip(keys, cells)):
                if k in rec and k not in ("page", "sheet_row"):
                    # Merge if two columns map to the same key (shouldn't happen
                    # given the data, but be safe and never overwrite content).
                    rec[k] = (rec[k] + "\n" + val).strip() if rec[k] and val else (rec[k] or val)
                else:
                    if val:
                        rec[k] = val
            records.append(rec)

    OUT.write_text(json.dumps(records, indent=2, ensure_ascii=False) + "\n")
    print(f"Wrote {len(records)} records to {OUT.relative_to(REPO)}")
    by_page = {}
    for rec in records:
        by_page[rec["page"]] = by_page.get(rec["page"], 0) + 1
    for page, n in by_page.items():
        print(f"  {page}: {n}")


if __name__ == "__main__":
    main()
