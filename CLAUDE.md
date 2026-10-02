# MOSIP Decode 2026 — PS1: Automated Conformance Testing

Harness that drives the OpenID Foundation conformance suite against MOSIP's Inji Certify
and Inji Verify, and feeds results into each module's existing `api-testrig`.

Team: Shardul (`shard-c6`) and Mukta. Final submission 26 Oct 2026, 11:59 PM IST. Deep detail lives in `docs/` —
this file is the always-loaded summary.

---

## Working rules — read these before doing anything

**1. Confirm before claiming.** We report findings upstream to MOSIP. A wrong report costs
our credibility, which is the only currency we have with maintainers. Every finding is
tagged `CONFIRMED` or `UNVERIFIED` in `docs/findings/findings.tex`. Nothing gets filed as a
bug until it is reproducible *and* the root cause is understood.

On Day 1 two failures looked like Inji Verify defects and were neither — one was an expired
request, one was a test-variant mismatch. Both were nearly reported. Check first.

**2. Read the source; don't guess.** Every guess made on Day 1 about MOSIP's behaviour was
wrong; every answer found by grepping `verify-service/src/main/` was right. The repos are
cloned locally — use them.

**3. Separate configuration gaps from implementation gaps.** "Your shipped sample config
can't be certified" and "you haven't implemented this part of the spec" are different
claims with different fixes. Maintainers take you seriously when you distinguish them.

**4. Check the assistant's environment before assuming what it can do.** This varies
between sessions and has already been documented wrongly once. As of 23 September the
assistant runs **natively on Shardul's Mac**, not in a separate VM: `gh` is authenticated
as `shard-c6`, `git`, `ngrok`, `mvn`, `pdflatex` and the `docker` CLI are all on PATH, and
files here are the real files. Two caveats remain — **Docker Desktop is usually not
running**, so the daemon must be started before any container work, and anything that
pushes, opens a PR or spends someone's quota is confirmed with the user first.

---

## Environment

| | |
|---|---|
| Working root | `~/projects/MOSIP` — this repo plus five sibling clones |
| ngrok domain (Shardul) | `sphere-dust-sandlot.ngrok-free.dev` — **per-developer; Mukta has her own** |
| Conformance suite | `https://localhost.emobix.co.uk:8443` (v5.3.1) — self-signed cert, use `curl -k` |
| Inji Verify | UI `:3000`, API `:8080`, context path `/v1/verify` |
| Test plan ID | `lN7C4DH1HvYmc` · alias `injiverify-shardul` |
| Versions | **Target: Inji 1.0 line** (`1.0.0-alpha.1` published; `release-1.0.x` branch). Tested so far: Verify 0.18.2 · Certify not yet run · Java 21 · Maven 3.9.16 |

Sibling clones: `inji-verify` · `inji-certify` · `mosip-functional-tests` ·
`conformance-suite` · `conformance-suite-automated-testing-tutorial`

The suite's local dev profile needs **no API token**. `/api/currentuser` answers
unauthenticated; the Swagger page's auth section describes the hosted deployment.

---

## Uncommitted local modifications

Not in any repo. A fresh clone lacks them; any one missing produces confusing failures.

**Target: the 1.0 worktree** — `../inji-verify-1.0`, a worktree of `inji-verify` at tag
`v1.0.0-alpha.1` (`git -C inji-verify worktree add --detach ../inji-verify-1.0 v1.0.0-alpha.1`):

1. `docker-compose/docker-compose.yml` — `VERIFY_SERVICE_PROXY_FOR_LOCALHOST` → ngrok host (5 places).
2. `docker-compose/db-init/init.sql` — `vp_submission` replaced with the canonical schema from
   `db_scripts`. Without it every submission returns HTTP 500 (finding F-10). Backup: `init.sql.bak`.
3. `docker-compose/config/config.json` — added credential **"OIDF Conformance PID (SD JWT)"**:
   `pre_registered`, DCQL `dc+sd-jwt`, `vct_values ["urn:eudi:pid:1"]`. The suite only ever presents
   that vct. Also *Mock Identity* switched to `pre_registered` (unused now). Backup: `config.json.bak`.
4. Runner side, gitignored: `configs/keys/vp-signing-jwk.json` (suite's test signing key, from
   `../conformance-suite/scripts/generate-vp-test-cert.py`) and `configs/runner.local.json`
   setting `clientId` to `redirect_uri:https://<ngrok-host>/v1/verify/v2/vp-submission/direct-post`.

Only one Verify version runs at a time — same container names and ports.

**0.18.2 clone** (`../inji-verify`, earlier evidence only):

1. **`inji-verify/docker-compose/docker-compose.yml`** — the literal placeholder
   `VERIFY_SERVICE_PROXY_FOR_LOCALHOST` sits in five env vars and is substituted by nothing.
   Replaced with the ngrok hostname.
