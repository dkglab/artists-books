#!/usr/bin/env python3
"""Probe Artstor/JSTOR links for a usable display-size cover image URL.

Background (see also the investigation notes in the project history):
  * Artstor is retired. The 856 $u links in artists-books-marc.xml now redirect
    into JSTOR's "Open Community Collections":
        library.artstor.org/public/<numeric>      -> jstor.org/stable/community.<numeric>
        library.artstor.org/public/SS33469_..._<id> -> jstor.org/stable/community.<other-id>
        library.artstor.org/asset|#/asset/...      -> the old single-page viewer route
  * The JSTOR /stable/community.* landing pages are reCAPTCHA-gated *by IP*, so
    they are unreachable from CI / this VM / headless networks (every request
    gets a "JSTOR: Access Check" 403). The page is what embeds the IIIF manifest
    reference, so we cannot discover the manifest from a blocked network.
  * BUT the image tier is NOT behind that wall:
      - IIIF Image API:  https://www.jstor.org/iiif/<id>/<region>/<size>/<rot>/<quality>.<fmt>
      - image origin:    https://stor.artstor.org/...  (Fastly, Access-Control-Allow-Origin: *)
    Given a correct IIIF image *identifier* (which lives in the manifest), these
    serve sized JPEGs directly and CORS-open (good for an <img> on GitHub Pages).

What this script does:
  * resolve   : follow redirects on an Artstor link and report the JSTOR
                community id / final URL (so you can learn the id mapping).
  * manifest  : given a IIIF manifest (URL, file, or stdin), parse v2 or v3,
                extract every canvas image + its IIIF Image service base, mint
                a sized derivative URL (default !600, wide), and VALIDATE each
                candidate (HTTP status, content-type, and JPEG/PNG dimensions
                sniffed from the bytes -- no Pillow needed).
  * marc      : list the artstor 856 links (and their $3 descriptions) for one
                or all records, so you can pick a candidate to probe.

Realistic workflow until we have one real example:
  1. Open one .../stable/community.<id> page in a normal browser on an unblocked
     network; in devtools copy the IIIF manifest request URL (or save its JSON).
  2. Feed it here:   artstor_probe.py manifest --manifest-file saved.json
     -> confirms whether a display-size JPG URL renders, and reveals the
        identifier pattern so we can derive URLs for all records.

Examples:
    python3 artstor_probe.py resolve https://library.artstor.org/public/25487930
    python3 artstor_probe.py resolve --marc 001234        # resolve a record's link
    python3 artstor_probe.py marc                          # list all artstor links
    python3 artstor_probe.py marc 001234                   # links for one record (001)
    python3 artstor_probe.py manifest https://www.jstor.org/iiif/.../manifest
    python3 artstor_probe.py manifest --manifest-file m.json --size '!800,'
    curl ... | python3 artstor_probe.py manifest --manifest-file -
"""
import argparse
import json
import os
import re
import struct
import sys
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET

HERE     = os.path.dirname(os.path.abspath(__file__))
MARC_XML = os.path.join(HERE, "artists-books-marc.xml")
MARC_NS  = "http://www.loc.gov/MARC21/slim"
M        = "{%s}" % MARC_NS

# A real browser UA; the image tier still applies bot heuristics (PerimeterX).
UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
TIMEOUT = 30


# --------------------------------------------------------------------------- #
# HTTP helpers
# --------------------------------------------------------------------------- #
def _request(url, method="GET", max_bytes=None):
    """Return (status, final_url, headers, body_bytes). Never raises on HTTP errors."""
    req = urllib.request.Request(url, method=method, headers={
        "User-Agent": UA,
        "Accept": "*/*",
    })
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            body = r.read(max_bytes) if max_bytes else r.read()
            return r.status, r.geturl(), dict(r.headers), body
    except urllib.error.HTTPError as e:
        body = b""
        try:
            body = e.read(max_bytes) if max_bytes else e.read()
        except Exception:
            pass
        return e.code, url, dict(e.headers or {}), body
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        return 0, url, {}, str(e).encode()


def _png_size(b):
    if b[:8] == b"\x89PNG\r\n\x1a\n" and b[12:16] == b"IHDR":
        w, h = struct.unpack(">II", b[16:24])
        return w, h
    return None


def _jpeg_size(b):
    if b[:2] != b"\xff\xd8":
        return None
    i, n = 2, len(b)
    while i + 9 < n:
        if b[i] != 0xFF:
            i += 1
            continue
        marker = b[i + 1]
        if 0xC0 <= marker <= 0xCF and marker not in (0xC4, 0xC8, 0xCC):
            h, w = struct.unpack(">HH", b[i + 5:i + 9])
            return w, h
        seg = struct.unpack(">H", b[i + 2:i + 4])[0]
        i += 2 + seg
    return None


