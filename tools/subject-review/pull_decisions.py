#!/usr/bin/env python3
"""Merge the subject review page's decisions (issue #225) into the two decisions files.

The page (index.html, published as a claude.ai artifact) keeps two
collections in its shared database:

  rows/<id>       one per heading: {q, cluster, take, final, cons, fine, notes, ...}
                  (fine, Priya's finer category, is written to
                  subjects/fine-categories.csv, as the site has only two)
                  q is the queue:
                    pairs    the #164 reconciliation. take head keeps the row,
                             priya/edit write `final`, unsure leaves it.
                    draft    a draft place. confirm keeps the row and
                             clears its draft note, out leaves it out, edit
                             writes `final`, unsure leaves it.
                    overlap  subject or construction. cons/subj/both/
                             neither set both schemes; `final` is the subject
                             row, `cons` the construction concept. A heading
                             that's also in pairs gets only its construction
                             side here.
  concepts/<id>   a subject concept's own decision. {prefLabel, category}: a
                  label for the whole concept, which every include=y row of
                  subjects/decisions.csv under it gets. {mergeInto}: the
                  concept is merged into another, and its rows move there.
                  (The Labels tab's rows only record which choice was made;
                  their effect is here.)

Save both collections first (Claude: ArtifactData `list` of `rows` and of
`concepts` with `out_dir`, querying `rows` per `g` if it holds over 1,000),
then run from the repo root:

  python3 tools/subject-review/pull_decisions.py <out_dir>

It checks what it writes the way the page does (slug concept IDs, valid
categories, labels, and one label and category per concept across each whole
file) and writes nothing if any check fails. Row order, columns and line
endings are kept. Prints what changed.
"""
import collections
import csv
import glob
import io
import json
import os
import re
import sys

SUBJECTS = "sources/subjects/decisions.csv"
CONSTRUCTION = "sources/construction/decisions.csv"
SHEET = "sources/subjects/pr164-review.csv"
OVERLAP = "sources/subjects/construction-overlap-review.csv"
FINE = "sources/subjects/fine-categories.csv"   # Priya's finer categories, kept
SLUG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
CATEGORIES = {"topical", "geographic"}
CONS_CATEGORIES = {"material", "process-technique", "hand-papermaking-traditions",
                   "structure-physical-format", "enclosure", "genre-form"}
FIELDS = ["include", "conceptId", "category", "prefLabel", "exactMatch", "note"]
CONS_FIELDS = ["include", "conceptId", "category", "prefLabel", "note"]
DRAFT = "auto-seeded draft; review"


def docs(folder):
    out = []
    for path in sorted(glob.glob(os.path.join(folder, "**", "*.json"), recursive=True)):
        with open(path, encoding="utf-8") as f:
            out.append(json.load(f))
    return out


def load(path):
    with open(path, newline="", encoding="utf-8") as f:
        raw = f.read()
    reader = csv.DictReader(io.StringIO(raw, newline=""))
    return raw, reader.fieldnames, list(reader)


def save(path, raw, cols, rows):
    le = "\r\n" if "\r\n" in raw else "\n"
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, cols, lineterminator=le)
        w.writeheader()
        w.writerows(rows)


def left_out(note=""):
    return {"include": "n", "conceptId": "", "category": "", "prefLabel": "", "exactMatch": "", "note": note}


def reviewed(note):
    """A decision on the page is the review, so the seed's '...; review' notes go."""
    return "" if note.endswith("; review") else note


def clean(final):
    new = {f: (final or {}).get(f, "").strip() for f in FIELDS}
    new["note"] = reviewed(new["note"])
    return new if new["include"] == "y" else left_out(new["note"])


def subject_final(d, current, in_pairs):
    """The subjects row a decision writes, or None to leave it as it is."""
    q, take = d.get("q") or "pairs", d.get("take")
    if q == "labels":
        return None   # its effect is in the concepts collection
    if q == "pairs":
        if take == "head" and current["note"] != reviewed(current["note"]):
            return {**{f: current[f] for f in FIELDS}, "note": ""}
        return clean(d.get("final")) if take in {"priya", "edit"} else None
    if q == "draft":
        if take == "confirm":
            return {**{f: current[f] for f in FIELDS}, "note": ""}
        return left_out() if take == "out" else clean(d.get("final")) if take == "edit" else None
    if in_pairs:
        return None
    if take == "cons":
        return left_out("construction")
    if take == "neither":
        return left_out()
    return clean(d.get("final")) if take in {"subj", "both"} else None


