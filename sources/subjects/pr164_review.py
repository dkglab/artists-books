#!/usr/bin/env python3
"""Build and apply the review sheet for the second subject pass in #164.

PR #164 has two subject passes that were made at the same time. Mert's
(bf0a69a, 03833cd) is applied to decisions.csv. Priya's (990d2b2 + 7febe8d)
was made on the July copy of decisions.csv (6ce1da22), so taking it wholesale
would revert the Nov 10 merged review (c7870e6c), #148 and Mert's pass. This
script recovers only the rows Priya herself changed (her side against
6ce1da22) and lists those whose decision differs from decisions.csv now.

  build:  pr164_review.py build  -> pr164-review.csv
  apply:  pr164_review.py apply  -> copies rows marked take=priya into
                                    decisions.csv (or take=edit, using the
                                    final_* columns), then validates them

Review by filling the `take` column: `head` (keep decisions.csv), `priya`
(take her values) or `edit` (use the final_* columns). Blank rows are left
alone. Both commands run from sources/subjects/.
"""
import collections
import csv
import io
import re
import subprocess
import sys

DECISIONS = "decisions.csv"
SHEET = "pr164-review.csv"
CONSTRUCTION = "../construction/decisions.csv"
JULY = "6ce1da22"          # the copy Priya's pass started from
PRIYA = "7febe8d1"         # tip of #164: both conflict sides, hers second
FIELDS = ["include", "conceptId", "category", "prefLabel", "exactMatch"]
SLUG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
CATEGORIES = {"topical", "geographic"}   # build-scheme.rq's VALUES table


def git_csv(rev, path="sources/subjects/decisions.csv"):
    text = subprocess.check_output(["git", "show", f"{rev}:{path}"], text=True)
    return text


def rows(text):
    return list(csv.DictReader(io.StringIO(text, newline="")))


def priya_side():
    """Her side of the conflict in 7febe8d1: between ======= and >>>>>>>."""
    lines = git_csv(PRIYA).splitlines(keepends=True)
    start = next(i for i, l in enumerate(lines) if l.startswith("======="))
    end = next(i for i, l in enumerate(lines) if l.startswith(">>>>>>>"))
    return rows("".join(lines[start + 1:end]))


def coarse(category):
    """topical-people -> topical; anything else that isn't known -> None."""
    head = category.split("-", 1)[0]
    return head if head in CATEGORIES else None


def flags(r, label_of_id):
    out = []
    inc, cid, cat, lab = r["include"], r["conceptId"], r["category"], r["prefLabel"]
    if inc not in {"y", "n"}:
        out.append("bad-include")
    if inc == "y":
        if not cid:
            out.append("blank-id")
        elif not SLUG.match(cid):
            out.append("bad-id")
        if not cat:
            out.append("blank-category")
        elif cat not in CATEGORIES:
            out.append("fine-category" if coarse(cat) else "unknown-category")
        if not lab.strip():
            out.append("blank-label")
        elif lab != lab.strip():
            out.append("label-whitespace")
        if cid and len(label_of_id.get(cid, ())) > 1:
            out.append("id-has-several-labels")
    return out