def image_dims(b):
    return _png_size(b) or _jpeg_size(b)


# --------------------------------------------------------------------------- #
# resolve
# --------------------------------------------------------------------------- #
def cmd_resolve(args):
    for url in args.urls:
        status, final, hdrs, _ = _request(url, method="GET", max_bytes=4096)
        m = re.search(r"/community\.(\d+)", final)
        community = m.group(1) if m else None
        print(f"input    : {url}")
        print(f"  status : {status}")
        print(f"  final  : {final}")
        print(f"  community id : {community or '(none found in final URL)'}")
        ct = hdrs.get("Content-Type", "")
        if status == 403 and "jstor.org" in final:
            print("  note   : 403 -> JSTOR reCAPTCHA wall (expected from a server IP)")
        print(f"  type   : {ct}")
        print()


# --------------------------------------------------------------------------- #
# manifest
# --------------------------------------------------------------------------- #
def _load_manifest(args):
    if args.manifest_file:
        if args.manifest_file == "-":
            return json.load(sys.stdin)
        with open(args.manifest_file, encoding="utf-8") as f:
            return json.load(f)
    if args.source:
        status, final, hdrs, body = _request(args.source)
        if status != 200:
            sys.exit(f"manifest fetch failed: HTTP {status} for {args.source}\n"
                     f"  body: {body[:300].decode('utf-8', 'replace')}")
        return json.loads(body)
    sys.exit("manifest: give a URL, or --manifest-file PATH (or - for stdin)")


def _txt(v):
    """Flatten IIIF v2/v3 label/value shapes to a short string."""
    if v is None:
        return ""
    if isinstance(v, str):
        return v
    if isinstance(v, list):
        return "; ".join(_txt(x) for x in v if x)
    if isinstance(v, dict):
        # v3 language map {"en": [".."]} or v2 {"@value": ".."}
        if "@value" in v:
            return _txt(v["@value"])
        return "; ".join(_txt(x) for x in v.values())
    return str(v)


def _service_base(service):
    """Pull the IIIF Image API base id from a (possibly nested/listed) service node."""
    if service is None:
        return None
    if isinstance(service, list):
        for s in service:
            b = _service_base(s)
            if b:
                return b
        return None
    if isinstance(service, dict):
        # heuristic: an Image API service has @id/id and a profile mentioning image
        base = service.get("@id") or service.get("id")
        prof = _txt(service.get("profile") or service.get("@type") or service.get("type"))
        if base and ("image" in (prof or "").lower() or "/iiif/" in base or True):
            return base.rstrip("/")
    return None


def _iter_images(manifest):
    """Yield dicts {label, image_id, service_base, width, height} for each canvas.

    Handles IIIF Presentation v2 (sequences/canvases/images/resource) and
    v3 (items/canvas/items/AnnotationPage/items/Annotation/body).
    """
    # ---- v2 ----
    for seq in manifest.get("sequences", []) or []:
        for canvas in seq.get("canvases", []) or []:
            label = _txt(canvas.get("label"))
            for img in canvas.get("images", []) or []:
                res = img.get("resource", {}) or {}
                yield {
                    "label": label,
                    "image_id": res.get("@id") or res.get("id"),
                    "service_base": _service_base(res.get("service")),
                    "width": res.get("width") or canvas.get("width"),
                    "height": res.get("height") or canvas.get("height"),
                }
    # ---- v3 ----
    for canvas in manifest.get("items", []) or []:
        if canvas.get("type") not in ("Canvas", None):
            continue
        label = _txt(canvas.get("label"))
        for page in canvas.get("items", []) or []:
            for anno in page.get("items", []) or []:
                body = anno.get("body", {}) or {}
                if isinstance(body, list):
                    body = body[0] if body else {}
                yield {
                    "label": label,
                    "image_id": body.get("id") or body.get("@id"),
                    "service_base": _service_base(body.get("service")),
                    "width": body.get("width") or canvas.get("width"),
                    "height": body.get("height") or canvas.get("height"),
                }


def _derivative_url(img, size):
    """Build a IIIF Image API URL for a given size, e.g. size='!600,' .

    Falls back to the plain image_id if there is no Image API service."""
    base = img.get("service_base")
    if base:
        return f"{base}/full/{size}/0/default.jpg"
    return img.get("image_id")