def main(out_dir):
    # a document with no heading is only a lease a first write took (index.html)
    rows = [d for d in docs(os.path.join(out_dir, "rows")) if d.get("cluster")]
    concept_docs = docs(os.path.join(out_dir, "concepts"))
    merges = {d["id"]: d["mergeInto"] for d in concept_docs if d.get("mergeInto")}
    overrides = {d["id"]: d for d in concept_docs if d.get("prefLabel")}
    s_raw, s_cols, s_rows = load(SUBJECTS)
    c_raw, c_cols, c_rows = load(CONSTRUCTION)
    s_by = {r["cluster"]: r for r in s_rows}
    c_by = {r["cluster"]: r for r in c_rows}
    labels = {r["cluster"]: r["labels"] for r in csv.DictReader(open(SHEET, newline="", encoding="utf-8"))}
    labels.update({r["cluster"]: r["labels"] for r in csv.DictReader(open(OVERLAP, newline="", encoding="utf-8"))})
    in_pairs = {r["cluster"] for r in csv.DictReader(open(SHEET, newline="", encoding="utf-8"))}

    errors, changed = [], []
    takes = collections.Counter(f"{d.get('q') or 'pairs'} {d.get('take') or 'todo'}" for d in rows)

    def put(by, out, cols, k, new, fields, where):
        r = by.get(k)
        if r is None:
            if new["include"] != "y":
                return
            r = {c: "" for c in cols}
            r.update(cluster=k, labels=labels.get(k, ""))
            out.append(r)
            by[k] = r
        before = {f: r[f] for f in fields}
        r.update({f: new[f] for f in fields})
        if before != {f: r[f] for f in fields}:
            changed.append(f"{where} {k}: " + ", ".join(f"{f} {before[f]!r} -> {r[f]!r}" for f in fields if before[f] != r[f]))

    # subjects: pairs first, then the other queues; a cluster has one owner
    order = {"pairs": 0, "draft": 1, "overlap": 2}
    for d in sorted(rows, key=lambda d: order.get(d.get("q") or "pairs", 3)):
        k = d["cluster"]
        cur = s_by.get(k, left_out())
        new = subject_final(d, cur, (d.get("q") == "overlap") and k in in_pairs)
        if new is None:
            continue
        if new["include"] == "y":
            # a merged concept is left to the merge loop below, which gives
            # the row the target's label and category as well as its ID
            o = overrides.get(new["conceptId"])
            if o:
                new.update(prefLabel=o["prefLabel"], category=o["category"])
            if not SLUG.match(new["conceptId"]):
                errors.append(f"subjects {k}: concept ID {new['conceptId']!r} isn't a slug")
            if new["category"] not in CATEGORIES:
                errors.append(f"subjects {k}: category {new['category']!r}")
            if not new["prefLabel"]:
                errors.append(f"subjects {k}: no label")
        put(s_by, s_rows, s_cols, k, new, FIELDS, "subjects")

    # Priya's finer category (topical-people, geographic-city, ...) becomes one
    # of the two the site has; the finer one is kept beside the decisions, in
    # FINE, for every heading whose row is taken from her side. The notes
    # column isn't used for it: its values are markers ("complex", ...).
    fine = {}
    if os.path.exists(FINE):
        fine = {r["cluster"]: r["fineCategory"] for r in csv.DictReader(open(FINE, newline="", encoding="utf-8"))}
    for d in rows:
        if (d.get("q") or "pairs") != "pairs" or d.get("take") in {None, "", "unsure"}:
            continue
        k, f = d["cluster"], (d.get("fine") or "").strip()
        if d["take"] in {"priya", "edit"} and f and s_by.get(k, {}).get("include") == "y":
            fine[k] = f
        else:
            fine.pop(k, None)

    # construction: the overlap queue's construction side
    cons_label = {r["conceptId"]: (r["prefLabel"], r["category"]) for r in c_rows if r["include"] == "y" and r["conceptId"]}
    for d in rows:
        if d.get("q") != "overlap" or d.get("take") in {None, "", "unsure"}:
            continue
        k = d["cluster"]
        if d["take"] in {"subj", "neither"}:
            if k in c_by:
                put(c_by, c_rows, c_cols, k, {"include": "n", "conceptId": "", "category": "", "prefLabel": "", "note": "subject (#225 review)" if d["take"] == "subj" else ""}, CONS_FIELDS, "construction")
            continue
        c = {f: (d.get("cons") or {}).get(f, "").strip() for f in ["conceptId", "category", "prefLabel"]}
        if c["conceptId"] in cons_label:
            c["prefLabel"], c["category"] = cons_label[c["conceptId"]]
        if not SLUG.match(c["conceptId"]):
            errors.append(f"construction {k}: concept ID {c['conceptId']!r} isn't a slug")
        if c["category"] not in CONS_CATEGORIES:
            errors.append(f"construction {k}: category {c['category']!r}")
        if not c["prefLabel"]:
            errors.append(f"construction {k}: no label")
        put(c_by, c_rows, c_cols, k, {"include": "y", **c, "note": ""}, CONS_FIELDS, "construction")

    # a concept merged into another (Labels tab) takes that concept's ID and
    # label. A chain (A into B, B into C) is followed to its end first, so the
    # result doesn't depend on the order the merges were saved in.
    def final(src):
        seen, cur = [src], merges[src]
        while cur in merges:
            if cur in seen:
                return None
            seen.append(cur)
            cur = merges[cur]
        return cur

    resolved = {}
    for src in merges:
        target = final(src)
        if target is None:
            errors.append(f"merge {src}: the merges into one another make a cycle")
        else:
            resolved[src] = target
    merged = 0
    for src, target in resolved.items():
        tl = next(((r["prefLabel"], r["category"]) for r in s_rows if r["include"] == "y" and r["conceptId"] == target), None)
        if tl is None:
            errors.append(f"merge {src} -> {target}: no heading carries {target}")
            continue
        for r in s_rows:
            if r["include"] == "y" and r["conceptId"] == src:
                r["conceptId"], (r["prefLabel"], r["category"]) = target, tl
                merged += 1
                changed.append(f"subjects {r['cluster']}: merged {src} into {target}")

    relabelled = 0
    for cid, o in overrides.items():
        for r in s_rows:
            if r["include"] == "y" and r["conceptId"] == cid and (r["prefLabel"], r["category"]) != (o["prefLabel"], o["category"]):
                r["prefLabel"], r["category"] = o["prefLabel"], o["category"]
                relabelled += 1

    for name, out in [("subjects", s_rows), ("construction", c_rows)]:
        seen = collections.defaultdict(set)
        for r in out:
            if r["include"] == "y":
                seen[r["conceptId"]].add((r["prefLabel"], r["category"]))
        for cid, ls in sorted(seen.items()):
            if len(ls) > 1:
                errors.append(f"{name} concept {cid}: several labels/categories {sorted(ls)}")
    if errors:
        print("\n".join(errors), file=sys.stderr)
        sys.exit(f"{len(errors)} problems; nothing written")

    save(SUBJECTS, s_raw, s_cols, s_rows)
    save(CONSTRUCTION, c_raw, c_cols, c_rows)
    if fine or os.path.exists(FINE):
        with open(FINE, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f, lineterminator="\n")
            w.writerow(["cluster", "fineCategory"])
            w.writerows(sorted(fine.items()))
    print("\n".join(changed))
    print(f"{len(changed)} row(s) changed, {merged} merged by {len(merges)} merge(s), {relabelled} relabelled by {len(overrides)} concept label(s)")
    print(f"finer categories kept in {FINE}: {len(fine)}")
    print(f"draft notes left: {sum(r['note'] == DRAFT for r in s_rows)}")
    print("decisions on the page: " + ", ".join(f"{k} {n}" for k, n in sorted(takes.items())))


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
