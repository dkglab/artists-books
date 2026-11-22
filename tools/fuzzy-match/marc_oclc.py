"""Which number in a MARC record is its OCLC number, and whose record it is (#222).

The rule mirrors the construct queries (queries/artists-books.rq and
queries/reference-works.rq), so the review sheets group on the same value the
graph carries:

- The 001 is an OCLC number only when it has an on/ocn/ocm prefix or the 003
  is "OCoLC". Most servers in the harvest waterfall put their own record id in
  001 (a K10plus PPN, an LC, LIBRIS or SIRSI id, an Alma MMS id), and reading
  the first digit run of a short one makes up an OCLC number.
- Otherwise the record's first 035 $a "(OCoLC)..." is used.
- Either way the number is the first digit run, leading zeros dropped, and at
  most 10 digits: a longer one is a local id.

A record whose 001 is not an OCLC number is still some catalogue's record, and
two books matched to the same one are as much a duplicate candidate as two
that share an OCLC number. record_id() names it by (server, 001).
"""
import re

NS = {"m": "http://www.loc.gov/MARC21/slim"}
OCLC_PREFIX = re.compile(r"\s*(on|ocn|ocm)", re.I)
OCLC_035 = re.compile(r"\s*\(OCoLC\)\D*(\d+)")


def _control(rec, tag):
    el = rec.find(f"m:controlfield[@tag='{tag}']", NS)
    return (el.text or "") if el is not None else ""


def _number(digits):
    n = digits.lstrip("0")
    return n if re.fullmatch(r"\d{1,10}", n) else ""


def oclc_001(rec):
    """True when the record's 001 is an OCLC number (prefix, or 003 OCoLC)."""
    c001 = _control(rec, "001")
    return bool(c001) and bool(OCLC_PREFIX.match(c001)
                               or re.sub(r"\s", "", _control(rec, "003")) == "OCoLC")


def oclc_number(rec):
    """The record's OCLC number, or "" when it has none."""
    if oclc_001(rec):
        m = re.search(r"\d+", _control(rec, "001"))
        n = _number(m.group(0)) if m else ""
        if n:
            return n
    for sf in rec.iterfind("m:datafield[@tag='035']/m:subfield[@code='a']", NS):
        m = OCLC_035.match(sf.text or "")
        if m:
            return _number(m.group(1))  # the first (OCoLC) 035 only
    return ""


def server(rec):
    """The harvest server the record came from (999 $d), else its 003."""
    for sf in rec.iterfind("m:datafield[@tag='999']/m:subfield[@code='d']", NS):
        if (sf.text or "").strip():
            return sf.text.strip()
    return _control(rec, "003").strip()


def record_id(rec):
    """(server, 001) for a record whose 001 is a local record id, else None.

    Keyed by server rather than 003, because a server's 003 is not consistent
    (LC's records carry DLC or nothing)."""
    c001 = _control(rec, "001").strip()
    if not c001 or oclc_001(rec):
        return None
    src = server(rec)
    return (src, c001) if src else None


def record_url(rec):
    """A link to the record in its own catalogue, where there is a stable one."""
    rid = record_id(rec)
    if not rid:
        return ""
    src, c001 = rid
    if src == "k10plus":
        return f"https://kxp.k10plus.de/DB=2.1/PPNSET?PPN={c001}"
    if src == "libris":
        return f"https://libris.kb.se/bib/{c001}"
    if src == "lc":  # LC's 001 has no public permalink; its 010 LCCN does
        for sf in rec.iterfind("m:datafield[@tag='010']/m:subfield[@code='a']", NS):
            lccn = re.sub(r"\s", "", sf.text or "")
            if lccn:
                return f"https://lccn.loc.gov/{lccn}"
    return ""
