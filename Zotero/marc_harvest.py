#!/usr/bin/env python3
"""Harvest full MARC records for the items in a Zotero CSV from Z39.50 servers.

Servers are tried in order (see SERVERS); the first that yields a verified
record for an item wins, so a book UNC does not hold can still be found at a
fallback catalogue.

Strategy (see Zotero/README.md):
  * Servers     : UNC Innopac first (tcp:afton.lib.unc.edu/INNOPAC), then public
                  fallbacks for what UNC lacks -- the Library of Congress, the
                  K10plus (German) academic union catalogue, LIBRIS (Sweden's
                  national catalogue), Penn State, and the Getty Research
                  Institute. Most are Z39.50; Getty is queried over SRU/CQL (see
                  `protocol`). See SERVERS for connection strings; all yield
                  MARC21 in UTF-8.
  * Search keys : per item, tried in order, first hit wins. Identifier keys are
                  trusted; title keys are verified against the CSV before use.
                    - bib          UNC only,  @attr 1=12 b<digits>   (unique)
                    - isbn         UNC + LC,   @attr 1=7 <isbn>
                    - title-author LC only,    @and 1=4 "<title>" 1=1003 "<author>"
                    - title        LC only,    @attr 1=4 "<title>"
                  (OCLC is not used -- neither target indexes it.)
  * Verify      : a title / title-author hit is kept only when the retrieved
                  record's 245 (and 100/260) agree with the CSV title plus the
                  author surname or the year; otherwise it is rejected (logged to
                  review.tsv). This guards the synthetic-999 join against a
                  coincidental title match being stamped onto the wrong itemKey.
  * Join key    : the Zotero itemKey. Each retrieved record is stamped with a
                  synthetic 999 $a <itemKey> $b <value> $c <keytype> $d <server>
                  field -- no content-based join.
  * Politeness  : one serial connection per server per batch, with a `sleep`
                  between queries and a pause between batches (more conservative
                  for LC, a shared national service).
  * Encoding    : both targets return UTF-8 bytes. UNC mislabels leader/09 as
                  MARC-8, so we rewrite leader/09 to 'a' (LC is already honest);
                  we do NOT transcode (that would double-encode).
  * Output      : a single MARCXML <collection>. Per-CSV harvest state lives under
                  marc/<csv-stem>/ (combined.marc is append-only and resumable).

Run:
    python3 marc_harvest.py --csv reference-resources.csv --out reference-resources-marc.xml
    python3 marc_harvest.py --csv reference-resources.csv --out reference-resources-marc.xml --limit 15
    python3 marc_harvest.py --csv reference-resources.csv --out reference-resources-marc.xml --combine
"""
import argparse
import csv
import difflib
import os
import re
import subprocess
import sys
import time
import unicodedata
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

HERE        = os.path.dirname(os.path.abspath(__file__))
MARC_DIR    = os.path.join(HERE, "marc")  # gitignored harvest state, per-CSV subdir

# YAZ is built under tools/yaz-client/ (see tools/yaz-client/Makefile), not
# installed system-wide. Resolve the binaries from there so the harvest uses our
# self-contained build rather than whatever happens to be on $PATH.
YAZ_BIN     = os.path.normpath(os.path.join(HERE, os.pardir, "tools", "yaz-client", "bin"))
YAZ_CLIENT  = os.path.join(YAZ_BIN, "yaz-client")
YAZ_MARCDUMP = os.path.join(YAZ_BIN, "yaz-marcdump")

MARC_NS     = "http://www.loc.gov/MARC21/slim"

