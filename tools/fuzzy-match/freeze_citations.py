#!/usr/bin/env python3
"""Freeze citations to sources/citations.ttl (issue #82, Phase 0, task 3).

The three Zotero libraries are frozen, so the citation edges are computed **once**
and committed as Turtle rather than recomputed every build (this deletes the
`citations.rq` construct stage; see `sources/README.md`). The frozen graph lives
under `sources/` with the other committed inputs -- `graph/` is build output
(gitignored, wiped by `make clean`) -- and is loaded into Fuseki alongside the
two constructed graphs (wired in task 4). Each `Cited:` note
paragraph (`sources/zotero/notes.xml`) is one reference work citing one artist's
book; this generator resolves both ends to their **canonical** URI and emits an
`ab:Citation`, capturing page numbers (#43/#44) while the note HTML is in hand.

Both ends are resolved against the Phase-0 canonical lists (task 2), never the
old crosswalks:

  * citing reference work -- matched from the paragraph text by cite_match.py's
    verified substring/`<em>`/fuzzy matcher (ported from #79), against the
    canonical `sources/reference-works.csv`.
  * cited artist's book -- the note's lib-3 itemKey mapped to the canonical AB
    node via `sources/artists-books.csv` `sourceKeys` (`3:<key>` -> canonicalKey).

Pages come straight from the note markup: a page number inside `<strong>` is an
image of the book (`ab:imagesOnPageNumber`, #44); the rest are passing mentions
(`ab:onPageNumber`, #43). Only confident, resolved paragraphs are emitted; the
uncertain / unmatched / orphaned ones go to the review CSV for a human to bless.
"""
import argparse
import csv
import re
import sys
import xml.etree.ElementTree as ET
from collections import defaultdict

from cite_match import match_all  # #79's verified reference-work matcher
from match import isbn_set, norm_title, year_of

BASE = "https://dkglab.github.io/ns/artists-books/"

BLOCK_DECISIONS = {"no", "unsure"}  # human says this citation is wrong -> don't emit

# Page marker: "p." / "pp." not glued to a preceding word (avoids "esp.", "Press.")
# and immediately followed by a page number (avoids the year's trailing period).
PAGE_MARK = re.compile(r"(?<![A-Za-z])pp?\.\s*(?=\[?\d)", re.I)
DIGIT_RUN = re.compile(r"\d+(?:\s*[-–]\s*\d+)?")  # "23" or "74-79" / en-dash


def norm_page(tok):
    return re.sub(r"\s*[-–]\s*", "-", tok).strip()


def dedupe(seq):
    seen, out = set(), []
    for x in seq:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out


def page_sort_key(tok):
    m = re.match(r"\d+", tok)
    return (int(m.group()) if m else 1 << 30, tok)


# --------------------------------------------------------------------------- #
# Inputs
# --------------------------------------------------------------------------- #
def load_refs(path):
    """Canonical reference works, shaped for cite_match.match_all."""
    refs = []
    with open(path, newline="") as fh:
        for r in csv.DictReader(fh):
            refs.append({
                "key": r["canonicalKey"],
                "title": r.get("title", ""),
                "ntitle": norm_title(r.get("title", "")),
                "year": year_of(r.get("date", "")),
                "isbns": isbn_set(r.get("ISBN", "")),
            })
    return refs


def load_book_index(path):
    """(lib-3 sourceKey -> canonical AB key, canonical AB key -> title)."""
    src2canon, title = {}, {}
    with open(path, newline="") as fh:
        for r in csv.DictReader(fh):
            title[r["canonicalKey"]] = r.get("title", "")
            for tok in r["sourceKeys"].split("; "):
                src2canon[tok] = r["canonicalKey"]
    return src2canon, title


