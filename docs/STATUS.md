# Status against the problem statement

*As of 27 October 2026. Deadline 2 November 2026.*

Problem statement 1, MOSIP Decode 2026: **Automated Conformance Testing for Inji Certify and
Inji Verify against the OpenID Suite.** This page checks each thing the problem statement
asks for against what exists, and points at the evidence. The architecture is in
[ARCHITECTURE.md](ARCHITECTURE.md).

**In one line:** all five mandatory tasks and all five good-to-haves are done and have been
demonstrated on a live stack, and a fresh clone reproduces the results from the README
alone; the bonus (parallel execution) is not done. What remains before submission is the
submission material itself: slide deck, video, college IDs, the email.

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
| iv | Result diff between runs | `python -m runner.diff before.json after.json [--component NAME]`: module by module, what changed in result, verdict or failing checks; exit 1 on any difference | **Done.** Used to show the combined run equals both standalone runs, and that a fresh clone reproduces the combined run exactly |
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
| Usage and installation instructions | README + ARCHITECTURE + TROUBLESHOOTING. **Fresh-clone tested 27 Oct**: a clean clone from GitHub, following only the README (new keys, settings from the example file), ran `--combined` end to end; `runner.diff` shows it identical to the 26 Oct run across all 26 modules |
| API documentation | CONTRACT.md (the result format), ARCHITECTURE.md §2 (suite API use), CLI `--help` |
| Slide deck | **Drafted 27 Oct**, 12 slides (a private claude.ai deck; exports to PowerPoint or PDF) |
| Video, 2–5 minutes | **To record**: shot list in [DEMO-SCRIPT.md](DEMO-SCRIPT.md) |
| Each student's college ID | **To do** |
| Submission email to decode@mosip.io (team, problem statement, URLs) | **To do**, by 1 November |

---

## Results so far

| | Inji Verify 1.0 (release-1.0.x QA build, 15 Oct) | Inji Certify 1.0 (release-1.0.x QA build) |
|---|---|---|
| Suite | Conformance suite build of 27 Oct 2026, pinned by digest | same |
| Plan | OID4VP 1.0 Final verifier, 12 modules | OID4VCI 1.0 issuer, 14 modules |
| Variant | sd_jwt_vc · url_query · redirect_uri · direct_post | pre-authorized code, issuer-initiated · sd_jwt_vc · DPoP · private_key_jwt |
| Suite results | 5 PASSED, 6 REVIEW, 1 FAILED | 3 PASSED, 1 WARNING, 2 SKIPPED, 8 FAILED |
| What that means | 11 consistent with conformance once each REVIEW is settled by Verify's own verdict. **1 real defect, F-16**: a revoked credential is accepted, because Verify never checks the status of SD-JWT credentials | The 3 passes are negative tests, each checked in Certify's log to be rejected for the right reason; 2 skips are optional features Certify does not offer; every failure traced to findings F-12–F-15 or an optional feature |
| Gate | Passes against the baseline; F-16 reported on every run as a known defect | Passes against the baseline |

On the earlier suite build (19 September), used until 27 October, the verifier plan had 11
modules (4 PASSED, 7 REVIEW) and the issuer plan 15. Every module the two builds share gives
the same result; the change is three verifier modules added, three dropped across the two plans.

Inji Verify was moved on 27 October from the published `1.0.0-alpha.1` to MOSIP's QA build of
`release-1.0.x` (commit `429293f`, the build that will become `1.0.0-rc.1`; it moves the service
logic into a new `verify-core` module and updates `vc-verifier` to 1.10.0-SNAPSHOT). All 12
modules give exactly the same results and checks on both. F-10 and F-16 are still present.

Findings: 16 catalogued in `docs/findings/findings.tex`. F-01–F-09 against Inji Verify
0.18.2 (several fixed on the 1.0 line); F-10, F-11 and F-16 on Inji Verify 1.0; F-12–F-15 on
Inji Certify 1.0. None has been filed upstream yet; F-10 (with its fix) is drafted in
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

**27 Oct.**

- Fresh-clone test. It found three gaps, all fixed: per-developer settings only in the
  handbook (now in the README, with `configs/runner.local.example.json`), `cryptography`
  missing from `requirements.txt`, and a traceback instead of a clear message on a missing
  key. Then the clean clone reproduced the combined run exactly.
- Result diff (`runner/diff.py`).
- Signed exports of the evidence plans, kept out of git (see below).
- First full run on GitHub Actions (run 6): passed, but on a newer suite than ours, because the
  workflow pulled `latest`. Suite now **pinned by digest** to the 27 Oct build; baseline moved
  to it and every new module checked against its log; local run identical to CI run 6.
- **F-16**: Inji Verify accepts a revoked SD-JWT credential (status check not implemented in
  MOSIP's `vc-verifier`, and the gap fails open). Gate rule narrowed so a known defect the suite
  itself fails, recorded as a finding, is reported but does not keep the gate red.
- Both forks merged with upstream `release-1.0.x` (no conflicts); testrig classes rebuilt
  (`1.0.0-rc.1-SNAPSHOT`) and passing in runner mode on the new stack: Verify 13/13,
  Certify 15/15.
- **Inji Verify moved to the `release-1.0.x` QA build** (pinned by digest; `1.0.0-alpha.1` still
  selectable from `docker/.env`). `runner.diff` against the alpha.1 run: no differences across
  26 modules. F-16 re-checked in the shipped `vc-verifier` 1.10.0-SNAPSHOT bytecode: SD-JWT
  status checking still throws "not supported", and Verify still reads that as not revoked.
  Baseline evidence moved to the new build; testrig classes 13/13 and 15/15 on it.
- Fixed the result summary's `skipped` count, which counted modules missing from the baseline
  instead of modules the suite skipped (Certify's 2 skips showed as 0).

Commits: this repository's `git log`; forks: `ab3feb4`, `e591115` (inji-verify) and
`8375fbc`, `7a87fc3` (inji-certify) on `feature/openid-conformance-test`.

---

## What is left, in order

1. **Review the deck** and **record the video** (2–5 min) following [DEMO-SCRIPT.md](DEMO-SCRIPT.md).
2. **Contribution record**: make the team split in the docs match the history.
3. **College IDs, cloud folder, submission email** to decode@mosip.io by 1 November. The
   signed exports in `evidence/` go in the cloud folder.
4. Optional: file F-10 upstream (needs the team's decision).

**On the signed exports.** `evidence/` (gitignored) holds the suite's signed export of each
evidence plan: `uzQR679oonrne` and `q4RAMcjJWpAhF` (the combined run), `2WXPDhBNMwyCL`
(Verify, Compose stack, same results as the 2 Oct baseline) and `89gcoUu8shPu1` (Certify
baseline), one signature per module. The suite deliberately does not redact private keys
from its logs, and a signed export cannot be redacted without breaking the signature, so the
zips contain our **test** keys. That is why they are not in git. After sharing them,
regenerate the test keys (README, *Per-developer settings*). The 2 Oct plan `nupFFSGqySsbb`
was on the earlier hand-built stack's database and is not exportable from this one.