# Z39.50 servers, tried in order. keytypes lists the search keys to try at that
# server, in precedence order (first hit wins). The throttle overrides keep LC --
# a shared national service -- gentler than UNC. Both targets serve UTF-8.
# show_n is how many candidate records to retrieve per query: 1 is enough for
# the unique identifier keys at UNC; title searches pull several to verify
# against, since the right record may not be the first hit. `protocol` defaults
# to "z3950" (Bib-1 prefix queries via yaz-client); "sru" servers are queried
# over HTTP/CQL and return MARCXML, which is converted to binary on ingest so
# the rest of the pipeline is identical.
SERVERS = [
    {"name": "unc", "conn": "tcp:afton.lib.unc.edu:210/INNOPAC",
     "keytypes": ("bib", "isbn"),
     "batch": 50, "qsleep": 0.4, "bsleep": 2, "show_n": 1},
    {"name": "lc",  "conn": "tcp:lx2.loc.gov:210/LCDB",
     "keytypes": ("isbn", "title-author", "title"),
     "batch": 10, "qsleep": 1.0, "bsleep": 4, "show_n": 3},
    # K10plus: the GBV/SWB union catalogue (~200 German/Austrian libraries),
    # strong on art and humanities and international holdings -- a good reach for
    # the European livre d'artiste / Kunstlerbuch reference works. Honest UTF-8.
    {"name": "k10plus", "conn": "tcp:sru.k10plus.de:210/opac-de-627",
     "keytypes": ("isbn", "title-author", "title"),
     "batch": 10, "qsleep": 1.0, "bsleep": 4, "show_n": 3},
    # Penn State (Sirsi Unicorn), a large US research library. Honest UTF-8.
    {"name": "psu", "conn": "tcp:zcat.libraries.psu.edu:2200/Unicorn",
     "keytypes": ("isbn", "title-author", "title"),
     "batch": 10, "qsleep": 1.0, "bsleep": 4, "show_n": 3},
    # NOTE: SUDOC (carmin.sudoc.abes.fr/ABES-Z39-PUBLIC) is reachable and would
    # reach the French references, but its public endpoint emits records in a
    # non-standard encoding that mislabels itself UTF-8 and that yaz cannot
    # cleanly transcode (accented text is mangled or dropped), so it is omitted.
    # LIBRIS, Sweden's national union catalogue. MARC21 in UTF-8.
    {"name": "libris", "conn": "tcp:z3950.libris.kb.se:210/libris",
     "keytypes": ("isbn", "title-author", "title"),
     "batch": 10, "qsleep": 1.0, "bsleep": 4, "show_n": 3},
    # Getty Research Institute (Ex Libris Alma), a premier art library, queried
    # over SRU/CQL. Holds much of the artist's-book exhibition/dealer ephemera
    # the other catalogues lack. Returns MARCXML in UTF-8.
    {"name": "getty", "conn": "https://na01.alma.exlibrisgroup.com/view/sru/01GRI_INST",
     "protocol": "sru", "keytypes": ("isbn", "title-author", "title"),
     "batch": 10, "qsleep": 0.5, "bsleep": 3, "show_n": 3},
]

# Identifier keys are trusted on a hit; title keys must be verified. Accept a
# title hit when its normalized 245 is very close to the CSV title, or
# reasonably close AND corroborated by the author surname or publication year.
IDENTIFIER_KEYS = ("bib", "isbn")
TITLE_KEYS      = ("title-author", "title")
TITLE_STRONG    = 0.85
TITLE_WEAK      = 0.60


def make_cfg(csv_path, out_xml):
    """Resolve all paths for one CSV; harvest state lives in marc/<csv-stem>/."""
    csv_path = os.path.abspath(csv_path)
    base = os.path.splitext(os.path.basename(csv_path))[0]
    state = os.path.join(MARC_DIR, base)
    return {
        "csv": csv_path,
        "out": os.path.abspath(out_xml),
        "state": state,
        "combined": os.path.join(state, "combined.marc"),  # binary MARC, append-only
        "manifest": os.path.join(state, "manifest.tsv"),   # itemKey server keytype value status
        "missing": os.path.join(state, "missing.tsv"),     # itemKey server value reason
        "review": os.path.join(state, "review.tsv"),       # itemKey server keytype value reason
    }


def clean_isbns(raw):
    """Split an ISBN field into clean 10/13-digit tokens (hyphens/price noise removed)."""
    out = []
    for tok in (raw or "").split():
        t = re.sub(r"[^0-9Xx]", "", tok)
        if len(t) in (10, 13):
            out.append(t.upper())
    return out


