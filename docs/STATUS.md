# Status against the problem statement

*As of 26 October 2026. Deadline 2 November 2026.*

Problem statement 1, MOSIP Decode 2026: **Automated Conformance Testing for Inji Certify and
Inji Verify against the OpenID Suite.** This page checks each thing the problem statement
asks for against what exists, and points at the evidence. The architecture is in
[ARCHITECTURE.md](ARCHITECTURE.md).

**In one line:** all five mandatory tasks are done and have been demonstrated on a live
stack; of the good-to-haves, CI, selective execution, expected failures and documentation
are done, result diff is not; the bonus (parallel execution) is not. What remains before
submission is mostly the submission material itself: slide deck, video, fresh-clone test,
college IDs, the email.

---

## Mandatory tasks

| # | The problem statement asks for | Where it is | Demonstrated | Status |
|---|---|---|---|---|
| i | Docker Compose: Inji Certify + Inji Verify + conformance suite | `docker/docker-compose.yml`, profiles `verify`, `certify`, `tunnel`; `scripts/stack.sh` | 26 Oct: `stack.sh up combined` brings up all three and checks every endpoint, public ones included | **Done** |
| ii | Programmatic runner over the suite's REST API: create, configure, run, poll, retrieve, for the issuer plan and the verifier plan | `runner/` (suite client modelled on the suite's own `conformance.py`; component clients; handoff; normalise; gate) | Verifier plan: 11 modules on Inji Verify 1.0, unattended. Issuer plan: 15 modules on Inji Certify 1.0, unattended | **Done** |
| iii | `OpenIDConformanceTest` TestNG class in the Inji Certify and Inji Verify api-testrigs; invokes the runner against the testrig's own endpoint; maps each test to pass/fail/skip; emits into the existing report | Forks `shard-c6/inji-verify` and `shard-c6/inji-certify`, branch `feature/openid-conformance-test` (on `release-1.0.x`), `api-test/.../testscripts/OpenIDConformanceTest.java` + `ConformanceCase.java`, registered in each suite XML and properties file | 26 Oct, **runner mode, live**: the class ran the runner itself, against its own base URL: Verify 12/12, Certify 16/16 (each module + the gate). **File mode**: same results. A doctored regression fails exactly that module and the gate. Unconfigured: one clean skip | **Done** (see note 1) |
| iv | Combined run: one entry point, both plans, one consolidated cross-module report | `./run-conformance.sh --combined`; `--report` writes `report.html`, `report.md`, `badge.svg` (`runner/report.py`) | 26 Oct: 26 modules in one run, one gate, each component identical to its standalone run; one result file feeds both testrigs (12/12, 16/16) | **Done** |
| v | One-command execution: `--component certify`, `--component verify`, `--combined` | `run-conformance.sh` (stack already up); `run-full-stack-conformance.sh` (stack up → run → report → stack down) | 26 Oct: `./run-full-stack-conformance.sh --combined` end to end, gate passed | **Done** |

**Note 1, on "in mosip-functional-tests".** The problem statement places the class "in the
Inji Certify api-testrig and the Inji Verify api-testrig in mosip-functional-tests". On the
1.0 line those api-testrigs live inside each component's own repository (`inji-verify/api-test`,
`inji-certify/api-test`), building on MOSIP's shared `apitest-commons` library from
mosip-functional-tests. That is where we put the class. Worth confirming with the mentors.

**Note 2, on the S3/minio bucket.** The class's results are ordinary TestNG results and
appear in the testrig's own report (checked in MOSIP's EmailableReport). The testrig's
upload of that report to its bucket needs a MOSIP deployment; it was not exercised.

## Good-to-have tasks

| # | Task | Where | Status |
|---|---|---|---|
| i | GitHub Actions CI/CD | `.github/workflows/full-stack-conformance.yml`: harness tests + stack validation on every push (green); full conformance run on demand (verify / certify / combined) and weekly, failing the build on a regression | **Done.** The full run needs two repository secrets (`PUBLIC_HOST`, `NGROK_AUTHTOKEN`) and has not yet run on GitHub; without them it is skipped, not failed |
| ii | Selective component/plan execution | `--component verify`, `--component certify`, `--combined`; plus `--only MODULE…` for a subset of a plan | **Done** |
| iii | Expected failures | `configs/contract/expected-failures.json`: every known failure with a reason and its evidence log; per-version baselines; the gate fails only on regressions | **Done** |
| iv | Result diff between runs | — (done by hand on 26 Oct to show the combined run matches the standalone runs) | **Not done** |
| v | Documentation | [ARCHITECTURE.md](ARCHITECTURE.md), [SELF-CERTIFICATION.md](SELF-CERTIFICATION.md), [TROUBLESHOOTING.md](TROUBLESHOOTING.md), [CONTRACT.md](CONTRACT.md), README, findings, handbook | **Done** (runner API reference is the CLI `--help` plus CONTRACT.md) |

## Bonus

| Task | Status |
|---|---|
| Parallel execution | **Not done.** Modules run one at a time; the suite's per-alias callbacks make concurrent modules on one alias unsafe |

## Deliverables listed in the problem statement

