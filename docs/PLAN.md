# Four-week plan — MOSIP Decode PS1

> **Roles below are TENTATIVE.** Shardul to confirm with Mukta and update this file.
> Everything marked *(tentative)* is a proposal, not a commitment.

**Team**: Shardul Chogale, Mukta Varak
**Started**: 20 September 2026
**Deliverable**: automated conformance-testing harness for Inji Certify and Inji Verify

---

## The split, and why

The work divides cleanly along an interface: a **Python side** that drives the OpenID
conformance suite's REST API, and a **Java side** that consumes results inside MOSIP's
existing `api-testrig` (TestNG/Extent). Splitting there lets us work in parallel without
blocking each other, and each of us owns one complete deliverable end to end — which
matters for judging, and for being able to say "I built X" in an internship interview.

| | *(tentative)* |
|---|---|
| **Shardul** | Python/automation: Docker Compose orchestration, the programmatic conformance runner, test-plan JSON configs, the one-command entry point, CI/CD |
| **Mukta** | Java/testrig: `OpenIDConformanceTest` classes, Extent/TestNG integration, benchmark and expected-failures model, documentation, demo video |
| **Both** | The combined-run entry point (the one place the two sides meet), and a daily 15-minute sync so the runner's output format and the testrig's expected input don't drift apart |

The contract between the two halves — the JSON shape the Python runner emits and the Java
side consumes — should be agreed and written down in week 1, before either side builds
much on top of it.

---

## Week 1 — Environment and first baseline

**Goal**: conformance suite and one MOSIP component running, one manual test completed end
to end, results understood.

### Status: substantially complete (Day 1, 20 Sep)

- [x] Conformance suite 5.3.1 running locally via prebuilt images
- [x] Inji Verify 0.18.2 running (3 containers)
- [x] ngrok tunnel; Verify's `did:web` DID resolves publicly
- [x] Confirmed the suite's REST API needs no token in local dev profile
- [x] Test plan created and validated (`lN7C4DH1HvYmc`)
- [x] Test 01 `happy-flow` executed; signed log exported
- [x] Nine findings catalogued, eight confirmed with evidence
- [x] `build-oid4vp-uri.py` — first reusable piece of the harness
- [ ] Tests 02–11 → **Day 2**
- [ ] ID2 verifier plan run (expected to produce actual passes) → **Day 2**
- [ ] Mukta: `api-test/` running in both `inji-verify` and `inji-certify`; document the
      existing TestNG result shape

### Carried forward

Inji Certify was deliberately deferred. Its `docker-compose-injistack` needs a PKCS12
keystore from Mimoto onboarding, a public DID endpoint, an external authorisation server,
and partner API keys. Verify was the cheaper path to a first result. Certify moves to
week 2–3, pending mentor guidance (see Q7 in the findings document).

---

## Week 2 — The programmatic conformance runner

**Goal**: replace the manual clicking with a script. This is the technical core.

**Shardul**
- [ ] Runner built on `run-test-plan.py` / `conformance.py`: create plan, configure
      variants, start each module, poll `/api/runner/{id}/wait-state`, retrieve results
- [ ] Handle the interactive steps — verifier tests need an authorisation request pushed in
      per module; generate these via Verify's own `/vp-session-request` API rather than the UI
- [ ] Verify's verifier plan working end to end before touching Certify
- [ ] Emit results as a stable JSON contract for the Java side

**Mukta**
- [ ] `OpenIDConformanceTest` TestNG class skeleton against that contract
- [ ] Test-plan JSON config templates under version control
- [ ] Architecture section of the documentation, written while the design is fresh

**End-of-week check**: one command produces a structured pass/fail result for the Verify
verifier plan with zero manual UI interaction.

**Risk**: this is the riskiest week. The verifier plans are interactive by design — the
suite waits for the verifier to initiate. If automating the handoff proves harder than
expected, fall back to a documented semi-automated flow and say so plainly (see Q6).

---

## Week 3 — api-testrig integration and the combined run

**Goal**: results stop being a JSON file we look at and start appearing in the same
Extent/TestNG report MOSIP already uses.

**Mukta (lead)**
- [ ] `OpenIDConformanceTest` in Inji Verify's `api-test`, mapping each conformance module
      to a TestNG pass/fail/skip
- [ ] Same for Inji Certify's `api-test`
- [ ] Benchmark gating with an **expected-failures file under version control** — given
      that today's honest baseline is a full set of failures at DCQL extraction, the gate
      must catch *regressions from the recorded baseline*, not absolute pass rates (see Q4)

**Shardul**
- [ ] Combined-run entry point producing one consolidated cross-module report
- [ ] `run-conformance.sh --component certify | --component verify | --combined`
- [ ] Start the GitHub Actions workflow early to de-risk week 4

**End-of-week check**: all three invocations work and land in the existing api-testrig
output. This is the **minimum viable submission** checkpoint — if we had to stop here, we
would still have something demoable.

---

## Week 4 — CI/CD, documentation, demo, buffer

**Goal**: turn a working build into a submittable one. Nothing new and risky starts.

**Shardul**
- [ ] GitHub Actions running the full check on push, failing on regression
- [ ] Good-to-have tasks in payoff order: selective component/plan execution → expected-
      failures handling → result diff between runs

**Mukta**
- [ ] Documentation complete: architecture, how the API automation works, per-component
      handoff, self-certification submission, troubleshooting
- [ ] Demo video and submission slides

**Both — final 2–3 days, buffer only**
- [ ] Fresh clone on a machine that has never run this, following only our own README
- [ ] Final combined run recorded
- [ ] Findings written up as GitHub issues against `mosip/inji-verify`
- [ ] **Submit early.** Only the last submission before the deadline counts, so an early
      submission is a safety net, not a commitment

---

## Submission checklist

- [ ] Docker Compose configuration (Certify + Verify + conformance suite)
- [ ] Test plan configuration templates with correct variants
- [ ] One-command runner script
- [ ] GitHub Actions workflow
- [ ] Documentation: architecture, automation flow, self-certification, troubleshooting
- [ ] Public GitHub repository with a clear README
- [ ] 1–2 page overview document **or** 5–7 slide pitch deck (confirm current requirement
      on the Unstop submission criteria page)
- [ ] Demo video, end to end
- [ ] Interoperability findings filed as upstream issues

On IP: MOSIP can request the source be contributed back, so keep the repo clean and
commented from the start rather than tidying at the end.

---

## Risks and fallbacks

**The DCQL gap dominates everything.** Inji Verify implements Presentation Exchange, not
DCQL, so no module in the OID4VP 1.0 Final verifier plan can pass. This is not a blocker
for our deliverable — the harness's value is orchestration, and the problem statement
explicitly asks for benchmark gating and expected-failures handling, which only make sense
because components don't pass everything. But it must be stated clearly in the submission,
and it makes the ID2 plan important as a source of actual passing tests.

**Interactive tests may resist full automation.** Fallback: document a semi-automated flow
honestly rather than overclaiming.

**Inji Certify setup may consume more time than budgeted.** Fallback: per-module
conformance for Verify alone is a complete, demoable, mandatory-task-satisfying submission.
The combined run and Certify are valuable but not what makes or breaks the demo.

**What never gets cut**: at least one component's conformance run working end to end, and
documentation good enough that a MOSIP maintainer can run it without asking us a question.
