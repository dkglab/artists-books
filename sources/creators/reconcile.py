#!/usr/bin/env python3
"""Freeze LC name-authority lookups for every LC id in occurrences.csv (#170, step 3).

For each LC id, fetches https://id.loc.gov/authorities/names/<id>.json once and
records, in sources/creators/lc-viaf.csv:

  lcId        the id looked up
  status      ok | deprecated | notfound | error
  label       madsrdf:authoritativeLabel -- the authorized heading, which
              build.py prefers as an agent's single rdfs:label
  viaf        numeric VIAF id the record links (identifiesRWO / external
              authorities), if any -- joins an LC-only agent to its VIAF one
  isni        ISNI the record links, if any
  replacedBy  for a cancelled/deprecated id, the id LC says to use instead

Like the MARC harvest this is a one-time external job whose output is frozen
and committed: build.py reads only the CSV. Resumable -- ids already in the CSV
(other than `error` rows) are skipped -- and chunkable with --limit. VIAF's own
API refuses scripted clients (403), so id.loc.gov's links are the route.

    python3 sources/creators/reconcile.py [--limit N] [--workers 2]
"""
import argparse
import concurrent.futures
import csv
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

D = "sources/creators"
OUT = f"{D}/lc-viaf.csv"
FIELDS = ["lcId", "status", "label", "viaf", "isni", "replacedBy"]
UA = "artists-books-reconcile/1.0 (research catalogue; id.loc.gov lookups)"


def lookup(lc):
    url = f"https://id.loc.gov/authorities/names/{lc}.json"
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=30) as r:
                data = json.load(r)
            break
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return {"lcId": lc, "status": "notfound"}
            if attempt == 2:
                return {"lcId": lc, "status": "error"}
        except Exception:
            if attempt == 2:
                return {"lcId": lc, "status": "error"}
        time.sleep(2 * (attempt + 1))
    me = f"http://id.loc.gov/authorities/names/{lc}"
    node = next((n for n in data if n.get("@id") == me), {})
    types = node.get("@type", [])

    def vals(key):
        return [v.get("@value") or v.get("@id") for k, vs in node.items() if k.endswith(key) for v in vs]

    label = (vals("#authoritativeLabel") or vals("#variantLabel") or vals("rdf-schema#label") or [""])[0]
    blob = json.dumps(node)
    viaf = re.findall(r"viaf\.org/viaf/(\d+)", blob)
    isni = re.findall(r"isni\.org/isni/([0-9X]{16})", blob)
    replaced = [re.sub(r"^.*/", "", u) for u in vals("#useInstead")]
    # A deprecated duplicate often names its successor only in prose, e.g.
    # "[Duplicate; submitted for deletion in favour of no2019156740]".
    for note in vals("#editorialNote") + vals("#deletionNote"):
        replaced += [m for m in re.findall(r"\b(n[a-z]{0,2}\d{6,})\b", note or "") if m != lc]
    replaced = list(dict.fromkeys(replaced))
    status = "deprecated" if any("DeprecatedAuthority" in t for t in types) else "ok"
    return {"lcId": lc, "status": status, "label": label,
            "viaf": viaf[0] if viaf else "", "isni": isni[0] if isni else "",
            "replacedBy": ";".join(replaced)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--workers", type=int, default=2)
    args = ap.parse_args()

    ids = set()
    with open(f"{D}/occurrences.csv", newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            ids.update(v for v in r["lcId"].split(";") if v)
    done = {}
    if os.path.exists(OUT):
        with open(OUT, newline="", encoding="utf-8") as fh:
            done = {r["lcId"]: r for r in csv.DictReader(fh) if r["status"] != "error"}
    todo = sorted(ids - set(done))
    if args.limit:
        todo = todo[:args.limit]
    print(f"{len(done)} done, {len(todo)} to look up", file=sys.stderr)

    def save():
        with open(OUT + ".tmp", "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=FIELDS, lineterminator="\n", restval="")
            w.writeheader()
            w.writerows(sorted(done.values(), key=lambda r: r["lcId"]))
        os.replace(OUT + ".tmp", OUT)

    with concurrent.futures.ThreadPoolExecutor(args.workers) as ex:
        for n, row in enumerate(ex.map(lookup, todo), 1):
            done[row["lcId"]] = row
            if n % 50 == 0:
                save()
                print(f"  {n}/{len(todo)}", file=sys.stderr)
    save()
    print(f"{len(done)} rows -> {OUT}", file=sys.stderr)


if __name__ == "__main__":
    main()
