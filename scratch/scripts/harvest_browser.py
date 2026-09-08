import json, sys
from playwright.sync_api import sync_playwright

SSIDS = sys.argv[1:] or ["14183099", "518143", "21000829", "639234", "14631054", "25487918"]
out = {}

with sync_playwright() as p:
    b = p.chromium.launch(headless=False, channel="chrome",
                          args=["--disable-blink-features=AutomationControlled"])
    ctx = b.new_context(viewport={"width": 1280, "height": 900})
    page = ctx.new_page()
    # one real page load to clear the JS challenge and mint cookies
    page.goto("https://www.jstor.org/stable/community.%s" % SSIDS[0],
              wait_until="domcontentloaded", timeout=90000)
    page.wait_for_timeout(12000)

    for ssid in SSIDS:
        try:
            r = page.evaluate(
                """async (ssid) => {
                    const res = await fetch('/content-service/content-data/community.' + ssid,
                                            {credentials: 'include'});
                    return {status: res.status, body: await res.text()};
                }""", ssid)
            if r["status"] == 200:
                out[ssid] = json.loads(r["body"])["content"]
                print(ssid, "OK", flush=True)
            else:
                out[ssid] = {"_status": r["status"]}
                print(ssid, "HTTP", r["status"], flush=True)
        except Exception as e:
            print(ssid, "ERR", str(e)[:100], flush=True)
        page.wait_for_timeout(3000)
    b.close()

json.dump(out, open("browser-meta.json", "w"), indent=1)
print("saved browser-meta.json")