def norm(s):
    """Lowercase, NFC, drop punctuation, collapse whitespace -- for matching/queries."""
    s = unicodedata.normalize("NFC", s or "")
    s = re.sub(r"[^\w\s]", " ", s.lower())
    return re.sub(r"\s+", " ", s).strip()


def main_title(title):
    """Main title (text before a ':' subtitle), normalized for a phrase query."""
    return norm((title or "").split(":")[0])


def author_surname(creators):
    """Surname of the primary creator from the CSV 'creators' column (last token),
    for an author search key. Empty when there is no creator."""
    if not creators:
        return ""
    first = creators.split(";")[0].strip()
    toks = first.split()
    return toks[-1] if toks else ""


def year_of(date):
    m = re.search(r"\d{4}", date or "")
    return m.group(0) if m else None


def item_keys(row):
    """Available search keys for one CSV row: keytype -> [(value, querymap), ...].

    value is what gets stamped into 999 $b; querymap maps a server protocol
    ("z3950" Bib-1 prefix, "sru" CQL) to the query expression for that key. A
    keytype with no entry for a server's protocol is simply skipped there (e.g.
    bib is UNC-only). For SRU the title query is title-only and leans on
    verify_title; CQL phrase-on-author is unreliable across Alma tenants.
    """
    keys = {}
    m = re.search(r"/UNCb(\d+)", row.get("url") or "")
    if m:
        keys["bib"] = [("b" + m.group(1), {"z3950": f"@attr 1=12 b{m.group(1)}"})]
    for i in clean_isbns(row.get("ISBN", "")):
        keys.setdefault("isbn", []).append(
            (i, {"z3950": f"@attr 1=7 {i}", "sru": f"alma.isbn={i}"}))
    # One title probe per item: prefer title+author (far more precise on Z39.50 --
    # in testing it returns a single exact hit where title alone returns dozens),
    # falling back to title alone only when the item has no author.
    title = main_title(row.get("title") or "")
    if title:
        surname = norm(author_surname(row.get("creators") or ""))
        if surname:
            keys["title-author"] = [(
                f"{surname} / {title}",
                {"z3950": f'@and @attr 1=4 @attr 4=1 "{title}" @attr 1=1003 "{surname}"',
                 "sru": f'alma.title="{title}"'})]
        else:
            keys["title"] = [(title,
                {"z3950": f'@attr 1=4 @attr 4=1 "{title}"',
                 "sru": f'alma.title="{title}"'})]
    return keys


def read_rows(cfg):
    with open(cfg["csv"], newline="") as fh:
        return list(csv.DictReader(fh))


def server_targets(rows, server):
    """[(itemKey, [(keytype, value, query), ...])] for rows with >=1 key this
    server can use, in the server's keytype precedence order. Queries are
    selected for the server's protocol; keys with no query for it are skipped."""
    proto = server.get("protocol", "z3950")
    targets = []
    for row in rows:
        keys = item_keys(row)
        probes = []
        for kt in server["keytypes"]:
            for value, querymap in keys.get(kt, []):
                query = querymap.get(proto)
                if query:
                    probes.append((kt, value, query))
        if probes:
            targets.append((row["itemKey"], probes))
    return targets


def load_state(cfg):
    """(ok_keys, attempted) from the manifest. ok_keys: itemKeys with a kept
    record (resolved, skip on every server). attempted: (itemKey, server) pairs
    already tried at that server (any status), so a re-run does not re-query
    them -- a UNC miss still leaves (key, "lc") open for the fallback."""
    ok, attempted = set(), set()
    if os.path.exists(cfg["manifest"]):
        with open(cfg["manifest"]) as fh:
            for line in fh:
                c = line.rstrip("\n").split("\t")
                if len(c) >= 5:
                    key, server, _kt, _v, status = c[:5]
                    attempted.add((key, server))
                    if status == "ok":
                        ok.add(key)
    return ok, attempted


def split_records(blob):
    """Split a binary MARC blob into individual records (each ends with 0x1D)."""
    recs, start = [], 0
    for i, byte in enumerate(blob):
        if byte == 0x1D:
            recs.append(blob[start:i + 1])
            start = i + 1
    return recs