def cmd_manifest(args):
    manifest = _load_manifest(args)
    ctx = manifest.get("@context")
    version = "v3" if (isinstance(ctx, str) and "/3/" in ctx) or "items" in manifest else "v2"
    print(f"manifest : {_txt(manifest.get('label')) or '(no label)'}")
    print(f"  iiif   : {version}  context={ctx}")
    images = list(_iter_images(manifest))
    print(f"  canvases/images: {len(images)}")
    print()

    cover_first = sorted(
        range(len(images)),
        key=lambda i: (0 if re.search(r"cover|exterior|front", images[i]["label"], re.I)
                       else 1, i),
    )
    shown = 0
    for idx in cover_first:
        if args.limit and shown >= args.limit:
            print(f"... ({len(images) - shown} more; raise --limit to see them)")
            break
        img = images[idx]
        url = _derivative_url(img, args.size)
        print(f"[{idx}] label: {img['label'] or '(none)'}")
        print(f"     declared size: {img.get('width')}x{img.get('height')}")
        print(f"     service base : {img.get('service_base') or '(none -- using image id)'}")
        print(f"     derivative   : {url}")
        if url and not args.no_validate:
            status, final, hdrs, body = _request(url, max_bytes=200_000)
            ct = hdrs.get("Content-Type", "")
            dims = image_dims(body) if status == 200 else None
            ok = status == 200 and ct.startswith("image/")
            cors = hdrs.get("Access-Control-Allow-Origin", "")
            print(f"     validate     : HTTP {status}  {ct}  "
                  f"dims={dims}  CORS={cors or '(none)'}  {'OK' if ok else 'FAIL'}")
        print()
        shown += 1


# --------------------------------------------------------------------------- #
# marc
# --------------------------------------------------------------------------- #
def _records():
    tree = ET.parse(MARC_XML)
    for rec in tree.findall(f"{M}record"):
        cf = rec.find(f'{M}controlfield[@tag="001"]')
        rid = (cf.text or "").strip() if cf is not None else ""
        links = []
        for df in rec.findall(f'{M}datafield[@tag="856"]'):
            u = three = None
            for sf in df:
                if sf.get("code") == "u":
                    u = (sf.text or "").strip()
                elif sf.get("code") == "3":
                    three = (sf.text or "").strip()
            if u and "artstor" in u.lower():
                links.append((u, three or ""))
        yield rid, links


def cmd_marc(args):
    want = set(args.records) if args.records else None
    n_rec = n_link = 0
    for rid, links in _records():
        if want is not None and rid not in want:
            continue
        if not links:
            continue
        n_rec += 1
        print(f"record {rid}:")
        for u, three in links:
            n_link += 1
            tag = "COVER" if re.search(r"cover|exterior", three, re.I) else "     "
            print(f"  [{tag}] {three or '(no $3 description)'}")
            print(f"          {u}")
        print()
    print(f"-- {n_rec} record(s), {n_link} artstor link(s)")


# --------------------------------------------------------------------------- #
def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("resolve", help="follow an Artstor link, report the JSTOR community id")
    r.add_argument("urls", nargs="*", help="Artstor/JSTOR URLs")
    r.add_argument("--marc", dest="marc_id",
                   help="instead of URLs, resolve the first artstor link of this 001 record")
    r.set_defaults(func=_resolve_dispatch)

    m = sub.add_parser("manifest", help="parse a IIIF manifest and validate image URLs")
    m.add_argument("source", nargs="?", help="manifest URL")
    m.add_argument("--manifest-file", help="read manifest JSON from a file (or - for stdin)")
    m.add_argument("--size", default="!600,",
                   help="IIIF size segment for the derivative (default '!600,')")
    m.add_argument("--limit", type=int, default=5, help="max images to show (0 = all)")
    m.add_argument("--no-validate", action="store_true", help="don't HTTP-fetch the derivatives")
    m.set_defaults(func=cmd_manifest)

    mc = sub.add_parser("marc", help="list artstor 856 links from the MARC XML")
    mc.add_argument("records", nargs="*", help="001 control numbers (default: all)")
    mc.set_defaults(func=cmd_marc)

    args = p.parse_args()
    args.func(args)


def _resolve_dispatch(args):
    if args.marc_id:
        for rid, links in _records():
            if rid == args.marc_id:
                if not links:
                    sys.exit(f"record {rid} has no artstor links")
                args.urls = [links[0][0]]
                break
        else:
            sys.exit(f"record {args.marc_id} not found")
    if not args.urls:
        sys.exit("resolve: give one or more URLs, or --marc <001>")
    cmd_resolve(args)


if __name__ == "__main__":
    main()