2. **`inji-verify/docker-compose/config/config.json`** — *Mock Identity (SD JWT)* changed
   from `clientIdScheme: did` to `pre_registered`. `did` delivers the authorisation request
   **by reference** via `request_uri`; `pre_registered` delivers it **inline**. Only inline
   matches the `request_method=url_query` variant. Backup at `config.json.bak`.

---

## What we know about Inji Verify 0.18.2

> **Scope warning (2 Oct).** Everything in this section is true of 0.18.2 and is *not* the
> target. The problem statement means the Inji **1.0 line**; on `1.0.0-alpha.1` and
> `release-1.0.x`, DCQL exists and the nonce is random. Re-check any claim here against the
> 1.0 line before acting on it, and never report one upstream without that check.

Confirmed against the OpenID Foundation's own suite. Full catalogue in
`docs/findings/findings.tex`.

- **No DCQL.** Uses `presentation_definition` (Presentation Exchange). OID4VP 1.0 Final
  requires `dcql_query`. Every module in the 1.0 Final verifier plan therefore terminates at
  `ExtractDCQLQueryFromAuthorizationRequest`. This is the fact that shapes the whole project.
- **Nonce is `base64(millisecond timestamp)`** — 73.68 bits of Shannon entropy against the
  suite's 96-bit threshold, and the `=` padding is not URL-safe. Two defects, one root cause.
- **`RESPONSE_MODE` is a `static final` constant** set to `direct_post`. No
  `direct_post.jwt`, so HAIP certification is impossible without a code change.
- **No mdoc / ISO 18013-5 support** anywhere in the source.
- **Client identifier schemes don't overlap** with 1.0 Final's plan: Verify does `did` and
  `pre_registered`; the plan offers `redirect_uri`, `x509_san_dns`, `x509_hash`.
- **DID document inconsistency**: document `id` has `:v1:`, `verificationMethod[0].id`
  does not.

A full set of failures is the honest baseline. That is fine — the problem statement asks
for benchmark-gating and expected-failures handling, which exist precisely because
components don't pass everything.

---

## Gotchas that have already cost us time

- **Authorisation requests expire after 300s** (`Constants.DEFAULT_EXPIRY`). Check liveness
  before pasting: `curl -s -o /dev/null -w "%{http_code}\n" $VERIFY/v1/verify/vp-request/$RID`
- **Env vars are read at container *creation*.** After editing `docker-compose.yml` you must
  `down` then `up -d`. `restart` is not enough.
- **Stopping the suite needs the file flag**: `docker compose -f docker-compose-prebuilt.yml down`.
  A plain `down` in that folder reports success and leaves everything running.
- **`did:web` has two resolution forms.** `did:web:host` → `/.well-known/did.json`;
  `did:web:host:v1:verify` → `/v1/verify/did.json`. Ours has path segments — **no `.well-known`**.
- **ngrok is mandatory**, not convenience: a `did:web` DID is resolved over public HTTPS and
  cannot point at localhost. It also sidesteps the suite and Verify being in separate
  Docker Compose projects that can't see each other's localhost.
- **`sed -i` differs by platform**: macOS needs `sed -i ''`; Windows has no sed (PowerShell `-replace`).

---

## Conventions

- **Findings** → `docs/findings/findings.tex`, one `\finding{F-NN — title}{severity status}`
  block each, with evidence quoted from the log and the spec section the suite cited.
  Rebuild: `cd docs/findings && pdflatex findings.tex && pdflatex findings.tex`
- **Logs** → `logs/<YYYY-MM-DD>/<testname>-<testId>.json`. Commit the `.sig` alongside — the
  signature is what makes a log evidence rather than a text file we could have edited.
  Update the index table in `logs/README.md`.
- **Day entries** → a dated subsection in `findings.tex` §2, recording objective, decisions
  with reasoning, runs executed, and status.
- **Commits** → imperative subject, body explaining *why*. Made under our own names, with
  **no assistant attribution lines of any kind** (no `Co-Authored-By`).

---

## Where the detail lives

| File | Contents |
|---|---|
| `docs/handbook/handbook.tex` | **Start here.** Start-to-end guide, record of every step, day-by-day planner to 26 Oct. One font (LM Mono) throughout |
| `docs/CONTEXT.md` | Full state, decisions and rationale, corrections made |
| `docs/findings/findings.tex` | Findings catalogue + 7 open questions for mentors |
| `docs/SETUP.md` | First-time setup, macOS and Windows |
| `docs/RUNBOOK.md` | Start / access / shutdown / troubleshooting |
| `docs/PLAN.md` | Four-week plan (re-anchored to the 23 Sep kickoff), proposed role split |
| `docs/CONTRACT.md` | The runner→testrig JSON contract — the one interface between the two halves |
| `docs/WEEK2.md` | Day-by-day build plan for the conformance runner |
| `configs/contract/` | Contract fixture (real Day 1 data) and the expected-failures baseline |

Commands available: `/stack-up`, `/stack-down`, `/health-check`, `/run-test`,
`/analyse-log`, `/log-day`.
