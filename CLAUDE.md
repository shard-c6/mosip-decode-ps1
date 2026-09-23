# MOSIP Decode 2026 — PS1: Automated Conformance Testing

Harness that drives the OpenID Foundation conformance suite against MOSIP's Inji Certify
and Inji Verify, and feeds results into each module's existing `api-testrig`.

Team: Shardul (`shard-c6`) and Mukta. Four-week hackathon. Deep detail lives in `docs/` —
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

**4. Git is the user's job.** The sandbox this assistant runs in cannot delete files inside
`.git`, so `git commit` fails on lock files. Write and edit freely; hand git commands to
the user to run in their own terminal.

---

## Environment

| | |
|---|---|
| Working root | `~/projects/MOSIP` — this repo plus five sibling clones |
| ngrok domain (Shardul) | `sphere-dust-sandlot.ngrok-free.dev` — **per-developer; Mukta has her own** |
| Conformance suite | `https://localhost.emobix.co.uk:8443` (v5.3.1) — self-signed cert, use `curl -k` |
| Inji Verify | UI `:3000`, API `:8080`, context path `/v1/verify` |
| Test plan ID | `lN7C4DH1HvYmc` · alias `injiverify-shardul` |
| Versions | Inji Verify 0.18.2 · Inji Certify 0.14.0 (not yet run) |

Sibling clones: `inji-verify` · `inji-certify` · `mosip-functional-tests` ·
`conformance-suite` · `conformance-suite-automated-testing-tutorial`

The suite's local dev profile needs **no API token**. `/api/currentuser` answers
unauthenticated; the Swagger page's auth section describes the hosted deployment.

---

## Uncommitted local modifications

Not in any repo. A fresh clone lacks both; either one missing produces confusing failures.

1. **`inji-verify/docker-compose/docker-compose.yml`** — the literal placeholder
   `VERIFY_SERVICE_PROXY_FOR_LOCALHOST` sits in five env vars and is substituted by nothing.
   Replaced with the ngrok hostname.
2. **`inji-verify/docker-compose/config/config.json`** — *Mock Identity (SD JWT)* changed
   from `clientIdScheme: did` to `pre_registered`. `did` delivers the authorisation request
   **by reference** via `request_uri`; `pre_registered` delivers it **inline**. Only inline
   matches the `request_method=url_query` variant. Backup at `config.json.bak`.

---

## What we know about Inji Verify 0.18.2

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
- **Commits** → imperative subject, body explaining *why*. Attribute co-authorship when
  written with an assistant.

---

## Where the detail lives

| File | Contents |
|---|---|
| `docs/CONTEXT.md` | Full state, decisions and rationale, corrections made |
| `docs/findings/findings.tex` | Findings catalogue + 7 open questions for mentors |
| `docs/SETUP.md` | First-time setup, macOS and Windows |
| `docs/RUNBOOK.md` | Start / access / shutdown / troubleshooting |
| `docs/PLAN.md` | Four-week plan, tentative role split |

Commands available: `/stack-up`, `/stack-down`, `/health-check`, `/run-test`,
`/analyse-log`, `/log-day`.
