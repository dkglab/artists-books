#!/usr/bin/env python3
"""Turn the creator name review page's verdicts into decisions.csv rows (#226).

The page keeps one document per case (its name key) in its `verdicts`
collection:

  {status: "decided" | "unsure", same: {agentKey: earlierAgentKey | "new" | "?"},
   zotero: {bookKey: agentKey | "none"}, notes,
   agents: [{key, label, lcId, decisionKey}], places: {bookKey: placeKey}, ...}

`agents` and `places` are the case as it was when the verdict was saved, so a
verdict is read against its own record list, never against a later
cases.json in which merges have renumbered or removed records.

A decided verdict becomes:
  - `merge` for each record judged the same person as an earlier one;
  - `distinct` for each pair of people judged different (records judged
    "Can't tell" are left out, so the case stays on the page);
  - `place` for each Zotero-only book: credited to the chosen record, or to
    nobody ("none").
An unsure verdict writes no rows; its note is printed.

Each row's note is "[review-page <case>] <reviewer's note>". Rows with that
prefix are the page's: a pull replaces the rows of every case it has a verdict
file for, so pulling is idempotent and a verdict changed on the page changes
its rows here. Rows of a case with no file in the folder are kept, so a
partial folder (one page of a listing) loses nothing; to drop a case's rows,
delete them by hand. Hand-written rows are always kept. An empty folder is
refused.

Save the collection first (Claude: ArtifactData `list` of `verdicts` with
`out_dir`), then run:

  python3 sources/creators/pull_verdicts.py <out_dir>/verdicts
  make -C sources -B creators/agents.csv
"""
import csv
import glob
import json
import os
import re
import sys

DECISIONS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "decisions.csv")
TAG = re.compile(r"^\[review-page ([^\]\s]+)\]")


def rows_for(case, v, warnings):
    if v.get("status") != "decided":
        return []
    notes = (v.get("notes") or "").strip()
    note = f"[review-page {case}] {notes}".strip()
    agents = v.get("agents") or []
    dkey = {a["key"]: a.get("decisionKey") or "" for a in agents}
    for a in agents:
        if not dkey[a["key"]]:
            warnings.append(f"{case}: record {a['key']} has no decision key, skipped")
    same = v.get("same") or {}

    # Person of each record: record 1 starts one, "new" another, a key joins
    # that record's person, "?" (or no answer) leaves the record out.
    person, order = {}, []
    for i, a in enumerate(agents):
        s = "new" if i == 0 else same.get(a["key"])
        if s == "new":
            person[a["key"]] = a["key"]
            order.append(a["key"])
        elif s in person:
            person[a["key"]] = person[s]
    out = []
    for a in agents:
        p = person.get(a["key"])
        if p and p != a["key"] and dkey[p] and dkey[a["key"]]:
            out.append({"action": "merge", "a": dkey[p], "b": dkey[a["key"]], "note": note})
    reps = [p for p in order if dkey[p]]
    for i, p in enumerate(reps):
        for q in reps[i + 1:]:
            out.append({"action": "distinct", "a": dkey[p], "b": dkey[q], "note": note})
    places = v.get("places") or {}
    for book, choice in sorted((v.get("zotero") or {}).items()):
        if choice in ("?", "", None):
            continue  # "Can't tell" or no answer: left on the page, no row
        if not places.get(book):
            warnings.append(f"{case}: no place key for Zotero book {book}, skipped")
        elif choice == "none":
            out.append({"action": "place", "a": places[book], "b": "", "note": note})
        elif dkey.get(choice):
            out.append({"action": "place", "a": places[book], "b": dkey[choice], "note": note})
        else:
            warnings.append(f"{case}: Zotero book {book} placed on unknown record {choice!r}, skipped")
    return out


def main(folder):
    verdicts = {}
    for p in sorted(glob.glob(os.path.join(folder, "*.json"))):
        with open(p, encoding="utf-8") as f:
            verdicts[os.path.basename(p)[:-5]] = json.load(f)
    if not verdicts:
        sys.exit(f"no verdict files (*.json) in {folder!r}; nothing pulled")

    with open(DECISIONS, newline="", encoding="utf-8") as f:
        r = csv.DictReader(f)
        cols, rows = r.fieldnames, list(r)
    def case_of(x):
        m = TAG.match(x.get("note") or "")
        return m.group(1) if m else None
    old = [x for x in rows if case_of(x) in verdicts]
    kept = [x for x in rows if case_of(x) not in verdicts]

    warnings, new = [], []
    for case, v in sorted(verdicts.items()):
        new += rows_for(case, v, warnings)
        if v.get("status") == "unsure":
            print(f"unsure  {case}: {(v.get('notes') or '').strip() or '(no note)'}")

    key = lambda x: (x["action"], x["a"], x["b"], x["note"])
    added = sorted(set(map(key, new)) - set(map(key, old)))
    removed = sorted(set(map(key, old)) - set(map(key, new)))
    with open(DECISIONS, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, cols, lineterminator="\n")
        w.writeheader()
        w.writerows(kept + new)
    for x in added:
        print("+ " + ",".join(x))
    for x in removed:
        print("- " + ",".join(x))
    for m in warnings:
        print("warning: " + m, file=sys.stderr)
    print(f"{len(verdicts)} verdicts -> {len(new)} rows "
          f"({len(added)} added, {len(removed)} removed)", file=sys.stderr)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
