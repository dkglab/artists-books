#!/usr/bin/env python3
"""Mine every creator field from both MARC directories (issue #170, step 1).

Walks the 1xx/7xx name fields (100/110/111/700/710/711 -- exactly the tags the
construct queries read) of every record in sources/marc/artists-books-marc/ and
sources/marc/reference-works-marc/, and writes one row per field occurrence to
sources/creators/occurrences.csv with the identifiers it carries:

  source        book | reference -- which MARC directory / construct query
  canonicalKey  the record's 999 $a
  tag           the MARC tag
  name          $a with trailing cataloguing punctuation stripped, *exactly* as
                the construct queries compute ?creator_name -- it is half of the
                join key they use to look the field up in agents.csv
  heading       $a $b $c $q $d joined, trailing punctuation tidied: the field's
                full heading, e.g. "Drucker, Johanna, 1952-"
  dates         $d (personal names only), tidied
  lcId          (ids are omitted for name/title fields with a $t, whose
                identifiers name the work, not the creator)
                LC name-authority id ($0 id.loc.gov URI or bare id, or $1
                id.loc.gov/rwo/agents URI)
  viaf, isni    $1 real-world-object ids
  gnd           $0 (DE-588) id
  wcEntity      $1 WorldCat Entity id
  role          $e / $4 relator terms, ";"-joined (informational)
  work          for a name/title field (one with $t, #32), an added entry for a
                *work* whose creator its $a names: "contained" when ind2 is 2
                (an analytical entry -- the record contains the work, so its
                creator made part of this record too), else "related" (based
                on, adapted from, inspired by ...: the creator made only the
                related work). The construct queries credit a "related" field
                to the related work alone, and build.py's Zotero fallback does
                not count it as a MARC creator field. Empty for a plain name.

It also writes sources/creators/zotero-creators.csv: the structured Zotero
creators of every canonical artists' book, for the no-MARC fallback.

Pure local read; no network. Run from the repo root:
    python3 sources/creators/mine.py
"""
import csv
import glob
import sqlite3
import os
import re
import sys
import xml.etree.ElementTree as ET

NS = "{http://www.loc.gov/MARC21/slim}"
TAGS = {"100", "110", "111", "700", "710", "711"}
DIRS = [("book", "sources/marc/artists-books-marc"),
        ("reference", "sources/marc/reference-works-marc")]


def query_name(raw):
    """The string the construct queries see as ?creator_name, so agents.csv can
    be joined on it exactly: the queries' REPLACE(?name_raw,
    "^\\s+|[\\s.,;:/]+$", ""). (Java's \\s is ASCII whitespace only, so the
    class is spelled out: Python's \\s would also eat NBSP.)

    Before SPARQL-Anything 1.3.0 the XML reader trimmed each text chunk, and an
    entity reference split the chunks, so "Peter &amp; Donna Thomas" arrived as
    "Peter&Donna Thomas" and this function had to mirror that. 1.3.0 reads the
    text intact."""
    ws = " \t\n\x0B\f\r"
    return re.sub(f"^[{ws}]+|[{ws}.,;:/]+$", "", raw)


def tidy(s):
    """Collapse whitespace and strip trailing cataloguing punctuation, but keep
    the full stop of a trailing initial or abbreviation ("Smith, J.", "Jr.")."""
    s = re.sub(r"\s+", " ", s).strip()
    s = re.sub(r"[\s,;:/]+$", "", s)
    if s.endswith(".") and not re.search(r"(\b[A-Z]|\bJr|\bSr|\bInc|\bLtd|\bCo|\bfl|\bca|\bb|\bd)\.$", s):
        s = s[:-1]
    return re.sub(r"[\s,;:/]+$", "", s)


