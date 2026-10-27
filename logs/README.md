# Conformance logs

Exported logs from the OpenID Foundation conformance suite, organised by date. **These are
the project's evidence.** Every finding in `docs/findings/findings.tex` and every entry in
`configs/contract/expected-failures.json` cites a file in here.

---

## Why the `.sig` matters

The suite exports each run as `.json` and `.html`, each with a `.sig` alongside — a
signature over the content. **Commit all of them.** The signature is what makes a log
verifiable evidence rather than a text file we could have edited, and it is the difference
between "we observed this" and "we assert this" when reporting upstream to MOSIP.

## Exporting

From the suite's test page use **Download all Logs**, or via the API:

```bash
curl -k https://localhost.emobix.co.uk:8443/api/log/<testId> \
  -o logs/<date>/<testname>-<testId>.json
```

## Layout and naming

The suite's own export is a folder per run, named for the module and its full variant:

```
logs/<YYYY-MM-DD>/<testname>-<variant...>-<testId>/
    <testname>-<testId>.json      <- cited as evidence
    <testname>-<testId>.json.sig
    <testname>-<testId>.html
    <testname>-<testId>.html.sig
```

Keep that layout as the suite produces it. Renaming breaks the `evidence` paths recorded in
the expected-failures baseline, and those paths are load-bearing: the Week 2 runner archives
logs here automatically and the gate reads them back.

**When adding a run, update three things together** — this index, the baseline entry in
`configs/contract/expected-failures.json`, and the findings document if the run produced or
changed a finding. A log that nothing references is a log nobody will trust later.

---

## Index

### 2026-09-20 — Day 1 (pre-kickoff)

Plan `lN7C4DH1HvYmc`, alias `injiverify-shardul`, against Inji Verify 0.18.2.
Variant for all three runs: `credential_format=sd_jwt_vc, client_id_prefix=redirect_uri,
request_method=url_query, vp_profile=plain_vp, response_mode=direct_post`

| Test ID | Module | Result | Notes |
|---|---|---|---|
| `dgeeosZpIfDK1bA` | happy-flow | FAILED | Not exported. Request had expired; discarded as a timing artefact, **not** a defect |
| `dMg4B5whxWgShIB` | happy-flow | FAILED | Suite never dereferenced `request_uri` under the `url_query` variant — variant mismatch, not a defect |
| `MtzpWoD2dVgtic0` | happy-flow | FAILED | **Day 1 baseline.** 15 checks passed, 4 failed, 3 warnings. Source of F-01, F-02, F-03, F-04, F-05, F-09. Terminated at `ExtractDCQLQueryFromAuthorizationRequest` |

The two discarded runs are listed deliberately. Both looked like Inji Verify defects and
neither was; recording why they were discarded is what stops them being rediscovered and
misreported later.

`MtzpWoD2dVgtic0` is also the source of `configs/contract/example-run.json`, the fixture the
Java side builds against.

### 2026-09-23 — Day 2 (event kickoff)

No runs. Planning and documentation only.

### 2026-09-29 — Day 4 (first automated runs)

Produced by `./run-conformance.sh`, not the suite UI. These are the JSON the runner fetched
from `/api/log/{id}` — **unsigned**. They are working evidence for the harness; anything
reported upstream still needs the suite's signed export.

| Test ID | Module | Result | Notes |
|---|---|---|---|
| — | happy-flow | HARNESS ERROR | Run 1. Our request to Verify lacked the definition `id`; HTTP 400. No module result, no log |
| `hcuWEvxGbvRgt7e` | happy-flow | FAILED | Run 2, `nonceMode=sdk`. **First unattended run.** Matches `MtzpWoD2dVgtic0` check-for-check |
| `Q9MaDZyfpJhjiDp` | happy-flow | FAILED | Run 3, `nonceMode=service`. Nonce checks pass; nothing else changes. Confirms F-01/F-02 root cause |

---

### 2026-10-02 — Day 6 (first runs on Inji Verify 1.0.0-alpha.1)

Automated, unsigned. Target version. Each run changed exactly one thing.

| Test ID | Module | Result | Notes |
|---|---|---|---|
| `Bob121tXCWTGf9y` | happy-flow | FAILED | First 1.0 run. DCQL extracted, nonce checks pass. Stopped: our plan config lacked a signing key |
| `gIA512EeJWehcHt` | happy-flow | FAILED | Signing key added. Verify answered **HTTP 500** — F-10 (database script) |
| `tpKVz6upccxpO5U` | happy-flow | FAILED | Database fixed. Verify rejected the credential's `vct` — correct behaviour |
| `ZQqnbYfw46wpmyI` | happy-flow | FAILED | PID credential as `dc+sd-jwt`. **Verify accepted the presentation (HTTP 200)**; client-id pairing failures only |
| `5KS13qvmbwOMNtY` | happy-flow | **REVIEW** | `redirect_uri:` client id. **35 pass, 0 fail, 0 warn.** Baseline for 1.0 |

Full plan, all 11 modules — two runs:

- Plan `YyUQFGfA9rlMr` — first full run. 4 PASSED, 7 REVIEW. REVIEW not yet resolved: the harness did
  not fetch Verify's verdict, so the negative tests' outcome was invisible.
- Plan `nupFFSGqySsbb` — with REVIEW resolution. Every module consistent with conformance; the two
  `request-uri-*` modules not applicable to `url_query`. **Source of the 1.0 baseline.**

### 2026-10-26 — first run on the Compose stack

Plan `2WXPDhBNMwyCL`: the full verifier plan against Inji Verify 1.0.0-alpha.1 brought up from
`docker/docker-compose.yml` rather than the hand-edited worktree. **Identical to plan
`YyUQFGfA9rlMr` (2 October) module for module and check for check**; gate passes against the
full baseline with no unknown modules, mismatches or harness errors. The same result fed to
`OpenIDConformanceTest` gives 12 of 12 passing in MOSIP's EmailableReport.

