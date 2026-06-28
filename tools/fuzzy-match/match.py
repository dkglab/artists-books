#!/usr/bin/env python3
"""Build the ABC <-> cited-record crosswalk (issue #55).

Each book in the personal-library *Artists' Books Collection* (ABC, lib 1 -- the
collection the website builds from) is matched to the lib-3 citation-index
record(s) describing the same work, so the "Cited:" notes that live on those
records can later be joined onto ABC pages (issue #53). The ABC and lib-3 records
have *different* Zotero item keys (the same work is catalogued once per library),
so the join is a bibliographic reconciliation, not a key lookup.

Precedence (first hit wins, recorded as `method`):

    1. oclc   -- OCLC number agrees                       confidence 1.00
    2. isbn   -- ISBN agrees (10/13 forms cross-checked)  confidence 1.00
    3. title  -- exact normalized title agrees            confidence 0.95
    4. fuzzy  -- rapidfuzz title similarity, re-ranked /   confidence = blended
                 confirmed by author + year               (review flag if < 0.93)

ABC signals come from artists-books.csv (title, ISBN, date) plus the harvested
MARC (artists-books-marc.xml: OCLC in 001, authors in 100/700 $a, joined to the
itemKey via 999 $a). Cited-record signals come from cited-records.csv (OCLC
parsed from the `extra` field).

Output: one row per ABC item -- matched or not -- so the file is a complete
census of the 1,341 ABC books. Unmatched items have an empty citedItemKey and
method `none`. A coverage summary is printed to stderr.
"""
import argparse
import csv
import re
import sys
import unicodedata
import xml.etree.ElementTree as ET

from rapidfuzz import fuzz, process

MARC_NS = {"m": "http://www.loc.gov/MARC21/slim"}

# Fuzzy thresholds (title similarity is 0..1).
FUZZY_FLOOR = 0.88      # title-driven path: assert a match at/above this title sim
CORROB_TITLE_FLOOR = 0.55  # corroborated path: tolerate lower title sim when the
CORROB_AUTHOR = 0.85       # author is (near-)identical AND the year matches exactly
REVIEW_BELOW = 0.93     # accepted fuzzy matches below this are flagged for review
TOPN = 12               # title candidates re-ranked by author + year


# --------------------------------------------------------------------------- #
# Normalizers
# --------------------------------------------------------------------------- #
def strip_accents(s):
    s = unicodedata.normalize("NFKD", s)
    return "".join(c for c in s if not unicodedata.combining(c))


def norm_oclc(s):
    """Bare significant digits (drops ocm/ocn/on prefixes and leading zeros)."""
    d = re.sub(r"\D", "", s or "")
    return d.lstrip("0")


def oclc_set_from_extra(extra):
    return {norm_oclc(m.group(1)) for m in re.finditer(r"OCLC:\s*(\d+)", extra or "")} - {""}


def _isbn13_to_10(d):
    core = d[3:12]
    s = sum((10 - i) * int(c) for i, c in enumerate(core))
    chk = (11 - s % 11) % 11
    return core + ("X" if chk == 10 else str(chk))


def _isbn10_to_13(d):
    core = "978" + d[:9]
    s = sum((1 if i % 2 == 0 else 3) * int(c) for i, c in enumerate(core))
    chk = (10 - s % 10) % 10
    return core + str(chk)


def isbn_set(s):
    """All ISBNs in a field, each expanded to its 10- and 13-digit forms."""
    out = set()
    for tok in re.split(r"[;,/\s]+", s or ""):
        t = re.sub(r"[^0-9Xx]", "", tok).upper()
        if len(t) == 10:
            out.add(t)
            if t[:9].isdigit():
                out.add(_isbn10_to_13(t))
        elif len(t) == 13 and t.isdigit():
            out.add(t)
            if t.startswith("978"):
                out.add(_isbn13_to_10(t))
    return out


def norm_title(s):
    s = strip_accents(s or "").casefold()
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return " ".join(s.split())


def norm_author(s):
    """Surname-leading author key (handles 'Last, First' and relator cruft)."""
    s = strip_accents(s or "").casefold()
    s = re.sub(r"[^a-z0-9, ]+", " ", s)
    s = s.split(",")[0]  # surname carries most of the discriminating signal
    return " ".join(s.split())


