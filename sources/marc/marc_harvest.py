#!/usr/bin/env python3
"""Harvest full MARC records for the items in a Zotero CSV from Z39.50 servers.

Servers are tried in order (see SERVERS); the first that yields a verified
record for an item wins, so a book UNC does not hold can still be found at a
fallback catalogue.

Strategy (see sources/marc/README.md):
  * Servers     : UNC Innopac first (tcp:afton.lib.unc.edu/INNOPAC), then public
                  fallbacks for what UNC lacks -- the Library of Congress, the
                  K10plus (German) academic union catalogue, LIBRIS (Sweden's
                  national catalogue), Penn State, and the Getty Research
                  Institute, Clark Art Institute, and NYARC art libraries, then
                  the two sources whose records we synthesize rather than fetch --
                  UW-Madison's catalogue JSON and eHive. Most are Z39.50; the Alma
                  art libraries are queried over SRU/CQL (see `protocol`). See
                  SERVERS for connection strings; all yield MARC21 in UTF-8.
  * Search keys : per item, tried in order, first hit wins. Identifier keys are
                  trusted; title keys are verified against the CSV before use.
                    - bib          UNC only,  @attr 1=12 b<digits>   (unique)
                    - oclc         uwmad only, identifiers=<oclc number>
                    - isbn         UNC + LC,   @attr 1=7 <isbn>
                    - title-author LC only,    @and 1=4 "<title>" 1=1003 "<author>"
                    - title        LC only,    @attr 1=4 "<title>"
                  (OCLC is usable only at uwmad, whose per-record JSON lets a
                  relevance-ranked hit be confirmed against the record's own
                  oclc_ids; no Z39.50/SRU target in the chain indexes it -- #99.)
  * Verify      : a title / title-author hit is kept only when the retrieved
                  record's 245 (and 100/260) agree with the CSV title plus the
                  author surname or the year; otherwise it is rejected (logged to
                  review.tsv). This guards the synthetic-999 join against a
                  coincidental title match being stamped onto the wrong itemKey.
  * Join key    : the CSV's canonical key (row["canonicalKey"], falling back to
                  the legacy row["itemKey"]; see row_key). Each retrieved record is
                  stamped with a synthetic 999 $a <key> $b <value> $c <keytype>
                  $d <server> field -- no content-based join. Since #82/#84 the
                  canonical harvest runs off the deduped lists
                  (sources/artists-books.csv / reference-works.csv) and stamps the
                  *canonical* key in 999 $a, so queries/artists-books.rq and
                  queries/reference-works.rq join MARC directly on ?canonical_key.
  * Premerged   : legacy MARC already carrying its 999 $a (e.g. the re-keyed lib-1
                  held records in marc/artists-books-held-marc.xml -- see
                  marc/rekey_held.py) can be supplied with --premerged: those keys
                  are skipped during harvest and the records merged in combine(),
                  so the ~1,340 held books need no re-harvest.
  * Transport   : Z39.50 fetches go through the `zoomfetch` C driver (issue #85),
                  which talks the protocol over YAZ's ZOOM API and frames each
                  record with its job id -- so records can't be misaligned to the
                  wrong query (the old yaz-client scripting reconstructed that by
                  position, the root of the "unalignable" failures). SRU targets
                  still go over HTTP/CQL via sru_search().
  * Politeness  : one serial connection per server per batch, with a `sleep`
                  between queries and a pause between batches (more conservative
                  for LC, a shared national service).
  * Encoding    : both targets return UTF-8 bytes. UNC mislabels leader/09 as
                  MARC-8, so we rewrite leader/09 to 'a' (LC is already honest);
                  we do NOT transcode (that would double-encode).
  * Output      : a per-record zip archive (#81) -- one <key>.xml MARCXML document
                  per record, read by the construct queries via nested Archive ->
                  XML triplifiers. Reproducible bytes (entries sorted, fixed 1980
                  mtimes) so a re-harvest that changes one record touches one entry.
                  Per-CSV harvest state lives under harvest/<csv-stem>/
                  (combined.marc is append-only and resumable).

Run (from sources/, or let `make -C sources marc/<stem>-marc.zip` drive it):
    python3 marc/marc_harvest.py --csv reference-works.csv --out marc/reference-works-marc.zip
    python3 marc/marc_harvest.py --csv reference-works.csv --out marc/reference-works-marc.zip --limit 15
    python3 marc/marc_harvest.py --csv reference-works.csv --out marc/reference-works-marc.zip --combine
"""
import argparse
import csv
import difflib
import json
import os
import re
import subprocess
import sys
import time
import unicodedata
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
import zipfile

HERE        = os.path.dirname(os.path.abspath(__file__))
MARC_DIR    = os.path.join(HERE, "harvest")  # gitignored harvest state, per-CSV subdir