def parse_pages(p):
    """(passing-mention pages, image pages) for one <p> citation element.

    Image pages are the page numbers marked <strong> (a photo of the book, #44);
    passing mentions are the remaining page numbers (#43). Both are read from the
    page region only -- the run after the "pp." marker -- so the year and other
    numbers in the reference string are never mistaken for pages.
    """
    full = "".join(p.itertext())
    marks = list(PAGE_MARK.finditer(full))
    if not marks:
        return [], []
    region = full[marks[0].end():]
    all_pages = dedupe(norm_page(t) for t in DIGIT_RUN.findall(region))
    region_set = set(all_pages)
    image = dedupe(
        norm_page(t)
        for s in p.iter("strong")
        for t in DIGIT_RUN.findall("".join(s.itertext()))
    )
    image = [t for t in image if t in region_set]  # only bold *page* numbers count
    image_set = set(image)
    passing = [t for t in all_pages if t not in image_set]
    return passing, image


def load_paragraphs(notes_path):
    """One dict per citation paragraph, carrying parsed pages + the flattened text."""
    out = []
    for note in ET.parse(notes_path).getroot().findall("note"):
        key = note.get("itemKey")
        for p in note.findall("p"):
            passing, image = parse_pages(p)
            out.append({
                "citedItemKey": key,
                "n": p.get("n"),
                "text": (p.get("text") or "").strip(),
                "em": " ".join("".join(e.itertext()) for e in p.findall("em")).strip(),
                "passing": passing,
                "image": image,
            })
    return out


# --------------------------------------------------------------------------- #
# Turtle emission
# --------------------------------------------------------------------------- #
def ttl_str(s):
    """Escape a string literal for a Turtle "..." quote."""
    return (s.replace("\\", "\\\\").replace('"', '\\"')
             .replace("\n", "\\n").replace("\r", "\\r").replace("\t", "\\t"))


def emit_ttl(path, citations):
    """citations: {(refKey, bookKey): {label, passing:set, image:set}} -> Turtle."""
    lines = [
        "# Frozen citation edges (issue #82, Phase 0, task 3).",
        "# Generated once by tools/fuzzy-match/freeze_citations.py from the frozen",
        "# Zotero notes against the canonical AB/RW lists; committed, not rebuilt.",
        "@prefix ab: <" + BASE + "> .",
        "@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .",
        "@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .",
        "",
    ]
    for (ref, book) in sorted(citations):
        c = citations[(ref, book)]
        iri = f"<{BASE}reference/{ref}/citation/{book}>"
        parts = [
            f"{iri} a ab:Citation",
            f"    ab:citedBy <{BASE}reference/{ref}>",
            f"    ab:cites <{BASE}item/{book}>",
            f'    rdfs:label "{ttl_str(c["label"])}"',
        ]
        passing = sorted(c["passing"], key=page_sort_key)
        image = sorted(c["image"], key=page_sort_key)
        if passing:
            vals = " , ".join(f'"{ttl_str(p)}"' for p in passing)
            parts.append(f"    ab:onPageNumber {vals}")
        if image:
            vals = " , ".join(f'"{ttl_str(p)}"' for p in image)
            parts.append(f"    ab:imagesOnPageNumber {vals}")
        lines.append(" ;\n".join(parts) + " .\n")
    with open(path, "w") as fh:
        fh.write("\n".join(lines))


def load_decisions(path):
    """Load the hand-owned citation-decisions overlay, keyed by (refKey, bookKey).

    Returns {(refKey, bookKey): decision} for rows carrying a recorded decision:
    'yes' blesses an uncertain (flagged) match into the graph; 'no'/'unsure'
    suppress a citation the matcher would otherwise emit. Blank/unreviewed rows --
    and a missing or unspecified file -- yield no override, so emission falls back
    to the matcher's own confidence (identical to the pre-overlay behaviour). Keyed
    by the (reference work, artist's book) pair, which is the citation's identity:
    the libraries are frozen and the matcher deterministic, so the pairing does not
    drift between runs. Same discipline as artists-books-dedup-decisions.csv.
    """
    decisions = {}
    if not path:
        return decisions
    try:
        fh = open(path, newline="")
    except FileNotFoundError:
        print(f"  no decisions overlay at {path}; emission follows matcher confidence",
              file=sys.stderr)
        return decisions
    with fh:
        for r in csv.DictReader(fh):
            d = (r.get("decision") or "").strip().lower()
            if d:
                decisions[(r["refKey"], r["bookKey"])] = d
    return decisions