def count_records(marc_bytes):
    """Count records in a binary MARC blob (records end with the 0x1D terminator)."""
    return marc_bytes.count(b"\x1d")


def run_batch(cfg, conn, batch, qsleep, show_n):
    """Query a batch over one connection to `conn`. batch is
    [(itemKey, [(keytype, value, query), ...]), ...]. Each probe retrieves up to
    show_n candidate records (`show 1+show_n`). Returns (results, stdout) where
    results is one (itemKey, probes) per item, in order, and probes is
        [(keytype, value, count, [record_bytes, ...]), ...]
    one per query in precedence order (count is the server's hit count; the list
    holds min(show_n, count) records). The caller selects/verifies.

    Returns (None, stdout) if the server output can't be aligned to the probes,
    so the caller can retry per item.
    """
    tmp = os.path.join(cfg["state"], "_batch.marc")
    if os.path.exists(tmp):
        os.remove(tmp)

    probes = []  # (keytype, value, query); probes for an item are contiguous
    cmds = ["format usmarc", "querytype prefix"]
    for _key, plist in batch:
        for keytype, value, query in plist:
            probes.append((keytype, value, query))
            cmds.append(f"find {query}")
            # Fetch up to show_n candidates one position at a time. `show 1+N`
            # asks for exactly N and this target rejects it as out-of-range when
            # fewer exist; `show k` past the end is just a harmless diagnostic, so
            # a probe yields min(show_n, count) records, in order.
            for k in range(1, show_n + 1):
                cmds.append(f"show {k}")
            cmds.append(f"sleep {qsleep}")
    cmds.append("quit")
    proc = subprocess.run(
        [YAZ_CLIENT, "-m", tmp, conn],
        input=("\n".join(cmds) + "\n").encode(),
        capture_output=True, timeout=60 + len(probes) * 10,
    )
    # yaz-client echoes retrieved records to stdout too, and some targets (e.g.
    # SUDOC) emit non-UTF-8 bytes there, so decode leniently -- we only read the
    # ASCII "Number of hits" lines; the actual records come from the -m file.
    stdout = proc.stdout.decode("utf-8", "replace")

    counts = [int(n) for n in re.findall(r"Number of hits:\s*(\d+)", stdout)]
    if len(counts) != len(probes):
        return None, stdout  # parsing slipped -- let caller retry per item

    records = split_records(open(tmp, "rb").read() if os.path.exists(tmp) else b"")
    # Each `show 1+show_n` returns min(show_n, count) records, in probe order.
    if len(records) != sum(min(show_n, c) for c in counts):
        return None, stdout  # show/hit misalignment -- retry per item

    rec_iter = iter(records)
    probe_recs = [[next(rec_iter) for _ in range(min(show_n, c))] for c in counts]

    results, i = [], 0
    for key, plist in batch:
        probelist = []
        for _ in range(len(plist)):
            keytype, value, _q = probes[i]
            probelist.append((keytype, value, counts[i], probe_recs[i]))
            i += 1
        results.append((key, probelist))
    return results, stdout


def select_record(cfg, key, probelist, rowmap):
    """Choose a record for one item from its probe results, in precedence order.
    Identifier-key hits are trusted; title-key hits are verified against the CSV.
    Returns (status, keytype, value, record_or_None, ncands, review_or_None)."""
    for keytype, value, count, recs in probelist:
        if count == 0:
            continue
        if keytype in IDENTIFIER_KEYS:
            review = f"{count} holdings; show picked first" if count > 1 else None
            return "ok", keytype, value, recs[0], count, review
        for rec in recs:  # title key: accept the first candidate that verifies
            if verify_title(cfg, rec, rowmap[key]):
                review = f"{count} candidates; verified one" if count > 1 else None
                return "ok", keytype, value, rec, count, review
    failed = any(kt in TITLE_KEYS and c > 0 for kt, _v, c, _r in probelist)
    return ("miss", "", "", None, 0,
            "title hits failed verification" if failed else None)


SLIM = "{http://www.loc.gov/MARC21/slim}"