| Deliverable | Where | Status |
|---|---|---|
| a. Docker Compose configuration | `docker/docker-compose.yml` | Done |
| b. Test plan configurations, JSON, for issuer and verifier plans, with correct 1.0 variants | `configs/runner.json` (per component: plan, variant, config); per-developer values in gitignored `configs/runner.local.json` | Done |
| c. One-command runner (`run-full-stack-conformance.sh`) | `run-full-stack-conformance.sh` | Done |
| d. GitHub Actions workflow (`.github/workflows/full-stack-conformance.yml`) | that path | Done (see good-to-have i) |
| e. Documentation: architecture, API automation, per-component handoff, self-certification, troubleshooting | ARCHITECTURE.md §§1–3, SELF-CERTIFICATION.md, TROUBLESHOOTING.md | Done |

## Submission items (from the organisers)

| Item | Status |
|---|---|
| Source code, with git history | Done: this repository + the two fork branches |
| Working prototype / demo | Done: the stack, the runner, the report; reproducible from a clone |
| Usage and installation instructions | README + ARCHITECTURE + TROUBLESHOOTING. **A fresh-clone test is still to do** |
| API documentation | CONTRACT.md (the result format), ARCHITECTURE.md §2 (suite API use), CLI `--help` |
| Slide deck | **To do** |
| Video, 2–5 minutes | **To do** |
| Each student's college ID | **To do** |
| Submission email to decode@mosip.io (team, problem statement, URLs) | **To do**, by 1 November |

---

## Results so far

| | Inji Verify 1.0.0-alpha.1 | Inji Certify 1.0 (release-1.0.x) |
|---|---|---|
| Plan | OID4VP 1.0 Final verifier, 11 modules | OID4VCI 1.0 issuer, 15 modules |
| Variant | sd_jwt_vc · url_query · redirect_uri · direct_post | pre-authorized code, issuer-initiated · sd_jwt_vc · DPoP · private_key_jwt |
| Suite results | 4 PASSED, 7 REVIEW, 0 failed | 3 PASSED, 1 WARNING, 3 SKIPPED, 8 FAILED |
| What that means | 9 genuinely exercised, all consistent with conformance once each REVIEW is settled by Verify's own verdict; 2 (`request-uri-*`) do not apply to this variant | The 3 passes are negative tests, each checked in Certify's log to be rejected for the right reason; 3 skips are optional features Certify does not offer; every failure traced to findings F-12–F-15 or an optional feature |
| Gate | Passes against the baseline | Passes against the baseline |

Findings: 15 catalogued in `docs/findings/findings.tex`. F-01–F-09 against Inji Verify
0.18.2 (several fixed on the 1.0 line); F-10, F-11 on Inji Verify 1.0; F-12–F-15 on Inji
Certify 1.0. None has been filed upstream yet; F-10 (with its fix) is drafted in
`docs/upstream/`.

---

## Everything done, in order

**Before the event (20 Sep).** Conformance suite and Inji Verify 0.18.2 running locally,
ngrok for Verify's `did:web`; first verifier module run by hand; nine findings catalogued.

**Week of 23 Sep.** Plan re-anchored to the kickoff; roles; the runner-to-testrig contract
(`docs/CONTRACT.md`) drafted against real data.

**29–30 Sep.** The runner: suite client, Inji Verify client, handoff, normalisation, gate.
First unattended runs reproduced the manual baseline exactly. A gate bug (harness errors
counted as passes) found and fixed. Project handbook started.

**2 Oct.** Retargeted to the Inji 1.0 line, which the problem statement means. Runner taught
Inji Verify 1.0 (DCQL, `/v2/vp-session-request`, the SDK's nonce and client metadata);
stopped writing private keys into logs (redaction + a repository-wide scan). Happy flow
passes on 1.0 unattended; F-10 found (Verify's shipped database script breaks every
submission). REVIEW results settled with Verify's own verdict. Full verifier plan: 9 of 11
exercised, all consistent with conformance; baseline recorded.

**26 Oct (deadline extended to 2 Nov).**

- `OpenIDConformanceTest` in Inji Verify's api-testrig; runner `--endpoint`.
- One Compose stack for the suite and Inji Verify; CI (tests, stack validation, on-demand run).
  The Compose stack reproduced the 2 Oct baseline check for check.
- Inji Certify added to the stack (release-1.0.x, its own authorisation server, SD-JWT
  credential configuration, transaction code) and the issuer side to the runner
  (pre-authorized offers, transaction codes). Full 15-module issuer plan; F-12–F-15 recorded;
  baseline recorded.
- `OpenIDConformanceTest` in Inji Certify's api-testrig.
- Combined run: both plans, one result, one gate.
- Both testrig classes run in runner mode live; a missing base URL now fails with a clear
  message instead of a confusing one.
- Consolidated report and badge (`--report`, `python -m runner.report`).
- `run-full-stack-conformance.sh`; CI workflow renamed to the problem statement's name and
  extended to Certify and combined runs.
- Architecture, status, self-certification and troubleshooting documents.

Commits: this repository's `git log`; forks: `ab3feb4`, `e591115` (inji-verify) and
`8375fbc`, `7a87fc3` (inji-certify) on `feature/openid-conformance-test`.

---

## What is left, in order

1. **Fresh-clone test** of the README instructions on a clean checkout (catches anything
   that only works on this laptop).
2. **Slide deck** and **video** (2–5 min): the architecture diagram, one combined run, the
   report, the testrig report, the findings.
3. **Signed evidence exports** from the suite UI for anything to be reported upstream.
4. **Contribution record**: make the team split in the docs match the history.
5. **College IDs, cloud folder, submission email** to decode@mosip.io by 1 November.
6. Optional, if time: result diff between runs (good-to-have iv); file F-10 upstream (needs
   the team's decision).
