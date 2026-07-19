#!/usr/bin/env python3
"""Emit scad-residual-manual.xml from the hand-adjudicated SCAD false-negatives
(issue #84, step 3).

The SCAD harvest rejected 76 items whose title probe hit but failed
verify_title. Re-querying each (adjudicate_scad.py) and reading the candidates
by hand separates genuine false-negatives -- the right book under a cataloguer's
variant title -- from true wrong matches. CONFIRMED lists only the former, each
as (canonicalKey, substring of the chosen candidate's 245) so the pick is
legible and re-checkable rather than a bare candidate index.

Each emitted record is stamped 999 $a <canonicalKey> $b manual $c manual
$d scad, matching what combine() stamps on harvested records.
"""
import json
import os
import subprocess
import sys
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import marc_harvest as mh

HERE = os.path.dirname(os.path.abspath(__file__))
CANDS = os.path.join(HERE, "harvest", "scad-residual-candidates.jsonl")
# combine() picks up <base>-manual.xml next to its --out, so this is the file a
# full re-harvest of artists-books-marc.zip merges these records back in from.
OUT = os.path.join(HERE, "artists-books-manual.xml")

# (canonicalKey, 245-substring identifying the chosen candidate, why it verified)
CONFIRMED = [
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
    n = 0
    for key, needle, why in CONFIRMED:
        entry = by_key.get(key)
        if entry is None:
            print(f"{key}: not in candidates.jsonl -- skipped", file=sys.stderr)
            continue
        picks = [c for c in entry["candidates"] if needle in c["title"]]
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
                          ("d", "scad")):
            sf = ET.SubElement(df, f"{{{mh.MARC_NS}}}subfield")
            sf.set("code", code); sf.text = val
        root.append(rec)
        n += 1
        print(f"{key}: {picks[0]['title'][:50]} ({why})")

    ET.ElementTree(root).write(OUT, encoding="utf-8", xml_declaration=True)
    print(f"\nwrote {OUT}: {n} records")


if __name__ == "__main__":
    main()