def lc_id(value):
    v = value.strip().rstrip(".")
    m = re.search(r"id\.loc\.gov/(?:authorities/names|rwo/agents)/([a-z]{1,3}\d+)", v)
    if m:
        return m.group(1)
    m = re.fullmatch(r"(?:\(DLC\))?\s*([a-z]{1,3})\s*(\d+)", v)
    if m:
        return m.group(1) + m.group(2)
    return None


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "sources/creators/occurrences.csv"
    rows = []
    for source, d in DIRS:
        for path in sorted(glob.glob(os.path.join(d, "*.xml"))):
            root = ET.parse(path).getroot()
            for rec in root.iter(NS + "record"):
                key = None
                for df in rec.iter(NS + "datafield"):
                    if df.get("tag") == "999":
                        for sf in df.findall(NS + "subfield"):
                            if sf.get("code") == "a":
                                key = (sf.text or "").strip()
                if not key:
                    continue
                for df in rec.findall(NS + "datafield"):
                    tag = df.get("tag")
                    if tag not in TAGS:
                        continue
                    sfs = [(sf.get("code"), sf.text or "") for sf in df.findall(NS + "subfield")]
                    a = [v for c, v in sfs if c == "a"]
                    if not a:
                        continue
                    personal = tag.endswith("00")
                    # Heading: the name part only (not $t/$e/$4 or a work title).
                    head_codes = "abcqd" if personal else "abcdn"
                    head = ""
                    for c, v in sfs:
                        if c == "t":
                            break
                        if c in head_codes:
                            v = v.strip()
                            # MARC usually ends $a with the comma before $d, but
                            # not always: supply it so labels read uniformly.
                            if c == "d" and head and not re.search(r"[,.;:(]$", head):
                                head += ","
                            head = f"{head} {v}" if head else v
                    rec_ids = {"lcId": set(), "viaf": set(), "isni": set(), "gnd": set(), "wcEntity": set()}
                    # A name/title field ($t) is an added entry for a *work*: its
                    # $0/$1 identify the name/title authority, not the person, so
                    # they would link the creator to the wrong id. Identity for
                    # such a field comes from its heading alone.
                    is_work = any(c == "t" for c, _ in sfs)
                    for c, v in sfs:
                        v = v.strip()
                        if is_work:
                            continue
                        if c == "0":
                            if "viaf.org/viaf/" in v:
                                rec_ids["viaf"].add(re.search(r"viaf/(\d+)", v).group(1))
                            elif v.startswith("(DE-588)"):
                                rec_ids["gnd"].add(v[len("(DE-588)"):].rstrip("."))
                            elif lc_id(v):
                                rec_ids["lcId"].add(lc_id(v))
                        elif c == "1":
                            m = re.search(r"viaf\.org/viaf/(\d+)", v)
                            if m:
                                rec_ids["viaf"].add(m.group(1))
                            m = re.search(r"isni\.org/isni/([0-9X]+)", v)
                            if m:
                                rec_ids["isni"].add(m.group(1))
                            m = re.search(r"id\.oclc\.org/worldcat/entity/(E[0-9A-Za-z]+)", v)
                            if m:
                                rec_ids["wcEntity"].add(m.group(1))
                            if lc_id(v):
                                rec_ids["lcId"].add(lc_id(v))
                    dates = [tidy(v) for c, v in sfs if c == "d"] if personal else []
                    roles = [tidy(v).lower() for c, v in sfs if c in "e4"]
                    rows.append({
                        "source": source,
                        "canonicalKey": key,
                        "tag": tag,
                        "name": query_name(a[0]),
                        "heading": tidy(head),
                        "dates": " ".join(dates),
                        **{k: ";".join(sorted(v)) for k, v in rec_ids.items()},
                        "role": ";".join(roles),
                        "work": ("contained" if df.get("ind2") == "2" else "related") if is_work else "",
                    })
    fields = ["source", "canonicalKey", "tag", "name", "heading", "dates",
              "lcId", "viaf", "isni", "gnd", "wcEntity", "role", "work"]
    with open(out, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    print(f"{len(rows)} creator-field occurrences -> {out}", file=sys.stderr)
    zotero_creators("sources/creators/zotero-creators.csv")


def zotero_creators(out):
    """The Zotero creators of every canonical artists' book, structured (last /
    first / single-field mode / creator type) rather than flattened like the
    `creators` column of artists-books.csv. The Zotero-creator fallback (step 6)
    reads this to credit books that have no MARC creator field."""
    with open("sources/artists-books.csv", newline="", encoding="utf-8") as fh:
        books = [(r["canonicalKey"], int(r["canonicalLib"])) for r in csv.DictReader(fh)]
    db = sqlite3.connect("file:sources/zotero/zotero.sqlite?mode=ro&immutable=1", uri=True)
    q = """SELECT ic.orderIndex, cr.lastName, cr.firstName, cr.fieldMode, ct.creatorType
             FROM items i
             JOIN itemCreators ic ON ic.itemID = i.itemID
             JOIN creators cr ON cr.creatorID = ic.creatorID
             JOIN creatorTypes ct ON ct.creatorTypeID = ic.creatorTypeID
            WHERE i.libraryID = ? AND i.key = ?
            ORDER BY ic.orderIndex"""
    n = 0
    with open(out, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["canonicalKey", "order", "lastName", "firstName", "fieldMode", "creatorType"])
        for key, lib in books:
            for order, last, first, mode, ctype in db.execute(q, (lib, key)):
                w.writerow([key, order, (last or "").strip(), (first or "").strip(), mode or 0, ctype])
                n += 1
    print(f"{n} Zotero book creators -> {out}", file=sys.stderr)


if __name__ == "__main__":
    main()
