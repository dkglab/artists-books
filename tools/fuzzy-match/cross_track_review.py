#!/usr/bin/env python3
"""Build the cross-track review sheet: works in both canonical lists (issue #113).

dedup.py (#82) deduplicates each list on its own: the artists'-books pass leaves
out the Reference resources collection, and the reference-works pass reads only
that collection. So a work that is in both lists, like Keith Smith's "Two
hundred books" (his book number 200, and a bibliography), keeps two canonical
keys and mints two nodes. Some of these are really one work that is both an
artist's book and a reference work. Others are reference works (exhibition
catalogues, critical surveys) filed among the artists' books, and some only
look alike (another edition, a borrowed ISBN). Telling them apart is a
librarian's call, so this script lists the candidate pairs for review.

A pair (artists'-book key, reference-work key) is a candidate on any of:

  sourceKey  both canonical rows list the same Zotero record in sourceKeys
             (the per-list dedups already linked them through sameAs)
  isbn       a shared ISBN (ISBN-10 compared as ISBN-13)
  oclc       the same MARC 001 OCLC number in both MARC directories
  title      the same normalized title, or the same main title (before the
             first colon) of three words or more, plus a shared creator surname

The decision vocabulary:

  both       one work, both an artist's book and a reference work: merge onto
             one key, typed ab:ArtistsBook and ab:ReferenceWork
  reference  one work, but not an artist's book: merge, and drop it from the
             artists'-books list
  no         different works (another edition, a coincidental title or ISBN):
             keep both
  unsure     needs another signal

(A work in the Reference resources collection that cites artists' books is a
reference work by definition, so there is no "artist's book only" value.)

The sheet (--out) is GENERATED and overwritten on every run. The decisions live
in the hand-owned overlay (--decisions), keyed by (abKey, rwKey), and are joined
into the sheet read-only, the same split as the dedup and OCLC review sheets.
Pass --seed-decisions to create the overlay with a blank row per pair; it
refuses to overwrite an existing file. Nothing reads the decisions back into
the dedup yet (that is #113's merge step, after the #214 review).
"""
import argparse
import csv
import os
import re
import sys
import unicodedata
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict

NS = {"m": "http://www.loc.gov/MARC21/slim"}
DECISIONS = {"", "both", "reference", "no", "unsure"}
DECISION_COLS = ["abKey", "rwKey", "abTitle", "rwTitle", "decision", "notes"]
COLS = ["abKey", "rwKey", "signals", "abTitle", "rwTitle", "abDate", "rwDate",
        "abCreators", "rwCreators", "abISBN", "rwISBN", "abOCLC", "rwOCLC",
        "abHeld", "abCitedBy", "rwCites", "abSourceKeys", "rwSourceKeys",
        "decision", "notes"]
SIGNAL_ORDER = ["sourceKey", "isbn", "oclc", "title"]


