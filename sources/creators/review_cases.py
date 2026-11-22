#!/usr/bin/env python3
"""Cases for the creator name review page: every personal name the clustering
leaves split over more than one agent (issue #170).

Each case is one name key with the agents carrying it, each agent's works and
the MARC fields that credit it there, and the books whose Zotero creator
matches the name but that build.py could not place (review.csv's
ambiguous-zotero rows). The review page reads this as cases.json; a reviewer's
verdict is meant to become rows in decisions.csv (merge, distinct, place).

A name drops off once it is settled: every pair of its agents is recorded as
`distinct` (authority.csv's distinctFrom) and no Zotero credit of it is still
unplaced. Merges make a name drop off by themselves, by leaving one agent.

Pure local read: agents.csv, authority.csv, occurrences.csv, lc-viaf.csv,
zotero-creators.csv, review.csv, the two canonical CSVs, both MARC record
directories (for 245 $c) and, when the site has been built, web/site (to say
which works have a page).

    python3 sources/creators/review_cases.py --out cases.json
"""
import argparse
import collections
import csv
import datetime
import json
import os
import re
import sys
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build import fold, name_key, split_dates  # the same keys build.py clusters on

HERE = os.path.dirname(os.path.abspath(__file__))
SOURCES = os.path.dirname(HERE)
ROOT = os.path.dirname(SOURCES)
MARC_NS = "{http://www.loc.gov/MARC21/slim}"
TRACKS = {"book": ("artists-books.csv", "marc/artists-books-marc", "item"),
          "reference": ("reference-works.csv", "marc/reference-works-marc", "reference")}


