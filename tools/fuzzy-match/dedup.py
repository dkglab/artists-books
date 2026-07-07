#!/usr/bin/env python3
"""Dedup the three Zotero libraries into canonical lists (issue #82, Phase 0, task 2).

One-time throwaway generator. The three libraries are frozen (see
`sources/zotero/README.md`), so we reconcile cross-library identity **once** and
snapshot the result as committed authoritative data:

    sources/artists-books.csv   -- one row per canonical artists' book
    sources/reference-works.csv -- one row per canonical reference work

Each row carries the **canonical key** (chosen by precedence lib 3 > lib 2 > lib 1,
see `sources/README.md` "Canonical key scheme"), the **source keys** of every
library record that deduplicated into it (as `libN:KEY` tokens), and a **held**
flag (true when a member is one of Sloane's physical holdings -- lib 1's
`Artists' Books Collection`).

Two reconciliation signals, in order of authority:

  1. owl:sameAs  -- the DB already records 10,677 explicit same-work links
     (mostly lib 3 -> lib 2, plus a few lib 1 -> lib 3). Authoritative: union
     these directly. This alone clusters lib 2 <-> lib 3.
  2. fuzzy       -- lib 1 records carry almost no sameAs (only 7 of the 1,341
     ABC books), so the residual lib-1 singletons are attached to their lib-2/
     lib-3 twin bibliographically, reusing match.py's ISBN / exact-title /
     author+year signals. Every fuzzy attach is flagged in the review CSV.

Unlike the old `match.py` (a pairwise lib-1 -> lib-3-cited bridge), this produces
one node per work across all three libraries; it *replaces* the crosswalk rather
than extending it. Reads `zotero.sqlite` directly -- no intermediate export CSVs,
since the whole tool is archived after Phase 0.
"""
import argparse
import csv
import sqlite3
import sys
from collections import defaultdict

from rapidfuzz import fuzz, process

from match import (
    CORROB_AUTHOR,
    CORROB_TITLE_FLOOR,
    FUZZY_FLOOR,
    REVIEW_BELOW,
    TOPN,
    agreement_score,
    isbn_set,
    norm_author,
    norm_title,
    oclc_set_from_extra,
    year_of,
)

# Zotero group library ids -> our libraryID (users/* targets are an unrelated
# external account, not our lib 1 owner, so they don't resolve to an in-DB node).
GROUP_TO_LIB = {"262987": 2, "2352415": 3}

# AB / RW collection scope, keyed by libraryID (see sources/zotero/README.md
# "Main book collections"). lib-3 ABCI is only ~88% inside "Artists' books", so
# both lib-3 collections are unioned; lib-2 ABCI is a subset of Master list.
AB_COLLECTIONS = {
    1: ["Artists' Books Collection"],
    2: ["Master list of artists' books with or without citations", "ABCI"],
    3: ["Artists' books", "ABCI"],
}
HELD_COLLECTION = ("Artists' Books Collection", 1)  # membership => a Sloane holding
REF_COLLECTION = ("Reference resources", 3)          # the reference-work scope (lib 3)

# ~63 lib-3 books carry a "Cited:" note but sit in no collection, so the
# collection scope alone misses them -- yet they are cited artists' books, and
# under #82 every cited book must be a first-class node (or its citation has
# nothing to attach to). Union note-bearing lib-3 records into the AB scope.
CITED_NOTE_INCLUDE = (
    "i.libraryID = 3 AND EXISTS (SELECT 1 FROM itemNotes n "
    "WHERE n.parentItemID = i.itemID AND n.note LIKE '%Cited%')"
)

# Output field set: canonical record's bibliographic fields, after the provenance
# columns. Matches the Zotero field names the Phase-1 construct queries read.
FIELD_COLS = [
    "title", "date", "publisher", "place", "ISBN", "ISSN", "language",
    "numPages", "edition", "series", "seriesNumber", "callNumber", "url",
    "extra", "shortTitle", "creators",
]
OUT_COLS = ["canonicalKey", "canonicalLib", "held", "sourceKeys"] + FIELD_COLS


# --------------------------------------------------------------------------- #
# Union-Find over (libraryID, itemKey) nodes
# --------------------------------------------------------------------------- #
class UnionFind:
    def __init__(self):
        self.parent = {}

    def find(self, x):
        self.parent.setdefault(x, x)
        root = x
        while self.parent[root] != root:
            root = self.parent[root]
        while self.parent[x] != root:  # path compression
            self.parent[x], x = root, self.parent[x]
        return root

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[ra] = rb


