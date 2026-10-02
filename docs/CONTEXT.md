# Project context — state of play

**Last updated**: 23 September 2026 — official event kickoff
**Purpose**: everything established so far, in one place. Read this first if you're picking
the project up after a break, joining it, or continuing in a new assistant session.

---

## 0. Read this first — the 1.0 line (2 October)

Everything up to 29 September was tested against **Inji Verify 0.18.2**. On 2 October we
found that upstream has an Inji 1.0 line — `release-1.0.x` in both inji-verify and
inji-certify, published as `1.0.0-alpha.1` — which is what the problem statement means by
"on 1.0". On that line, DCQL is implemented and the nonce is random, so F-01, F-02 and F-03
do not apply there. Our findings stand for 0.18.2 but are scoped to it; the baseline moves to
`1.0.0-alpha.1`. Details: Day 6 in `docs/findings/findings.tex`.

## 1. The one-paragraph version

We are building an automated conformance-testing harness for MOSIP's Inji stack (PS1,
MOSIP Decode 2026). On Day 1 we stood up the OpenID Foundation conformance suite and Inji
Verify locally, drove one verifier test (`oid4vp-1final-verifier-happy-flow`) end to end by
hand, and catalogued nine findings — eight of them confirmed with evidence from the OpenID
Foundation's own tooling. The headline result: **Inji Verify 0.18.2 implements the
superseded Presentation Exchange query model rather than DCQL, so no module in the OID4VP
1.0 Final verifier plan can pass.** That is not a blocker for our deliverable; it is the
baseline our harness will gate against.

---

## 2. Concrete environment values

Keep these to hand — most of them appear in commands.

| Thing | Value |
|---|---|
| Working root | `~/projects/MOSIP` (macOS, Apple Silicon arm64, Docker Desktop) |
| Our repo | `~/projects/MOSIP/mosip-decode-ps1` |
| GitHub (Shardul) | `shard-c6` |
| ngrok static domain | `sphere-dust-sandlot.ngrok-free.dev` — **Shardul's only; Mukta needs her own** |
| Conformance suite | `https://localhost.emobix.co.uk:8443` — v5.3.1, rev `440eec8` |
| Inji Verify UI | `http://localhost:3000` |
| Inji Verify API | `http://localhost:8080`, context path `/v1/verify` |
| Verify DID document | `https://sphere-dust-sandlot.ngrok-free.dev/v1/verify/did.json` |
| Test plan ID | `lN7C4DH1HvYmc` |
| Suite alias | `injiverify-shardul` |

### Component versions
Inji Verify service & UI 0.18.2 · Inji Certify 0.14.0 (not yet run) · conformance suite 5.3.1

### Sibling clones under `~/projects/MOSIP`
`inji-verify` · `inji-certify` · `mosip-functional-tests` (GitHub) ·
`conformance-suite` · `conformance-suite-automated-testing-tutorial` (GitLab)

---

## 3. Local modifications to upstream code

**These are not committed anywhere.** A fresh clone will not have them. Both are documented
in SETUP.md, but record them here because forgetting either produces confusing failures.

**1. `inji-verify/docker-compose/docker-compose.yml`**
The literal placeholder `VERIFY_SERVICE_PROXY_FOR_LOCALHOST` appears in five environment
variables and is substituted by nothing. Replaced with the ngrok hostname.
Revert: `git checkout docker-compose.yml`

**2. `inji-verify/docker-compose/config/config.json`**
The *Mock Identity (SD JWT)* credential changed from `"clientIdScheme":"did"` to
`"pre_registered"`. Backup at `config/config.json.bak`.
Why: `did` delivers the authorisation request **by reference** via `request_uri`;
`pre_registered` delivers it **inline**. Only inline matches the plan's
`request_method=url_query` variant.

### What's in `config.json` by default
| # | Name | clientIdScheme | Format |
|---|---|---|---|
| 0 | MOSIP ID | did | ldp_vc |
| 1 | Life Insurance | did | ldp_vc |
| 2 | Health Insurance | pre_registered | ldp_vc |
| 3 | **Mock Identity (SD JWT)** | **pre_registered** *(we changed this)* | **vc+sd-jwt** |
| 4 | Land Registry | did | ldp_vc |

Entry 3 is the only one usable with the `sd_jwt_vc` plan variant.

---

## 4. Decisions taken, and why