# --------------------------------------------------------------------------- #
def main():
    ap = argparse.ArgumentParser(description="Freeze citations to Turtle (#82).")
    ap.add_argument("--notes", required=True, help="sources/zotero/notes.xml")
    ap.add_argument("--refs", required=True, help="sources/reference-works.csv")
    ap.add_argument("--books", required=True, help="sources/artists-books.csv")
    ap.add_argument("--out", required=True, help="graph/citations.ttl")
    ap.add_argument("--review", required=True, help="citation review CSV")
    ap.add_argument("--decisions", help="hand-owned citation-decisions overlay "
                    "(sources/citations-decisions.csv); optional")
    args = ap.parse_args()

    refs = load_refs(args.refs)
    src2canon, book_title = load_book_index(args.books)
    ref_title = {r["key"]: r["title"] for r in refs}
    paras = load_paragraphs(args.notes)
    results = match_all(paras, refs)  # index-aligned with paras
    decisions = load_decisions(args.decisions)  # hand-owned overrides, gates emission

    citations = {}
    review_rows = []
    stats = defaultdict(int)
    for para, res in zip(paras, results):
        book = src2canon.get(f"3:{para['citedItemKey']}", "")
        ref = res["refItemKey"]
        decision = decisions.get((ref, book), "")     # hand-owned override
        if res["method"] == "none" and not res["review"]:
            status = "annotation"                     # editorial aside, not a citation
        elif not ref:
            status = "unmatched"                       # no reference work resolved
        elif decision in BLOCK_DECISIONS:
            status = "blocked"                         # human rejected this match -> suppress
        elif res["review"] == "yes" and decision != "yes":
            status = "review"                          # uncertain match, not yet blessed
        elif not book:
            status = "orphan"                          # cited record has no canonical AB node
        else:
            status = "emitted"
        stats[status] += 1

        if status == "emitted":
            key = (ref, book)
            cit = citations.setdefault(key, {"label": para["text"], "passing": [], "image": []})
            cit["passing"] = dedupe(cit["passing"] + para["passing"])
            cit["image"] = dedupe(cit["image"] + para["image"])
            if len(para["text"]) > len(cit["label"]):  # keep the fullest label
                cit["label"] = para["text"]
        if status != "annotation":
            review_rows.append({
                "status": status, "refKey": ref, "refTitle": ref_title.get(ref, ""),
                "bookKey": book, "bookTitle": book_title.get(book, ""),
                "method": res["method"], "confidence": res["confidence"],
                "onPages": ", ".join(para["passing"]), "imagePages": ", ".join(para["image"]),
                "verbatim": para["text"],
            })

    # Image pages are a kind of on-page (imagesOnPageNumber rdfs:subPropertyOf
    # onPageNumber); the data lists each page once, so drop any that appear in both.
    for cit in citations.values():
        cit["passing"] = [p for p in cit["passing"] if p not in set(cit["image"])]

    emit_ttl(args.out, citations)
    with open(args.review, "w", newline="") as fh:
        cols = ["status", "refKey", "refTitle", "bookKey", "bookTitle", "method",
                "confidence", "onPages", "imagePages", "verbatim"]
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        w.writerows(review_rows)

    books = {b for _, b in citations}
    works = {r for r, _ in citations}
    print(f"\ncitations frozen: {len(citations)} edges "
          f"linking {len(books)} artists' books to {len(works)} reference works",
          file=sys.stderr)
    for s in ("emitted", "review", "blocked", "unmatched", "orphan", "annotation"):
        if stats[s]:
            print(f"  {s:10} {stats[s]:5} paragraphs", file=sys.stderr)


if __name__ == "__main__":
    main()
