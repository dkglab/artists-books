import json, sys, re
from playwright.sync_api import sync_playwright

ssid = sys.argv[1] if len(sys.argv) > 1 else "25487918"
url = f"https://www.jstor.org/stable/community.{ssid}"

reqs = []
with sync_playwright() as p:
    b = p.chromium.launch(headless=False, channel="chrome", args=["--disable-blink-features=AutomationControlled"])
    ctx = b.new_context(
        user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36",
        viewport={"width": 1440, "height": 1000},
    )
    page = ctx.new_page()

    def on_resp(r):
        reqs.append({"status": r.status, "url": r.url, "ct": r.headers.get("content-type", "")})

    page.on("response", on_resp)
    page.goto(url, wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(12000)
    try:
        page.wait_for_load_state("networkidle", timeout=20000)
    except Exception:
        pass
    page.wait_for_timeout(5000)

    html = page.content()
    title = page.title()
    ctx.storage_state(path=f"state.json")
    b.close()

open(f"page-{ssid}.html", "w").write(html)
print("TITLE:", title)
print("=== interesting responses ===")
for r in reqs:
    u = r["url"]
    if re.search(r"iiif|info\.json|manifest|/api/|tile|\.jpg|\.jpeg|\.png|media|asset|image", u, re.I):
        print(r["status"], r["ct"][:40], u[:220])
print("=== total responses:", len(reqs))
json.dump(reqs, open(f"reqs-{ssid}.json", "w"), indent=1)
