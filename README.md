# MOSIP Decode 2026 — PS1: Automated Conformance Testing

Automated conformance-testing harness for **Inji Certify** and **Inji Verify** against the
OpenID Foundation conformance suite.

**Team**: Shardul Chogale (conformance engine and evidence) · Mukta Varak (platform and delivery)

**Problem statement**: *Automated Conformance Testing for Inji Certify and Inji Verify
against OpenID Suite* (Medium complexity)
**Status**: in progress — environment and baseline built 20 September (pre-kickoff);
event officially started 23 September 2026

Work is divided by skill into two halves that meet at a single JSON contract, split roughly
evenly between us — see [the contribution split](docs/PLAN.md#contribution-split) for the
per-task breakdown and how it maps onto the problem statement's deliverables.

---

## What this is

Inji Certify issues verifiable credentials; Inji Verify checks them. Both claim to follow
OpenID standards (OpenID4VCI for issuance, OpenID4VP for presentation). The OpenID
Foundation publishes a **conformance suite** that checks whether an implementation actually
obeys the spec it claims to — but today that suite is driven by hand, one click at a time,
through a web UI.

This project replaces the human with a script: spin up the components and the suite, drive
the suite's REST API to run the issuer and verifier plans, and feed the results into each
module's existing `api-testrig` so conformance becomes a gate on every release.

---

## Documentation

**Start with the [Project Handbook](docs/handbook/handbook.pdf)** — the clean guide to
running everything from a fresh machine to shutdown, a record of every step taken, and
the day-by-day planner to the 26 October deadline. Source: `docs/handbook/handbook.tex`.

| Document | What it covers |
|---|---|
| [docs/handbook/handbook.pdf](docs/handbook/handbook.pdf) | **Start here.** Mentor brief, start-to-end guide, record of steps, planner |
| [docs/SETUP.md](docs/SETUP.md) | First-time setup, macOS and Windows |
| [docs/RUNBOOK.md](docs/RUNBOOK.md) | Starting, accessing and cleanly shutting down the stacks |
| [docs/PLAN.md](docs/PLAN.md) | Four-week plan and role split |
| [docs/CONTRACT.md](docs/CONTRACT.md) | The runner→testrig JSON contract |
| [docs/WEEK2.md](docs/WEEK2.md) | Day-by-day build plan for the conformance runner |
| [docs/findings/findings.tex](docs/findings/findings.tex) | Dated findings log, failure catalogue, open questions for mentors |

Build the findings PDF:

```bash
cd docs/findings && pdflatex findings.tex && pdflatex findings.tex
```

---

## Running the harness

```bash
python3 -m pip install -r requirements.txt
./run-conformance.sh --component verify
```

Also `--component certify` and `--combined`. Exit status is the gate's verdict: `0` when
nothing regressed against the recorded baseline, `1` on a regression, `2` on a configuration
error — which is what CI should key on.

The stack must be up first (see [docs/RUNBOOK.md](docs/RUNBOOK.md)), and `configs/runner.json`
carries a per-developer ngrok hostname you will need to change.

> **Status**: unit-tested but **not yet run against a live conformance suite**. The handoff
> and screenshot mechanisms are derived from the suite's source, not yet observed working.

```bash
python3 -m pytest tests/ -q
```

## Repository layout

```
runner/        the conformance runner — suite client, handoff, gate, orchestrator
tests/         unit tests (run without Docker; normalisation uses the real Day 1 log)
docs/          setup, runbook, plan, contract, week plan, findings (LaTeX)
logs/          exported conformance suite logs, by date — our evidence
scripts/       standalone harness tooling
configs/       runner config, test plan configurations, the contract fixture and baseline
```

This repo holds **our** work. The upstream code lives in sibling clones — see SETUP.md.

---

## Upstream repositories

| Repository | Role |
|---|---|
| [mosip/inji-verify](https://github.com/mosip/inji-verify) | Verifier under test |
| [mosip/inji-certify](https://github.com/mosip/inji-certify) | Issuer under test |
| [mosip/mosip-functional-tests](https://github.com/mosip/mosip-functional-tests) | `api-testrig` framework we integrate into |
| [openid/conformance-suite](https://gitlab.com/openid/conformance-suite) | The conformance suite itself |
| [conformance-suite-automated-testing-tutorial](https://gitlab.com/openid/conformance-suite-automated-testing-tutorial) | OpenID Foundation's own automation worked example |

### Our forks

The `OpenIDConformanceTest` work lands on branches of these forks, shaped so each could be
opened as an upstream pull request. `api-test/` lives inside `inji-verify` and
`inji-certify` — not in `mosip-functional-tests`, which carries only `apitest-commons`.

- Shardul: [inji-verify](https://github.com/shard-c6/inji-verify) ·
  [inji-certify](https://github.com/shard-c6/inji-certify) ·
  [mosip-functional-tests](https://github.com/shard-c6/mosip-functional-tests)
- Mukta: <!-- TODO: add once her forks exist -->

---

## Findings so far

Nine findings catalogued against Inji Verify 0.18.2 on day one, eight confirmed with
evidence from the OpenID Foundation's own conformance suite. Headlines:

- **Nonce has insufficient entropy** — it is a base64-encoded millisecond timestamp rather
  than a random value. Confirmed independently by the suite: 73.68 bits of Shannon entropy
  against a 96-bit threshold.
- **No DCQL support** — Verify implements the superseded Presentation Exchange query model,
  so no module in the OID4VP 1.0 Final verifier plan can complete.
- **No `direct_post.jwt`** — response mode is a hardcoded constant, so HAIP certification is
  currently impossible.

Full catalogue with evidence, severity and spec references in the findings document. Each
finding is tagged CONFIRMED or UNVERIFIED; nothing is reported upstream until it is
reproducible and the root cause is understood.

---

## License

Source contributions are intended for upstream donation to MOSIP on request, per the
MOSIP Decode rules.
