import csv, json, subprocess, time, sys, random

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36")
CSV = "/Users/ryanshaw/Code/artists-books/sources/artstor-ssid.csv"

gap = float(sys.argv[1])
n = int(sys.argv[2])

rows = [r for r in csv.DictReader(open(CSV)) if r["ssid"]]
random.seed(7)
sample = random.sample(rows, n)

ok, first_403_at, results = 0, None, []
t0 = time.time()
for i, r in enumerate(sample, 1):
    ssid = r["ssid"]
    p = subprocess.run(
        ["curl", "-sS", "-A", UA, "-H", "Cookie: x=y", "-o", "rt.json",
         "-w", "%{http_code}",
         f"https://www.jstor.org/content-service/content-data/community.{ssid}"],
        capture_output=True, text=True).stdout.strip()
    if p == "200":
        ok += 1
        c = json.load(open("rt.json"))["content"]
        md = {x["label"]: x["value"] for x in c.get("metadata", [])}
        results.append({
            "ssid": ssid, "key": r["canonicalKey"], "title": c.get("displayTitle"),
            "pageCount": c.get("pageCount"), "n_iiif": len(c.get("iiifLinks") or []),
            "fileName": (md.get("File Name") or [None])[0],
            "view": (md.get("Image View Description") or [None])[0],
            "links": c.get("iiifLinks"),
        })
    else:
        if first_403_at is None:
            first_403_at = i
        results.append({"ssid": ssid, "http": p})
    time.sleep(gap)

el = time.time() - t0
print(f"gap={gap}s n={n} ok={ok} first_non200_at_request={first_403_at} elapsed={el:.0f}s rate={n/el:.2f}/s")
json.dump(results, open(f"ratetest-{gap}.json", "w"), indent=1)
