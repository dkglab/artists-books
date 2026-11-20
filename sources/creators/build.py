#!/usr/bin/env python3
"""Resolve creator identity across the corpus (issue #170, steps 2, 4-6).

Reads
  sources/creators/occurrences.csv     every MARC creator field (mine.py)
  sources/creators/zotero-creators.csv the structured Zotero creators (mine.py)
  sources/creators/lc-viaf.csv         frozen id.loc.gov lookups: LC id ->
                                       VIAF, ISNI, authorized label, successor
                                       (reconcile.py; optional)
  sources/creators/decisions.csv       hand overrides (optional)
and writes
  sources/creators/authority.csv       one row per resolved agent
  sources/creators/agents.csv          the join table both construct queries
                                       read: (source, canonicalKey, tag, name)
                                       -> agent URI, key and preferred label
  sources/creators/review.csv          what the rules declined to decide

Clustering (union-find over field occurrences):
  1. Identifiers: occurrences sharing an LC id, VIAF, ISNI, GND id or WorldCat
     Entity are one agent; ids in the same field link each other; the frozen
     id.loc.gov table links an LC id to its VIAF/ISNI (and a deprecated id to
     its successor).
  2. Dated headings: personal-name occurrences with the same name *and* the same
     birth year ("Drucker, Johanna, 1952-") are one agent; corporate/meeting
     occurrences with the same full heading likewise. A group is merged only if
     the merge would not put two different LC ids into one agent; otherwise it
     goes to review.
  3. Name joins for agents still without an identifier: a dated one joins the
     single identified agent with that name whose birth year doesn't contradict
     it; then an undated one joins the single other agent with that name. None
     -> it stays a local agent of its own; several -> review, and it stays
     local.
  4. decisions.csv: `merge` (a, b) unions the agents holding two keys;
     `separate` (a) exempts a name key from rule 3; `label` (a, label) sets an
     agent's preferred label. Keys are typed: lc:<id>, viaf:<id>, isni:<id>,
     gnd:<id>, name:<name key>, heading:<heading key>.

An agent with an LC id is labelled with LC's authorized heading; otherwise with
its commonest controlled, then dated, then any heading.

URI minting is unchanged from the queries' old per-field rule, applied to the
agent: VIAF, else ISNI, else ab:creator/<lcId>, else ab:creator/<slug of label>.

Books with no MARC creator field are credited from Zotero, joined by name key to
an agent only when exactly one agent carries that name.
"""
import collections
import csv
import os
import re
import sys
import unicodedata

D = "sources/creators"
AB = "https://dkglab.github.io/ns/artists-books/"
ID_FIELDS = ["lcId", "viaf", "isni", "gnd", "wcEntity"]

# A trailing date segment of a personal heading: "1952-", "1883-1964",
# "b. 1940", "active 1970-1980", "approximately 1500".
DATE_TAIL = re.compile(
    r"(?:,\s*|\s+)(?:\(?\s*(?:b\.|d\.|born|died|ca\.|approximately|active|fl\.|"
    r"\d{1,2}(?:st|nd|rd|th) cent)\s*)?\d{3,4}\??(?:-\S*)?\)?\s*$", re.I)
YEAR = re.compile(r"\d{3,4}")

# Zotero creator type -> (LC relator code, relator term). The terms match the
# ones the construct queries' relator table labels MARC $e roles with.
ZOTERO_ROLES = {
    "artist": ("art", "artist"), "author": ("aut", "author"),
    "bookAuthor": ("aut", "author"), "creator": ("cre", "creator"),
    "editor": ("edt", "editor"), "seriesEditor": ("edt", "editor"),
    "contributor": ("ctb", "contributor"), "translator": ("trl", "translator"),
    "organizer": ("orm", "organizer"), "sponsor": ("spn", "sponsor"),
    "cosponsor": ("spn", "sponsor"), "interviewee": ("ive", "interviewee"),
    "interviewer": ("ivr", "interviewer"), "composer": ("cmp", "composer"),
    "commenter": ("wac", "writer of added commentary"),
}
# Creator types that make a Zotero creator a principal one -- the equivalent of
# a MARC 1xx, emitted as bflc:PrimaryContribution so the book's cards credit it.
ZOTERO_PRIMARY = {"artist", "author", "bookAuthor", "creator"}


def fold(s):
    """Match key for a name: accents, case, punctuation and spacing dropped, so
    "Di Palma, Ray" = "DiPalma, Ray" and "Van Abbe-Museum" = "Van Abbemuseum"
    (the letters must still agree exactly)."""
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[\W_]+", "", s.casefold())


