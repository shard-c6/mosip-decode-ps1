---
description: Start ngrok, the conformance suite and Inji Verify, then verify health
---

Bring the conformance testing environment up, in order. Report what you did and the health
check results; do not start running tests.

**1. ngrok** — this one the user must run themselves, in its own terminal tab that stays
open. Remind them, then wait for confirmation that the `Forwarding` line shows
`sphere-dust-sandlot.ngrok-free.dev`:

```
ngrok http 3000
```

If the forwarding hostname differs from the one in
`inji-verify/docker-compose/docker-compose.yml`, stop and say so — Verify would advertise a
DID nobody can resolve.

**2. Conformance suite**

```
cd ~/projects/MOSIP/conformance-suite
docker compose -f docker-compose-prebuilt.yml up -d
```

**3. Inji Verify**

```
cd ~/projects/MOSIP/inji-verify/docker-compose
docker compose up -d
```

**4. Health check** — both must return JSON:

```
curl -k https://localhost.emobix.co.uk:8443/api/currentuser
curl https://sphere-dust-sandlot.ngrok-free.dev/v1/verify/did.json
```

If the DID call 404s, the path is `/v1/verify/did.json` — no `.well-known`. If it times
out, ngrok is down. If containers are up but Verify behaves as though unconfigured, the env
vars were read at creation time: `down` then `up -d`, not `restart`.
