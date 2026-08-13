import json, sys, os, re
from playwright.sync_api import sync_playwright

ssid = sys.argv[1]
url = f"https://www.jstor.org/stable/community.{ssid}"
outdir = f"cap-{ssid}"
os.makedirs(outdir, exist_ok=True)

log = []

with sync_playwright() as p:
    b = p.chromium.launch(headless=False, channel="chrome",
                          args=["--disable-blink-features=AutomationControlled"])
    ctx = b.new_context(viewport={"width": 1440, "height": 1100})
    page = ctx.new_page()

    def on_resp(r):
        e = {"status": r.status, "url": r.url, "ct": r.headers.get("content-type", ""),
             "method": r.request.method, "type": r.request.resource_type}
        log.append(e)
        u = r.url
        if r.request.resource_type in ("xhr", "fetch") or "__data.json" in u:
            try:
                body = r.text()
                e["body_len"] = len(body)
                fn = re.sub(r"[^A-Za-z0-9._-]", "_", u.split("://", 1)[-1])[:150]
                open(f"{outdir}/{fn}.txt", "w").write(body[:400000])
            except Exception as ex:
                e["body_err"] = str(ex)[:80]

    page.on("response", on_resp)
    page.goto(url, wait_until="domcontentloaded", timeout=90000)
    page.wait_for_timeout(15000)
    try:
        page.wait_for_load_state("networkidle", timeout=25000)
    except Exception:
        pass
    # scroll to trigger lazy viewer
    for _ in range(4):
        page.mouse.wheel(0, 900)
        page.wait_for_timeout(1500)
    page.wait_for_timeout(4000)
    page.screenshot(path=f"{outdir}/shot.png", full_page=False)
    open(f"{outdir}/page.html", "w").write(page.content())
    ctx.storage_state(path=f"{outdir}/state.json")
    b.close()

json.dump(log, open(f"{outdir}/log.json", "w"), indent=1)
print("responses:", len(log))
for e in log:
    if e["type"] in ("xhr", "fetch") or re.search(r"artstor|sequoia|iiif|cirrostratus|\.jpg|\.jpeg|\.png|\.tif", e["url"], re.I):
        print(e["status"], e["type"], e["url"][:190])