# YAZ is built under tools/yaz-client/ (see tools/yaz-client/Makefile), not
# installed system-wide. Resolve the binaries from there so the harvest uses our
# self-contained build rather than whatever happens to be on $PATH.
# HERE is sources/marc/; the toolkit lives at the repo root under tools/, so two
# levels up (sources/marc -> sources -> repo root), matching the Makefile's
# ../tools/yaz-client when run from sources/.
YAZ_BIN     = os.path.normpath(os.path.join(HERE, os.pardir, os.pardir, "tools", "yaz-client", "bin"))
YAZ_MARCDUMP = os.path.join(YAZ_BIN, "yaz-marcdump")
# The Z39.50 fetch driver (issue #85): our own tiny C program over YAZ's ZOOM API,
# built alongside yaz-marcdump under tools/yaz-client/bin. It fetches records with
# id-per-record framing, so alignment can't break (no more "unalignable").
ZOOMFETCH   = os.path.join(YAZ_BIN, "zoomfetch")

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
#
# Precedence is by *relevance to artist's books*, not catalogue size or measured
# hit rate (the harvest is a waterfall -- each server only sees the residual its
# predecessors missed, so per-server rates are not comparable; see issue #88):
#   1. UNC first          -- home institution; prefer its own holdings/call numbers.
#   2. the art libraries  -- NYARC/Getty/Clark/Emory hold the artist's-book
#                            exhibition and dealer ephemera the general catalogues
#                            lack, and catalogue it best, so prefer their records
#                            when they have the work (a full-corpus experiment over
#                            the non-held residual bore this out: NYARC ~15%, Getty
#                            ~8% even on the hardest leftovers -- issue #88). Emory's
#                            Rose Library holds the Nexus Press archive + a deep
#                            artist's-book collection (issue #84).
#   3. the big US libraries -- LC, Harvard (English-language cataloguing).
#   4. the big EU library   -- K10plus (the ~80M-record German union catalogue).
#   5. the rest             -- PSU and LIBRIS, both near-dead weight (~0.7% and
#                            ~0.6% yield); kept as a last reach but demoted so
#                            they never pre-empt a better-catalogued record.
SERVERS = [
    # 1. UNC (home institution) -- Innopac v1.1 over Z39.50.
    {"name": "unc", "conn": "tcp:afton.lib.unc.edu:210/INNOPAC",
     # bib/isbn are exact-identifier lookups (trusted); title/title-author are
     # verified against the CSV like the fallbacks, reaching UNC-held reference
     # works that carry no ISBN or III bib number in the Zotero export.
     # batch amortises the Init handshake over one connection; since #85 the
     # zoomfetch driver tags every record with its job id, so a session UNC's
     # Innopac v1.1 server drops or truncates no longer corrupts alignment -- the
     # unanswered tail simply defers and retries -- and the old batch:10 workaround
     # for the "unalignable" bug is gone.
     "keytypes": ("bib", "isbn", "title-author", "title"),
     "batch": 50, "qsleep": 0.4, "bsleep": 2, "show_n": 3},
    # 2. Art libraries (Ex Libris Alma, SRU/CQL) -- hold and best catalogue the
    #    artist's-book ephemera the general catalogues lack. Return MARCXML/UTF-8.
    # NYARC -- New York Art Resources Consortium (MoMA, Frick, Brooklyn Museum).
    {"name": "nyarc", "conn": "https://na01.alma.exlibrisgroup.com/view/sru/01NYA_INST",
     "protocol": "sru", "keytypes": ("isbn", "title-author", "title"),
     "batch": 10, "qsleep": 0.5, "bsleep": 3, "show_n": 3},
    # Getty Research Institute, a premier art library.
    {"name": "getty", "conn": "https://na01.alma.exlibrisgroup.com/view/sru/01GRI_INST",
     "protocol": "sru", "keytypes": ("isbn", "title-author", "title"),
     "batch": 10, "qsleep": 0.5, "bsleep": 3, "show_n": 3},
    # Clark Art Institute, another art library.
    {"name": "clark", "conn": "https://na05.alma.exlibrisgroup.com/view/sru/01CLARKART_INST",
     "protocol": "sru", "keytypes": ("isbn", "title-author", "title"),
     "batch": 10, "qsleep": 0.5, "bsleep": 3, "show_n": 3},
    # Emory (Ex Libris Alma, GALILEO consortium inst 01GALI_EMORY, na03 pod) --
    # grouped with the art libraries, not the general ones, because its Stuart A.
    # Rose Library holds the Nexus Press archive and a deep artist's-book
    # collection: it catalogues the small-press / Atlanta artist's-book tail that
    # the general catalogues miss (issue #84 -- e.g. the ~22 Nexus Press works with
    # no UNC/ISBN key). alma.oclc_control_number is a dead index here as on the
    # other Alma tenants (returns nothing for real and fake numbers alike), so we
    # rely on isbn/title-author/title like the rest.
    {"name": "emory", "conn": "https://na03.alma.exlibrisgroup.com/view/sru/01GALI_EMORY",
     "protocol": "sru", "keytypes": ("isbn", "title-author", "title"),
     "batch": 10, "qsleep": 0.5, "bsleep": 3, "show_n": 3},
    # SCAD (Savannah College of Art and Design) -- absorbed the Atlanta College of
    # Art and holds the Nexus Press / ACA imprint books directly, so it catalogues
    # the Atlanta artist's-book tail (issue #84) that even Emory's Rose Library can
    # miss. Innovative Interfaces III Z39.50 SERVER v1.1 on library.scad.edu:210
    # (db INNOPAC). An earlier note held this catalogue unreachable (iii.com host
    # firewalling datacenter clients on :210/:443); re-probed 2026-07, both the
    # :210 Z39.50 server and the :443 WebPAC accept connections and return MARC21.
    # No OCLC/bib index we can key on, and these small-press books rarely carry an
    # ISBN, so it leans on title-author/title -- and several tail titles are single
    # common words ("Alice", "Distance", "Climax"), so the title-verify (245 vs CSV
    # title + author surname / year) is doing real work here.
    # Encoding: like UNC, SCAD mislabels leader/09 as blank/MARC-8 but the bytes are
    # real UTF-8 (verified 2026-07: Cäcilia/Benoît/Dalí/São Paulo/raisonné all valid
    # UTF-8), so the combine() leader/09->'a' rewrite handles it with no transcode.
    {"name": "scad", "conn": "tcp:library.scad.edu:210/INNOPAC",
     "protocol": "z3950", "keytypes": ("isbn", "title-author", "title"),
     "batch": 10, "qsleep": 1.0, "bsleep": 4, "show_n": 3},
    # 3. Big US libraries -- English-language cataloguing.
    # LC (Z39.50): a shared national service, throttled gentler than UNC. UTF-8.
    {"name": "lc",  "conn": "tcp:lx2.loc.gov:210/LCDB",
     "keytypes": ("isbn", "title-author", "title"),
     "batch": 10, "qsleep": 1.0, "bsleep": 4, "show_n": 3},
    # Harvard (Ex Libris Alma), a very large research library on the na03 pod.
    {"name": "harvard", "conn": "https://na03.alma.exlibrisgroup.com/view/sru/01HVD_INST",
     "protocol": "sru", "keytypes": ("isbn", "title-author", "title"),
     "batch": 10, "qsleep": 0.5, "bsleep": 3, "show_n": 3},
    # 4. Big EU library -- K10plus, the GBV/SWB union catalogue (~200 German/
    #    Austrian libraries), strong on art/humanities and international holdings:
    #    a good reach for the European livre d'artiste / Kunstlerbuch. Honest UTF-8.
    {"name": "k10plus", "conn": "tcp:sru.k10plus.de:210/opac-de-627",
     "keytypes": ("isbn", "title-author", "title"),
     "batch": 10, "qsleep": 1.0, "bsleep": 4, "show_n": 3},
    # 5. The rest -- near-dead weight, kept only as a last reach (see #88).
    # Penn State (Sirsi Unicorn), a large US research library. Honest UTF-8.
    {"name": "psu", "conn": "tcp:zcat.libraries.psu.edu:2200/Unicorn",
     "keytypes": ("isbn", "title-author", "title"),
     "batch": 10, "qsleep": 1.0, "bsleep": 4, "show_n": 3},
    # LIBRIS, Sweden's national union catalogue. MARC21 in UTF-8.
    {"name": "libris", "conn": "tcp:z3950.libris.kb.se:210/libris",
     "keytypes": ("isbn", "title-author", "title"),
     "batch": 10, "qsleep": 1.0, "bsleep": 4, "show_n": 3},
    # 6. UW-Madison / UW System -- the Kohler Art Library's named "Artists' Book
    # Collection" plus Memorial Special Collections, over the catalogue's own
    # JSON front end (issue #99 lever 2). Placed after every real-MARC catalogue
    # and before eHive for the same reason eHive is last: its records are
    # *synthesized* (uw_to_marcxml) from a discovery-layer JSON document, which
    # is thinner than the MARC a real catalogue serves, so it must only ever see
    # what those catalogues could not resolve. eHive stays behind it because its
    # scope is narrower still -- one institution's account.
    # Alma SRU is not published for this tenant: the institution code is
    # 01UWI_MAD (read off a record's own location_data) and the Ex Libris SRU
    # endpoint rejects it, the same off-by-default wall CARLI/SAIC presents. The
    # JSON front end is the only route in.
    # It is the *UW System* union catalogue, not just Madison: confirmed hits
    # come back held at UW Milwaukee, Stevens Point and La Crosse too.
    # This is the only server with an `oclc` keytype -- see item_keys and
    # uw_confirms for why that is sound here and nowhere else.
    {"name": "uwmad", "conn": "https://search.library.wisc.edu",
     "protocol": "uwmad", "keytypes": ("oclc", "isbn", "title-author", "title"),
     "batch": 10, "qsleep": 0.5, "bsleep": 3, "show_n": 3},
    # 7. eHive -- the Visual Studies Workshop collection (issue #99 lever 1).
    # Last in the waterfall on purpose: it is a museum CMS whose records we
    # synthesize into MARC (ehive_to_marcxml), so it must only ever see what the
    # eleven real catalogues could not resolve, and can never displace genuine
    # cataloguing for a book one of them holds.
    # VSW is #99's dominant single cluster -- ~200 works, more than the next
    # seven clusters combined -- and is catalogued here rather than in any
    # Z39.50/SRU target, which is why no amount of adding library servers reaches
    # it. conn is an API path, not a host: the account is the search scope, so
    # this is the one server whose "catalogue" is a single institution's holdings.
    # Needs EHIVE_CLIENT_ID / EHIVE_CLIENT_SECRET / EHIVE_TRACKING_ID in the
    # environment (see ehive_client.py); with none set the server is skipped.
    # No isbn keytype: eHive's isbn_issn is on ~12% of records and its search is
    # relevance-ranked full text, so an ISBN probe is not the exact-identifier
    # lookup the trusted IDENTIFIER_KEYS path assumes.
    # fetch_n over show_n: copies of one work are separate object records, so we
    # over-fetch and let ehive_candidates() dedupe down to show_n distinct works.
    {"name": "ehive", "conn": "/api/v2/accounts/3931/objectrecords",
     "protocol": "ehive", "keytypes": ("title-author", "title"),
     "batch": 25, "qsleep": 0.15, "bsleep": 1, "show_n": 5, "fetch_n": 25},
    # NOTE: SUDOC (carmin.sudoc.abes.fr/ABES-Z39-PUBLIC) is reachable and would
    # reach the French references, but its public endpoint emits records in a
    # non-standard encoding that mislabels itself UTF-8 and that yaz cannot
    # cleanly transcode (accented text is mangled or dropped), so it is omitted.
]

