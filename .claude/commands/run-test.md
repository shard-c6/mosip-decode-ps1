---
description: Walk through running one conformance test module end to end
argument-hint: [module name, e.g. oid4vp-1final-verifier-invalid-sd-hash]
---

Guide the user through running conformance module **$1** (ask which one if not given).
These tests are interactive — the suite waits for the verifier to initiate — so you
coordinate, the user clicks.

Run `/health-check` first if the environment state is unknown.

**1. Arm the test.** User: in the suite, open the plan (`lN7C4DH1HvYmc`) and click
**Run Test** on the module, or **Repeat Test** if it has already run. Wait until it shows
WAITING with a paste box. Nothing expires on this side.

**2. Generate a request.** User: in the Verify UI, clear the DevTools Network panel, click
**Request Verifiable Credentials**, and select **Mock Identity (SD JWT)** — the only
credential configured for `sd_jwt_vc` and `pre_registered`. Then copy the
`vp-session-request` response JSON from the Network panel.

The 300-second clock starts here.

**3. Build the URI.** From the repo root:

```
pbpaste | python3 scripts/build-oid4vp-uri.py          # macOS
Get-Clipboard | python scripts/build-oid4vp-uri.py     # Windows
```

It prints an expiry countdown on stderr and the `openid4vp://...` line on stdout. If it
says already expired, go back to step 2 — don't paste a dead request, it produces a
misleading `ExtractNonceFromAuthorizationRequest` failure that looks like a Verify defect
and isn't.

**4. Submit.** User pastes the URI into the suite and submits.

**5. Export the log.**

```
curl -k https://localhost.emobix.co.uk:8443/api/log/<testId> \
  -o logs/$(date +%Y-%m-%d)/<module>-<testId>.json
```

Also download the `.sig` from the suite UI and commit both.

**6. Analyse.** Run `/analyse-log` on the exported file, add the row to the index table in
`logs/README.md`, and append anything new to `docs/findings/findings.tex`.

**Expected outcome for any module in the 1.0 Final plan**: interruption at
`ExtractDCQLQueryFromAuthorizationRequest`. That uniformity is the result, not a problem.
Anything that gets *past* that point is genuinely interesting — say so loudly.
