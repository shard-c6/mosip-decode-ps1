---
description: Shut down all stacks cleanly without destroying data
---

Shut everything down so nothing holds ports or state into the next session.

```
cd ~/projects/MOSIP/inji-verify/docker-compose
docker compose down

cd ~/projects/MOSIP/conformance-suite
docker compose -f docker-compose-prebuilt.yml down
```

Then remind the user to `Ctrl-C` the ngrok tab.

Confirm clean with `docker ps` — an empty table means ports 3000, 8080, 5432, 8443 and 8444
are free.

**Never add `-v`.** `docker compose down -v` deletes volumes; on the conformance suite that
destroys every test plan and log ever run. If the user explicitly asks for a full reset,
confirm they understand that before proceeding.

**The `-f docker-compose-prebuilt.yml` flag is required** on the suite. Without it the
command targets the default compose file, reports success, and leaves all three containers
running.

If containers remain after `down`, stop by name — Verify's are fixed in its compose file:
`docker stop verify-service verify-ui postgres-db`