def year_of(s):
    m = re.search(r"\b(1[5-9]\d\d|20\d\d)\b", s or "")
    return m.group(1) if m else ""


# --------------------------------------------------------------------------- #
# Loaders
# --------------------------------------------------------------------------- #
def load_marc(path):
    """itemKey (999 $a) -> {'oclc': str, 'author': str} from the MARC harvest."""
    out = {}
    for rec in ET.parse(path).getroot().findall(".//m:record", MARC_NS):
        key = oclc = author = ""
        for cf in rec.findall("m:controlfield", MARC_NS):
            if cf.get("tag") == "001":
                oclc = norm_oclc(cf.text)
        names = {"100": "", "700": ""}
        for df in rec.findall("m:datafield", MARC_NS):
            tag = df.get("tag")
            if tag == "999":
                for sf in df.findall("m:subfield", MARC_NS):
                    if sf.get("code") == "a":
                        key = (sf.text or "").strip()
            elif tag in names and not names[tag]:
                for sf in df.findall("m:subfield", MARC_NS):
                    if sf.get("code") == "a":
                        names[tag] = sf.text or ""
        author = names["100"] or names["700"]  # prefer main entry, else first added
        if key:
            out[key] = {"oclc": oclc, "author": norm_author(author)}
    return out


def load_abc(abc_path, marc_path):
    marc = load_marc(marc_path)
    items = []
    with open(abc_path, newline="") as fh:
        for row in csv.DictReader(fh):
            key = row["itemKey"]
            m = marc.get(key, {})
            items.append(
                {
                    "key": key,
                    "title": row.get("title", ""),
                    "ntitle": norm_title(row.get("title", "")),
                    "isbns": isbn_set(row.get("ISBN", "")),
                    "oclc": m.get("oclc", ""),
                    "author": m.get("author", ""),
                    "year": year_of(row.get("date", "")),
                }
            )
    return items


def load_cited(path):
    rows = []
    with open(path, newline="") as fh:
        for row in csv.DictReader(fh):
            rows.append(
                {
                    "key": row["itemKey"],
                    "title": row.get("title", ""),
                    "ntitle": norm_title(row.get("title", "")),
                    "isbns": isbn_set(row.get("ISBN", "")),
                    "oclcs": oclc_set_from_extra(row.get("extra", "")),
                    "author": norm_author((row.get("creators", "") or "").split(";")[0]),
                    "year": year_of(row.get("date", "")),
                }
            )
    return rows


# --------------------------------------------------------------------------- #
# Matching
# --------------------------------------------------------------------------- #
def build_indexes(cited):
    oclc_ix, isbn_ix, title_ix = {}, {}, {}
    for c in cited:
        for o in c["oclcs"]:
            oclc_ix.setdefault(o, []).append(c)
        for i in c["isbns"]:
            isbn_ix.setdefault(i, []).append(c)
        if c["ntitle"]:
            title_ix.setdefault(c["ntitle"], []).append(c)
    return oclc_ix, isbn_ix, title_ix


def agreement_score(abc, cand):
    """How well author + year corroborate a title match (0..1, plus signflags)."""
    author = year = None
    if abc["author"] and cand["author"]:
        author = fuzz.token_sort_ratio(abc["author"], cand["author"]) / 100.0
    if abc["year"] and cand["year"]:
        year = 1.0 if abc["year"] == cand["year"] else 0.0
    return author, year


def pick_corroborated(abc, candidates):
    """Among same-title candidates, prefer the one author/year agree with."""
    best, best_rank = candidates[0], -1.0
    for cand in candidates:
        author, year = agreement_score(abc, cand)
        rank = (author or 0.0) + (year or 0.0)
        if rank > best_rank:
            best, best_rank = cand, rank
    return best