**Inji Verify before Inji Certify.** Verify is three containers with no external
dependencies. Certify's `docker-compose-injistack` needs a PKCS12 keystore from Mimoto
onboarding, a public DID endpoint, an external authorisation server and partner API keys.
The verifier plan is 12 modules against the issuer plan's 61. Verify was roughly five times
less setup for a first real result, and everything learned transfers.

**Non-HAIP plan.** The HAIP verifier plan offers only `direct_post.jwt`. Verify hardcodes
`direct_post`. We used *OpenID for Verifiable Presentations 1.0 Final: Test a verifier —
alpha tests* instead, which offers plain `direct_post`.

**Credential format `sd_jwt_vc`.** The only two options are `sd_jwt_vc` and `iso_mdl`, and
Verify has no mdoc code at all.

**Variant actually used:**
`credential_format=sd_jwt_vc, client_id_prefix=redirect_uri, request_method=url_query,
vp_profile=plain_vp, response_mode=direct_post`

---

## 5. Findings summary

Full catalogue with evidence in `docs/findings/findings.tex`. Short form:

| ID | Finding | Severity | Status |
|---|---|---|---|
| F-01 | Nonce is a base64 timestamp — insufficient entropy (73.68 vs 96 bits) | HIGH | Confirmed |
| F-02 | Nonce contains `=` padding, not URL-safe | MEDIUM | Confirmed |
| F-03 | No DCQL support; terminates every 1.0 Final test | HIGH | Confirmed |
| F-04 | Uses superseded `presentation_definition` | MEDIUM | Confirmed |
| F-05 | `client_metadata` absent in inline mode | MEDIUM | **Unverified** |
| F-06 | No `direct_post.jwt`; HAIP certification impossible | HIGH | Confirmed |
| F-07 | DID document verification method id missing `:v1:` segment | MEDIUM | Confirmed |
| F-08 | No mdoc / ISO 18013-5 support | LOW | Confirmed |
| F-09 | Client identifier prefixes have no overlap with 1.0 Final | MEDIUM | Confirmed |

**F-05 must not be reported upstream yet.** Verify *did* send `client_metadata` with full
`vp_formats` in the `did` (signed JWT) path. In the `pre_registered` path its API response
contained none, so our reconstructed URI couldn't include one. Whether Verify omits it or
the UI adds it at QR-build time is unresolved. Check the actual QR payload before deciding.

---

## 6. Gotchas learned the hard way

**Authorisation requests expire after 300 seconds.** `Constants.DEFAULT_EXPIRY = 300`.
Check liveness before pasting:
`curl -s -o /dev/null -w "%{http_code}\n" $VERIFY/v1/verify/vp-request/$RID` → want `200`.

**Environment variables are read when a container is created, not when the file changes.**
After editing `docker-compose.yml` you must `down` then `up -d`. A `restart` is not enough.
This cost us one confusing round trip.

**Stopping the conformance suite needs the file flag.**
`docker compose -f docker-compose-prebuilt.yml down`. A plain `docker compose down` in that
folder targets the default compose file, reports success, and leaves everything running.

**`did:web` path resolution has two forms.** `did:web:host` → `https://host/.well-known/did.json`;
`did:web:host:v1:verify` → `https://host/v1/verify/did.json`. Ours has path segments, so
**no `.well-known`**.

**ngrok is mandatory, not convenience.** Verify's identity is a `did:web` DID resolved over
public HTTPS. Nothing can resolve a DID pointing at localhost. Using ngrok also sidesteps
the separate problem that the suite and Verify run in different Docker Compose projects and
can't see each other's `localhost`.

**The conformance suite's local dev profile needs no API token.** `/api/currentuser`
answers unauthenticated. The Swagger page describes the hosted deployment's auth, which
doesn't apply. Admin users can't mint tokens anyway — that page will refuse you.

**Self-signed certificate warnings are expected** on `localhost.emobix.co.uk:8443`. The
hostname is a real domain that resolves to 127.0.0.1. Use `curl -k` and click through in
the browser. This reasoning applies only because the destination is your own machine.

**`sed -i` differs by platform.** macOS needs `sed -i ''`; Windows has no sed — use
PowerShell's `-replace`.

---

## 7. Corrections made during Day 1

Recorded because the same mistakes are easy to repeat, and because a couple nearly became
bogus upstream reports.

- ngrok domain was assumed `.ngrok-free.app`; it is actually `.ngrok-free.dev`. Five
  compose lines pointed at a nonexistent host until corrected.
- DID document path was assumed `/v1/verify/.well-known/did.json`; correct is
  `/v1/verify/did.json`. Resolved by reading `DidWebController.java` rather than guessing again.