def sru_search(base, cql, maxrec):
    """SRU searchRetrieve -> (numberOfRecords, [slim record Elements])."""
    params = urllib.parse.urlencode({
        "version": "1.2", "operation": "searchRetrieve",
        "recordSchema": "marcxml", "maximumRecords": str(maxrec), "query": cql,
    })
    try:
        raw = urllib.request.urlopen(f"{base}?{params}", timeout=30).read()
        root = ET.fromstring(raw)
    except Exception:
        return 0, []
    n = 0
    for el in root.iter():  # SRW namespace varies across tenants; match by tag
        if el.tag.endswith("numberOfRecords") and (el.text or "").strip().isdigit():
            n = int(el.text)
            break
    return n, root.findall(f".//{SLIM}record")


def marc_element_to_binary(rec):
    """Encode one MARCXML <record> Element as a binary MARC (ISO 2709) record.

    Done in pure Python because the bundled yaz-marcdump is built without
    libxml2 and so cannot read MARCXML. Producing binary lets SRU hits flow
    through the same combined.marc / verify / combine path as Z39.50 hits.
    Lengths and offsets are byte counts (UTF-8); leader/09 is set to 'a'."""
    FT, SUB, RT = b"\x1e", b"\x1f", b"\x1d"
    fields = []  # (tag, data-bytes incl. trailing field terminator)
    for cf in rec.findall(f"{SLIM}controlfield"):
        fields.append((cf.get("tag") or "001", (cf.text or "").encode("utf-8") + FT))
    for df in rec.findall(f"{SLIM}datafield"):
        ind = ((df.get("ind1") or " ")[:1] + (df.get("ind2") or " ")[:1])
        data = ind.encode("utf-8")
        for sf in df.findall(f"{SLIM}subfield"):
            data += SUB + (sf.get("code") or " ")[:1].encode("utf-8") + (sf.text or "").encode("utf-8")
        fields.append((df.get("tag") or "999", data + FT))

    directory, pos = b"", 0
    for tag, data in fields:
        directory += f"{tag:0>3.3}{len(data):04d}{pos:05d}".encode("ascii")
        pos += len(data)
    directory += FT
    fielddata = b"".join(d for _t, d in fields)
    base = 24 + len(directory)
    total = base + len(fielddata) + 1

    lead = list(((rec.findtext(f"{SLIM}leader") or "") + " " * 24)[:24])
    lead[0:5] = f"{total:05d}"
    lead[9] = "a"            # UTF-8
    lead[10], lead[11] = "2", "2"   # indicator count, subfield code length
    lead[12:17] = f"{base:05d}"
    lead[20:24] = "4500"
    return "".join(lead).encode("utf-8") + directory + fielddata + RT


def marcxml_to_binary(elements):
    """Convert SRU MARCXML <record> Elements to binary MARC records."""
    return [marc_element_to_binary(el) for el in elements]


def run_sru(cfg, server, batch, show_n):
    """SRU equivalent of run_batch: one HTTP request per probe (CQL), returning
    the same (itemKey, [(keytype, value, count, [record_bytes...]), ...]) shape."""
    results = []
    for key, plist in batch:
        probelist = []
        for keytype, value, cql in plist:
            n, els = sru_search(server["conn"], cql, show_n)
            probelist.append((keytype, value, n, marcxml_to_binary(els[:show_n])))
            time.sleep(server["qsleep"])
        results.append((key, probelist))
    return results


def _subfields(rec, tag, codes):
    out = []
    for df in rec.findall(f"{{{MARC_NS}}}datafield"):
        if df.get("tag") == tag:
            for sf in df.findall(f"{{{MARC_NS}}}subfield"):
                if sf.get("code") in codes:
                    out.append(sf.text or "")
    return out


