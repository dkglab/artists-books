#!/usr/bin/env python3
"""Normalize Zotero "Cited:" note HTML into one HTML file per note, packed into a
reproducible zip for SPARQL-Anything (issue #53).

Reads the `itemKey,note` CSV produced by notes_export.sql on stdin and writes a zip
(`--out`) holding one `<itemKey>.html` document per note. The construct query reads
these directly via SPARQL-Anything's archive + HTML triplifiers and computes the
citation join in SPARQL (substring on the reference title, <em>-exact fallback) --
replacing the old cite_match.py crosswalk. Each `<p n="I">` carries the 1-based
paragraph index; the reference matcher reads the flattened text off each `<p>`'s
`#innerText`, so no `text=` attribute is emitted.

The zip is written deterministically (entries sorted by itemKey, fixed 1980 mtimes)
so an unchanged database produces byte-identical output and git shows no churn.

Zotero note HTML is messy -- HTML entities (`&nbsp;`, `&rsquo;`), malformed nesting
(`<em>...<em>.</em></em>`), and walls of inline-styled `<span>`s -- so it is not
parseable as strict XML. We parse it leniently and re-emit only the structure the
citation model needs, guaranteeing well-formedness:

  * one `<p>` per source citation paragraph (the "Cited:" header paragraph and
    empty paragraphs are dropped);
  * `<em>` preserved -- the only reliable delimiter of the citing work's title (#42);
  * **bold canonicalized to `<strong>`** -- whether the source used `<strong>`/`<b>`
    or an inline `font-weight: bold` span (the bold page numbers are the image-page
    signal for #43). `font-weight: normal` spans are cruft, NOT bold.

Each `<p>` also carries:
  * `text="..."` -- the flattened, whitespace-normalized reference string, so the
    construct query can read the citation label directly without reconstructing it
    from fragmented XML text nodes;
  * `n="I"`     -- a per-item 1-based index, used to mint a stable citation IRI.

The `<em>`/`<strong>` child markup is retained for the downstream page/title parsers
(#42/#43/#44); this export only makes the notes *readable*, it does not parse pages.
"""
import argparse
import csv
import re
import sys
import zipfile
from html.parser import HTMLParser
from xml.sax.saxutils import escape

# A <span style="..."> is bold only for an explicit bold weight, not the
# ubiquitous `font-weight: normal` styling cruft.
BOLD_STYLE = re.compile(r"font-weight:\s*(bold|[6-9]00)\b", re.I)
HEADER = re.compile(r"^\s*(cited|citation)\s*:?\s*$", re.I)


class NoteParser(HTMLParser):
    """Collect each <p> as a list of (text, in_em, in_bold) runs.

    A tag stack tolerant of unclosed/mis-nested tags tracks emphasis and bold
    state, so the sloppy source markup cannot produce malformed output.
    """

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.paragraphs = []      # list of paragraphs; each a list of runs
        self._cur = None          # runs of the open <p>, or None
        self._stack = []          # [(tag, adds_em, adds_bold)]
        self._divdepth = 0        # nesting depth of <div>s
        self._csl_depth = None    # div depth that opened the current csl-entry para

    def _open_p(self):
        self._close_p()      # flush an auto-closed (unclosed) previous paragraph
        self._stack = []     # inline formatting never spans paragraphs
        self._cur = []

    def handle_starttag(self, tag, attrs):
        if tag == "div":
            self._divdepth += 1
            # A few notes use a CSL bibliography (<div class="csl-entry">…</div>)
            # instead of <p> for each citation; treat that as a paragraph too.
            if "csl-entry" in (dict(attrs).get("class") or ""):
                self._open_p()
                self._csl_depth = self._divdepth
            return
        if tag == "p":
            self._open_p()
            return
        if tag == "br":
            if self._cur is not None:
                self._cur.append((" ", self._em(), self._bold()))
            return
        adds_em = tag in ("em", "i")
        adds_bold = tag in ("strong", "b")
        if tag == "span":
            style = dict(attrs).get("style") or ""
            if BOLD_STYLE.search(style):
                adds_bold = True
        self._stack.append((tag, adds_em, adds_bold))

    def handle_endtag(self, tag):
        if tag == "div":
            if self._csl_depth == self._divdepth:  # close the csl-entry paragraph
                self._close_p()
                self._csl_depth = None
            self._divdepth -= 1
            return
        if tag == "p":
            self._close_p()
            return
        for i in range(len(self._stack) - 1, -1, -1):  # pop to nearest match
            if self._stack[i][0] == tag:
                del self._stack[i:]
                return

    def _close_p(self):
        if self._cur is not None:
            self.paragraphs.append(self._cur)
            self._cur = None

    def handle_data(self, data):
        if self._cur is not None and data:
            self._cur.append((data, self._em(), self._bold()))

    def _em(self):
        return any(f[1] for f in self._stack)

    def _bold(self):
        return any(f[2] for f in self._stack)


def _norm(text):
    """nbsp -> space, collapse internal whitespace (preserving edge spaces)."""
    return re.sub(r"\s+", " ", text.replace("\xa0", " "))


def _merge(runs):
    """Merge adjacent runs sharing the same (em, bold); drop empties."""
    out = []
    for text, em, bold in runs:
        text = _norm(text)
        if not text:
            continue
        if out and out[-1][1] == em and out[-1][2] == bold:
            out[-1] = (out[-1][0] + text, em, bold)
        else:
            out.append((text, em, bold))
    return out


def _render(runs):
    """(flattened text, inner XHTML) for one paragraph's runs."""
    flat = " ".join("".join(t for t, _, _ in runs).split())
    parts = []
    for text, em, bold in runs:
        chunk = escape(text)
        if bold:
            chunk = f"<strong>{chunk}</strong>"
        if em:
            chunk = f"<em>{chunk}</em>"
        parts.append(chunk)
    return flat, "".join(parts)


def citations(note_html):
    """Yield (flattened_text, inner_xhtml) per non-header citation paragraph."""
    p = NoteParser()
    p.feed(note_html)
    p.close()
    p._close_p()  # flush a trailing <p> with no explicit close
    for runs in p.paragraphs:
        runs = _merge(runs)
        flat = "".join(t for t, _, _ in runs).strip()
        if not flat or HEADER.match(flat):   # drop empty + "Cited:" header
            continue
        yield _render(runs)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", required=True, help="output zip of per-note HTML files")
    args = ap.parse_args()

    # Collect paragraphs per itemKey. An item can carry up to two DB notes (two CSV
    # rows); the paragraph index continues across them so (itemKey, n) stays unique.
    notes = {}     # itemKey -> list of (n, inner_xhtml)
    counters = {}  # itemKey -> running paragraph index
    for row in csv.DictReader(sys.stdin):
        key = row["itemKey"]
        paras = list(citations(row["note"]))
        if not paras:
            continue
        n = counters.get(key, 0)
        bucket = notes.setdefault(key, [])
        for _flat, inner in paras:
            n += 1
            bucket.append((n, inner))
        counters[key] = n

    # Deterministic zip: entries sorted, fixed mtime, so unchanged input -> identical
    # bytes (no git churn on rebuild).
    with zipfile.ZipFile(args.out, "w", zipfile.ZIP_DEFLATED) as zf:
        for key in sorted(notes):
            body = "\n".join(f'<p n="{n}">{inner}</p>' for n, inner in notes[key])
            html = f"<html><body>\n{body}\n</body></html>\n"
            info = zipfile.ZipInfo(f"{key}.html", date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            zf.writestr(info, html)


if __name__ == "__main__":
    main()
