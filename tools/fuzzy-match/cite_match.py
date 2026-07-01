#!/usr/bin/env python3
"""Build the citation <-> reference-resource crosswalk (issue #42).

Each "Cited:" note paragraph (sources/zotero/notes.xml) is a free-text reference to a
*reference work* that cites an artist's book. To give those citations a stable
identity anchored on the reference resource -- reference/<refItemKey>/citation/...
-- each paragraph must be reconciled to one of the rows in the *Reference
resources* collection (sources/zotero/reference-resources.csv).

The note paragraph literally contains the reference work's full title (often also
wrapped in <em>), so the dominant, high-precision signal is: a reference row whose
normalized title is a substring of the normalized paragraph text. Year (and the
<em> title, when present) corroborate and disambiguate.

Precedence (first hit wins, recorded as `method`):

    1. substring -- a reference title (>= MIN_SUBSTR chars) is a substring of the
                    paragraph; longest title wins, year used to break ties / boost.
    2. em-exact  -- the <em> title normalizes exactly to a reference title.
    3. fuzzy     -- rapidfuzz on the <em> title; flagged for review below REVIEW_BELOW.

Output: one row per scoped note paragraph (paragraphs on the lib-3 cited records
that the ABC crosswalk links to). Unmatched paragraphs that still look like a real
citation get an empty refItemKey and review=yes; pure annotation paragraphs (the
"*Note: ...*" asides) are recorded as method `none` without a review flag. Mirrors
the conventions of abc-master-crosswalk.csv (method/confidence/review). A coverage
summary is printed to stderr.
"""
import argparse
import csv
import re
import sys
import xml.etree.ElementTree as ET

from rapidfuzz import fuzz, process

# Reuse the ABC matcher's normalizers so both crosswalks key titles identically.
from match import norm_title, year_of, isbn_set

MIN_SUBSTR = 10         # ignore reference titles shorter than this as substrings
FUZZY_FLOOR = 0.88      # accept an <em> fuzzy match at/above this title similarity
REVIEW_BELOW = 0.93     # accepted matches below this are flagged for review
SHORT_TITLE = 16        # substring matches on titles shorter than this want review
TOPN = 8


def load_refs(path):
    """reference-resources rows with normalized title / year / ISBNs."""
    rows = []
    with open(path, newline="") as fh:
        for r in csv.DictReader(fh):
            rows.append(
                {
                    "key": r["itemKey"],
                    "title": r.get("title", ""),
                    "ntitle": norm_title(r.get("title", "")),
                    "year": year_of(r.get("date", "")),
                    "isbns": isbn_set(r.get("ISBN", "")),
                }
            )
    return rows


def load_paragraphs(notes_path, scope_keys):
    """(citedItemKey, n, text, emtitle) for paragraphs on scoped cited records."""
    out = []
    root = ET.parse(notes_path).getroot()
    for note in root.findall("note"):
        key = note.get("itemKey")
        if scope_keys is not None and key not in scope_keys:
            continue
        for p in note.findall("p"):
            text = (p.get("text") or "").strip()
            em = " ".join("".join(e.itertext()) for e in p.findall("em")).strip()
            out.append({"citedItemKey": key, "n": p.get("n"), "text": text, "em": em})
    return out


def is_annotation(text):
    """Editorial asides, not references (e.g. '*Note: ...*', 'Cited*:')."""
    t = text.strip()
    return (not t) or t.startswith("*") or t.lower().rstrip("*: ") == "cited"


def match_substring(ntext, text_years, refs):
    """Longest reference title that is a substring of the paragraph.

    The full title appearing verbatim is the high-precision signal, so a year is
    only used to *boost* confidence and to break length ties -- never to penalize:
    citation titles routinely embed date ranges ("...Work of Art 1963-2000") that
    are not the publication year, so a mismatch is not evidence against the match.
    """
    best, best_len = None, 0
    for r in refs:
        nt = r["ntitle"]
        if len(nt) < MIN_SUBSTR or nt not in ntext:
            continue
        # Prefer the longest title; on length ties, prefer one whose year is present.
        better = len(nt) > best_len or (
            len(nt) == best_len and r["year"] and r["year"] in text_years
            and not (best and best["year"] in text_years)
        )
        if better:
            best, best_len = r, len(nt)
    if best is None:
        return None
    conf = 0.99 if (best["year"] and best["year"] in text_years) else 0.95
    # Only short, generic titles ("Artists books") are ambiguous enough to review.
    review = "yes" if len(best["ntitle"]) < SHORT_TITLE else ""
    return best, "substring", conf, review


