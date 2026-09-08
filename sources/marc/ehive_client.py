#!/usr/bin/env python3
"""eHive API v2 client: the OAuth2-flavoured authorization dance plus GET helpers.

Why its own module: eHive is the only source in the MARC track behind
credentials, and its handshake is idiosyncratic enough to be worth isolating from
marc_harvest.py, which otherwise knows only "issue a query, get records back".
The harvester's run_ehive() uses get_json() and never sees a token.

The flow (three legs, all driven by *headers* rather than a form body):

  1. POST /api/oauth2/v2/authorize   Client-Id + Client-Secret
     -> 303 See Other, with the access grant in an **Access-Grant response
        header**. This is the trap: urllib follows a 303 by default, chasing
        Location: /api/oauth2/v2/token as a plain GET with none of the required
        headers, and the grant is lost with it. _NoRedirect below turns the 303
        into an HTTPError we can read the headers off instead.
  2. GET  /api/oauth2/v2/token       Client-Id + Access-Grant
     -> 200 {"clientId":…, "oauthToken":…, "grantType":"API"}
  3. GET  /api/v2/<method>?trackingId=…   Client-Id + Authorization: Basic <token>

The token expires on a fixed clock, after which eHive answers 401; get_json()
re-authorizes once and retries, so a long harvest doesn't die at the token's
lifetime boundary.

Credentials come from the environment, never from the repo -- eHive's own docs
call these secrets, and sources/ is committed:

    EHIVE_CLIENT_ID, EHIVE_CLIENT_SECRET, EHIVE_TRACKING_ID

Generated at Edit My Profile > API Keys in the eHive account. Probe the
connection (and discover an account's shape) with:

    python3 marc/ehive_client.py --account 3406
    python3 marc/ehive_client.py --path /api/v2/accounts/3406/objects
"""

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

BASE = "https://ehive.com"
AUTHORIZE = f"{BASE}/api/oauth2/v2/authorize"
TOKEN = f"{BASE}/api/oauth2/v2/token"

TIMEOUT = 30


class EHiveError(RuntimeError):
    pass


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """Surface 3xx as an HTTPError rather than following it.

    The authorize leg answers 303 with the access grant in a response header;
    following the redirect would discard it (and hit the token endpoint without
    the Client-Id/Access-Grant headers it needs)."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


_opener = urllib.request.build_opener(_NoRedirect)


def _request(url, headers, method="GET", data=None):
    req = urllib.request.Request(url, data=data, method=method)
    for k, v in headers.items():
        req.add_header(k, v)
    return _opener.open(req, timeout=TIMEOUT)


def credentials():
    """(clientId, clientSecret, trackingId) from the environment."""
    keys = ("EHIVE_CLIENT_ID", "EHIVE_CLIENT_SECRET", "EHIVE_TRACKING_ID")
    vals = [os.environ.get(k, "").strip() for k in keys]
    missing = [k for k, v in zip(keys, vals) if not v]
    if missing:
        raise EHiveError(
            "missing eHive credentials in the environment: " + ", ".join(missing)
            + "\n(generate them at Edit My Profile > API Keys, then export them;"
            " they must not be written into the repo)")
    return tuple(vals)


def authorize(client_id, client_secret):
    """Legs 1 and 2: authorization credentials -> access grant -> OAuth token."""
    try:
        resp = _request(AUTHORIZE, {
            "Content-Type": "application/x-www-form-urlencoded",
            "Client-Id": client_id,
            "Client-Secret": client_secret,
            "Authorization": "OAuth",
            "Grant-Type": "client_credentials",
        }, method="POST", data=b"")
        # A 2xx here means the server did not issue the expected 303 redirect.
        grant = resp.headers.get("Access-Grant")
        if not grant:
            raise EHiveError(
                f"authorize returned {resp.status} with no Access-Grant header "
                "(expected 303 See Other)")
    except urllib.error.HTTPError as e:
        if e.code not in (301, 302, 303, 307, 308):
            raise EHiveError(f"authorize failed: HTTP {e.code} {e.reason}") from e
        grant = e.headers.get("Access-Grant")
        if not grant:
            raise EHiveError(
                f"authorize returned {e.code} but no Access-Grant header; "
                f"headers were: {dict(e.headers)}") from e

    try:
        resp = _request(TOKEN, {
            "Content-Type": "application/x-www-form-urlencoded",
            "Client-Id": client_id,
            "Access-Grant": grant,
            "Connection": "keep-alive",
            "Authorization": "OAuth",
            "Grant-Type": "authorization_code",
        })
        payload = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raise EHiveError(f"token request failed: HTTP {e.code} {e.reason}") from e

    token = payload.get("oauthToken")
    if not token:
        raise EHiveError(f"token endpoint returned no oauthToken: {payload}")
    return token


class Session:
    """An authorized eHive session that re-authorizes when its token expires."""

    def __init__(self, qsleep=0.0):
        self.client_id, self._secret, self.tracking_id = credentials()
        self.qsleep = qsleep
        self.token = None
        self.calls = 0

    def _auth(self):
        self.token = authorize(self.client_id, self._secret)
        return self.token

    def get_json(self, path, params=None, _retried=False):
        """GET an API method, returning parsed JSON. path is like
        "/api/v2/accounts/3406" or a full URL; trackingId is added for you."""
        if self.token is None:
            self._auth()
        url = path if path.startswith("http") else BASE + path
        query = dict(params or {})
        query["trackingId"] = self.tracking_id
        url = f"{url}?{urllib.parse.urlencode(query)}"
        try:
            resp = _request(url, {
                "Client-Id": self.client_id,
                "Authorization": f"Basic {self.token}",
                "Grant-Type": "authorization_code",
            })
            body = resp.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            # 401 = the token aged out mid-harvest; re-authorize once and retry.
            if e.code == 401 and not _retried:
                self._auth()
                return self.get_json(path, params, _retried=True)
            raise EHiveError(f"GET {path} failed: HTTP {e.code} {e.reason}") from e
        finally:
            self.calls += 1
            if self.qsleep:
                time.sleep(self.qsleep)
        return json.loads(body)


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--account", help="probe /api/v2/accounts/<id>")
    g.add_argument("--path", help="probe an arbitrary API path")
    ap.add_argument("--param", action="append", default=[], metavar="K=V",
                    help="extra query parameter (repeatable)")
    args = ap.parse_args()

    params = dict(p.split("=", 1) for p in args.param)
    path = args.path or f"/api/v2/accounts/{args.account}"
    try:
        s = Session()
        print(f"authorized (clientId {s.client_id[:6]}…)", file=sys.stderr)
        print(json.dumps(s.get_json(path, params), indent=2)[:8000])
    except EHiveError as e:
        print(f"error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