# --------------------------------------------------------------------------- #
# Loading from zotero.sqlite
# --------------------------------------------------------------------------- #
def _scope_predicate(collections_by_lib):
    """SQL EXISTS clause selecting book items in the given per-library collections."""
    clauses = []
    for lib, names in collections_by_lib.items():
        quoted = ", ".join("'" + n.replace("'", "''") + "'" for n in names)
        clauses.append(f"(c.libraryID = {lib} AND c.collectionName IN ({quoted}))")
    return " OR ".join(clauses)


def load_scope(conn, collections_by_lib, exclude=None, extra_include=None):
    """Return {(lib, key): record dict} for book items in scope.

    `exclude` is an optional (collectionName, libraryID) whose members are dropped
    (used to keep the reference works out of the artists'-book set).
    `extra_include` is an optional raw-SQL boolean OR'd with the collection scope
    (used to fold in note-bearing lib-3 records that sit in no collection).
    """
    include = _scope_predicate(collections_by_lib)
    extra_sql = f"OR ({extra_include})" if extra_include else ""
    exclude_sql = ""
    if exclude:
        name, lib = exclude
        exclude_sql = f"""
          AND NOT EXISTS (SELECT 1 FROM collectionItems ci JOIN collections c USING(collectionID)
                          WHERE ci.itemID = i.itemID
                            AND c.libraryID = {lib}
                            AND c.collectionName = '{name.replace("'", "''")}')"""
    pivots = ",\n            ".join(
        f"MAX(CASE WHEN f.fieldName = '{fn}' THEN idv.value END) AS \"{fn}\""
        for fn in FIELD_COLS if fn != "creators"
    )
    sql = f"""
        SELECT
            i.libraryID AS libraryID,
            i.key AS itemKey,
            {pivots},
            (
                SELECT GROUP_CONCAT(name, '; ') FROM (
                    SELECT TRIM(REPLACE(REPLACE(REPLACE(
                             CASE
                               WHEN cr.fieldMode = 1  THEN cr.lastName
                               WHEN cr.firstName = '' THEN cr.lastName
                               WHEN cr.lastName = ''  THEN cr.firstName
                               ELSE cr.firstName || ' ' || cr.lastName
                             END, '|', ''), '  ', ' '), '  ', ' ')) AS name
                    FROM itemCreators ic
                    JOIN creators cr ON cr.creatorID = ic.creatorID
                    WHERE ic.itemID = i.itemID
                    ORDER BY ic.orderIndex
                )
            ) AS creators
        FROM items i
        JOIN itemTypes it ON it.itemTypeID = i.itemTypeID
        LEFT JOIN itemData id ON id.itemID = i.itemID
        LEFT JOIN fieldsCombined f ON f.fieldID = id.fieldID
        LEFT JOIN itemDataValues idv ON idv.valueID = id.valueID
        WHERE it.typeName NOT IN ('attachment', 'note', 'annotation')
          AND (EXISTS (SELECT 1 FROM collectionItems ci JOIN collections c USING(collectionID)
                       WHERE ci.itemID = i.itemID AND ({include}))
               {extra_sql}){exclude_sql}
        GROUP BY i.itemID
    """
    records = {}
    for row in conn.execute(sql):
        r = dict(row)
        node = (r["libraryID"], r["itemKey"])
        r["ntitle"] = norm_title(r.get("title") or "")
        r["isbns"] = isbn_set(r.get("ISBN") or "")
        r["oclcs"] = oclc_set_from_extra(r.get("extra") or "")
        r["author"] = norm_author((r.get("creators") or "").split(";")[0])
        r["year"] = year_of(r.get("date") or "")
        records[node] = r
    return records


def load_sameas(conn):
    """Yield (from_node, to_node) for every owl:sameAs edge resolvable to two nodes."""
    item_node = {
        iid: (lib, key)
        for iid, lib, key in conn.execute("SELECT itemID, libraryID, key FROM items")
    }
    edges = []
    for iid, obj in conn.execute(
        "SELECT itemID, object FROM itemRelations r "
        "JOIN relationPredicates p USING(predicateID) WHERE p.predicate = 'owl:sameAs'"
    ):
        src = item_node.get(iid)
        if not src or "/items/" not in obj:
            continue
        head, key = obj.rsplit("/items/", 1)
        gid = head.rsplit("/groups/", 1)[-1] if "/groups/" in head else None
        lib = GROUP_TO_LIB.get(gid)
        if lib is None:  # users/* target (external), unresolvable to our libraries
            continue
        edges.append((src, (lib, key)))
    return edges