def build():
    july = {r["cluster"]: r for r in rows(git_csv(JULY))}
    head = {r["cluster"]: r for r in csv.DictReader(open(DECISIONS, newline=""))}
    priya = priya_side()
    claimed = {r["cluster"] for r in csv.DictReader(open(CONSTRUCTION, newline=""))
               if r["include"] == "y"}

    # Which prefLabels each conceptId would carry if her rows were taken,
    # alongside the rows of decisions.csv that already use it.
    label_of_id = collections.defaultdict(set)
    for r in list(head.values()) + priya:
        if r["include"] == "y" and r["conceptId"] and r["prefLabel"].strip():
            label_of_id[r["conceptId"]].add(r["prefLabel"].strip())

    out = []
    for p in priya:
        k = p["cluster"]
        j = july.get(k)
        h = head.get(k, {f: "" for f in FIELDS + ["note", "labels"]})
        hers = j is None or any(j[f] != p[f] for f in FIELDS + ["note"])
        differs = any(h.get(f, "") != p[f] for f in FIELDS)
        if not (hers and differs):
            continue
        changed = [f for f in FIELDS if h.get(f, "") != p[f]]
        fl = flags(p, label_of_id)
        if k in claimed and p["include"] == "y":
            fl.append("claimed-by-construction")
        if k not in head:
            fl.append("new-cluster")
        elif j is not None and any(j[f] != h[f] for f in FIELDS):
            fl.append("also-reviewed-in-head")
        row = {"cluster": k, "labels": p["labels"], "take": "",
               "changed": " ".join(changed), "flags": " ".join(fl)}
        for f in FIELDS + ["note"]:
            row[f"head_{f}"] = h.get(f, "")
        for f in FIELDS + ["note"]:
            row[f"priya_{f}"] = p[f]
        for f in FIELDS:
            row[f"final_{f}"] = ""
        out.append(row)

    out.sort(key=lambda r: (coarse(r["priya_category"]) or "~",
                            r["priya_conceptId"] or "~", r["cluster"]))
    cols = (["cluster", "labels", "take", "changed", "flags"]
            + [f"head_{f}" for f in FIELDS + ["note"]]
            + [f"priya_{f}" for f in FIELDS + ["note"]]
            + [f"final_{f}" for f in FIELDS])
    with open(SHEET, "w", newline="") as fh:
        w = csv.DictWriter(fh, cols, lineterminator="\n")
        w.writeheader()
        w.writerows(out)
    c = collections.Counter(f for r in out for f in r["flags"].split())
    print(f"{SHEET}: {len(out)} rows")
    for f, n in c.most_common():
        print(f"  {f}: {n}")


def apply():
    sheet = list(csv.DictReader(open(SHEET, newline="")))
    with open(DECISIONS, newline="") as fh:
        raw = fh.read()
    reader = csv.DictReader(io.StringIO(raw, newline=""))
    cols, dec = reader.fieldnames, list(reader)
    by_key = {r["cluster"]: r for r in dec}
    errors, n = [], 0
    for s in sheet:
        take = s["take"].strip().lower()
        if take in {"", "head"}:
            continue
        if take not in {"priya", "edit"}:
            errors.append(f"{s['cluster']}: take must be head, priya or edit, not {take!r}")
            continue
        src = "priya_" if take == "priya" else "final_"
        new = {f: s[src + f].strip() for f in FIELDS}
        if new["category"] and new["category"] not in CATEGORIES and coarse(new["category"]):
            new["category"] = coarse(new["category"])
        if new["include"] == "n":
            new.update(conceptId="", category="", prefLabel="")
        fl = [f for f in flags(new, {}) if f != "id-has-several-labels"]
        if fl:
            errors.append(f"{s['cluster']}: {' '.join(fl)}")
            continue
        r = by_key.get(s["cluster"])
        if r is None:
            r = {c: "" for c in cols}
            r.update(cluster=s["cluster"], labels=s["labels"])
            dec.append(r)
            by_key[r["cluster"]] = r
        r.update(new)
        r["note"] = s["priya_note"] if take == "priya" else r["note"]
        n += 1

    labels = collections.defaultdict(set)
    for r in dec:
        if r["include"] == "y":
            labels[r["conceptId"]].add((r["prefLabel"], r["category"]))
    for cid, ls in sorted(labels.items()):
        if len(ls) > 1:
            errors.append(f"conceptId {cid}: several labels/categories {sorted(ls)}")
    if errors:
        print("\n".join(errors), file=sys.stderr)
        sys.exit(f"{len(errors)} problems; decisions.csv not written")
    le = "\r\n" if "\r\n" in raw else "\n"
    with open(DECISIONS, "w", newline="") as fh:
        w = csv.DictWriter(fh, cols, lineterminator=le)
        w.writeheader()
        w.writerows(dec)
    print(f"applied {n} rows to {DECISIONS}")


if __name__ == "__main__":
    {"build": build, "apply": apply}[sys.argv[1] if len(sys.argv) > 1 else "build"]()