def read(path):
    with open(path, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def shown_date(date):
    """The CSV date as recorded: Zotero stores it as "<sortable> <as entered>"
    ("0000-00-00 c1979"), and the as-entered half is what a reviewer wants."""
    parts = (date or "").split(" ", 1)
    return parts[1].strip() if len(parts) == 2 else (date or "").strip()


def statement_of_responsibility(path):
    """245 $c of a MARC record, '' if none."""
    try:
        rec = ET.parse(path).getroot()
    except (OSError, ET.ParseError):
        return ""
    for df in rec.iter(f"{MARC_NS}datafield"):
        if df.get("tag") == "245":
            for sf in df.findall(f"{MARC_NS}subfield"):
                if sf.get("code") == "c":
                    return (sf.text or "").strip().rstrip(" .")
    return ""


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    works = {}
    for src, (csv_name, _marc, _path) in TRACKS.items():
        for r in read(os.path.join(SOURCES, csv_name)):
            works[(src, r["canonicalKey"])] = r
    lc = {r["lcId"]: r for r in read(os.path.join(HERE, "lc-viaf.csv"))}
    authority = {r["agentKey"]: r for r in read(os.path.join(HERE, "authority.csv"))}
    occ_rows = read(os.path.join(HERE, "occurrences.csv"))
    occ = {(o["source"], o["canonicalKey"], o["tag"], o["name"]): o for o in occ_rows}
    zotero = collections.defaultdict(list)
    for z in read(os.path.join(HERE, "zotero-creators.csv")):
        zotero[z["canonicalKey"]].append(z)
    agents_rows = read(os.path.join(HERE, "agents.csv"))

    # Name key -> agents carrying it, from the MARC fields (a Zotero row's name
    # is already folded and carries no heading).
    by_name = collections.defaultdict(set)
    display = {}
    for a in agents_rows:
        if a["tag"] == "zotero" or not a["tag"].endswith("00"):
            continue
        o = occ.get((a["source"], a["canonicalKey"], a["tag"], a["name"]))
        if not o:
            continue
        name_part, _dates = split_dates(o["heading"])
        nk = fold(name_part)
        by_name[nk].add(a["agentKey"])
        display.setdefault(nk, name_part.rstrip(" ,."))

    unplaced = collections.defaultdict(list)  # name key -> [book key]
    for r in read(os.path.join(HERE, "review.csv")):
        if r["issue"] == "ambiguous-zotero":
            unplaced[r["key"].split(":", 1)[1]].append(r["detail"].split(":", 1)[0])

    def work(src, key):
        r = works.get((src, key), {})
        csv_name, marc_dir, path = TRACKS[src]
        marc = os.path.join(marc_dir, f"{key}.xml")
        has_marc = os.path.exists(os.path.join(SOURCES, marc))
        return {
            "src": src, "key": key, "title": r.get("title", ""),
            "date": shown_date(r.get("date", "")), "publisher": r.get("publisher", ""),
            "place": r.get("place", ""), "zoteroCreators": r.get("creators", ""),
            "marc": f"sources/{marc}" if has_marc else None,
            "soc": statement_of_responsibility(os.path.join(SOURCES, marc)) if has_marc else "",
            "page": os.path.exists(os.path.join(ROOT, "web/site", path, key, "index.html")),
        }

    def zotero_name(key, nk):
        for z in zotero.get(key, []):
            if fold(z["lastName"] + z["firstName"]) == nk or \
                    fold(z["lastName"] + split_dates(z["firstName"])[0]) == nk:
                return z
        return None

    distinct = {k: set(a.get("distinctFrom", "").split()) for k, a in authority.items()}

    def settled(nk, keys):
        return not unplaced.get(nk) and all(
            b in distinct.get(a, set()) for a in keys for b in keys if a != b)

    # How many occurrences each field: key names; a decision may only use a
    # key that names exactly one (build.py refuses the rest). Counted over the
    # raw rows, as build.py does: two fields of one name in one record are two
    # occurrences, though `occ` above keeps one of them.
    field_count = collections.Counter(
        (o["source"], o["canonicalKey"], o["tag"], name_key(o["tag"], o["heading"]))
        for o in occ_rows)

    def decision_key(au, fields):
        """A decisions.csv key that names this agent and no other: its LC, VIAF
        or ISNI id, else the field: key of one of its MARC fields."""
        for prefix, f in (("lc", "lcId"), ("viaf", "viaf"), ("isni", "isni")):
            if au.get(f):
                return f"{prefix}:{au[f]}"
        for src, key, tag, heading in fields:
            fk = (src, key, tag, name_key(tag, heading))
            if field_count[fk] == 1:
                return "field:" + ":".join(fk)
        return ""

    def year_of(heading):
        m = re.search(r"\d{4}", split_dates(heading)[1])
        return m.group(0) if m else ""

    cases, n_settled = [], 0
    for nk, keys in sorted(by_name.items()):
        if len(keys) < 2:
            continue
        if settled(nk, keys):
            n_settled += 1
            continue
        agents = []
        for ak in keys:
            au = authority.get(ak, {})
            lc_id = au.get("lcId", "")
            rec = lc.get(lc_id, {})
            rows = [a for a in agents_rows if a["agentKey"] == ak]
            ws = {}
            for a in rows:
                w = ws.setdefault((a["source"], a["canonicalKey"]),
                                  dict(work(a["source"], a["canonicalKey"]),
                                       zotero=False, fields=[]))
                if a["tag"] == "zotero":
                    w["zotero"] = True
                    z = zotero_name(a["canonicalKey"], nk)
                    if z:
                        w["zoteroName"] = f"{split_dates(z['firstName'])[0]} {z['lastName']}".strip()
                    continue
                o = occ.get((a["source"], a["canonicalKey"], a["tag"], a["name"]), {})
                w["fields"].append({"tag": a["tag"], "heading": o.get("heading", a["name"]),
                                    "role": o.get("role", ""), "lcId": o.get("lcId", ""),
                                    "viaf": o.get("viaf", "")})
            fields = [(a["source"], a["canonicalKey"], a["tag"],
                       occ.get((a["source"], a["canonicalKey"], a["tag"], a["name"]), {}).get("heading", a["name"]))
                      for a in rows if a["tag"] != "zotero"]
            headings = [h for h in au.get("headings", "").split(" | ") if h]
            # A heading whose dates LC's record doesn't carry: the catalogue
            # linked a dated heading to an undated (or differently dated) LC
            # record, so the id may not be the person the heading names.
            notes = []
            if rec.get("label"):
                lc_year = year_of(rec["label"])
                for h in headings:
                    if year_of(h) and year_of(h) != lc_year:
                        notes.append(f"Catalogued as \u201c{h}\u201d, but LC's heading for "
                                     f"{lc_id} is \u201c{rec['label']}\u201d.")
            agents.append({
                "key": ak, "decisionKey": decision_key(au, fields), "notes": notes, "label": au.get("label", rows[0]["label"] if rows else ak),
                "uri": au.get("agentUri", rows[0]["agentUri"] if rows else ""),
                "lcId": lc_id, "viaf": au.get("viaf", ""), "isni": au.get("isni", ""),
                "lcLabel": rec.get("label", ""), "lcStatus": rec.get("status", ""),
                "lcReplacedBy": rec.get("replacedBy", ""),
                "headings": headings,
                "works": sorted(ws.values(), key=lambda w: (w["date"] or "9999", w["key"])),
            })
        # Record 1 is the anchor: the agent credited on the most works.
        agents.sort(key=lambda a: (-len(a["works"]), a["key"]))
        unresolved = []
        for key in unplaced.get(nk, []):
            w = dict(work("book", key), zotero=False, fields=[],
                     placeKey=f"field:book:{key}:zotero:{nk}")
            z = zotero_name(key, nk)
            w["zoteroType"] = z["creatorType"] if z else ""
            w["zoteroName"] = (f"{split_dates(z['firstName'])[0]} {z['lastName']}".strip()
                               if z else "")
            unresolved.append(w)
        cases.append({"id": nk, "name": display[nk], "agents": agents,
                      "unresolved": unresolved})

    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump({"generated": datetime.date.today().isoformat(), "cases": cases},
                  fh, ensure_ascii=False, indent=1)
    print(f"{len(cases)} cases -> {args.out} ({n_settled} settled names left out)")


if __name__ == "__main__":
    main()
