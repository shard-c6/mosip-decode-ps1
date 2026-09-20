# Runbook — starting, using and shutting down the stacks

Day-to-day operations. First-time install is in [SETUP.md](SETUP.md).

**Read the shutdown section before you start anything.** Leaving these containers running
eats memory and disk, and a half-stopped stack is the most common cause of "it worked
yesterday".

Commands are identical on macOS and Windows unless marked otherwise. On Windows use
**PowerShell**; on macOS use **Terminal**.

---

## Quick reference

| Goal | Command |
|---|---|
| Start conformance suite | `cd conformance-suite && docker compose -f docker-compose-prebuilt.yml up -d` |
| Start Inji Verify | `cd inji-verify/docker-compose && docker compose up -d` |
| Start tunnel | `ngrok http 3000` (leave running) |
| Stop one stack | `docker compose down` in that folder |
| Stop everything | see [Full shutdown](#full-shutdown) |
| Reclaim disk | see [Deep clean](#deep-clean-monthly-or-when-disk-is-tight) |

---

## Starting up

Do these in order. Paths assume `~/projects/MOSIP` (macOS) or `C:\projects\MOSIP` (Windows).

### 1. Start the tunnel first

```bash
ngrok http 3000
```

Leave this terminal tab open for the whole session — closing it kills the tunnel and
everything downstream breaks. Confirm the `Forwarding` line shows your static domain.

> If the `Forwarding` hostname is **not** the domain you configured in `docker-compose.yml`,
> stop and fix that before continuing, or Verify will advertise a DID nobody can resolve.

### 2. Start the conformance suite

```bash
cd ~/projects/MOSIP/conformance-suite
docker compose -f docker-compose-prebuilt.yml up -d
```

Three containers start: `mongodb`, `server`, `nginx`. The `-d` runs them in the background
so you keep your terminal.

Open <https://localhost.emobix.co.uk:8443> and accept the certificate warning. Your test
plans from previous sessions are still there — the suite stores them in a MongoDB volume
that survives restarts.

### 3. Start Inji Verify

```bash
cd ~/projects/MOSIP/inji-verify/docker-compose
docker compose up -d
```

Three containers: `verify-service`, `verify-ui`, `postgres-db`.

### 4. Confirm everything is healthy

```bash
docker compose ps                    # run in each folder; all should show "running"
curl -k https://localhost.emobix.co.uk:8443/api/currentuser
curl https://YOUR-DOMAIN.ngrok-free.dev/v1/verify/did.json
```

Both curls returning JSON means you are ready to test.

---

## Access points

| What | URL |
|---|---|
| Conformance suite | <https://localhost.emobix.co.uk:8443> |
| Conformance suite API docs | <https://localhost.emobix.co.uk:8443/swagger-ui/index.html> |
| Inji Verify UI (local) | <http://localhost:3000> |
| Inji Verify UI (public) | `https://YOUR-DOMAIN.ngrok-free.dev` |
| Inji Verify API docs | <http://localhost:8080/v1/verify/swagger-ui/index.html> |
| Verify DID document | `https://YOUR-DOMAIN.ngrok-free.dev/v1/verify/did.json` |
| ngrok inspector | <http://127.0.0.1:4040> |

The ngrok inspector is worth knowing about — it shows every request flowing through the
tunnel, which is invaluable when the conformance suite says it received something
unexpected.

---

## Watching logs

```bash
docker compose logs -f                    # everything in this stack
docker compose logs -f verify-service     # one container
docker compose logs --tail=50 verify-service
```

`Ctrl-C` stops the log view — it does **not** stop the container.

---

## Shutting down

### Stop for the day (keeps data)

In **each** stack folder:

```bash
cd ~/projects/MOSIP/inji-verify/docker-compose
docker compose down

cd ~/projects/MOSIP/conformance-suite
docker compose -f docker-compose-prebuilt.yml down
```

Then `Ctrl-C` the ngrok tab.

`down` stops and removes the containers and their network but **keeps the volumes**, so
your test plans, logs and database survive. This is what you want almost every time.

> **Note the `-f docker-compose-prebuilt.yml` on the conformance suite.** A plain
> `docker compose down` in that folder targets the default `docker-compose.yml` instead and
> will leave your containers running while telling you it found nothing. This is the single
> easiest mistake to make here.

### Full shutdown

Verify nothing is left behind:

```bash
docker ps
```

If that prints an empty table (headers only), you are clean. If containers are still
listed, stop them by name:

```bash
docker stop <container-name>
```

### Reset one stack to a clean slate

When a stack is misbehaving and you want it factory-fresh:

```bash
docker compose down -v
```

The `-v` **deletes the volumes too**. For Inji Verify that wipes its Postgres database
(harmless — it re-initialises). For the conformance suite that **deletes every test plan
and log you have ever run**. Export anything you care about first.

### Deep clean (monthly, or when disk is tight)

These images are large. To see what Docker is holding:

```bash
docker system df
```

To reclaim space safely — removes stopped containers, unused networks, dangling images and
build cache, but **keeps** volumes and images currently in use:

```bash
docker system prune
```

More aggressive — also removes images not used by a running container. You will re-download
several gigabytes next start:

```bash
docker system prune -a
```

> Do **not** run `docker system prune -a --volumes` unless you intend to destroy your
> conformance suite history.

---

## Running a conformance test

The full walkthrough is in the findings document's Reproduction section. In brief:

1. In the suite: create or open the plan, click **Run Test** on a module (it goes to WAITING).
2. In the Verify UI: **Request Verifiable Credentials** → select **Mock Identity (SD JWT)**.
3. In DevTools → Network, open the `vp-session-request` response and copy the JSON.
4. Build the URI to paste:

   **macOS**
   ```bash
   pbpaste | python3 scripts/build-oid4vp-uri.py
   ```
   **Windows**
   ```powershell
   Get-Clipboard | python scripts/build-oid4vp-uri.py
   ```

5. Paste the printed `openid4vp://...` line into the suite and submit.

**The request expires 300 seconds after it is issued.** The script prints a countdown; if
it warns the request is expired, regenerate from step 2. Check liveness before pasting:

```bash
curl -s -o /dev/null -w "%{http_code}\n" https://YOUR-DOMAIN.ngrok-free.dev/v1/verify/vp-request/REQ_ID
```

`200` means alive.

### Exporting results

From the test page in the suite, use **Download all Logs**, or via the API:

```bash
curl -k https://localhost.emobix.co.uk:8443/api/log/<testId> -o logs/<date>/<testname>-<testId>.json
```

Commit exported logs to `logs/<date>/`. They are our evidence.

---

## Troubleshooting

**"Failed to fetch status" toast in the Verify UI.** The UI long-polls
`/v1/verify/vp-request/{id}/status` for up to 55 seconds and something in the ngrok path
cuts it short. It does not affect request generation. It *may* prevent the UI from
displaying a success screen, which matters when a test wants a screenshot — in that case
read the result from the API instead.

**Suite reports a parameter it didn't expect, or a missing one.** Check the ngrok inspector
at <http://127.0.0.1:4040> to see exactly what left your machine, then compare against the
`incoming_query_string_params` block in the suite's log entry.

**DID document 404s.** The path is `/v1/verify/did.json` — no `.well-known`. The
`.well-known` form applies only to DIDs with no path segments; ours has `:v1:verify`.

**Containers start but Verify behaves as if unconfigured.** Environment variables are read
when a container is **created**, not when the file changes. After editing
`docker-compose.yml` you must `docker compose down` then `up -d`. A plain `restart` is not
enough.

**Changed `config/config.json` but the UI shows the old credentials.** That file is mounted
into the verify-ui container. `docker compose restart verify-ui`, then hard-reload the
browser (macOS `Cmd+Shift+R`, Windows `Ctrl+F5`).
