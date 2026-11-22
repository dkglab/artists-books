#!/usr/bin/env python3
"""Build data.json for the dedup review page (issue #70).

Two review queues, both read from committed sources (run from the repo root):

  dedup  every fuzzy lib-1 attach in sources/artists-books-dedup-review.csv:
         the Sloane (lib 1) Zotero record beside its fuzzy twin's, plus the
         MARC record of the canonical node(s) they map to.
  oclc   every shared-OCLC group in sources/artists-books-oclc-review.csv:
         each book node's canonical Zotero row and its own MARC record.

MARC records are rendered as plain text lines ("245 10 $a ... $c ..."), so the
page needs no MARC parsing. Usage: python3 tools/review-app/build_data.py OUT
"""
import csv
import glob
import json
import os
import re
import sys
import xml.etree.ElementTree as ET
from collections import OrderedDict, defaultdict

NS = {"m": "http://www.loc.gov/MARC21/slim"}
MARC_DIR = "sources/marc/artists-books-marc"


def read_csv(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def marc_text(key):
    path = os.path.join(MARC_DIR, f"{key}.xml")
    if not os.path.exists(path):
        return None
    rec = ET.parse(path).getroot().find("m:record", NS)
    lines = []
    leader = rec.find("m:leader", NS)
    if leader is not None and leader.text:
        lines.append(f"LDR    {leader.text}")
    for el in rec:
        tag = el.get("tag")
        if el.tag.endswith("controlfield"):
            lines.append(f"{tag}    {el.text or ''}")
        elif el.tag.endswith("datafield"):
            ind = (el.get("ind1") or " ") + (el.get("ind2") or " ")
            subs = " ".join(f"${sf.get('code')} {(sf.text or '').strip()}"
                            for sf in el.iterfind("m:subfield", NS))
            lines.append(f"{tag} {ind.replace(' ', '_')} {subs}")
    return "\n".join(lines)


def main(out):
    items = {r["itemKey"]: r for r in read_csv("sources/zotero/all-items.csv")}
    names = {r["creatorID"]: r["name"] for r in read_csv("sources/zotero/all-creators.csv")}
    creators = defaultdict(list)
    for r in sorted(read_csv("sources/zotero/all-item_creators.csv"),
                    key=lambda r: int(r["orderIndex"])):
        creators[r["itemKey"]].append(
            names.get(r["creatorID"], "?") +
            ("" if r["creatorType"] == "author" else f" ({r['creatorType']})"))
    books = {r["canonicalKey"]: r for r in read_csv("sources/artists-books.csv")}
    canon = {}
    for r in books.values():
        for k in r["sourceKeys"].split(";"):
            canon[k.strip().split(":")[-1]] = r["canonicalKey"]

    # Held (Sloane) records carry their UNC bib number in 999 $b. A fuzzy pair
    # that was later split by a no/unsure decision leaves the held record filed
    # under the twin's key, so attach each held record to the lib-1 item whose
    # catalogue URL names that bib, not to whichever key the file is under.
    by_bib, bib_of = {}, {}
    for path in glob.glob(os.path.join(MARC_DIR, "*.xml")):
        m = re.search(r'tag="999".*?code="b">(b\d+)<.*?code="c">bib<', open(path, encoding="utf-8").read())
        if m:
            key = os.path.basename(path)[:-4]
            by_bib[m.group(1)] = key
            bib_of[key] = m.group(1)

    def item_bib(key):
        m = re.search(r"UNC(b\d+)", items.get(key, {}).get("url", ""))
        return m.group(1) if m else None

    marc = {}

    def want_marc(key):
        if key and key not in marc:
            t = marc_text(key)
            if t:
                marc[key] = t
        return key if key in marc else None

    def zot_item(key):
        r = items.get(key, {})
        return {
            "title": r.get("title", ""), "creators": "; ".join(creators.get(key, [])),
            "date": r.get("date", ""), "publisher": r.get("publisher", ""),
            "place": r.get("place", ""), "edition": r.get("edition", ""),
            "pages": r.get("numPages", ""), "isbn": r.get("ISBN", ""),
            "callNumber": r.get("callNumber", ""), "url": r.get("url", ""),
            "extra": r.get("extra", ""), "collections": r.get("collections", ""),
        }

    def zot_book(key):
        b = books[key]
        return {
            "title": b["title"], "creators": b["creators"], "date": b["date"],
            "publisher": b["publisher"], "place": b["place"], "edition": b["edition"],
            "pages": b["numPages"], "isbn": b["ISBN"], "callNumber": b["callNumber"],
            "url": b["url"], "extra": b["extra"], "sourceKeys": b["sourceKeys"],
        }

    dedup = []
    for r in read_csv("sources/artists-books-dedup-review.csv"):
        a, b = r["lib1Key"], r["twinKey"]
        ca, cb = canon.get(a), canon.get(b)
        bib = item_bib(a)
        marc_a = by_bib.get(bib) if bib else (ca if ca == cb else None)
        marc_b = cb if cb and bib_of.get(cb) != bib and cb != marc_a else None
        if not marc_a and ca != cb:
            marc_a = ca
        dedup.append({
            "id": a, "conf": float(r["confidence"]), "flag": r["review"] == "yes",
            "sides": [
                {"key": a, "lib": "1", "canon": ca, "marc": want_marc(marc_a),
                 "held": books.get(ca, {}).get("held") == "true", "zot": zot_item(a)},
                {"key": b, "lib": r["twinLib"], "canon": cb,
                 "marc": want_marc(marc_b),
                 "held": books.get(cb, {}).get("held") == "true", "zot": zot_item(b)},
            ],
        })

    groups = OrderedDict()
    for r in read_csv("sources/artists-books-oclc-review.csv"):
        g = groups.setdefault(r["oclc"], {"id": r["oclc"], "n": int(r["group"]),
                                          "hint": r["hint"], "nodes": []})
        k = r["canonicalKey"]
        g["nodes"].append({
            "key": k, "held": r["held"] == "true", "marc": want_marc(k),
            "match": {"method": r["matchMethod"], "server": r["matchServer"],
                      "on": r["matchedOn"]},
            "zot": zot_book(k),
        })

    data = {"site": "https://dev-artists-books-bdhx.sprites.app",
            "dedup": dedup, "oclc": list(groups.values()), "marc": marc}
    with open(out, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
    print(f"{len(dedup)} dedup pairs, {len(groups)} OCLC groups, "
          f"{len(marc)} MARC records -> {out} ({os.path.getsize(out) // 1024} KB)",
          file=sys.stderr)


if __name__ == "__main__":
    main(sys.argv[1])
