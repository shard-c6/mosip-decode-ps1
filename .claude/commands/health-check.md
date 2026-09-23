---
description: Verify the environment is running correctly before testing
---

Check the environment end to end and report a short pass/fail summary. Run these and
interpret the results — don't just dump output.

```
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
curl -k -s https://localhost.emobix.co.uk:8443/api/currentuser
curl -s https://sphere-dust-sandlot.ngrok-free.dev/v1/verify/did.json
```

Expected:

- **Six containers running**: `mongodb`, `server`, `nginx` (suite); `verify-service`,
  `verify-ui`, `postgres-db` (Verify)
- **`/api/currentuser`** returns JSON with `"displayName":"DEVMODE@developer.com"`
- **`did.json`** returns a DID document with `@context`, an `id` matching
  `did:web:<host>:v1:verify`, and a `verificationMethod` carrying an Ed25519 public key

Diagnosis when something fails:

| Symptom | Likely cause |
|---|---|
| DID call times out | ngrok tunnel is down — check its tab |
| DID call 404s | wrong path; it's `/v1/verify/did.json`, no `.well-known` |
| Suite unreachable | suite containers not up, or you skipped `-f docker-compose-prebuilt.yml` on a previous `down` |
| Verify up but misconfigured | env vars read at creation — `down` then `up -d`, not `restart` |
| Wrong hostname in DID | `docker-compose.yml` points at a different ngrok domain than the live tunnel |

Also check `docker-compose.yml` still has the ngrok hostname in all five places and no
remaining `VERIFY_SERVICE_PROXY_FOR_LOCALHOST` placeholder.
