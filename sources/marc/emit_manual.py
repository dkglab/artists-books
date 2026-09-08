#!/usr/bin/env python3
"""Emit artists-books-manual.xml from hand-adjudicated harvest false-negatives.

A harvest rejects items whose title probe hit but failed verify_title.
Re-querying each (adjudicate_review.py) and reading the candidates by hand
separates genuine false-negatives -- the right book under a cataloguer's variant
title -- from true wrong matches. Each CONFIRMED entry is (canonicalKey,
substring of the chosen candidate's 245, why) so the pick is legible and
re-checkable rather than a bare candidate index.

Each emitted record is stamped 999 $a <canonicalKey> $b manual $c manual
$d <server>, matching what combine() stamps on harvested records.

Runs are keyed by CSV stem in CONFIRMED_BY_RUN; select one with STEM. The output
is **merged, not overwritten**: records stamped with a different $d server are
carried through untouched, so emitting the eHive picks cannot silently drop the
SCAD ones already in the file. Re-running one server replaces just its own
records, so the script stays idempotent per run.
"""
import json
import os
import subprocess
import sys
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import marc_harvest as mh

HERE = os.path.dirname(os.path.abspath(__file__))
STEM = os.environ.get("STEM", "scad-residual")
CANDS = os.path.join(HERE, "harvest", f"{STEM}-candidates.jsonl")
# combine() picks up <base>-manual.xml next to its --out, so this is the file a
# full re-harvest of artists-books-marc.zip merges these records back in from.
OUT = os.path.join(HERE, "artists-books-manual.xml")

# (canonicalKey, 245-substring identifying the chosen candidate, why it verified)
CONFIRMED_SCAD = [
    ("VJR5T9ZG", "air born an artist s book",
     "CSV title mashes two bound-together works; Kresge+Kennedy, 1994"),
    ("L466X8MJ", "bobby book nr 100",
     "SCAD catalogued 'Bob' as 'Bobby'; Keith A. Smith, Nexus Press, 1985"),
    ("9H7N8P5P", "carl andre ausstellung vom 18 oktober",
     "exact title+year; ranked 4th so the show_n=3 harvest never saw it"),
    ("BQQRZ9CX", "dark shadow gilbert and george",
     "245 carries the 'the sculptors 1974' subtitle the CSV omits"),
    ("KBSM8ETH", "fahrten uber den rhein",
     "CSV title carries a stray '/|' separator; Stoltz, usus, 2007"),
    ("MI2CXLYF", "earn christy caravaglio",
     "245 appends the author to the one-word title; 1996"),
    ("9MCGNRCF", "futura",
     "Futura 25 is the series number of Thomkins' palindrome; H. Mayer, 1968"),
    ("5FMAYRE8", "money",
     "245 $a Money / 246 Iconomics; DeCoster, Nexus Press, 1984"),
    ("FYS7QI64", "marilyn monroe 1926 1962",
     "exact title; Colmer, 2003 imprint vs CSV 2004"),
    ("A6PZ7SEC", "oral aural written a book",
     "245 has the fuller 'written'; Melamed, Nexus Press, 1998"),
    ("U59K33M4", "nature s details",
     "CSV prepends the series title 'Rocks'; Timm, Mystical Places Press"),
    ("8W5JRUUG", "the vicious circle series",
     "245 appends 'series'; Emily Martin, 1997"),
]

# eHive / Visual Studies Workshop (#99). 11 of 35 rejects. Two distinct kinds:
#
#   * show-depth misses (#98) -- the record verifies outright, it just ranked
#     below the harvest's window: "letters" (rank 9), "spine" (rank 8),
#     "six" (rank 6).
#   * threshold false-negatives -- a variant or fuller title, corroborated by an
#     exact author match and a year within one.
#
# Deliberately NOT confirmed, though a mechanical re-run at show_n=10 would take
# them:
#   4JJDRHEP  "Perspectives IV, The Moon at Seventeen Days of Age" verifies
#             against "Perspectives II: The Matterhorn" on the shared series
#             title plus a matching 1976 -- the wrong-installment failure
#             verify_title's docstring warns about. Perspectives II, VII and VIII
#             are all present; IV is not. It would also collide with I2LUTMLH,
#             which is the real Matterhorn.
#   AA3JMRN2  ranks 6 and 7 are "A Reading by Gary Snyder" and "A Reading by
#             Mark Strand", both `various`, both 1972. The CSV title
#             ("A Reading by \'85") is garbled and cannot disambiguate, so
#             accepting either is a coin flip between two different books.
#   XE4T9VS4  "The First Rip-Off Show" against Joel Swartz's "Rip off book"
#             (1970) -- a different title and year.
CONFIRMED_EHIVE = [
    ("ILJTV7CI", "letters",
     "exact title+author+year (Benedetto, 1973); ranked 9th, outside show_n"),
    ("YWTQXLZC", "spine",
     "exact title+year; 100 carries both Lyons and Zimmermann; ranked 8th"),
    ("86YBPSEL", "six",
     "exact one-word title, various, 1971; ranked 6th, outside show_n"),
    ("EVHJCHT6", "letter",
     "CSV appends the occasion (\"Letter, New Year's, 1980\"); Weaver, 1980"),
    ("SLMGAUZI", "lithography notes",
     "CSV title is the collaborator's name; 100 has both Childs and Koster, 1979"),
    ("RTZFLWPY", "castles in the sand an allegory",
     "CSV inverts the title to 'Sand Castles'; LaLonde, 1990"),
    ("I2LUTMLH", "perspectives ii the matterhorn",
     "CSV drops the series prefix; Lyons, 1976 imprint vs CSV 1977"),
    ("LUWKIW5E", "perspectives iii tamiami trail",
     "CSV drops the series prefix; Lyons, 1976 imprint vs CSV 1978"),
    ("UXD3Z72C", "the disillusioned magician",
     "CSV records the title as 'Disenchanted'; Young, 1986 vs CSV 1985"),
    ("2ISVSZBR", "the four temperaments",
     "CSV appends the subtitle 'an animated sequence'; Gordon, 1974 vs CSV 1975"),
    ("G7PIKUD9", "untitled this is our autobiography",
     "CSV prepends the fill-in-the-blank line; various, 1974 vs CSV 1975"),
]