def split_dates(heading):
    """('Drucker, Johanna', '1952-') from 'Drucker, Johanna, 1952-'."""
    m = DATE_TAIL.search(heading)
    if not m:
        return heading, ""
    return heading[:m.start()].rstrip(" ,"), heading[m.start():].strip(" ,")


def slug(s):
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c)).lower()
    return re.sub(r"(^-)|(-$)", "", re.sub(r"[^a-z0-9]+", "-", s))


def read(path):
    if not os.path.exists(path):
        return []
    with open(path, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def write(path, fields, rows):
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, lineterminator="\n", extrasaction="ignore", restval="")
        w.writeheader()
        w.writerows(rows)


class UF:
    def __init__(self):
        self.p = {}

    def find(self, x):
        self.p.setdefault(x, x)
        while self.p[x] != x:
            self.p[x] = self.p[self.p[x]]
            x = self.p[x]
        return x

    def union(self, a, b):
        a, b = self.find(a), self.find(b)
        if a != b:
            self.p[max(a, b)] = min(a, b)


def main():
    occ = read(f"{D}/occurrences.csv")
    # The frozen id.loc.gov lookups (reconcile.py). A deprecated id is read as
    # the one LC says to use instead, so both name the same agent.
    lc_rec = {r["lcId"]: r for r in read(f"{D}/lc-viaf.csv")}
    for r in list(lc_rec.values()):
        if r["status"] == "deprecated" and r["replacedBy"] and r["replacedBy"] in lc_rec:
            lc_rec[r["lcId"]] = dict(lc_rec[r["replacedBy"]], lcId=r["replacedBy"])
    decisions = read(f"{D}/decisions.csv")
    review = []

    uf = UF()
    for i, o in enumerate(occ):
        o["i"] = i
        o["personal"] = o["tag"].endswith("00")
        name_part, dates = split_dates(o["heading"]) if o["personal"] else (o["heading"], "")
        o["nameKey"] = fold(name_part)
        year = YEAR.search(dates)
        o["headingKey"] = (f"{o['nameKey']}:{year.group(0)}" if year else "") if o["personal"] \
            else fold(o["heading"])
        o["lcId"] = ";".join(sorted({lc_rec[v]["lcId"] if v in lc_rec else v
                                     for v in o["lcId"].split(";") if v}))
        o["ids"] = [f"{f}:{v}" for f in ID_FIELDS for v in o[f].split(";") if v]
        for v in o["lcId"].split(";"):
            rec = lc_rec.get(v, {})
            o["ids"] += [f"{f}:{rec[f]}" for f in ("viaf", "isni") if rec.get(f)]
        o["ids"] = sorted(set(o["ids"]))
        uf.find(("o", i))

    # 1. Identifiers.
    for o in occ:
        for k in o["ids"]:
            uf.union(("o", o["i"]), ("id", k))

    def lc_ids(root):
        return {k for k in members_ids[root] if k.startswith("lcId:")}

    def recompute():
        m = collections.defaultdict(set)
        for o in occ:
            m[uf.find(("o", o["i"]))].update(o["ids"])
        return m

    members_ids = recompute()

    def try_merge(roots, why, key):
        roots = sorted(set(roots))
        lcs = set().union(*(lc_ids(r) for r in roots))
        if len(lcs) > 1:
            review.append({"issue": "conflicting-ids", "key": key,
                           "detail": f"{why} would merge {' + '.join(sorted(lcs))}"})
            # Still pool the group's id-less part into one local agent; rule 3
            # then sees it as one candidate set, and a decision can place it.
            roots = [r for r in roots if not lc_ids(r)]
            if not roots:
                return False
        for r in roots[1:]:
            uf.union(roots[0], r)
        merged = set().union(*(members_ids.pop(r, set()) for r in roots))
        members_ids[uf.find(roots[0])] = merged
        return True

    # Decisions.
    separate = {d["a"] for d in decisions if d["action"] == "separate"}

    # 2. Dated / corporate headings.
    by_heading = collections.defaultdict(list)
    for o in occ:
        if o["headingKey"] and o["headingKey"] not in separate:
            by_heading[o["headingKey"]].append(o)
    for hk, group in sorted(by_heading.items()):
        try_merge([uf.find(("o", o["i"])) for o in group], "same heading", f"heading:{hk}")

    # 3. Name-level joins, for clusters that rule 1-2 left without an LC, VIAF
    #    or ISNI anchor ("local" clusters, GND-only ones included). A dated local cluster joins the one
    #    identified cluster with its name whose birth years don't contradict
    #    it; then an undated local cluster joins the one other cluster carrying
    #    its name. Anything with several candidates goes to review.
    def snapshot():
        info = collections.defaultdict(lambda: {"names": set(), "years": set(), "ids": False, "dated": False})
        for o in occ:
            c = info[uf.find(("o", o["i"]))]
            c["names"].add(o["nameKey"])
            # An "anchor" is an LC/VIAF/ISNI id. A GND or WorldCat Entity id
            # alone can't contradict an LC one, so it doesn't stop a name join.
            c["ids"] |= any(o[f] for f in ("lcId", "viaf", "isni"))
            if o["personal"] and o["headingKey"]:
                c["dated"] = True
                c["years"].add(o["headingKey"].rsplit(":", 1)[1])
        by_name = collections.defaultdict(set)
        for r, c in info.items():
            for nk in c["names"]:
                by_name[nk].add(r)
        return info, by_name

    def compatible(a, b):
        return not a["years"] or not b["years"] or bool(a["years"] & b["years"])

    # Dated phase: a local dated agent joins the one anchored agent with its
    # name whose birth years don't contradict it.
    info, by_name = snapshot()
    for nk in sorted(by_name):
        if nk in separate:
            continue
        roots = by_name[nk]
        anchored = [r for r in roots if info[r]["ids"]]
        for r in sorted(roots):
            c = info[r]
            if c["ids"] or not c["dated"]:
                continue
            cands = {uf.find(a) for a in anchored if compatible(c, info[a])}
            if len(cands) == 1:
                uf.union(uf.find(r), next(iter(cands)))
            elif len(cands) > 1:
                review.append({"issue": "ambiguous-dated-name", "key": f"name:{nk}",
                               "detail": f"{len(cands)} candidate agents"})

    # Undated phase: every local undated agent of one name (id-less or GND-only)
    # is pooled -- what the old name slug did -- and the pool joins the one
    # anchored-or-dated agent carrying that name, if there is exactly one.
    info, by_name = snapshot()
    for nk in sorted(by_name):
        roots = by_name[nk]
        pool = sorted(r for r in roots if not info[r]["ids"] and not info[r]["dated"])
        if not pool:
            continue
        for r in pool[1:]:
            uf.union(uf.find(pool[0]), uf.find(r))
        if nk in separate:
            continue
        cands = {uf.find(r) for r in roots if r not in pool}
        if len(cands) == 1:
            uf.union(uf.find(pool[0]), next(iter(cands)))
        elif len(cands) > 1:
            review.append({"issue": "ambiguous-undated-name", "key": f"name:{nk}",
                           "detail": f"{len(cands)} candidate agents"})

    # 4. Hand merges.
    key_root = {}
    for o in occ:
        r = ("o", o["i"])
        for k in o["ids"]:
            key_root[k.replace("lcId:", "lc:")] = r
        key_root[f"name:{o['nameKey']}"] = r
        if o["headingKey"]:
            key_root[f"heading:{o['headingKey']}"] = r
    for d in decisions:
        if d["action"] == "merge":
            if d["a"] in key_root and d["b"] in key_root:
                uf.union(uf.find(key_root[d["a"]]), uf.find(key_root[d["b"]]))
            else:
                review.append({"issue": "stale-decision", "key": d["a"], "detail": f"merge with {d['b']}: key not found"})

    # Build agents.
    clusters = collections.defaultdict(list)
    for o in occ:
        clusters[uf.find(("o", o["i"]))].append(o)
    label_override = {}
    for d in decisions:
        if d["action"] == "label" and d["a"] in key_root:
            label_override[uf.find(key_root[d["a"]])] = d["b"]

    agents = {}
    used_keys = collections.Counter()
    for root, os_ in sorted(clusters.items(), key=lambda kv: min(o["i"] for o in kv[1])):
        def ids(field):
            return collections.Counter(k.split(":", 1)[1] for o in os_ for k in o["ids"]
                                       if k.startswith(field + ":"))
        lc, viaf, isni = ids("lcId"), ids("viaf"), ids("isni")
        pick = lambda c: sorted(c.items(), key=lambda kv: (-kv[1], kv[0]))[0][0] if c else ""
        lc_id = pick(lc)
        # VIAF renumbers clusters as it merges them, so a MARC $1 can carry an
        # older VIAF id than the one LC links today: prefer LC's.
        rec = lc_rec.get(lc_id, {})
        viaf_id = rec.get("viaf") or pick(viaf)
        isni_id = rec.get("isni") or pick(isni)
        if len(viaf) > 1 and not rec.get("viaf"):
            review.append({"issue": "multiple-viaf", "key": f"viaf:{viaf_id}",
                           "detail": "; ".join(sorted(viaf))})
        # Preferred label: the commonest heading among controlled occurrences,
        # else among dated ones, else overall; longer then alphabetical on ties.
        pool = [o for o in os_ if o["lcId"]] or [o for o in os_ if o["headingKey"] and o["personal"]] or os_
        heads = collections.Counter(o["heading"] for o in pool)
        label = (label_override.get(root)
                 or lc_rec.get(lc_id, {}).get("label")
                 or sorted(heads.items(), key=lambda kv: (-kv[1], -len(kv[0]), kv[0]))[0][0])
        base = lc_id or slug(label) or "unnamed"
        used_keys[base] += 1
        key = base if used_keys[base] == 1 else f"{base}-{used_keys[base]}"
        if viaf_id:
            uri = f"http://viaf.org/viaf/{viaf_id}"
        elif isni_id:
            uri = f"http://isni.org/isni/{isni_id}"
        else:
            uri = f"{AB}creator/{key}"
        agents[root] = {"agentKey": key, "agentUri": uri, "label": label,
                        "lcId": lc_id, "viaf": viaf_id, "isni": isni_id,
                        "personal": any(o["personal"] for o in os_),
                        "nameKeys": {o["nameKey"] for o in os_},
                        "headings": " | ".join(sorted(collections.Counter(o["heading"] for o in os_))),
                        "occurrences": len(os_),
                        "works": len({(o["source"], o["canonicalKey"]) for o in os_})}

    rows = {}
    for o in occ:
        a = agents[uf.find(("o", o["i"]))]
        k = (o["source"], o["canonicalKey"], o["tag"], o["name"], a["agentKey"])
        rows[k] = {"source": o["source"], "canonicalKey": o["canonicalKey"], "tag": o["tag"],
                   "name": o["name"], "agentKey": a["agentKey"], "agentUri": a["agentUri"],
                   "label": a["label"]}

    # 6. Zotero fallback for books with no MARC creator field.
    marc_books = {o["canonicalKey"] for o in occ if o["source"] == "book"}
    by_name = collections.defaultdict(set)
    for root, a in agents.items():
        for nk in a["nameKeys"]:
            by_name[nk].add(root)
    zstats = collections.Counter()
    for z in read(f"{D}/zotero-creators.csv"):
        if z["canonicalKey"] in marc_books:
            continue
        if z["fieldMode"] == "1" or not z["firstName"]:
            nk = fold(z["lastName"])
        else:
            first, _ = split_dates(z["firstName"])
            nk = fold(f"{z['lastName']} {first}")
        cands = by_name.get(nk, set())
        if len(cands) != 1:
            zstats["unmatched" if not cands else "ambiguous"] += 1
            if cands:
                review.append({"issue": "ambiguous-zotero", "key": f"name:{nk}",
                               "detail": f"{z['canonicalKey']}: {len(cands)} candidate agents"})
            continue
        zstats["matched"] += 1
        a = agents[next(iter(cands))]
        code, term = ZOTERO_ROLES.get(z["creatorType"], ("", ""))
        rows[("book", z["canonicalKey"], "zotero", nk, a["agentKey"])] = {
            "source": "book", "canonicalKey": z["canonicalKey"], "tag": "zotero",
            "name": nk, "agentKey": a["agentKey"], "agentUri": a["agentUri"], "label": a["label"],
            "primary": "y" if z["creatorType"] in ZOTERO_PRIMARY else "",
            "roleUri": f"http://id.loc.gov/vocabulary/relators/{code}" if code else "",
            "roleTerm": term}

    write(f"{D}/agents.csv", ["source", "canonicalKey", "tag", "name", "agentKey", "agentUri", "label",
                              "primary", "roleUri", "roleTerm"],
          sorted(rows.values(), key=lambda r: (r["source"], r["canonicalKey"], r["tag"], r["name"], r["agentKey"])))
    write(f"{D}/authority.csv", ["agentKey", "agentUri", "label", "lcId", "viaf", "isni", "works", "occurrences", "headings"],
          sorted(agents.values(), key=lambda a: a["agentKey"]))
    seen = set()
    review = [r for r in review if not (tuple(r.values()) in seen or seen.add(tuple(r.values())))]
    write(f"{D}/review.csv", ["issue", "key", "detail"], sorted(review, key=lambda r: (r["issue"], r["key"])))
    print(f"{len(occ)} occurrences -> {len(agents)} agents; "
          f"{sum(1 for a in agents.values() if a['viaf'])} with VIAF, "
          f"{sum(1 for a in agents.values() if a['lcId'] and not a['viaf'])} LC-only; "
          f"Zotero fallback {dict(zstats)}; {len(review)} review rows", file=sys.stderr)


if __name__ == "__main__":
    main()
