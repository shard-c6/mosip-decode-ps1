# Troubleshooting

Problems we actually hit with the Compose stack, the runner and the api-testrig classes, and
what fixes them. For first-time install of Docker, ngrok and the clones see
[SETUP.md](SETUP.md) sections 1–4; the stack itself is in [ARCHITECTURE.md](ARCHITECTURE.md).

Quick health check, with the stack up:

```bash
scripts/stack.sh status
curl -sk -o /dev/null -w "%{http_code} suite\n"   https://localhost.emobix.co.uk:8443/api/currentuser
curl -s  -o /dev/null -w "%{http_code} verify\n"  http://localhost:8080/v1/verify/did.json
curl -s  -o /dev/null -w "%{http_code} certify\n" http://localhost:8090/v1/certify/.well-known/openid-credential-issuer
curl -s  -o /dev/null -w "%{http_code} public\n"  -H "ngrok-skip-browser-warning: 1" https://$PUBLIC_HOST/v1/verify/actuator/health
```

All should print 200.

---

## Bringing the stack up

| Symptom | Cause | Fix |
|---|---|---|
| `docker/.env not found` | Settings missing | `cp docker/.env.example docker/.env` and set `PUBLIC_HOST` to your ngrok domain, hostname only |
| `Docker is not running` | Docker Desktop not started | Start it and wait for the whale icon to settle |
| `... did not answer within 6 minutes` for the **public** URL | ngrok not running, or running for a different domain or port | `ngrok http --url=https://$PUBLIC_HOST 3000` in another terminal, or `stack.sh up … --tunnel` with `NGROK_AUTHTOKEN` in `docker/.env`. **Not both**: a free account allows one session |
| Port already allocated (3000, 8080, 8090, 8443, 5432) | Another stack, or a local Postgres | `scripts/stack.sh down`; stop the other service. Only one copy of this stack can run |
| Changed `docker/.env` or the compose file and nothing changed | Containers read settings when they are *created* | `scripts/stack.sh down` then `up` again; a restart is not enough |
| Apple Silicon: `platform (linux/amd64) does not match` | Inji images are amd64-only | A warning; they run under emulation. Slow first start is normal |
| Suite server exits at start | It insists on the `OIDC_*` variables even in the dev profile | Already set to dummy values in the compose file; don't remove them |

## Inji Verify

| Symptom | Cause | Fix |
|---|---|---|
| Every presentation answered with HTTP 500 | Inji Verify 1.0's shipped database script is out of date (finding F-10; still so on `release-1.0.x`, 26 Oct) | Use our `docker/inji-verify/db-init/init.sql`, mounted by the compose file. With an old volume, `stack.sh down` and remove the `verify-db` volume so the script runs again |
| Happy flow fails on client id checks | `clientId` not set for your ngrok host | `configs/runner.local.json`: `"clientId": "redirect_uri:https://<your-host>/v1/verify/v2/vp-submission/direct-post"` |
| A request expires before delivery | Verify's requests live 300 s | The runner creates them just in time; if a module sits a long time in `WAITING`, re-run it with `--only <module>` |
| Test needs a signing key | Suite's test credential key missing | `python ../conformance-suite/scripts/generate-vp-test-cert.py --hostname $PUBLIC_HOST --output configs/keys/vp-signing-jwk.json --ca-output configs/keys/vp-test-ca.pem` |

## Inji Certify

| Symptom | Cause | Fix |
|---|---|---|
| `/pre-authorized-data` fails: unknown credential configuration | The SD-JWT configuration is not registered (Certify ships only `ldp_vc`) | `scripts/stack.sh up certify` registers it if missing; by hand: POST `docker/inji-certify/sd-jwt-credential-config.json` to `/v1/certify/credential-configurations` |
| Credential endpoint answers 401 | Certify validating tokens against eSignet instead of itself | Use our `docker/inji-certify/config/` (issuer URI and JWKS pointed at Certify itself) |
| Every flow stops at `CheckServerConfiguration` | Certify's metadata has no `authorization_endpoint` (F-12) | Reach Certify through the gateway (`https://$PUBLIC_HOST`), which adds it; see `docker/gateway/nginx.conf` |
| Suite waits forever after the offer | It wants the transaction code | `vci.static_tx_code` in the plan config and `txCode` in `issuerRequest` must match (both `4815` in `configs/runner.json`) |
| `jwks_file` not found | Wallet client keys missing | `python3 scripts/generate-client-jwks.py` |
| "Mimoto onboarding / PKCS12" in Certify's docs | Applies to Mimoto, not to conformance | Nothing to do: Certify generates its own keystore in the `certify-keys` volume at first start |

