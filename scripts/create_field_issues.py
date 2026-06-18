#!/usr/bin/env python3
"""Create one GitHub issue per field row and load them into a GitHub Project.

Reads scripts/website_sources_of_info.json (produced by extract_fields.py) and,
via the `gh` CLI:

  * creates the source:* issue labels (idempotent),
  * creates/reuses a GitHub Project on the owner, plus Page + Priority fields,
  * links the project to the repo,
  * creates one issue per row (body reproduces every non-empty cell verbatim),
  * adds each issue to the project and sets its Page field.

Idempotent / resumable: rows whose issue title already exists are skipped, so a
re-run never duplicates. Writes scripts/migration_map.json (sheet/row -> issue).

Prerequisite: the gh token needs the `project` scope and org access:
    gh auth refresh -h github.com -s project,read:org

Usage:
    python scripts/create_field_issues.py --dry-run     # preview, no writes
    python scripts/create_field_issues.py --owner dkglab --repo dkglab/artists-books
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
JSON_IN = REPO_ROOT / "scripts" / "website_sources_of_info.json"
MAP_OUT = REPO_ROOT / "scripts" / "migration_map.json"

PROJECT_TITLE = "ABCI Website Fields"

PAGE_PREFIX = {
    "Main page": "[Main]",
    "single record page": "[Single record]",
    "results page": "[Results]",
    "reference page": "[Reference]",
}

# Body sections, in display order: (json key, heading).
BODY_SECTIONS = [
    ("vocab", "Vocabulary term"),
    ("acceptable_source", "Acceptable source for input"),
    ("source", "Source of info"),
    ("item_name", "Item name in source"),
    ("questions", "Questions"),
    ("notes", "Notes"),
    ("description", "Description / purpose"),
]

# substring (lowercased) -> label name, scanned against the `source` cell.
SOURCE_LABELS = [
    ("zotero", "source:zotero"),
    ("library cat", "source:library-cat"),
    ("lib cat", "source:library-cat"),
    ("worldcat", "source:worldcat"),
    ("jstor", "source:jstor"),
    ("ulan", "source:ulan"),
    ("wikidata", "source:wikidata"),
]

LABEL_DEFS = {
    "source:zotero": ("0e8a16", "Field sourced from Zotero"),
    "source:library-cat": ("1d76db", "Field sourced from the library catalog (MARC)"),
    "source:worldcat": ("5319e7", "Field sourced from WorldCat"),
    "source:jstor": ("b60205", "Field sourced from JSTOR/Artstor"),
    "source:ulan": ("d93f0b", "Field sourced from Getty ULAN"),
    "source:wikidata": ("fbca04", "Field sourced from Wikidata"),
}


def run(cmd, *, capture=True, check=True):
    """Run a command, returning stdout. Raises on nonzero unless check=False."""
    result = subprocess.run(
        cmd,
        capture_output=capture,
        text=True,
    )
    if check and result.returncode != 0:
        sys.exit(f"Command failed ({result.returncode}): {' '.join(cmd)}\n{result.stderr}")
    return result


def issue_title(rec):
    return f"{PAGE_PREFIX.get(rec['page'], '[?]')} {rec['field']}".strip()


def issue_body(rec):
    lines = [f"**Page:** {rec['page']}"]
    for key, heading in BODY_SECTIONS:
        val = rec.get(key, "")
        if val:
            if "\n" in val:
                lines.append(f"**{heading}:**\n\n```\n{val}\n```")
            else:
                lines.append(f"**{heading}:** {val}")
    lines.append("")
    lines.append(f"_Migrated from website_sources_of_info.xlsx — {rec['page']} row {rec['sheet_row']}._")
    return "\n\n".join(lines)


def source_labels(rec):
    # Scan the source cell; fall back to item_name when source is empty (the
    # spreadsheet occasionally puts the source token in the wrong column, e.g.
    # results-page "reference books" has "zotero" under item name in source).
    src = rec.get("source", "").lower() or rec.get("item_name", "").lower()
    found = []
    for needle, label in SOURCE_LABELS:
        if needle in src and label not in found:
            found.append(label)
    return found


# ---- gh helpers -----------------------------------------------------------

def ensure_labels(repo, needed):
    for label in sorted(needed):
        color, desc = LABEL_DEFS[label]
        r = run(
            ["gh", "label", "create", label, "--repo", repo,
             "--color", color, "--description", desc],
            check=False,
        )
        if r.returncode == 0:
            print(f"  created label {label}")
        elif "already exists" in r.stderr:
            print(f"  label {label} already exists")
        else:
            sys.exit(f"label create failed: {r.stderr}")


def ensure_project(owner):
    existing = run(["gh", "project", "list", "--owner", owner, "--format", "json"]).stdout
    for p in json.loads(existing).get("projects", []):
        if p.get("title") == PROJECT_TITLE:
            print(f"  reusing project #{p['number']} ({p['url']})")
            return p["number"]
    created = json.loads(
        run(["gh", "project", "create", "--owner", owner,
             "--title", PROJECT_TITLE, "--format", "json"]).stdout
    )
    print(f"  created project #{created['number']} ({created['url']})")
    return created["number"]


def project_node_id(owner, number):
    return json.loads(
        run(["gh", "project", "view", str(number), "--owner", owner, "--format", "json"]).stdout
    )["id"]


def ensure_fields(owner, number):
    fields = json.loads(
        run(["gh", "project", "field-list", str(number), "--owner", owner,
             "--format", "json"]).stdout
    )["fields"]
    names = {f["name"] for f in fields}
    if "Page" not in names:
        run(["gh", "project", "field-create", str(number), "--owner", owner,
             "--name", "Page", "--data-type", "SINGLE_SELECT",
             "--single-select-options",
             "Main page,single record page,results page,reference page"])
        print("  created Page field")
    if "Priority" not in names:
        run(["gh", "project", "field-create", str(number), "--owner", owner,
             "--name", "Priority", "--data-type", "SINGLE_SELECT",
             "--single-select-options", "High,Medium,Low"])
        print("  created Priority field")
    # Re-fetch so we have ids for any field we just created.
    fields = json.loads(
        run(["gh", "project", "field-list", str(number), "--owner", owner,
             "--format", "json"]).stdout
    )["fields"]
    page = next(f for f in fields if f["name"] == "Page")
    option_ids = {o["name"]: o["id"] for o in page.get("options", [])}
    return page["id"], option_ids


def link_repo(owner, number, repo):
    run(["gh", "project", "link", str(number), "--owner", owner, "--repo", repo],
        check=False)


def existing_issue_titles(repo):
    out = run(["gh", "issue", "list", "--repo", repo, "--state", "all",
               "--limit", "300", "--json", "number,title"]).stdout
    return {i["title"]: i["number"] for i in json.loads(out)}


# ---- main -----------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--owner", default="dkglab")
    ap.add_argument("--repo", default="dkglab/artists-books")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    records = json.loads(JSON_IN.read_text())
    print(f"Loaded {len(records)} records from {JSON_IN.relative_to(REPO_ROOT)}")

    if args.dry_run:
        for rec in records:
            labels = source_labels(rec)
            print(f"\n### {issue_title(rec)}")
            print(f"    page={rec['page']!r}  labels={labels}")
            preview = issue_body(rec).replace("\n", "\n    ")
            print(f"    {preview}")
        print(f"\n[dry-run] would create/sync {len(records)} issues. No changes made.")
        return

    needed_labels = {l for rec in records for l in source_labels(rec)}
    print("Ensuring labels...")
    ensure_labels(args.repo, needed_labels)

    print("Ensuring project...")
    number = ensure_project(args.owner)
    proj_id = project_node_id(args.owner, number)
    link_repo(args.owner, number, args.repo)
    page_field_id, page_options = ensure_fields(args.owner, number)

    print("Fetching existing issues (for resume)...")
    existing = existing_issue_titles(args.repo)

    mapping = []
    for rec in records:
        title = issue_title(rec)
        labels = source_labels(rec)
        if title in existing:
            print(f"  skip (exists): {title} -> #{existing[title]}")
            mapping.append({"page": rec["page"], "sheet_row": rec["sheet_row"],
                            "title": title, "issue": existing[title], "created": False})
            continue
        cmd = ["gh", "issue", "create", "--repo", args.repo,
               "--title", title, "--body", issue_body(rec)]
        for l in labels:
            cmd += ["--label", l]
        url = run(cmd).stdout.strip().splitlines()[-1]
        print(f"  created {title} -> {url}")

        item = json.loads(
            run(["gh", "project", "item-add", str(number), "--owner", args.owner,
                 "--url", url, "--format", "json"]).stdout
        )
        opt_id = page_options.get(rec["page"])
        if opt_id:
            run(["gh", "project", "item-edit", "--id", item["id"],
                 "--project-id", proj_id, "--field-id", page_field_id,
                 "--single-select-option-id", opt_id])
        mapping.append({"page": rec["page"], "sheet_row": rec["sheet_row"],
                        "title": title, "url": url, "created": True})

    MAP_OUT.write_text(json.dumps(mapping, indent=2, ensure_ascii=False) + "\n")
    created = sum(1 for m in mapping if m["created"])
    print(f"\nDone. {created} created, {len(mapping) - created} already existed.")
    print(f"Map written to {MAP_OUT.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
