import json, subprocess, time

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36")
BASE = "https://www.jstor.org"
SSIDS = ["14183099", "518143", "21000829", "639234", "14631054", "25487918"]


def curl(url, out="/dev/null", headers=True):
    args = ["curl", "-sS", "-w", "%{http_code}\t%{content_type}\t%{size_download}\t%{time_total}",
            "-o", out]
    if headers:
        args += ["-A", UA, "-H", "Cookie: x=y"]
    r = subprocess.run(args + [url], capture_output=True, text=True)
    p = r.stdout.strip().split("\t")
    return {"code": p[0], "ct": p[1], "size": int(p[2] or 0), "t": float(p[3] or 0)}


def meta(ssid):
    """Fetch content-data with exponential backoff on 403."""
    delay = 100
    for attempt in range(4):
        m = curl(f"{BASE}/content-service/content-data/community.{ssid}", out="cd.json")
        if m["code"] == "200":
            return json.load(open("cd.json"))["content"], attempt
        time.sleep(delay)
        delay *= 2
    return None, -1


rows = []
for ssid in SSIDS:
    rec = {"ssid": ssid}
    c, tries = meta(ssid)
    rec["meta_retries"] = tries
    if c is None:
        rec["meta"] = "BLOCKED"
        rows.append(rec)
        print(json.dumps(rec), flush=True)
        continue
    links = c.get("iiifLinks") or []
    rec["title"] = c.get("displayTitle")
    rec["pageCount"] = c.get("pageCount")
    rec["pageNames"] = c.get("pageNames")
    rec["n_iiif"] = len(links)
    md = {x["label"]: x["value"] for x in c.get("metadata", [])}
    rec["fileName"] = md.get("File Name")
    rec["ssid_echo"] = md.get("SSID")
    rec["imgViewDesc"] = md.get("Image View Description")
    rec["links"] = links
    if links:
        rec["id0"] = links[0]
        # IIIF fetched with NO headers at all, to prove it is open
        info = curl(f"{BASE}{links[0]}/info.json", out="info.json", headers=False)
        rec["info_http"] = info["code"]
        rec["info_ms"] = round(info["t"] * 1000)
        if info["code"] == "200":
            j = json.load(open("info.json"))
            rec["wh"] = f'{j["width"]}x{j["height"]}'
            rec["info_at_id"] = j.get("@id")
        img = curl(f"{BASE}{links[0]}/full/!1200,1200/0/default.jpg",
                   out=f"img-{ssid}.jpg", headers=False)
        rec["img_http"] = img["code"]
        rec["img_ct"] = img["ct"]
        rec["img_bytes"] = img["size"]
        rec["img_ms"] = round(img["t"] * 1000)
    rows.append(rec)
    print(json.dumps(rec, ensure_ascii=False), flush=True)
    time.sleep(8)

json.dump(rows, open("verify2.json", "w"), indent=1)
print("DONE")
