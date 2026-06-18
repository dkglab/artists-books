#!/usr/bin/env python3
"""Set Status (always) and Priority (only if unset) on an ABCI Website Fields
project item, by issue number.

Used during the field-by-field review pass: as each issue is refined we set its
workflow Status and, if no Priority has been assigned yet, a suggested one.

Usage:
    python scripts/set_project_fields.py <issue#> --status "In Progress" --priority High
    python scripts/set_project_fields.py 12 --status "In Progress" --priority High
"""

import argparse
import json
import subprocess
import sys

OWNER = "dkglab"
PROJECT = "4"


def gh_json(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(f"command failed: {' '.join(cmd)}\n{r.stderr}")
    return json.loads(r.stdout) if r.stdout.strip() else {}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("issue", type=int)
    ap.add_argument("--status", required=True, help="Todo | In Progress | Done")
    ap.add_argument("--priority", required=True, help="suggested High | Medium | Low (applied only if unset)")
    ap.add_argument("--target", help="Target date YYYY-MM-DD (merge date of the finishing commit; set when Status=Done)")
    args = ap.parse_args()

    proj_id = gh_json(["gh", "project", "view", PROJECT, "--owner", OWNER, "--format", "json"])["id"]
    fields = gh_json(["gh", "project", "field-list", PROJECT, "--owner", OWNER, "--format", "json"])["fields"]
    fmap = {f["name"]: f for f in fields}

    def option_id(field_name, opt_name):
        for o in fmap[field_name].get("options", []):
            if o["name"].lower() == opt_name.lower():
                return o["id"]
        sys.exit(f"no option {opt_name!r} on field {field_name!r}")

    items = gh_json(["gh", "project", "item-list", PROJECT, "--owner", OWNER,
                     "--format", "json", "--limit", "200"])["items"]
    item = next((i for i in items if i.get("content", {}).get("number") == args.issue), None)
    if not item:
        sys.exit(f"issue #{args.issue} not found as a project item")

    def edit(field_name, opt_name):
        subprocess.run(
            ["gh", "project", "item-edit", "--id", item["id"], "--project-id", proj_id,
             "--field-id", fmap[field_name]["id"],
             "--single-select-option-id", option_id(field_name, opt_name)],
            check=True, capture_output=True, text=True,
        )

    def edit_date(field_name, value):
        subprocess.run(
            ["gh", "project", "item-edit", "--id", item["id"], "--project-id", proj_id,
             "--field-id", fmap[field_name]["id"], "--date", value],
            check=True, capture_output=True, text=True,
        )

    edit("Status", args.status)
    print(f"#{args.issue}: Status -> {args.status}")

    current_target = item.get("target")  # item-list flattens fields by lowercased name
    if args.target:
        if current_target:
            print(f"#{args.issue}: Target already set ({current_target}) — left unchanged")
        else:
            edit_date("Target", args.target)
            print(f"#{args.issue}: Target -> {args.target}")
    elif args.status.lower() == "done" and not current_target:
        print(f"#{args.issue}: WARNING Status=Done but no --target given (set the finishing commit's merge date)")

    current_priority = item.get("priority")  # item-list flattens fields by lowercased name
    if current_priority:
        print(f"#{args.issue}: Priority already set ({current_priority}) — left unchanged")
    else:
        edit("Priority", args.priority)
        print(f"#{args.issue}: Priority -> {args.priority} (suggested)")


if __name__ == "__main__":
    main()