# --------------------------------------------------------------------------- #
# Clustering
# --------------------------------------------------------------------------- #
TITLE_MIN = 6        # min normalized-title length to trust a title+author merge
ISBN_MAX_BUCKET = 25  # an identifier shared by more nodes than this is junk, skip


def union_by_signal(uf, records, keys_of, max_bucket=None):
    """Union every node that shares a key produced by keys_of(record).

    Applied globally across all three libraries after the sameAs pass, this is
    the high-precision dedup that sameAs misses -- e.g. two lib-2 records of one
    work where only one carries the lib-3 sameAs, but both share the ISBN. A
    bucket larger than max_bucket is skipped (a junk identifier, not a work) and
    reported. Returns the list of skipped (key, size) pairs.
    """
    buckets = defaultdict(list)
    for n, rec in records.items():
        for k in keys_of(rec):
            buckets[k].append(n)
    skipped = []
    for k, nodes in buckets.items():
        if max_bucket is not None and len(nodes) > max_bucket:
            skipped.append((k, len(nodes)))
            continue
        for m in nodes[1:]:
            uf.union(nodes[0], m)
    return skipped


def title_author_key(rec):
    """Merge key for the no-ISBN case: exact normalized title + author + year.

    Author keeps identical generic titles by different authors apart; **year**
    keeps distinct editions of one work apart (e.g. the 1980..2016 editions of
    Tom Phillips' *A Humument*, or Moeglin-Delcroix 1985 vs 2012). Editions still
    collapse when an authoritative ISBN or sameAs links them; this pass just
    won't collapse them on bibliographic near-identity alone -- the safe default
    for a frozen canonical set, where a wrong merge is harder to undo than a
    missed one. All three parts must be present."""
    if rec["author"] and rec["year"] and len(rec["ntitle"]) >= TITLE_MIN:
        return [(rec["ntitle"], rec["author"], rec["year"])]
    return []


def fuzzy_residual(uf, records, review):
    """Attach lib-1 nodes still in a lib-1-only cluster to a group twin by fuzzy
    title (author+year re-ranked). The exact signals (sameAs/ISBN/OCLC/title+
    author) already ran globally, so only near-miss titles reach here -- exactly
    the uncertain candidates worth a human's review."""
    group_nodes = [n for n in records if n[0] in (2, 3)]
    group_recs = [records[n] for n in group_nodes]
    title_choices = [rec["ntitle"] for rec in group_recs]  # index-aligned
    cluster_has_group = {uf.find(n) for n in records if n[0] in (2, 3)}

    for n in [x for x in records if x[0] == 1]:
        if uf.find(n) in cluster_has_group:
            continue
        abc = records[n]
        cand, conf = _fuzzy(abc, group_nodes, group_recs, title_choices)
        if cand is None:
            continue
        uf.union(n, cand)
        review.append({
            "lib1Key": n[1], "twinKey": cand[1], "twinLib": cand[0],
            "method": "fuzzy", "confidence": f"{conf:.3f}",
            "review": "yes" if conf < REVIEW_BELOW else "",
            "lib1Title": abc.get("title") or "", "twinTitle": records[cand].get("title") or "",
        })


def _fuzzy(abc, group_nodes, group_recs, title_choices):
    """Best title candidate re-ranked by author/year (mirrors match.py.fuzzy_match)."""
    if not abc["ntitle"]:
        return None, 0.0
    hits = process.extract(abc["ntitle"], title_choices, scorer=fuzz.token_sort_ratio, limit=TOPN)
    best, best_conf = None, 0.0
    for _choice, score, idx in hits:
        cand = group_recs[idx]
        title_sim = score / 100.0
        author, year = agreement_score(abc, cand)
        corroborated = author is not None and author >= CORROB_AUTHOR and year == 1.0
        if not (title_sim >= FUZZY_FLOOR or (corroborated and title_sim >= CORROB_TITLE_FLOOR)):
            continue
        conf = title_sim
        if author is not None and author >= 0.80:
            conf = min(0.99, conf + 0.04)
        if year == 1.0:
            conf = min(0.99, conf + 0.03)
        elif year == 0.0:
            conf -= 0.10
        if conf > best_conf:
            best, best_conf = group_nodes[idx], conf
    if best is None:
        return None, 0.0
    return best, round(best_conf, 3)


def build_clusters(uf, records, provenance):
    """root -> {'members': [nodes with records], 'sourceKeys': [libN:KEY, ...]}"""
    clusters = defaultdict(lambda: {"members": [], "allnodes": set()})
    for n in records:
        clusters[uf.find(n)]["members"].append(n)
        clusters[uf.find(n)]["allnodes"].add(n)
    # Fold in sameAs neighbours (even out-of-scope) as provenance-only source keys.
    for n in list(records):
        for nb in provenance.get(n, ()):
            clusters[uf.find(n)]["allnodes"].add(nb)
    return clusters