- The first `ExtractNonceFromAuthorizationRequest` failure was nearly filed as "Verify
  omits the nonce." It does not. The suite never dereferenced `request_uri` because the
  `url_query` variant doesn't fetch request objects. **Confirming before claiming is the
  rule that saved this one.**
- We were told to create an API token; it turned out to be unnecessary locally.

---

## 8. Tooling built so far

`scripts/build-oid4vp-uri.py` — takes Inji Verify's `/vp-session-request` response
(pre_registered/inline mode) and emits a paste-ready `openid4vp://` URI with correct
URL-encoding, plus an expiry countdown on stderr.

```bash
pbpaste | python3 scripts/build-oid4vp-uri.py        # macOS
Get-Clipboard | python scripts/build-oid4vp-uri.py   # Windows
```

This is the first reusable component of the harness — the Week 2 runner will do the same
job through Verify's API rather than the clipboard.

---

## 9. Where things stand

**Important calendar correction.** The 20 September session happened **three days before
the event officially started**. MOSIP Decode kicked off on **23 September 2026**; the
kickoff webinar (23 Sep) was held and recorded but we did not attend live; we worked from its transcript on 2 Oct. Nothing was done between 20 and
23 September, so the "Day 2" list written on Day 1 is still entirely outstanding — it has
simply moved into Week 1 proper. `docs/PLAN.md` has been re-anchored to the real calendar.

**Done** (all of it pre-kickoff): environment; module 01 executed three times (two
discarded as artefacts, one baseline); nine findings catalogued; repo scaffolded with
SETUP, RUNBOOK, PLAN, findings and this file; forks of all three MOSIP repos created.

**Outstanding, carried into Week 1 (23–28 September)**
1. Modules 02–11 of the 1.0 Final alpha verifier plan. Expect all to interrupt at
   `ExtractDCQLQueryFromAuthorizationRequest` — that uniformity *is* the result.
2. The **ID2 verifier plan** (1 module) — the draft generation Verify appears to target,
   and the most likely source of an actually-passing test. The harness needs at least one.
3. Resolve F-05 one way or the other.
4. Mukta: get `api-test/` running in both repos; document the existing TestNG result shape.
5. Role split agreed 23 September (see PLAN.md). Contract drafted in `docs/CONTRACT.md`;
   awaiting Mukta's review of the four open points at the end of it.

**Outstanding admin**
- Push the local commit — the repo exists at `shard-c6/mosip-decode-ps1` on branch
  `master`, and local is **one commit ahead** (`d7dede0`)
- Fill the `### Our forks` placeholder in README.md — the forks already exist
- Add Mukta as collaborator; she adds Shardul on hers
- Share the agreed role split (PLAN.md) and `docs/CONTRACT.md` with Mukta so she can start
- Move Day 1 log exports into `logs/2026-09-20/` (commit `.json` and `.sig` both)
- ~~Confirm the real submission deadline~~ — **done 30 Sep: 26 October 2026, 11:59 PM IST.**
  Planner in `docs/handbook/handbook.tex`, Part 4

**Questions waiting on mentors**: Q1–Q8 in the findings document. Q1 (which spec version to
benchmark against) is the one that most shapes the rest of the build. The weekly Wednesday sessions (5–6 PM IST, from 30 Sep) are the channel; even so, the
community forum is the only channel — and no answer may arrive, so the runner is being
designed so plan name and variants are configuration rather than code.

---

## 10. Note for future assistant sessions

**This section was wrong before 23 September and is worth reading carefully, because it
changes between sessions.** The earlier version claimed Claude ran in a separate Linux VM
with no Docker, no `gh`, and a network that blocked GitLab and ngrok. That was true of that
session's harness; it is not true now.

As of 23 September 2026 the assistant runs **natively on Shardul's Mac**:

- `gh` is authenticated as `shard-c6`; `git`, `ngrok`, `mvn` (3.9.16), `pdflatex` and the
  `docker` CLI are all on PATH. Java is **21**, not 11.
- Git operations work directly. Still confirm before anything that pushes or opens a PR.
- **Docker Desktop is usually not running.** The CLI is present but the daemon is not, so
  any container work needs Docker Desktop started first — and the containers are heavy, so
  start them deliberately rather than as a side effect.
- Files under `~/projects/MOSIP` are the real files.

**Verify this rather than trusting it.** A quick `docker ps`, `gh auth status` and
`java -version` at the start of a session costs seconds and has already caught one
wrong assumption.
