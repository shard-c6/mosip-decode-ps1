#!/usr/bin/env python3
"""
Build an openid4vp:// authorization request URI from Inji Verify's
/v1/verify/vp-session-request response (pre_registered / inline mode),
for pasting into the OpenID Foundation conformance suite verifier plans.

Usage:
    python3 build-oid4vp-uri.py response.json
    pbpaste | python3 build-oid4vp-uri.py
"""
import sys, json, time
from urllib.parse import urlencode

raw = open(sys.argv[1]).read() if len(sys.argv) > 1 else sys.stdin.read()
doc = json.loads(raw)

ad = doc.get("authorizationDetails")
if not ad:
    sys.exit("ERROR: no 'authorizationDetails'. This looks like a 'did' "
             "(by-reference) response; expected pre_registered/inline.")

exp = doc.get("expiresAt")
if exp:
    left = exp / 1000 - time.time()
    print(f"# request expires in {left:.0f}s", file=sys.stderr)
    if left <= 0:
        print("# WARNING: ALREADY EXPIRED - regenerate in the UI", file=sys.stderr)

params = {
    "client_id":               ad["clientId"],
    "response_type":           ad.get("responseType", "vp_token"),
    "response_mode":           ad.get("responseMode", "direct_post"),
    "response_uri":            ad["responseUri"],
    "nonce":                   ad["nonce"],
    "presentation_definition": json.dumps(ad["presentationDefinition"],
                                          separators=(",", ":")),
    "state":                   doc.get("requestId", ""),
}
print("openid4vp://?" + urlencode(params))