def read_csv(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def fold(s):
    s = unicodedata.normalize("NFKD", s or "")
    return "".join(c for c in s if not unicodedata.combining(c)).casefold()


def norm_title(s):
    return " ".join(re.findall(r"[a-z0-9]+", fold(s)))


def main_title(s):
    return norm_title(re.split(r"\s*[:;]\s*", s or "", maxsplit=1)[0])


# A creator naming a body, not a person: its last word ("centre", "gallery",
# "press") is no surname, and two catalogues from different galleries would
# share it. Zotero gives no person/body flag, and its body names are often
# split oddly ("Andi Wrexford Arts Centre McGarry"), so any creator holding
# one of these words is skipped.
CORPORATE = re.compile(
    r"\b(arts|centre|center|gallery|galerie|galleries|museum|musee|library|libraries|"
    r"bibliotheque|press|editions?|university|universite|college|institute|foundation|"
    r"society|department|school|ecole|collection|council|association|(?:private|firm))\b")
NOT_SURNAMES = {"various", "donor", "and", "the"}


def surnames(creators):
    """Surname-ish tokens of a '; '-joined Zotero creator string ('First Last')."""
    out = set()
    for c in (creators or "").split(";"):
        c = fold(c)
        if CORPORATE.search(c):
            continue
        words = re.findall(r"[a-z]+", c)
        if words:
            out.add(words[-1])
    return {w for w in out if len(w) > 2 and w not in NOT_SURNAMES}


def isbn13(raw):
    d = re.sub(r"[^0-9X]", "", raw.upper())
    if len(d) == 13 and d.isdigit():
        return d
    if len(d) == 10:
        core = "978" + d[:9]
        check = (10 - sum((1 if i % 2 == 0 else 3) * int(c) for i, c in enumerate(core)) % 10) % 10
        return core + str(check)
    return None


def isbns(field):
    return {i for i in (isbn13(t) for t in re.split(r"[\s;,]+", field or "")) if i}


def oclc_of(marc_dir, key):
    path = os.path.join(marc_dir, f"{key}.xml")
    if not os.path.exists(path):
        return ""
    rec = ET.parse(path).getroot().find("m:record", NS)
    el = rec.find("m:controlfield[@tag='001']", NS) if rec is not None else None
    return oclc_number((el.text or "") if el is not None else "")


def oclc_number(control):
    """The OCLC number in a 001, guarded as in the construct queries
    (reference-works.rq, #51): the first digit run, leading zeros dropped,
    accepted only when the 001 has an on/ocn/ocm prefix or the run is at most
    10 digits. A longer bare 001 is a local system id (an Alma MMS id), and
    truncating it would make up an OCLC number that two records can share."""
    m = re.search(r"\d+", control)
    if not m:
        return ""
    raw = m.group(0).lstrip("0")
    if re.match(r"(on|ocn|ocm)", control, re.I) or len(raw) <= 10:
        return raw
    return ""


def source_keys(row):
    return {k.strip() for k in row["sourceKeys"].split(";") if k.strip()}


def candidates(books, refs, marc_ab, marc_rw):
    pairs = defaultdict(set)
    by_src, by_isbn, by_oclc, by_title = (defaultdict(set) for _ in range(4))
    oclc = {}
    for b in books:
        k = b["canonicalKey"]
        for s in source_keys(b):
            by_src[s].add(k)
        for i in isbns(b["ISBN"]):
            by_isbn[i].add(k)
        oclc[k] = oclc_of(marc_ab, k)
        if oclc[k]:
            by_oclc[oclc[k]].add(k)
        by_title[main_title(b["title"])].add(k)
    book = {b["canonicalKey"]: b for b in books}
    for r in refs:
        rk = r["canonicalKey"]
        for s in source_keys(r):
            for k in by_src.get(s, ()):
                pairs[(k, rk)].add("sourceKey")
        for i in isbns(r["ISBN"]):
            for k in by_isbn.get(i, ()):
                pairs[(k, rk)].add("isbn")
        oclc[rk] = oclc_of(marc_rw, rk)
        for k in by_oclc.get(oclc[rk], ()) if oclc[rk] else ():
            pairs[(k, rk)].add("oclc")
        mt = main_title(r["title"])
        for k in by_title.get(mt, ()):
            b = book[k]
            same_full = norm_title(b["title"]) == norm_title(r["title"])
            if (same_full or len(mt.split()) >= 3) and surnames(b["creators"]) & surnames(r["creators"]):
                pairs[(k, rk)].add("title")
    return pairs, oclc


def main():
    ap = argparse.ArgumentParser(description="Cross-track (AB/RW) review sheet (#113).")
    ap.add_argument("--books", required=True, help="sources/artists-books.csv")
    ap.add_argument("--refs", required=True, help="sources/reference-works.csv")
    ap.add_argument("--marc-books", required=True, help="sources/marc/artists-books-marc")
    ap.add_argument("--marc-refs", required=True, help="sources/marc/reference-works-marc")
    ap.add_argument("--citations", required=True, help="sources/citations-review.csv")
    ap.add_argument("--decisions", required=True, help="sources/cross-track-decisions.csv")
    ap.add_argument("--out", help="sources/cross-track-review.csv")
    ap.add_argument("--seed-decisions", action="store_true",
                    help="create --decisions with a blank row per pair, then stop")
    args = ap.parse_args()

    books, refs = read_csv(args.books), read_csv(args.refs)
    book = {b["canonicalKey"]: b for b in books}
    ref = {r["canonicalKey"]: r for r in refs}
    pairs, oclc = candidates(books, refs, args.marc_books, args.marc_refs)
    order = sorted(pairs, key=lambda p: (fold(ref[p[1]]["title"]), p))

    if args.seed_decisions:
        if os.path.exists(args.decisions):
            sys.exit(f"{args.decisions} exists; not overwriting the hand-owned decisions")
        with open(args.decisions, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, DECISION_COLS, lineterminator="\n")
            w.writeheader()
            for ak, rk in order:
                w.writerow({"abKey": ak, "rwKey": rk, "abTitle": book[ak]["title"],
                            "rwTitle": ref[rk]["title"], "decision": "", "notes": ""})
        print(f"seeded {len(order)} pairs -> {args.decisions}", file=sys.stderr)
        return
    if not args.out:
        sys.exit("--out is required unless --seed-decisions")

    decisions = {}
    for r in read_csv(args.decisions):
        d = (r.get("decision") or "").strip()
        if d not in DECISIONS:
            sys.exit(f"{args.decisions}: unknown decision {d!r} for {r['abKey']}/{r['rwKey']}")
        decisions[(r["abKey"], r["rwKey"])] = (d, r.get("notes", ""))
    for p in set(decisions) - set(pairs):
        print(f"warning: decision for {p[0]}/{p[1]} matches no current candidate pair",
              file=sys.stderr)

    # One per (reference, book) pair, as in the frozen graph: a work cited in
    # several note paragraphs has several emitted rows but one ab:Citation.
    cited = {(r["refKey"], r["bookKey"]) for r in read_csv(args.citations)
             if r["status"] == "emitted"}
    cited_by = Counter(bk for _, bk in cited)
    cites = Counter(rk for rk, _ in cited)

    with open(args.out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, COLS, lineterminator="\n")
        w.writeheader()
        for ak, rk in order:
            b, r = book[ak], ref[rk]
            d, notes = decisions.get((ak, rk), ("", ""))
            w.writerow({
                "abKey": ak, "rwKey": rk,
                "signals": " ".join(s for s in SIGNAL_ORDER if s in pairs[(ak, rk)]),
                "abTitle": b["title"], "rwTitle": r["title"],
                "abDate": b["date"], "rwDate": r["date"],
                "abCreators": b["creators"], "rwCreators": r["creators"],
                "abISBN": b["ISBN"], "rwISBN": r["ISBN"],
                "abOCLC": oclc.get(ak, ""), "rwOCLC": oclc.get(rk, ""),
                "abHeld": b["held"], "abCitedBy": cited_by[ak], "rwCites": cites[rk],
                "abSourceKeys": b["sourceKeys"], "rwSourceKeys": r["sourceKeys"],
                "decision": d, "notes": notes,
            })
    sig = Counter(s for p in order for s in pairs[p])
    print(f"{len(order)} candidate pairs ({len({p[1] for p in order})} reference works); "
          + ", ".join(f"{s} {sig[s]}" for s in SIGNAL_ORDER) + f" -> {args.out}",
          file=sys.stderr)


if __name__ == "__main__":
    main()