def decode_record(cfg, record_bytes):
    """Parse one binary MARC record -> (normalized title, normalized authors, year).

    yaz-marcdump reads a file (not stdin), so the record is written to a temp
    file in the harvest state dir first.
    """
    tmp = os.path.join(cfg["state"], "_verify.marc")
    with open(tmp, "wb") as fh:
        fh.write(record_bytes)
    xml = subprocess.run(
        [YAZ_MARCDUMP, "-l", "9=97", "-i", "marc", "-o", "marcxml", tmp],
        capture_output=True,
    ).stdout
    try:
        root = ET.fromstring(xml)
    except ET.ParseError:
        return "", "", None
    rec = root if root.tag.endswith("record") else root.find(f"{{{MARC_NS}}}record")
    if rec is None:
        return "", "", None
    title = norm(" ".join(_subfields(rec, "245", ("a", "b"))))
    authors = norm(" ".join(
        _subfields(rec, "100", ("a",)) + _subfields(rec, "110", ("a",)) +
        _subfields(rec, "700", ("a",)) + _subfields(rec, "710", ("a",))))
    year = None
    for tag in ("260", "264"):
        for c in _subfields(rec, tag, ("c",)):
            m = re.search(r"\d{4}", c)
            if m:
                year = m.group(0)
                break
        if year:
            break
    return title, authors, year


def verify_title(cfg, record_bytes, row):
    """True if a title-keyed record plausibly describes the CSV item.

    A strong title match is taken on its own; in the weak band the publication
    year must corroborate. (Author surname is deliberately not used as a
    corroborator: corporate "surnames" like "Press" match unrelated records --
    e.g. "The artist publisher" wrongly matching "The artist in Edo".)"""
    rtitle, _rauthors, ryear = decode_record(cfg, record_bytes)
    ctitle = norm(row.get("title") or "")
    if not rtitle or not ctitle:
        return False
    ratio = difflib.SequenceMatcher(None, rtitle, ctitle).ratio()
    if ratio >= TITLE_STRONG:
        return True
    if ratio < TITLE_WEAK:
        return False
    cyear = year_of(row.get("date") or "")
    return bool(cyear and ryear == cyear)


def harvest(cfg, limit=None):
    os.makedirs(cfg["state"], exist_ok=True)
    rows = read_rows(cfg)
    rowmap = {r["itemKey"]: r for r in rows}
    ok_keys, attempted = load_state(cfg)

    for server in SERVERS:
        name = server["name"]
        targets = server_targets(rows, server)
        pending = [(k, p) for (k, p) in targets
                   if k not in ok_keys and (k, name) not in attempted]
        if limit:
            pending = pending[:limit]
        print(f"[{name}] candidates={len(targets)} already_ok={len(ok_keys)} "
              f"this_run={len(pending)}")

        proto = server.get("protocol", "z3950")
        bsize, show_n = server["batch"], server["show_n"]
        for start in range(0, len(pending), bsize):
            batch = pending[start:start + bsize]

            if proto == "sru":
                results = run_sru(cfg, server, batch, show_n)
            else:
                results, _log = run_batch(cfg, server["conn"], batch, server["qsleep"], show_n)
                if results is None:
                    # An unalignable batch usually means the server throttled or
                    # dropped a busy connection. Back off, then retry the whole
                    # batch once; if still bad, fall back to one item per
                    # connection with a pause between, deferring what still fails.
                    print(f"  !! [{name}] batch at {start}: output unalignable; "
                          f"backing off {server['bsleep'] * 5}s and retrying",
                          file=sys.stderr)
                    time.sleep(server["bsleep"] * 5)
                    results, _ = run_batch(cfg, server["conn"], batch, server["qsleep"], show_n)
                if results is None:
                    results = []
                    for one in batch:
                        r, _ = run_batch(cfg, server["conn"], [one], server["qsleep"], show_n)
                        if r is None:
                            print(f"  !! {one[0]}: still unalignable, deferring to "
                                  f"next run", file=sys.stderr)  # no row -> retried
                        else:
                            results.extend(r)
                        time.sleep(server["qsleep"])

            # Select/verify a record per item (identifier hits trusted, title
            # hits verified against the CSV).
            accepted, rows_out, reviews = [], [], []
            for key, probelist in results:
                status, kt, value, rec, _n, review = select_record(
                    cfg, key, probelist, rowmap)
                rows_out.append((key, kt, value, status))
                if status == "ok":
                    accepted.append((key, rec))
                if review:
                    rows_out_kt = kt if status == "ok" else ""
                    reviews.append((key, rows_out_kt, value if status == "ok" else "",
                                    review))

            data = b"".join(rec for _k, rec in accepted)
            if count_records(data) != len(accepted):
                print(f"  !! [{name}] batch at {start}: {count_records(data)} "
                      f"records but {len(accepted)} accepted -- ABORT to avoid "
                      f"misaligned itemKeys", file=sys.stderr)
                sys.exit(2)

            with open(cfg["combined"], "ab") as fh:
                fh.write(data)
            with open(cfg["manifest"], "a") as mf, \
                    open(cfg["missing"], "a") as miss, \
                    open(cfg["review"], "a") as rev:
                for key, kt, value, status in rows_out:
                    mf.write(f"{key}\t{name}\t{kt}\t{value}\t{status}\n")
                    if status != "ok":
                        miss.write(f"{key}\t{name}\t{value}\tnot found / not verified\n")
                for key, kt, value, reason in reviews:
                    rev.write(f"{key}\t{name}\t{kt}\t{value}\t{reason}\n")

            for key, _rec in accepted:
                ok_keys.add(key)  # later servers skip items resolved here

            print(f"  [{name}] batch {start // bsize}: {len(batch)} queried, "
                  f"{len(accepted)} kept, {len(batch) - len(accepted)} missing")
            if start + bsize < len(pending):
                time.sleep(server["bsleep"])

    combine(cfg)