### 2026-10-26 — Inji Certify (release-1.0.x), OID4VCI 1.0 issuer plan

Plan `89gcoUu8shPu1`: the full issuer plan, 15 modules, for the pre-authorized code / SD-JWT /
DPoP variant. 3 PASSED (each checked in Certify's own log to be rejected for the right reason),
3 SKIPPED, 1 WARNING, 8 FAILED, every failure traced to F-12 to F-15 or an optional feature.
**Source of the Certify baseline.** All results through the F-12 gateway shim.

### 2026-10-26 — combined run (problem statement task iv)

`./run-conformance.sh --combined`: one invocation runs both plans and writes one result with
one gate. Plans `uzQR679oonrne` (Inji Verify, 11 modules) and `q4RAMcjJWpAhF` (Inji Certify,
15 modules). **Each identical, module for module and check for check, to its standalone run**
(`2WXPDhBNMwyCL` and `89gcoUu8shPu1`). Gate passes: no regressions, unknown modules, harness
errors or review mismatches. The same result file fed to both api-testrig classes gives 12 of 12
(`OpenIDConformanceTest` in Inji Verify) and 16 of 16 (in Inji Certify) in MOSIP's EmailableReport.

### 2026-10-26 — runner mode in the api-testrigs, and the one-command run

- Plan `QYRHeZCoMVQRG` (Certify, 2 modules, then stopped): first attempt by Inji Certify's
  `OpenIDConformanceTest` to run the runner itself. TestNG was started without MOSIP's launcher,
  so the testrig's base URL was empty and the runner was given a relative endpoint; it stopped at
  the first offer. Led to the class checking for an absolute URL first. Not a conformance result.
- Plans `UByUkX1NUvsK6` (Inji Certify, 15 modules) and `OF4joC3VfcDh7` (Inji Verify, 11 modules):
  each api-testrig class ran the runner against its own base URL. 16 of 16 and 12 of 12 TestNG
  tests pass; both gates pass.
- Plans `g590BHmwSppVo` (Inji Verify) and `sYMCFZ5C9a6RA` (Inji Certify):
  `./run-full-stack-conformance.sh --combined` — stack up, both plans, result, consolidated
  report and badge. Gate passes.

## Outstanding

The two `request-uri-*` modules, which need a signed by-reference request (`release-1.0.x` head).

Signed exports of the evidence plans (27 Oct) are in the gitignored `evidence/` folder, not
here: they contain the suite's copy of our test private keys, which a signature prevents
redacting. See `docs/STATUS.md`.

### 2026-10-27 — fresh-clone test

Plans `QsTB0J2hoDsWi` (Inji Verify) and `YxYPKLEUz0Zv0` (Inji Certify): a clean clone from
GitHub, set up from the README alone with newly generated keys, ran
`./run-full-stack-conformance.sh --combined`. Gate passes; `python -m runner.diff` against the
26 Oct combined run: no differences across all 26 modules. Its logs stayed in the throwaway
clone and are not copied here; the result is reproduced, not new evidence.

### 2026-10-27 — the latest suite (27 Oct build, now pinned)

- GitHub Actions run 6, plans `RVpJfDDO5I4BZ` (Inji Verify, 12 modules) and `6MKy3R9t4SDQH`
  (Inji Certify, 14 modules): the first full run on CI. It pulled the suite's `latest`, a newer
  build than ours, whose plans differ (three verifier modules added, three modules dropped).
  Logs are in the run's artifact, not here.
- Plans `dk7WTeEpVfDCW` and `9soA2jgYi4lki`: the same suite build, pinned by digest, run
  locally. `runner.diff` against CI run 6: no differences across 26 modules.
  **Source of the current baseline**: its logs are in `2026-10-27/` (the new modules' evidence
  is `present-revoked-credential-r1i7jlHHrzwZDTc`, `present-credential-without-status-Y9R2Ru9ZNOgZx6U`,
  `wrong-vct-oRYhmanHgNGolE0`).
- Plans `tsEPVoEXK87hL` (Inji Verify) and `kQsIvua57Vdib` (Inji Certify): after moving the
  baseline. Gate passes with no module lacking a baseline; F-16 reported as a known defect.
  Logs not kept; results identical to the run above.
- Plans `QpHhlq7hq6TLz` (Inji Verify, 13 of 13) and `pygcrOj5sEs4Q` (Inji Certify, 15 of 15):
  the api-testrig classes, rebuilt on the forks merged with upstream `release-1.0.x`, running
  the runner themselves.

### 2026-10-27 — Inji Verify release-1.0.x QA build

Inji Verify moved from `1.0.0-alpha.1` to MOSIP's QA image of `release-1.0.x` (commit `429293f`);
suite and Inji Certify unchanged.

- Plan `3Z0H96UD635fo` (Inji Verify, 12 modules): the first run on the new build. `runner.diff`
  against the alpha.1 run above: no differences. **Source of the current Inji Verify baseline**:
  its 12 logs are in `2026-10-27/` (test IDs in `configs/contract/expected-failures.json`). The
  Inji Certify plan from the same run (`y1ck1VcTYMzq9`) repeats earlier results; logs not kept.
- Plans `zDI8B7cVXSPw1` and `JRXxlFuVDAWpn`: after moving the baseline. Identical; logs not kept.
- Plans `iRyPNlpQkxF2v` (Inji Verify, 13 of 13) and `Cc8WoTsp8a4MI` (Inji Certify, 15 of 15): the
  api-testrig classes on the new build. Logs not kept.
