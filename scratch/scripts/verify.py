import json, subprocess, time, sys

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36")
BASE = "https://www.jstor.org"
SSIDS = ["14183099", "518143", "21000829", "639234", "14631054", "25487918"]


def curl(url, out=None, head=False):
    args = ["curl", "-sS", "-A", UA, "-H", "Cookie: x=y",
            "-w", "%{http_code}\t%{content_type}\t%{size_download}\t%{time_total}"]
    args += ["-o", out or "/dev/null"]
    args.append(url)
    r = subprocess.run(args, capture_output=True, text=True)
    parts = r.stdout.strip().split("\t")
    return {"code": parts[0], "ct": parts[1], "size": int(parts[2] or 0), "t": float(parts[3] or 0)}


rows = []
for ssid in SSIDS:
    rec = {"ssid": ssid}
    m = curl(f"{BASE}/content-service/content-data/community.{ssid}", out="cd.json")
    rec["meta_http"] = m["code"]
    rec["meta_ms"] = round(m["t"] * 1000)
    if m["code"] != "200":
        rows.append(rec); continue
    c = json.load(open("cd.json"))["content"]
    links = c.get("iiifLinks") or []
    rec["title"] = c.get("displayTitle")
    rec["pageCount"] = c.get("pageCount")
    rec["pageNames"] = c.get("pageNames")
    rec["n_iiif"] = len(links)
    fn = [x for x in c.get("metadata", []) if x["label"] == "File Name"]
    rec["fileNames"] = fn[0]["value"] if fn else None
    ss = [x for x in c.get("metadata", []) if x["label"] == "SSID"]
    rec["ssid_echo"] = ss[0]["value"] if ss else None
    if not links:
        rows.append(rec); continue
    rec["id0"] = links[0]
    info = curl(f"{BASE}{links[0]}/info.json", out="info.json")
    rec["info_http"] = info["code"]
    rec["info_ms"] = round(info["t"] * 1000)
    if info["code"] == "200":
        try:
            j = json.load(open("info.json"))
            rec["wh"] = f'{j["width"]}x{j["height"]}'
            rec["info_id"] = j.get("@id")
        except Exception as e:
            rec["info_err"] = str(e)[:60]
    img = curl(f"{BASE}{links[0]}/full/!1200,1200/0/default.jpg", out=f"img-{ssid}.jpg")
    rec["img_http"] = img["code"]
    rec["img_ct"] = img["ct"]
    rec["img_bytes"] = img["size"]
    rec["img_ms"] = round(img["t"] * 1000)
    rows.append(rec)
    time.sleep(0.5)

json.dump(rows, open("verify.json", "w"), indent=1)
for r in rows:
    print(json.dumps(r, ensure_ascii=False))