## Runner and gate

| Symptom | Meaning | What to do |
|---|---|---|
| Exit 2, `configuration error` | Bad or missing config | Read the message; check `configs/runner.json` and your `runner.local.json` |
| Exit 1, `GATE FAILED`, a **regression** | A module got worse than its baseline | Open the module's log (`logUrl` in the result, or `logs/<date>/`). Real regression: fix the component. Expected change: update `configs/contract/expected-failures.json` **with a reason** |
| Exit 1, **harness error** | The runner could not run a module (e.g. could not reach a component) | Not a conformance result. Check the stack's health first |
| Exit 1, **review mismatch** | A negative test the verifier should have rejected was accepted (or the reverse) | Treat as a real defect until shown otherwise |
| A **known defect** line in the gate output (e.g. F-16) | The verifier's verdict contradicts the test, but the suite already failed the module and the baseline names the finding (`acknowledgedMismatch`) | Nothing to do; it is reported on every run. Remove the acknowledgement once MOSIP fixes the defect |
| A module listed as having **no baseline** | New module in the plan, or a new plan | Run it, check the result is understood, then add it to the baseline |
| `httpx is not installed` | Python dependencies | `python3 -m pip install -r requirements.txt` |

## The api-testrig classes (`OpenIDConformanceTest`)

| Symptom | Cause | Fix |
|---|---|---|
| One skipped test: `OpenID conformance not configured` | Neither setting given | Set `conformanceResultFile` or `conformanceRunnerDir` in the module's properties file or as `-D…` |
| `No absolute injiCertifyBaseURL / injiVerifyBaseUrl to run conformance against` | Testrig configuration not loaded (TestNG started directly, not through MOSIP's runner), or the property empty | Set it in the properties file, or pass `-DinjiCertifyBaseURL=http://localhost:8090` / `-DinjiVerifyBaseUrl=http://localhost:8080` |
| `Conformance runner failed with exit status …` | The runner itself failed; its output is printed above | Read it; usually the stack is down |
| `NullPointerException` in `EmailableReport` after the tests | MOSIP's report listener expects files that only exist under the testrig's own launcher | Harmless when TestNG is run directly; the test results themselves are complete |
| Build fails in a git worktree (`git-commit-id-plugin`) | The plugin cannot read a worktree's `.git` file | `mvn … -Dmaven.gitcommitid.skip=true` |

## Updating the conformance suite

The suite is pinned by image digest in `docker/docker-compose.yml`, because "latest" changes
whenever the OpenID Foundation publishes and the baseline only means something against a
known suite. A newer suite can add, drop or tighten modules: the 27 Oct build added three
verifier modules (one of which found F-16) and dropped three.

1. `docker pull registry.gitlab.com/openid/conformance-suite:latest` and the same for
   `…/conformance-suite/nginx:latest`; note each `RepoDigests` value
   (`docker image inspect … --format '{{index .RepoDigests 0}}'`).
2. Try it without editing anything: put `SUITE_DIGEST=sha256:…` and
   `SUITE_NGINX_DIGEST=sha256:…` in `docker/.env`, then `scripts/stack.sh down` and
   `scripts/stack.sh up combined`.
3. `./run-conformance.sh --combined --output results/new-suite.json`, then
   `python -m runner.diff <last result> results/new-suite.json --component inji-verify`
   (and `inji-certify`). Every difference is either a module added or dropped, a new check,
   or a changed result: explain each one before touching the baseline.
4. Update `configs/contract/expected-failures.json` (entries for new modules, remove dropped
   ones, `suite.image`), move the default digests in `docker-compose.yml`, remove the two lines
   from `docker/.env`, and run again: the gate should pass with no "no baseline" modules.
