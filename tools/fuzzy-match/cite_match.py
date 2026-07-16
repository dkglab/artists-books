#!/usr/bin/env python3
"""Reference-work matcher: reconcile a "Cited:" note paragraph to a reference work.

Each paragraph of a Zotero "Cited:" note (sources/zotero/notes.xml) is a free-text
reference to a *reference work* that cites an artist's book. match_all() reconciles
each paragraph to one canonical reference work, by title:

    * substring -- a reference title appears verbatim in the paragraph. This is the
      dominant, high-precision signal (the paragraph quotes the full title); the
      embedded year boosts confidence and breaks length ties.
    * em-exact  -- the <em> title normalizes exactly to a reference title.
    * fuzzy     -- rapidfuzz on the <em> title (flagged for review below
      REVIEW_BELOW).

freeze_citations.py imports match_all to build the frozen citation graph
(sources/citations.ttl). This module was formerly also the standalone citation <->
reference-resource crosswalk builder (issue #42); that crosswalk was retired under
#82 (citations are now frozen by freeze_citations.py), so only the reusable matcher
remains here.
"""
import re

from rapidfuzz import fuzz, process

# Reuse the canonical matcher's title normalizer so titles key identically.
from match import norm_title

MIN_SUBSTR = 10         # ignore reference titles shorter than this as substrings
FUZZY_FLOOR = 0.88      # accept an <em> fuzzy match at/above this title similarity
REVIEW_BELOW = 0.93     # accepted matches below this are flagged for review
SHORT_TITLE = 16        # substring matches on titles shorter than this want review
TOPN = 8


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