# Identifier keys are trusted on a hit; title keys must be verified. Accept a
# title hit when its normalized 245 is very close to the CSV title, or
# reasonably close AND corroborated by the author surname or publication year.
# Keys select_record trusts without a verify_title check. "oclc" is here only
# because the one server that uses it (uwmad) confirms every candidate against
# the retrieved record's own oclc_ids before handing it back -- see uw_confirms.
# A server that queried an OCLC index and trusted the ranking would not be sound:
# UW's identifiers index is relevance-ranked, and a nonexistent OCLC number still
# returns a plausible-looking single hit.
IDENTIFIER_KEYS = ("bib", "isbn", "oclc")
TITLE_KEYS      = ("title-author", "title")
TITLE_STRONG    = 0.85
TITLE_WEAK      = 0.60


def make_cfg(csv_path, out_xml, premerged=None):
    """Resolve all paths for one CSV; harvest state lives in harvest/<csv-stem>/."""
    csv_path = os.path.abspath(csv_path)
    out_xml = os.path.abspath(out_xml)
    base = os.path.splitext(os.path.basename(csv_path))[0]
    state = os.path.join(MARC_DIR, base)
    return {
        "csv": csv_path,
        "out": out_xml,
        "state": state,
        "combined": os.path.join(state, "combined.marc"),  # binary MARC, append-only
        "manifest": os.path.join(state, "manifest.tsv"),   # itemKey server keytype value status
        "missing": os.path.join(state, "missing.tsv"),     # itemKey server value reason
        "review": os.path.join(state, "review.tsv"),       # itemKey server keytype value reason
        # Committed records supplied by hand for items no reachable catalogue
        # serves (each already carries its 999 $a itemKey); merged by combine().
        "manual": os.path.join(os.path.dirname(out_xml), base + "-manual.xml"),
        # Optional pre-keyed MARC (records already carrying their 999 $a) to skip
        # during harvest and merge in combine() -- e.g. the re-keyed held records.
        "premerged": os.path.abspath(premerged) if premerged else None,
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


# A real OCLC number in the Zotero url/extra columns, for the uwmad `oclc` key.
# Guarded because those columns also carry cataloguer prose -- "[No WorldCat
# Record Found 11/5/2020]" matches a bare /oclc/i search. Kept identical to
# residual_csv.py's OCLC_RE so the harvest and the residual count agree on which
# rows carry a usable OCLC number (#99 measures the lever at 713 rows).
OCLC_RE = re.compile(r"worldcat\.org/oclc/(\d+)|\boclc[:\s#]*(\d{5,})", re.I)


def oclc_of(row):
    """The OCLC number in a row's url/extra columns, or None."""
    m = OCLC_RE.search((row.get("url") or "") + " " + (row.get("extra") or ""))
    return (m.group(1) or m.group(2)) if m else None


def item_keys(row):
    """Available search keys for one CSV row: keytype -> [(value, querymap), ...].

    value is what gets stamped into 999 $b; querymap maps a server protocol
    ("z3950" Bib-1 prefix, "sru" CQL, "uwmad" query params) to the query
    expression for that key. A keytype with no entry for a server's protocol is
    simply skipped there (e.g. bib is UNC-only, oclc is uwmad-only). For SRU the
    title query is title-only and leans on verify_title; CQL phrase-on-author is
    unreliable across Alma tenants.

    The uwmad entries are param dicts rather than query strings because that
    catalogue's advanced search is fielded on distinct HTTP parameters
    (title=/names=/identifiers=) rather than one query expression.
    """
    keys = {}
    m = re.search(r"/UNCb(\d+)", row.get("url") or "")
    if m:
        keys["bib"] = [("b" + m.group(1), {"z3950": f"@attr 1=12 b{m.group(1)}"})]
    # OCLC is uwmad-only: no Z39.50/SRU target in the chain indexes it usefully
    # (LC answers @attr 1=1007 with "[114] Unsupported Use attribute"; the Alma
    # tenants' alma.oclc_control_number silently matches everything -- #99).
    oclc = oclc_of(row)
    if oclc:
        keys["oclc"] = [(oclc, {"uwmad": {"identifiers": oclc}})]
    for i in clean_isbns(row.get("ISBN", "")):
        keys.setdefault("isbn", []).append(
            (i, {"z3950": f"@attr 1=7 {i}", "sru": f"alma.isbn={i}",
                 "uwmad": {"identifiers": i}}))
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
                 "sru": f'alma.title="{title}"',
                 "ehive": title,
                 "uwmad": {"title": title, "names": surname}})]
        else:
            keys["title"] = [(title,
                {"z3950": f'@attr 1=4 @attr 4=1 "{title}"',
                 "sru": f'alma.title="{title}"',
                 "ehive": title,
                 "uwmad": {"title": title}})]
    return keys


def read_rows(cfg):
    with open(cfg["csv"], newline="") as fh:
        return list(csv.DictReader(fh))


def row_key(row):
    """Join key stamped into 999 $a: the canonical key (#82/#84 deduped identity),
    falling back to the legacy per-library itemKey for older CSVs."""
    return row.get("canonicalKey") or row.get("itemKey")


def record_key(rec):
    """A MARC record Element's 999 $a join key, or None."""
    for df in rec.findall(f"{{{MARC_NS}}}datafield"):
        if df.get("tag") == "999":
            for sf in df.findall(f"{{{MARC_NS}}}subfield"):
                if sf.get("code") == "a":
                    return sf.text
    return None


