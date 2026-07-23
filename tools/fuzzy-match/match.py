#!/usr/bin/env python3
"""Bibliographic matching helpers shared by dedup.py (issue #82).

Normalizers and comparators for reconciling the same work catalogued across
libraries: OCLC / ISBN expansion, accent-folded title and author keys, a year
extractor, and an author+year agreement score. dedup.py imports these to collapse
lib 1/2/3 duplicates into one canonical node, and cite_match.py reuses norm_title
so both key titles identically.

This module was formerly also the standalone ABC <-> cited-record crosswalk
builder (issue #55); that crosswalk was retired under #82 (the canonical dedup
subsumes it), so only the reusable matching library remains here.
"""
import re
import unicodedata

from rapidfuzz import fuzz

# Fuzzy thresholds (title similarity is 0..1); imported by dedup.py.
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
# Matching
# --------------------------------------------------------------------------- #
def agreement_score(abc, cand):
    """How well author + year corroborate a title match (0..1, plus signflags)."""
    author = year = None
    if abc["author"] and cand["author"]:
        author = fuzz.token_sort_ratio(abc["author"], cand["author"]) / 100.0
    if abc["year"] and cand["year"]:
        year = 1.0 if abc["year"] == cand["year"] else 0.0
    return author, year
