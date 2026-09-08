import subprocess, time, datetime
UA=("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36")
t0=time.time()
while time.time()-t0 < 5400:
    r=subprocess.run(['curl','-sS','-o','/dev/null','-w','%{http_code}','-A',UA,
                      '-H','Cookie: x=y',
                      'https://www.jstor.org/content-service/content-data/community.14183099'],
                     capture_output=True,text=True)
    code=r.stdout.strip()
    print(f"{datetime.datetime.now():%H:%M:%S} elapsed={int(time.time()-t0)}s http={code}", flush=True)
    if code=='200':
        print("UNBLOCKED", flush=True); break
    time.sleep(90)