CONFIRMED_BY_RUN = {
    "scad-residual": ("scad", CONFIRMED_SCAD),
    "vsw-residual": ("ehive", CONFIRMED_EHIVE),
}
SERVER, CONFIRMED = CONFIRMED_BY_RUN[STEM]


def to_marcxml(marc_text):
    """A <record> Element from one binary MARC record held as text in the
    candidates dump. The bytes are valid UTF-8 (verified: every candidate's
    ISO-2709 declared length survives the round-trip), so encode() recovers them
    exactly; -l 9=97 marks leader/09 'a' as combine() does, with no transcode."""
    raw = subprocess.run(
        [mh.YAZ_MARCDUMP, "-l", "9=97", "-i", "marc", "-o", "marcxml", "/dev/stdin"],
        input=marc_text.encode("utf-8"), capture_output=True,
    ).stdout
    root = ET.fromstring(raw)
    return root if root.tag.endswith("record") else root.find(f"{{{mh.MARC_NS}}}record")


def main():
    by_key = {}
    with open(CANDS) as fh:
        for line in fh:
            d = json.loads(line)
            by_key[d["key"]] = d

    root = ET.Element("collection")
    root.set("xmlns", mh.MARC_NS)

    # Carry through records emitted for *other* servers. combine() reads one
    # manual file per archive, so every run's picks share it; rewriting it from
    # this run's CONFIRMED alone would drop the rest.
    kept = 0
    for _key, rec in mh.read_keyed_records(OUT):
        d = rec.find(f"{{{mh.MARC_NS}}}datafield[@tag='999']")
        server = None
        if d is not None:
            for sf in d.findall(f"{{{mh.MARC_NS}}}subfield"):
                if sf.get("code") == "d":
                    server = sf.text
        if server != SERVER:
            root.append(rec)
            kept += 1
    if kept:
        print(f"carried through {kept} records from other runs")

    n = 0
    for key, needle, why in CONFIRMED:
        entry = by_key.get(key)
        if entry is None:
            print(f"{key}: not in candidates.jsonl -- skipped", file=sys.stderr)
            continue
        # An exact 245 match wins over substring containment: one-word titles
        # ("six", "letters", "spine") occur inside many other candidate titles,
        # so a bare `in` test reads as ambiguous and skips the right record.
        picks = ([c for c in entry["candidates"] if c["title"] == needle]
                 or [c for c in entry["candidates"] if needle in c["title"]])
        if len(picks) != 1:
            print(f"{key}: {len(picks)} candidates match {needle!r} -- skipped",
                  file=sys.stderr)
            continue
        rec = to_marcxml(picks[0]["marc"])
        for old in rec.findall(f"{{{mh.MARC_NS}}}datafield[@tag='999']"):
            rec.remove(old)
        df = ET.SubElement(rec, f"{{{mh.MARC_NS}}}datafield")
        df.set("tag", "999"); df.set("ind1", " "); df.set("ind2", " ")
        for code, val in (("a", key), ("b", "manual"), ("c", "manual"),
                          ("d", SERVER)):
            sf = ET.SubElement(df, f"{{{mh.MARC_NS}}}subfield")
            sf.set("code", code); sf.text = val
        root.append(rec)
        n += 1
        print(f"{key}: {picks[0]['title'][:50]} ({why})")

    ET.ElementTree(root).write(OUT, encoding="utf-8", xml_declaration=True)
    print(f"\nwrote {OUT}: {n} {SERVER} records + {kept} carried = {n + kept}")


if __name__ == "__main__":
    main()
