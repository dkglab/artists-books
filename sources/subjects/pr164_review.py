#!/usr/bin/env python3
"""Build the review sheet for the second subject pass in #164.

PR #164 has two subject passes that were made at the same time. Mert's
(bf0a69a, 03833cd) is applied to decisions.csv. Priya's (990d2b2 + 7febe8d)
was made on the July copy of decisions.csv (6ce1da22), so taking it wholesale
would revert the Nov 10 merged review (c7870e6c), #148 and Mert's pass. This
script recovers only the rows Priya herself changed (her side against
6ce1da22) and lists those whose decision differs from decisions.csv now.

  pr164_review.py build  -> pr164-review.csv   (run from sources/subjects/)

The sheet isn't filled in by hand: it's reviewed on the shared page in
tools/subject-review/, whose pull_decisions.py writes the decisions into
decisions.csv. Both commits above must be in the local repository.
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
    try:
        return subprocess.run(["git", "show", f"{rev}:{path}"], text=True,
                              check=True, capture_output=True).stdout
    except subprocess.CalledProcessError:
        sys.exit(f"commit {rev} isn't in this repository: fetch it first "
                 f"(git fetch origin {rev}, or the #164 branch if it still exists)")


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
        row = {"cluster": k, "labels": p["labels"],
               "changed": " ".join(changed), "flags": " ".join(fl)}
        for f in FIELDS + ["note"]:
            row[f"head_{f}"] = h.get(f, "")
        for f in FIELDS + ["note"]:
            row[f"priya_{f}"] = p[f]
        out.append(row)

    out.sort(key=lambda r: (coarse(r["priya_category"]) or "~",
                            r["priya_conceptId"] or "~", r["cluster"]))
    cols = (["cluster", "labels", "changed", "flags"]
            + [f"head_{f}" for f in FIELDS + ["note"]]
            + [f"priya_{f}" for f in FIELDS + ["note"]])
    with open(SHEET, "w", newline="") as fh:
        w = csv.DictWriter(fh, cols, lineterminator="\n")
        w.writeheader()
        w.writerows(out)
    c = collections.Counter(f for r in out for f in r["flags"].split())
    print(f"{SHEET}: {len(out)} rows")
    for f, n in c.most_common():
        print(f"  {f}: {n}")


if __name__ == "__main__":
    if sys.argv[1:] not in ([], ["build"]):
        sys.exit("usage: pr164_review.py [build]")
    build()