def fuzzy_match(abc, cited, title_choices):
    """Best title candidate, re-ranked by author/year; returns (cand, confidence)."""
    if not abc["ntitle"]:
        return None, 0.0
    hits = process.extract(
        abc["ntitle"], title_choices, scorer=fuzz.token_sort_ratio, limit=TOPN
    )
    best, best_conf = None, 0.0
    for _choice, score, idx in hits:
        cand = cited[idx]
        title_sim = score / 100.0
        author, year = agreement_score(abc, cand)
        # Two acceptance paths:
        #   A. title-driven  -- title sim alone clears FUZZY_FLOOR
        #   B. corroborated  -- weaker title, but author is (near-)identical AND
        #      the year matches exactly (catches edition/series title variants
        #      like "South America, 1972." vs "Richard Long : South America, 1972.")
        corroborated = author is not None and author >= CORROB_AUTHOR and year == 1.0
        if not (title_sim >= FUZZY_FLOOR
                or (corroborated and title_sim >= CORROB_TITLE_FLOOR)):
            continue
        conf = title_sim
        if author is not None and author >= 0.80:
            conf = min(0.99, conf + 0.04)
        if year == 1.0:
            conf = min(0.99, conf + 0.03)
        elif year == 0.0:
            conf -= 0.10  # title agrees but years conflict -> likely different work
        if conf > best_conf:
            best, best_conf = cand, conf
    if best is None:
        return None, 0.0
    return best, round(best_conf, 3)


def match_all(abc_items, cited):
    oclc_ix, isbn_ix, title_ix = build_indexes(cited)
    title_choices = [c["ntitle"] for c in cited]  # index-aligned with `cited`
    results = []
    for abc in abc_items:
        cand = method = None
        conf = 0.0

        if abc["oclc"] and abc["oclc"] in oclc_ix:
            cand, method, conf = pick_corroborated(abc, oclc_ix[abc["oclc"]]), "oclc", 1.0
        if cand is None:
            hit = next((k for k in abc["isbns"] if k in isbn_ix), None)
            if hit:
                cand, method, conf = pick_corroborated(abc, isbn_ix[hit]), "isbn", 1.0
        if cand is None and abc["ntitle"] in title_ix:
            cand, method, conf = pick_corroborated(abc, title_ix[abc["ntitle"]]), "title", 0.95
        if cand is None:
            cand, conf = fuzzy_match(abc, cited, title_choices)
            if cand is not None:
                method = "fuzzy"

        review = "yes" if (method == "fuzzy" and conf < REVIEW_BELOW) else ""
        results.append(
            {
                "abcItemKey": abc["key"],
                "citedItemKey": cand["key"] if cand else "",
                "method": method or "none",
                "confidence": f"{conf:.3f}" if cand else "0.000",
                "review": review,
                "abcTitle": abc["title"],
                "citedTitle": cand["title"] if cand else "",
            }
        )
    return results


# --------------------------------------------------------------------------- #
def main():
    ap = argparse.ArgumentParser(description="Build the ABC <-> cited-record crosswalk.")
    ap.add_argument("--abc", required=True, help="artists-books.csv")
    ap.add_argument("--marc", required=True, help="artists-books-marc.xml")
    ap.add_argument("--cited", required=True, help="cited-records.csv")
    ap.add_argument("--out", required=True, help="output crosswalk CSV")
    args = ap.parse_args()

    abc_items = load_abc(args.abc, args.marc)
    cited = load_cited(args.cited)
    results = match_all(abc_items, cited)

    fields = ["abcItemKey", "citedItemKey", "method", "confidence", "review",
              "abcTitle", "citedTitle"]
    with open(args.out, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(results)

    # Coverage summary -> stderr.
    counts = {}
    review = 0
    for r in results:
        counts[r["method"]] = counts.get(r["method"], 0) + 1
        if r["review"] == "yes":
            review += 1
    total = len(results)
    matched = total - counts.get("none", 0)
    print(f"\nABC <-> cited-record crosswalk: {matched}/{total} matched "
          f"({100 * matched / total:.1f}%)", file=sys.stderr)
    for m in ("oclc", "isbn", "title", "fuzzy", "none"):
        if m in counts:
            print(f"  {m:6} {counts[m]:5}", file=sys.stderr)
    print(f"  (fuzzy flagged for review: {review})", file=sys.stderr)


if __name__ == "__main__":
    main()
