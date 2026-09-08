#!/usr/bin/env bash
# Does this host's egress IP work for the issue-9 SSID -> IIIF harvest?
#
# Run on the candidate harvester host (fly.io sprite, CI runner, laptop).
# Makes 3 requests total, so it will not trip the rate limiter.
#
# Distinguishes the three failure modes, which look nothing alike:
#   200                     -> usable
#   403 "Access Check"      -> rate limited (temporary; back off, retry later)
#   200 "Client Challenge"  -> Fastly JS challenge = IP reputation block (fatal for curl)

set -u

UA='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36'
SSID=14183099
IIIF='/iiif/2016/04/29/16/e31d56f8-4cf7-4053-a74b-033fcb088b79_deflate.tif'
TMP=$(mktemp)
trap 'rm -f "$TMP"' EXIT

classify() {
  local code=$1 file=$2
  if grep -q 'Client Challenge' "$file" 2>/dev/null; then
    echo "JS CHALLENGE (IP reputation block)"
  elif grep -q 'Access Check' "$file" 2>/dev/null; then
    echo "RATE LIMITED (temporary)"
  elif [ "$code" = 200 ]; then
    echo "OK"
  else
    echo "unexpected http=$code"
  fi
}

echo "== 1. metadata API (needs browser UA + any cookie)"
code=$(curl -sS -A "$UA" -H 'Cookie: x=y' -o "$TMP" -w '%{http_code}' \
  "https://www.jstor.org/content-service/content-data/community.$SSID")
printf '   http=%s  %s\n' "$code" "$(classify "$code" "$TMP")"
if [ "$code" = 200 ]; then
  printf '   iiifLinks: %s\n' \
    "$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))["content"]["iiifLinks"])' "$TMP" 2>/dev/null)"
fi

echo "== 2. IIIF info.json (no headers at all)"
code=$(curl -sS -o "$TMP" -w '%{http_code}' "https://www.jstor.org$IIIF/info.json")
printf '   http=%s  %s\n' "$code" "$(classify "$code" "$TMP")"

echo "== 3. IIIF image bytes (no headers at all)"
read -r code ctype bytes <<<"$(curl -sS -o /dev/null \
  -w '%{http_code} %{content_type} %{size_download}' "https://www.jstor.org$IIIF/full/,400/0/default.jpg")"
printf '   http=%s type=%s bytes=%s\n' "$code" "$ctype" "$bytes"

cat <<'EOF'

Interpretation:
  1 OK                  -> harvest can run here.
  1 RATE LIMITED        -> inconclusive, this IP is in a cooldown. Wait 10+ min
                           (do NOT keep probing, that extends the block) and rerun.
  1 JS CHALLENGE        -> this egress IP cannot run the harvest with plain curl.
                           Harvest from a residential IP instead and commit the CSV.
  2 and 3 should be OK on any host. If they are, the *build* can run here
  regardless of what step 1 says -- only the one-time harvest needs step 1.
EOF
