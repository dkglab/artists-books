import json, os, re, sys
from playwright.sync_api import sync_playwright

url = sys.argv[1] if len(sys.argv) > 1 else "https://www.jstor.org/site/unc-chapel-hill/artists-books/"
outdir = "cap-browse"
os.makedirs(outdir, exist_ok=True)
log = []

with sync_playwright() as p:
    b = p.chromium.launch(headless=False, channel="chrome",
                          args=["--disable-blink-features=AutomationControlled"])
    ctx = b.new_context(viewport={"width": 1440, "height": 1100})
    page = ctx.new_page()

    def on_resp(r):
        e = {"status": r.status, "url": r.url, "type": r.request.resource_type,
             "method": r.request.method}
        log.append(e)
        if r.request.resource_type in ("xhr", "fetch"):
            try:
                body = r.text()
                e["len"] = len(body)
                e["post"] = (r.request.post_data or "")[:2000]
                fn = re.sub(r"[^A-Za-z0-9._-]", "_", r.url.split("://", 1)[-1])[:140]
                open(f"{outdir}/{fn}.txt", "w").write(body[:600000])
            except Exception:
                pass

    page.on("response", on_resp)
    page.goto(url, wait_until="domcontentloaded", timeout=90000)
    page.wait_for_timeout(15000)
    for _ in range(5):
        page.mouse.wheel(0, 1200)
        page.wait_for_timeout(2000)
    page.screenshot(path=f"{outdir}/shot.png")
    open(f"{outdir}/page.html", "w").write(page.content())
    b.close()

json.dump(log, open(f"{outdir}/log.json", "w"), indent=1)
for e in log:
    if e["type"] in ("xhr", "fetch") and "google" not in e["url"] and "cookielaw" not in e["url"]:
        print(e["status"], e["method"], e["url"][:170], "len=", e.get("len"))