def match_em(em, refs, title_ix, title_choices):
    """Exact-normalized then fuzzy match on the <em> title."""
    nem = norm_title(em)
    if not nem:
        return None
    if nem in title_ix:
        return title_ix[nem][0], "em-exact", 0.95, ""
    hits = process.extract(nem, title_choices, scorer=fuzz.token_sort_ratio, limit=TOPN)
    if not hits:
        return None
    choice, score, idx = hits[0]
    sim = score / 100.0
    if sim < FUZZY_FLOOR:
        return None
    return refs[idx], "fuzzy", round(sim, 3), ("yes" if sim < REVIEW_BELOW else "")


def match_all(paras, refs):
    title_ix = {}
    for r in refs:
        if r["ntitle"]:
            title_ix.setdefault(r["ntitle"], []).append(r)
    title_choices = [r["ntitle"] for r in refs]  # index-aligned with refs

    results = []
    for p in paras:
        cand = method = review = None
        conf = 0.0
        ntext = norm_title(p["text"])
        text_years = set(re.findall(r"\b(?:1[5-9]\d\d|20\d\d)\b", p["text"]))

        if is_annotation(p["text"]):
            method = "none"
        else:
            hit = match_substring(ntext, text_years, refs)
            if hit is None and p["em"]:
                hit = match_em(p["em"], refs, title_ix, title_choices)
            if hit is not None:
                cand, method, conf, review = hit
            else:
                method, review = "none", "yes"  # looks like a citation but unmatched

        results.append(
            {
                "citedItemKey": p["citedItemKey"],
                "n": p["n"],
                "refItemKey": cand["key"] if cand else "",
                "method": method,
                "confidence": f"{conf:.3f}",
                "review": review or "",
                "refTitle": cand["title"] if cand else "",
                "citationText": p["text"],
            }
        )
    return results


def main():
    ap = argparse.ArgumentParser(description="Build the citation <-> reference crosswalk.")
    ap.add_argument("--notes", required=True, help="notes.xml")
    ap.add_argument("--refs", required=True, help="reference-resources.csv")
    ap.add_argument("--abc-crosswalk", required=True,
                    help="abc-master-crosswalk.csv (scopes paragraphs to cited records in use)")
    ap.add_argument("--out", required=True, help="output crosswalk CSV")
    args = ap.parse_args()

    with open(args.abc_crosswalk, newline="") as fh:
        scope = {r["citedItemKey"] for r in csv.DictReader(fh) if r["citedItemKey"].strip()}

    refs = load_refs(args.refs)
    paras = load_paragraphs(args.notes, scope)
    results = match_all(paras, refs)

    fields = ["citedItemKey", "n", "refItemKey", "method", "confidence", "review",
              "refTitle", "citationText"]
    with open(args.out, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(results)

    counts, review = {}, 0
    for r in results:
        counts[r["method"]] = counts.get(r["method"], 0) + 1
        if r["review"] == "yes":
            review += 1
    total = len(results)
    matched = sum(1 for r in results if r["refItemKey"])
    print(f"\ncitation <-> reference crosswalk: {matched}/{total} paragraphs matched "
          f"({100 * matched / total:.1f}%)", file=sys.stderr)
    for m in ("substring", "em-exact", "fuzzy", "none"):
        if m in counts:
            print(f"  {m:10} {counts[m]:5}", file=sys.stderr)
    print(f"  (flagged for review: {review})", file=sys.stderr)


if __name__ == "__main__":
    main()