def combine(cfg):
    """Convert combined.marc -> single MARCXML <collection>, stamping itemKeys."""
    if not os.path.exists(cfg["combined"]):
        print("no combined.marc yet -- nothing to combine", file=sys.stderr)
        return
    raw = subprocess.run(
        # Both servers send UTF-8 bytes; just mark leader/09 'a' (97). No transcode.
        [YAZ_MARCDUMP, "-l", "9=97", "-i", "marc", "-o", "marcxml", cfg["combined"]],
        capture_output=True, text=True,
    ).stdout

    ET.register_namespace("", MARC_NS)
    root = ET.fromstring(raw)
    records = root.findall(f"{{{MARC_NS}}}record")

    # Manifest ok rows, in retrieval order, as (itemKey, server, keytype, value).
    # Current format is 5 cols (itemKey, server, keytype, value, status); tolerate
    # the older 4-col (itemKey, keytype, value, status) and 3-col bib-only
    # (itemKey, value, status) formats, attributing both to the UNC server.
    ok_rows = []
    for line in open(cfg["manifest"]):
        c = line.rstrip("\n").split("\t")
        if c[-1] != "ok":
            continue
        if len(c) >= 5:
            ok_rows.append((c[0], c[1], c[2], c[3]))
        elif len(c) == 4:
            ok_rows.append((c[0], "unc", c[1], c[2]))
        else:
            ok_rows.append((c[0], "unc", "bib", c[1]))
    if len(ok_rows) != len(records):
        print(f"FATAL: {len(records)} records vs {len(ok_rows)} ok manifest rows; "
              f"refusing to stamp itemKeys", file=sys.stderr)
        sys.exit(3)

    for rec, (key, server, keytype, value) in zip(records, ok_rows):
        df = ET.SubElement(rec, f"{{{MARC_NS}}}datafield")
        df.set("tag", "999"); df.set("ind1", " "); df.set("ind2", " ")
        # $a join key (itemKey), $b resolving value, $c key type, $d source server.
        for code, val in (("a", key), ("b", value), ("c", keytype), ("d", server)):
            sf = ET.SubElement(df, f"{{{MARC_NS}}}subfield")
            sf.set("code", code); sf.text = val

    ET.ElementTree(root).write(cfg["out"], encoding="unicode", xml_declaration=True)
    print(f"wrote {cfg['out']}: {len(records)} records (itemKey in 999 $a)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--csv", required=True, help="input Zotero CSV")
    ap.add_argument("--out", required=True, help="output MARCXML collection path")
    ap.add_argument("--limit", type=int, help="only process first N pending per server")
    ap.add_argument("--combine", action="store_true",
                    help="just (re)build the output XML from existing harvest state")
    args = ap.parse_args()
    cfg = make_cfg(args.csv, args.out)
    if args.combine:
        combine(cfg)
    else:
        harvest(cfg, limit=args.limit)