def read_keyed_records(path):
    """[(key, record Element)] from a MARCXML file whose records carry their join
    key in 999 $a (records without one are skipped). Used for --premerged and the
    hand-supplied manual file."""
    if not path or not os.path.exists(path):
        return []
    root = ET.parse(path).getroot()
    # Accept both a <collection> of records and a bare <record> (per-record file).
    records = root.findall(f"{{{MARC_NS}}}record") or (
        [root] if root.tag == f"{{{MARC_NS}}}record" else [])
    return [(k, rec) for rec in records if (k := record_key(rec)) is not None]


def record_document(rec):
    """One <record> serialized as a standalone <collection>-wrapped MARCXML doc,
    mirroring the collection structure so the queries' `?record a marc:record`
    traversal is unchanged -- only the container holds a single record."""
    coll = ET.Element(f"{{{MARC_NS}}}collection")
    coll.append(rec)
    return ET.tostring(coll, encoding="unicode", xml_declaration=True)


def write_record_zip(records, out_zip):
    """Write records to a reproducible per-record zip archive (#81): one <key>.xml
    per record (key from 999 $a), entries sorted with fixed 1980 mtimes so an
    unchanged input gives byte-identical bytes and git shows no churn -- the same
    discipline notes.zip uses (#79). The queries read the key from 999, not the
    filename, so the <key>.xml naming is just for a stable, debuggable layout.
    Returns (n_written, n_no_key)."""
    ET.register_namespace("", MARC_NS)
    docs, no_key = {}, 0
    for rec in records:
        key = record_key(rec)
        if key is None:
            no_key += 1
            continue
        docs[key] = record_document(rec)  # last wins on a duplicate key
    with zipfile.ZipFile(out_zip, "w", zipfile.ZIP_DEFLATED) as zf:
        for key in sorted(docs):
            info = zipfile.ZipInfo(f"{key}.xml", date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            zf.writestr(info, docs[key])
    return len(docs), no_key


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
            targets.append((row_key(row), probes))
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


def count_records(marc_bytes):
    """Count records in a binary MARC blob (records end with the 0x1D terminator)."""
    return marc_bytes.count(b"\x1d")


def parse_zoom(out):
    """Parse zoomfetch's framed stdout (issue #85) into per-job results.

    Returns (hits, recs) where hits maps a job id -> server hit count for every
    job that was *answered* (emitted a HITS or ERROR line), and recs maps a job
    id -> [record_bytes, ...] in index order. A job id absent from `hits` was not
    answered -- the connection died (FATAL) before reaching it, or the driver was
    cut short -- and the caller defers it rather than recording a false miss.

    Framing (see zoomfetch.c): an ASCII tab-separated header line, then for a
    RECORD exactly <bytelen> raw ISO 2709 bytes and a trailing newline. Records
    are binary (they contain newlines), so the stream is parsed with a byte
    cursor, not line-by-line."""
    hits, recs = {}, {}
    i, n = 0, len(out)
    while i < n:
        j = out.find(b"\n", i)
        if j < 0:
            break
        parts = out[i:j].split(b"\t")
        i = j + 1
        tag = parts[0]
        if tag == b"HITS" and len(parts) >= 3:
            hits[parts[1].decode()] = int(parts[2])
        elif tag == b"RECORD" and len(parts) >= 4:
            jid = parts[1].decode()
            blen = int(parts[3])
            recs.setdefault(jid, []).append(out[i:i + blen])
            i += blen
            if i < n and out[i:i + 1] == b"\n":  # trailing newline after the bytes
                i += 1
        elif tag in (b"ERROR", b"FATAL") and len(parts) >= 2:
            # A server search diagnostic (ERROR) is a real, non-retryable miss:
            # record it as an answered job with 0 hits. A connection-level FATAL
            # means the job wasn't really tested -- leave it unanswered so the
            # caller defers it (the driver stops emitting after a FATAL).
            if tag == b"ERROR":
                hits.setdefault(parts[1].decode(), 0)
    return hits, recs


def run_zoom(cfg, server, batch, show_n):
    """Fetch a batch over one persistent connection via the zoomfetch driver.
    batch is [(itemKey, [(keytype, value, query), ...]), ...]. Returns results as
        [(itemKey, [(keytype, value, count, [record_bytes, ...]), ...]), ...]
    one probe per query in precedence order (count is the server hit count; the
    list holds min(show_n, count) records) -- the same shape run_sru returns and
    select_record consumes.

    Every probe is fed to the driver with a unique job id, and every record comes
    back tagged with that id, so there is no positional reconstruction and hence
    no "unalignable" failure mode. A probe the driver did not answer (connection
    died before reaching it) is deferred: it is emitted with count = None so the
    caller leaves the item unattempted to retry next run.

    Returns None only if the driver hangs (subprocess timeout) -- the caller
    defers the whole batch, never crashing a resumable harvest."""
    conn = server["conn"]
    qsleep = server["qsleep"]

    # Flatten probes to lines `<jobid>\t<query>\t<show_n>`; jobid is the flat
    # probe index. per_item keeps the (jobid, keytype, value) grouping to reassemble.
    lines, per_item, pid = [], [], 0
    for key, plist in batch:
        ids = []
        for keytype, value, query in plist:
            jid = str(pid); pid += 1
            lines.append(f"{jid}\t{query}\t{show_n}")
            ids.append((jid, keytype, value))
        per_item.append((key, ids))

    try:
        proc = subprocess.run(
            [ZOOMFETCH, "--syntax", "usmarc", "--sleep", str(qsleep),
             "--maxrecords", str(show_n), conn],
            input=("\n".join(lines) + "\n").encode(),
            capture_output=True, timeout=60 + len(lines) * 10,
        )
    except subprocess.TimeoutExpired:
        # A hung/dropped server (zoomfetch never returned). Defer the whole batch:
        # the caller retries it on the next run -- never crash a resumable harvest.
        return None

    hits, recs = parse_zoom(proc.stdout)
    results = []
    for key, ids in per_item:
        probelist = []
        for jid, keytype, value in ids:
            # count None == not answered (deferred); an answered job has an int.
            count = hits.get(jid)
            probelist.append((keytype, value, count, recs.get(jid, [])))
        results.append((key, probelist))
    return results


def select_record(cfg, key, probelist, rowmap):
    """Choose a record for one item from its probe results, in precedence order.
    Identifier-key hits are trusted; title-key hits are verified against the CSV.
    Returns (status, keytype, value, record_or_None, ncands, review_or_None).

    status is "ok" (a record was chosen), "miss" (every probe was tested and none
    matched), or "defer" (some probe was left unanswered -- count is None because
    the connection died before the driver reached it -- and nothing else resolved
    the item, so it is left unattempted to retry rather than recorded as a false
    miss)."""
    for keytype, value, count, recs in probelist:
        if not count or not recs:  # 0 hits, unanswered (None), or no record bytes
            continue
        if keytype in IDENTIFIER_KEYS:
            review = f"{count} holdings; show picked first" if count > 1 else None
            return "ok", keytype, value, recs[0], count, review
        for rec in recs:  # title key: accept the first candidate that verifies
            if verify_title(cfg, rec, rowmap[key]):
                review = f"{count} candidates; verified one" if count > 1 else None
                return "ok", keytype, value, rec, count, review
    if any(count is None for _kt, _v, count, _r in probelist):
        return "defer", "", "", None, 0, None
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
    """SRU equivalent of run_zoom: one HTTP request per probe (CQL), returning
    the same (itemKey, [(keytype, value, count, [record_bytes...]), ...]) shape.
    SRU has no persistent-connection drop to defer, so count is always an int."""
    results = []
    for key, plist in batch:
        probelist = []
        for keytype, value, cql in plist:
            n, els = sru_search(server["conn"], cql, show_n)
            probelist.append((keytype, value, n, marcxml_to_binary(els[:show_n])))
            time.sleep(server["qsleep"])
        results.append((key, probelist))
    return results


# --- eHive (issue #99) -------------------------------------------------------
#
# eHive is a museum-collection CMS, not a library catalogue: it answers JSON
# object records, so there is nothing to fetch as MARC and the records below are
# *synthesized* from its fields. That is sound only because the synthesis is
# narrow -- title, maker, physical description, summary -- and because every
# candidate still has to clear verify_title against the CSV before it is kept.
# combine() stamps 999 $d "ehive", so a synthesized record is always
# distinguishable from real cataloguing in the committed archive.

EHIVE_LIBRARY_TYPE = "LIBRARY"


def ehive_fields(obj):
    """Flatten an eHive object record's fieldSets into {identifier: [values]}.

    eHive nests every value as fieldSets -> fieldRows -> fields -> attributes,
    where the attribute list is key/value pairs and the one we want is "value".
    Identifiers repeat (a record may carry several primary_creator_maker), so
    each maps to a list in catalogue order."""
    out = {}
    for fs in obj.get("fieldSets", []):
        for row in fs.get("fieldRows", []):
            for f in row.get("fields", []):
                for a in f.get("attributes", []):
                    if a.get("key") == "value" and (a.get("value") or "").strip():
                        out.setdefault(f.get("identifier"), []).append(a["value"].strip())
    return out


def ehive_to_marcxml(obj):
    """One eHive object record -> a MARCXML <record> Element.

    Only fields the construct query actually consumes are emitted (100/700
    contributions, 300 physical description, 520 summary), plus 245 -- which the
    graph does not read (the title is a plain rdfs:label off the CSV, #11) but
    verify_title does, so it is what gates the record being kept at all.

    Deliberately **no 001**. queries/artists-books.rq reads 001 as an OCLC number
    and accepts any digit run of 10 or fewer as one; an eHive objectRecordId is
    ~6 digits, so emitting it would mint a confident link to an unrelated
    worldcat.org record. There is no OCLC number in eHive to put there instead.
    (The 001 match in that query is OPTIONAL for exactly this case.)

    Publication data (264) is emitted for verify_title's benefit, not the
    graph's: the query takes publisher/place/date from the CSV, but decode_record
    reads the year off 260/264 $c, and that year is what lets a weak-band title
    match be corroborated instead of dropped.

    **Requires a full record.** The search endpoint returns a truncated field
    set -- no publication_date, publisher, publication_place or edition -- so a
    candidate must be re-fetched from /api/v2/objectrecords/{id} before it is
    mapped. Mapping a search hit directly loses the date on ~95% of records and
    silently strands their weak-band matches in review.tsv.

    eHive's `edition` field is deliberately **not** mapped to MARC 250. Its
    values are edition sizes and copy numbers ("30", "500", "1/31", "/3"), not
    the edition statement 250 means; routing them there would assert
    bf:editionStatement "1/31" on the book. An honest home for them would be a
    new ab: term for edition size, which is out of scope here (#99)."""
    f = ehive_fields(obj)
    rec = ET.Element(f"{{{MARC_NS}}}record")

    def datafield(tag, ind1=" ", ind2=" ", **subs):
        """Append tag with the given subfields, skipping empty ones."""
        pairs = [(c, v) for c, v in subs.items() if v]
        if not pairs:
            return
        df = ET.SubElement(rec, f"{{{MARC_NS}}}datafield")
        df.set("tag", tag); df.set("ind1", ind1); df.set("ind2", ind2)
        for code, val in pairs:
            sf = ET.SubElement(df, f"{{{MARC_NS}}}subfield")
            sf.set("code", code); sf.text = val

    makers = f.get("primary_creator_maker", [])
    roles = f.get("primary_creator_maker_role", [])
    # eHive names are already inverted ("Sesto, Carl"), matching MARC 100 $a.
    if makers:
        datafield("100", ind1="1", a=makers[0], e=(roles[0] if roles else ""))
    for i, extra in enumerate(makers[1:], start=1):
        datafield("700", ind1="1", a=extra, e=(roles[i] if i < len(roles) else ""))

    datafield("245", ind1=("1" if makers else "0"), ind2="0",
              a=" ".join(f.get("name", [])))
    # date_made is the fallback: a handful of records use it where the rest use
    # publication_date. "1975 circa" is fine -- decode_record pulls the \d{4}.
    pubdate = (f.get("publication_date") or f.get("date_made") or [""])[0]
    datafield("264", ind2="1",
              a=(f.get("publication_place") or [""])[0],
              b=(f.get("publisher") or [""])[0],
              c=pubdate)
    # 300 $b is illustrative content in the query's reading; eHive's
    # medium_description ("offset lithography, screenless duotones") is a
    # statement of exactly that. $c is dimensions. There is no extent ($a) in
    # eHive -- object_type is only ever a form word like "Book".
    datafield("300",
              b="; ".join(f.get("medium_description", [])),
              c="; ".join(f.get("measurement_description", [])))
    datafield("520", a=" ".join(f.get("web_public_description", [])))
    for isbn in clean_isbns(" ".join(f.get("isbn_issn", []))):
        datafield("020", a=isbn)
    return rec


def ehive_candidates(payload, show_n):
    """LIBRARY object records from one eHive response, de-duplicated, best first.

    VSW catalogues each physical copy as its own object record ("copy 1" ...
    "copy 13"), so an undeduplicated top-3 can be three copies of one work and
    push the actually-matching book out of the window -- the show-depth ceiling
    #98 describes, arrived at by a different route. Collapsing on the normalized
    title first means show_n counts distinct works, not copies; the lowest
    objectRecordId wins a tie, which is stable across runs."""
    seen = {}
    for obj in payload.get("objectRecords", []):
        if obj.get("catalogueType") != EHIVE_LIBRARY_TYPE:
            continue
        title = norm(" ".join(ehive_fields(obj).get("name", [])))
        if not title:
            continue
        prev = seen.get(title)
        if prev is None or (obj.get("objectRecordId") or 0) < (prev.get("objectRecordId") or 0):
            seen[title] = obj
    return list(seen.values())[:show_n]


_EHIVE_FULL = {}


def ehive_full_record(sess, obj):
    """Re-fetch a candidate in full, because search results are truncated.

    /api/v2/accounts/{id}/objectrecords omits publication_date, publisher,
    publication_place and edition from the fieldSets it returns; only
    /api/v2/objectrecords/{id} carries them. Cached per run because the same
    object can surface as a candidate for more than one probe. Returns the
    search hit unchanged if the fetch fails, so a transient error costs the date
    rather than the record."""
    oid = obj.get("objectRecordId")
    if oid not in _EHIVE_FULL:
        try:
            _EHIVE_FULL[oid] = sess.get_json(f"/api/v2/objectrecords/{oid}")
        except Exception as e:
            print(f"  !! [ehive] full record {oid}: {e}", file=sys.stderr)
            _EHIVE_FULL[oid] = obj
    return _EHIVE_FULL[oid]


_EHIVE_SESSION = {}


def ehive_session(server):
    """One authorized eHive session per process, created on first use so a
    harvest that never reaches the eHive server needs no credentials."""
    if "s" not in _EHIVE_SESSION:
        from ehive_client import Session
        _EHIVE_SESSION["s"] = Session(qsleep=server.get("qsleep", 0.2))
    return _EHIVE_SESSION["s"]


def run_ehive(cfg, server, batch, show_n):
    """eHive equivalent of run_zoom/run_sru: one account-scoped search per probe.

    The reported count is the number of distinct candidates handed back, not
    eHive's totalObjects -- a relevance search over the account reports every
    ranked record (often thousands), which would make review.tsv read
    "7671 candidates" for what is really a shortlist of eight."""
    sess = ehive_session(server)
    results = []
    for key, plist in batch:
        probelist = []
        for keytype, value, query in plist:
            try:
                payload = sess.get_json(server["conn"],
                                        {"query": query, "limit": server["fetch_n"]})
            except Exception as e:
                print(f"  !! [{server['name']}] {key}: {e}", file=sys.stderr)
                probelist.append((keytype, value, 0, []))
                continue
            recs = []
            for c in ehive_candidates(payload, show_n):
                full = ehive_full_record(sess, c)
                if full is not None:
                    recs.append(marc_element_to_binary(ehive_to_marcxml(full)))
            probelist.append((keytype, value, len(recs), recs))
        results.append((key, probelist))
    return results


# --- UW-Madison / UW System (issue #99) --------------------------------------
#
# search.library.wisc.edu is a discovery layer over the UW System Alma tenant,
# not a MARC service: its Alma SRU is unpublished (institution code 01UWI_MAD,
# read off a record's own location_data, is rejected by the Ex Libris endpoint),
# so the only route in is the catalogue's own HTML search plus its per-record
# JSON document. Records are therefore *synthesized* here, as they are for
# eHive -- see uw_to_marcxml for what that does and does not carry.
#
# Three properties of this source shape the adapter:
#
#   * The `identifiers` index is relevance-ranked, not an exact key. A
#     nonexistent OCLC number (9999999999) returns one plausible-looking record
#     -- an unrelated Thai children's book -- with no diagnostic. This is the
#     Alma alma.oclc_control_number match-all trap in milder, more dangerous
#     form: milder because it returns one hit rather than the whole catalogue,
#     more dangerous because one hit looks like a successful lookup. uw_confirms
#     therefore re-checks every identifier-key candidate against the retrieved
#     record's own oclc_ids/isbns, which is what earns `oclc` its place in
#     IDENTIFIER_KEYS.
#
#   * Search results are truncated. The results page carries only title, author
#     and date; publication data, extent, notes, ISBNs and OCLC numbers live in
#     the per-record JSON. This is exactly eHive's re-fetch lesson (#131) at a
#     second source, which is why it is now stated as a rule rather than a
#     footnote: a discovery layer's result list is a shortlist, never a record.
#
#   * It is a union catalogue. Confirmed hits come back held at UW Milwaukee,
#     Stevens Point and La Crosse as well as Madison, so the reach is wider than
#     the Kohler Art Library alone -- though Kohler's named "Artists' Book
#     Collection" is where most of them land.
#
# robots.txt allows /search/catalog and /catalog for User-agent *; the requests
# below are per-title lookups from a residual list, not a crawl, and carry a
# descriptive User-Agent so the operator can identify and throttle them.

UW_UA = ("artists-books-harvest/1.0 "
         "(+https://github.com/dkglab/artists-books; MARC enrichment, issue #99)")

# One search result item: the /catalog/<mms> link in its heading. Only the
# heading link is matched -- a result block also links the cover image to the
# same record, and the facet rail links elsewhere.
UW_RESULT_RE = re.compile(r'<h2><a[^>]*href="/catalog/(\d+)"')


def uw_get(url, tries=3, timeout=30):
    """GET a UW catalogue URL as text, with a descriptive UA and a short retry.
    Returns None when every attempt fails, so a probe degrades to 0 hits rather
    than aborting a resumable harvest."""
    req = urllib.request.Request(url, headers={"User-Agent": UW_UA})
    for attempt in range(tries):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read().decode("utf-8", "replace")
        except Exception:
            if attempt == tries - 1:
                return None
            time.sleep(2 * (attempt + 1))


def uw_search(base, params, show_n):
    """Fielded advanced search -> [mms id], best first, at most show_n.

    params are the advanced form's own field names (title, names, identifiers);
    match=all ANDs them, which is what makes title+author a real conjunction
    here rather than the title-only fallback the Alma tenants force.
    """
    qs = urllib.parse.urlencode(dict(params, match="all"))
    body = uw_get(f"{base}/search/catalog?{qs}")
    if body is None:
        return []
    return UW_RESULT_RE.findall(body)[:show_n]


_UW_RECORDS = {}


def uw_record(base, mms):
    """One record's JSON `data` dict, cached per run (the same record can surface
    for more than one probe). Returns None if the fetch or parse fails."""
    if mms not in _UW_RECORDS:
        body = uw_get(f"{base}/catalog/{mms}.json")
        try:
            _UW_RECORDS[mms] = json.loads(body)["document"]["data"]
        except Exception:
            print(f"  !! [uwmad] record {mms}: unreadable JSON", file=sys.stderr)
            _UW_RECORDS[mms] = None
    return _UW_RECORDS[mms]


def uw_confirms(data, keytype, value):
    """True if a record really carries the identifier we searched for.

    The search index is relevance-ranked, so a hit is a suggestion, not a lookup:
    a nonexistent OCLC number still returns a record. Confirming against the
    retrieved record's own oclc_ids / isbns turns the suggestion back into an
    exact-identifier match, which is the whole basis for select_record trusting
    an oclc or isbn hit without verify_title. Title keys are not confirmed here
    -- they go through verify_title like every other server's."""
    if keytype == "oclc":
        return value in {str(x) for x in (data.get("oclc_ids") or [])}
    if keytype == "isbn":
        return value in {re.sub(r"[^0-9Xx]", "", str(x)).upper()
                         for x in (data.get("isbns") or [])}
    return True


def uw_oclc_control_number(data):
    """The record's OCLC control number in prefixed form (ocm/ocn/on...), for 001.

    queries/artists-books.rq reads 001 as an OCLC number and mints a worldcat.org
    link from it, guarded to an OCLC prefix or a digit run of at most 10 -- so a
    bare 11-digit OCLC number would be silently dropped as a local system id.
    UW's `identifiers` array carries the prefixed cataloguing form alongside the
    bare digits, so prefer that; fall back to bare digits only when they pass the
    query's own guard, and otherwise emit no 001 at all rather than one that would
    mint a link to an unrelated record (the eHive rule, #130).
    """
    oclcs = {str(x) for x in (data.get("oclc_ids") or [])}
    if not oclcs:
        return None
    for ident in (str(x) for x in (data.get("identifiers") or [])):
        m = re.match(r"^(?:ocm|ocn|on)0*(\d+)$", ident, re.I)
        if m and m.group(1).lstrip("0") in {o.lstrip("0") for o in oclcs}:
            return ident
    bare = sorted(oclcs, key=len)[0]
    return bare if len(bare.lstrip("0")) <= 10 else None


def uw_authority_ids(data):
    """{normalized heading: LC name-authority id} from the record's infocard_data.

    infocard_data pairs a heading with its authority id ("Drucker, Johanna,
    1952-" -> "n81067311"), which is what MARC 100/700 $0 carries and what the
    construct query uses to mint a creator URI when no VIAF/ISNI is present.
    Matching is by normalized heading because the JSON gives no other link back
    to the name it describes."""
    out = {}
    try:
        cards = json.loads(data.get("infocard_data") or "[]")
    except Exception:
        return out
    for card in cards:
        name, ident = card.get("name"), card.get("id")
        if name and ident:
            out[norm(name)] = ident
    return out


# ISBD punctuation is the subfield boundary in a flattened 300: "extent : other
# details ; dimensions". The discovery layer serves the field as one string, so
# splitting on that punctuation is a faithful reconstruction of $a/$b/$c rather
# than a guess -- and the query reads those three subfields separately.
UW_EXTENT_RE = re.compile(r"^(?P<a>[^:;]*?)(?:\s*:\s*(?P<b>[^;]*?))?(?:\s*;\s*(?P<c>.*))?$")


def uw_physical_subfields(desc):
    """A flattened 300 string -> (extent, other physical details, dimensions)."""
    m = UW_EXTENT_RE.match((desc or "").strip())
    if not m:
        return "", "", ""
    return (m.group("a") or "").strip(), (m.group("b") or "").strip(), \
           (m.group("c") or "").strip()


def uw_to_marcxml(data):
    """One UW catalogue JSON record -> a MARCXML <record> Element.

    Like ehive_to_marcxml this is a *synthesis*, sound only because it is narrow
    and because every record still has to clear either uw_confirms (identifier
    keys) or verify_title (title keys) before it is kept. combine() stamps
    999 $d "uwmad", so a synthesized record stays distinguishable in the archive.

    What is mapped, and why:
      001  the OCLC control number (see uw_oclc_control_number) -- unlike eHive,
           this source does carry a real one, so the WorldCat link the query
           mints from 001 is correct rather than fabricated.
      020  isbns.
      100/700  display_author and the remaining names, already inverted as MARC
           expects, with $0 from infocard_data where the heading matches.
      245  title, split on ISBD " : " into $a/$b, with responsibility in $c.
           The graph does not read 245 (the title is a plain rdfs:label off the
           CSV, #11) but verify_title does, so this is what gates a title hit.
      250/260/264  replayed verbatim from display_publication_data, which is not
           a rendering but the actual MARC field, indicators and subfields.
           decode_record reads the year off 260/264 $c, and that year is what
           corroborates a weak-band title match.
      300  reconstructed $a/$b/$c from the flattened physical description.
      500  display_notes.

    Deliberately **no 520**: this catalogue's JSON exposes no summary or abstract
    field. display_notes are 500-type notes ("Quotations from: ..."), not a
    summary of the work, and routing them to 520 would put cataloguer's notes
    where the site renders a description. Books resolved here therefore carry no
    summary -- an honest gap, not a bug.
    """
    rec = ET.Element(f"{{{MARC_NS}}}record")

    def datafield(tag, ind1=" ", ind2=" ", **subs):
        """Append tag with the given subfields, skipping empty ones."""
        pairs = [(c, v) for c, v in subs.items() if v]
        if not pairs:
            return
        df = ET.SubElement(rec, f"{{{MARC_NS}}}datafield")
        df.set("tag", tag); df.set("ind1", ind1); df.set("ind2", ind2)
        for code, val in pairs:
            sf = ET.SubElement(df, f"{{{MARC_NS}}}subfield")
            sf.set("code", code); sf.text = val

    control = uw_oclc_control_number(data)
    if control:
        cf = ET.SubElement(rec, f"{{{MARC_NS}}}controlfield")
        cf.set("tag", "001"); cf.text = control

    for isbn in clean_isbns(" ".join(str(i) for i in (data.get("isbns") or []))):
        datafield("020", a=isbn)

    authorities = uw_authority_ids(data)
    primary = (data.get("display_author") or "").strip()
    if primary:
        datafield("100", ind1="1", a=primary, **{"0": authorities.get(norm(primary), "")})
    for name in (data.get("names") or []):
        name = (name or "").strip()
        if name and name != primary:
            datafield("700", ind1="1", a=name, **{"0": authorities.get(norm(name), "")})

    title = (data.get("title") or "").strip()
    main, _sep, sub = title.partition(" : ")
    datafield("245", ind1=("1" if primary else "0"), ind2="0",
              a=(main + " :" if sub else main), b=sub,
              c=(data.get("responsibility") or "").strip())

    # display_publication_data is a JSON string holding real MARC fields
    # (250/260/264) with their indicators and subfields; replay them as-is.
    try:
        pubfields = json.loads(data.get("display_publication_data") or "[]")
    except Exception:
        pubfields = []
    for pf in pubfields:
        subs = {}
        for entry in pf.get("data", []):
            for code, val in entry.items():
                subs.setdefault(code, []).append(val)
        datafield(str(pf.get("field") or "260"),
                  ind1=(pf.get("i1") or " "), ind2=(pf.get("i2") or " "),
                  **{c: " ".join(v) for c, v in subs.items()})

    extent, details, dimensions = uw_physical_subfields(
        (data.get("physical_descriptions") or [""])[0])
    datafield("300", a=extent, b=details, c=dimensions)

    for note in (data.get("display_notes") or []):
        datafield("500", a=note)
    return rec


def run_uwmad(cfg, server, batch, show_n):
    """UW equivalent of run_zoom/run_sru/run_ehive: one fielded search per probe,
    then a per-record JSON fetch for each candidate.

    The count reported is the number of candidates actually handed back -- after
    uw_confirms has dropped identifier hits the record does not bear out -- so a
    review.tsv line counts real candidates rather than the relevance ranking's
    suggestions."""
    results = []
    for key, plist in batch:
        probelist = []
        for keytype, value, params in plist:
            recs = []
            for mms in uw_search(server["conn"], params, show_n):
                time.sleep(server["qsleep"])
                data = uw_record(server["conn"], mms)
                if data is None or not uw_confirms(data, keytype, value):
                    continue
                recs.append(marc_element_to_binary(uw_to_marcxml(data)))
                # An identifier key is a lookup: one confirmed record settles it.
                if keytype in IDENTIFIER_KEYS:
                    break
            probelist.append((keytype, value, len(recs), recs))
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
    """Parse one binary MARC record -> (full title, main title, authors, year),
    titles and authors normalized.

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
        return "", "", "", None
    title = norm(" ".join(_subfields(rec, "245", ("a", "b"))))
    # Main title only (245 $a before any ':' subtitle), so a CSV title that omits
    # a long catalogue subtitle can still match -- common for exhibition catalogs.
    main = main_title(" ".join(_subfields(rec, "245", ("a",))))
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
    return title, main, authors, year


def verify_title(cfg, record_bytes, row):
    """True if a title-keyed record plausibly describes the CSV item.

    A strong title match is taken on its own; in the weak band the publication
    year must corroborate. (Author surname is deliberately not used as a
    corroborator: corporate "surnames" like "Press" match unrelated records --
    e.g. "The artist publisher" wrongly matching "The artist in Edo".)"""
    rtitle, rmain, _rauthors, ryear = decode_record(cfg, record_bytes)
    ctitle = norm(row.get("title") or "")
    cmain = main_title(row.get("title") or "")
    if not rtitle or not ctitle:
        return False
    full = difflib.SequenceMatcher(None, rtitle, ctitle).ratio()
    if full >= TITLE_STRONG:
        return True
    # Weak band: the publication year must corroborate. Main-title agreement
    # (CSV title vs record 245 $a sans subtitle) may satisfy the weak band -- this
    # reaches exhibition catalogs whose 245 carries a long subtitle the CSV omits
    # -- but never grants acceptance on its own, so a generic series title
    # ("Book as art") cannot be stamped onto the wrong installment by year.
    main = (difflib.SequenceMatcher(None, rmain, cmain).ratio()
            if rmain and cmain else 0.0)
    if max(full, main) < TITLE_WEAK:
        return False
    cyear = year_of(row.get("date") or "")
    return bool(cyear and ryear == cyear)


def harvest(cfg, limit=None, servers=None):
    os.makedirs(cfg["state"], exist_ok=True)
    rows = read_rows(cfg)
    rowmap = {row_key(r): r for r in rows}
    ok_keys, attempted = load_state(cfg)
    # Pre-keyed records (e.g. re-keyed held MARC) are already resolved: skip them
    # on every server; combine() merges them back in.
    for key, _rec in read_keyed_records(cfg.get("premerged")):
        ok_keys.add(key)

    for server in (servers or SERVERS):
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
            elif proto == "uwmad":
                results = run_uwmad(cfg, server, batch, show_n)
            elif proto == "ehive":
                results = run_ehive(cfg, server, batch, show_n)
            else:
                # zoomfetch tags every record with its job id, so there is no
                # positional alignment to break (issue #85): the only failure mode
                # left is a hung driver, which returns None -> defer the whole
                # batch to the next run rather than crash the resumable harvest.
                results = run_zoom(cfg, server, batch, show_n)
                if results is None:
                    print(f"  !! [{name}] batch at {start}: zoomfetch timed out; "
                          f"deferring to next run", file=sys.stderr)
                    continue

            # Select/verify a record per item (identifier hits trusted, title
            # hits verified against the CSV). A "defer" item had a probe the driver
            # never answered (connection dropped mid-batch); leave it unrecorded so
            # it stays pending and retries next run, rather than logging a false miss.
            accepted, rows_out, reviews = [], [], []
            for key, probelist in results:
                status, kt, value, rec, _n, review = select_record(
                    cfg, key, probelist, rowmap)
                if status == "defer":
                    continue
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
    """Build the output MARCXML <collection>: stamp the canonical key into 999 $a
    on each harvested record, then merge the pre-keyed --premerged and manual
    records. Runs even with no harvested records yet (premerged/manual only) -- so
    the held baseline can be produced before the non-held harvest has run."""
    ET.register_namespace("", MARC_NS)

    have_harvest = os.path.exists(cfg["combined"]) and os.path.getsize(cfg["combined"]) > 0
    if not have_harvest and not os.path.exists(cfg.get("premerged") or "") \
            and not os.path.exists(cfg["manual"]):
        print("no combined.marc, premerged or manual records -- nothing to combine",
              file=sys.stderr)
        return

    if have_harvest:
        raw = subprocess.run(
            # Both servers send UTF-8 bytes; just mark leader/09 'a' (97). No transcode.
            [YAZ_MARCDUMP, "-l", "9=97", "-i", "marc", "-o", "marcxml", cfg["combined"]],
            capture_output=True, text=True,
        ).stdout
        root = ET.fromstring(raw)
        records = root.findall(f"{{{MARC_NS}}}record")
    else:
        root = ET.Element(f"{{{MARC_NS}}}collection")
        records = []

    harvested_keys = set()
    if records:
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
            harvested_keys.add(key)
            # Strip any pre-existing 999 the source catalogue stamped (999 is a
            # locally-defined field; NYARC populates it with staff data -- #95)
            # so each record carries exactly one 999 = our canonical join key.
            for old in rec.findall(f"{{{MARC_NS}}}datafield[@tag='999']"):
                rec.remove(old)
            df = ET.SubElement(rec, f"{{{MARC_NS}}}datafield")
            df.set("tag", "999"); df.set("ind1", " "); df.set("ind2", " ")
            # $a join key (canonical), $b resolving value, $c key type, $d server.
            for code, val in (("a", key), ("b", value), ("c", keytype), ("d", server)):
                sf = ET.SubElement(df, f"{{{MARC_NS}}}subfield")
                sf.set("code", code); sf.text = val

    # Merge pre-keyed records (each already carrying its 999 $a): first the
    # --premerged file (e.g. the re-keyed lib-1 held MARC), then the hand-supplied
    # manual records for items no reachable catalogue serves. A harvested record
    # for the same key wins (freshly verified), so skip keys already present.
    n_premerged = 0
    for key, rec in read_keyed_records(cfg.get("premerged")):
        if key not in harvested_keys:
            root.append(rec)
            harvested_keys.add(key)
            n_premerged += 1
    n_manual = 0
    for key, mrec in read_keyed_records(cfg["manual"]):
        if key not in harvested_keys:
            root.append(mrec)
            harvested_keys.add(key)
            n_manual += 1

    # Emit a per-record zip archive (#81), not one big <collection> file: one
    # <key>.xml per record, read by the construct queries via nested Archive -> XML
    # triplifiers. Diffable (a re-harvest that changes one record touches one entry).
    n_archive, n_nokey = write_record_zip(root.findall(f"{{{MARC_NS}}}record"), cfg["out"])
    total = len(records) + n_premerged + n_manual
    print(f"wrote {cfg['out']}: {len(records)} harvested + {n_premerged} premerged "
          f"+ {n_manual} manual = {total} records -> {n_archive} archive entries "
          f"(canonical key in 999 $a)")
    if n_nokey:
        print(f"  WARNING: {n_nokey} records had no 999 $a and were dropped",
              file=sys.stderr)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--csv", required=True, help="input Zotero CSV")
    ap.add_argument("--out", required=True, help="output per-record zip archive (#81)")
    ap.add_argument("--limit", type=int, help="only process first N pending per server")
    ap.add_argument("--combine", action="store_true",
                    help="just (re)build the output XML from existing harvest state")
    ap.add_argument("--premerged", help="MARCXML of pre-keyed records (999 $a) to "
                    "skip during harvest and merge on combine (e.g. re-keyed held MARC)")
    ap.add_argument("--servers", help="comma-separated server names to query, in the "
                    "given order (default: all of SERVERS in their listed order). "
                    "Resumable state is per (item, server), so this only restricts "
                    "which servers run this pass -- e.g. --servers harvard,libris")
    args = ap.parse_args()
    cfg = make_cfg(args.csv, args.out, premerged=args.premerged)
    servers = None
    if args.servers:
        by_name = {s["name"]: s for s in SERVERS}
        names = [n.strip() for n in args.servers.split(",") if n.strip()]
        unknown = [n for n in names if n not in by_name]
        if unknown:
            ap.error(f"unknown server(s): {', '.join(unknown)}; "
                     f"known: {', '.join(by_name)}")
        servers = [by_name[n] for n in names]
    if args.combine:
        combine(cfg)
    else:
        harvest(cfg, limit=args.limit, servers=servers)