def canonical_row(members, allnodes, records):
    """Pick the canonical member (lib 3 > lib 2 > lib 1; lowest key breaks ties)
    and build its output row."""
    canon = min(members, key=lambda n: (-n[0], n[1]))  # highest lib, then lowest key
    lib, key = canon
    held = "true" if any(m[0] == 1 for m in members) else ""
    source_keys = "; ".join(f"{l}:{k}" for l, k in sorted(allnodes, key=lambda n: (-n[0], n[1])))
    rec = records[canon]
    row = {"canonicalKey": key, "canonicalLib": lib, "held": held, "sourceKeys": source_keys}
    for fn in FIELD_COLS:
        row[fn] = rec.get(fn) or ""
    return row


# --------------------------------------------------------------------------- #
def dedup(conn, scope_collections, exclude, do_fuzzy, extra_include=None):
    records = load_scope(conn, scope_collections, exclude=exclude, extra_include=extra_include)
    provenance = defaultdict(set)
    uf = UnionFind()
    # 1. sameAs -- authoritative, DB-recorded same-work links (mostly lib3<->lib2).
    for a, b in load_sameas(conn):
        provenance[a].add(b)
        provenance[b].add(a)
        if a in records and b in records:  # union only in-scope <-> in-scope
            uf.union(a, b)
    # 2-4. high-precision bibliographic dedup across all libraries (catches the
    # duplicates sameAs misses, e.g. two lib-2 records of one work).
    skipped = union_by_signal(uf, records, lambda r: r["isbns"], ISBN_MAX_BUCKET)
    skipped += union_by_signal(uf, records, lambda r: r["oclcs"], ISBN_MAX_BUCKET)
    union_by_signal(uf, records, title_author_key)
    for k, size in skipped:
        print(f"  skipped junk identifier {k!r} shared by {size} records", file=sys.stderr)
    for n in records:  # ensure singletons have a root
        uf.find(n)

    # 5. fuzzy residual -- only lib-1 books with no exact twin (uncertain; reviewed).
    review = []
    if do_fuzzy:
        fuzzy_residual(uf, records, review)

    clusters = build_clusters(uf, records, provenance)
    rows = [canonical_row(c["members"], c["allnodes"], records)
            for c in clusters.values() if c["members"]]
    rows.sort(key=lambda r: (r["title"] or "").casefold())
    return rows, review


def write_csv(path, cols, rows):
    with open(path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def summarize(label, rows, review):
    held = sum(1 for r in rows if r["held"])
    by_lib = defaultdict(int)
    for r in rows:
        by_lib[r["canonicalLib"]] += 1
    print(f"\n{label}: {len(rows)} canonical works "
          f"(canonical lib3={by_lib[3]} lib2={by_lib[2]} lib1={by_lib[1]}; held={held})",
          file=sys.stderr)
    if review:
        by_method = defaultdict(int)
        flagged = 0
        for r in review:
            by_method[r["method"]] += 1
            flagged += r["review"] == "yes"
        methods = " ".join(f"{m}={n}" for m, n in sorted(by_method.items()))
        print(f"  lib-1 fuzzy-attached: {len(review)} ({methods}); "
              f"flagged for review: {flagged}", file=sys.stderr)


def main():
    ap = argparse.ArgumentParser(description="Dedup the three Zotero libraries (#82).")
    ap.add_argument("--db", required=True, help="sources/zotero/zotero.sqlite")
    ap.add_argument("--out-books", required=True, help="sources/artists-books.csv")
    ap.add_argument("--out-refs", required=True, help="sources/reference-works.csv")
    ap.add_argument("--review", required=True, help="lib-1 attach review CSV")
    args = ap.parse_args()

    conn = sqlite3.connect(f"file:{args.db}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row

    books, review = dedup(conn, AB_COLLECTIONS, exclude=REF_COLLECTION, do_fuzzy=True,
                          extra_include=CITED_NOTE_INCLUDE)
    refs, _ = dedup(conn, {3: [REF_COLLECTION[0]]}, exclude=None, do_fuzzy=False)

    write_csv(args.out_books, OUT_COLS, books)
    write_csv(args.out_refs, OUT_COLS, refs)
    write_csv(args.review,
              ["lib1Key", "twinKey", "twinLib", "method", "confidence", "review",
               "lib1Title", "twinTitle"], review)

    summarize("artists-books", books, review)
    summarize("reference-works", refs, [])


if __name__ == "__main__":
    main()
