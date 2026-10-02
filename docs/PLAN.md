# Plan — MOSIP Decode PS1

**Team**: Shardul Chogale (`shard-c6`), Mukta Varak
**Official kickoff**: 23 September 2026 — Day 2 of the event as this plan is written
**Deadline**: **26 October 2026, 11:59 PM IST** — confirmed 30 September on the official
event page ("Final Submission Deadline"). Earlier versions of this file assumed ~21 October;
the real date adds five days, used as a fifth week for finishing and submitting.
**Target version (2 Oct)**: the Inji **1.0 line** — `1.0.0-alpha.1` is the newest published
build — not 0.18.2, which everything before 2 October was tested on.
**Mandatory submissions** (kickoff, 23 Sep): source code, working prototype, slide deck,
**video demo**.
**Weekly Connect** (mentors): Wednesdays 5:00–6:00 PM IST — 30 Sep, 7, 14, 21 Oct.

> **The day-by-day schedule for both of us now lives in the Project Handbook, Part 4
> (`docs/handbook/handbook.tex`).** It supersedes the week sections below wherever they
> differ. This file keeps the reasoning — the split, where the code lives, the risks.
**Deliverable**: automated conformance-testing harness for Inji Certify and Inji Verify

---

## Where we actually are

**One day of work exists, and it happened before the event started.** On 20 September —
three days pre-kickoff — we stood up the conformance suite and Inji Verify, ran one
verifier module end to end by hand, and catalogued nine findings. That is banked, and it
means Week 1's usual work (environment, first baseline) is substantially done on day two.

It also means the earlier version of this file, which dated Week 1 from 20 September, was
measuring against the wrong calendar. Corrected here.

**Nothing has happened between 20 and 23 September.** The Day 2 list below is the same Day
2 list written on Day 1; it was never started.

### Banked from 20 September (pre-kickoff)

- [x] Conformance suite 5.3.1 running locally via prebuilt images
- [x] Inji Verify 0.18.2 running (3 containers)
- [x] ngrok tunnel; Verify's `did:web` DID resolves publicly
- [x] Confirmed the suite's REST API needs no token in the local dev profile
- [x] Test plan created and validated (`lN7C4DH1HvYmc`)
- [x] Module 01 `happy-flow` executed; signed log exported as evidence
- [x] Nine findings catalogued, eight confirmed
- [x] `build-oid4vp-uri.py` — first reusable piece of the harness
- [x] Repo scaffolded; forks of all three MOSIP repos created

### Carried forward, not started

- [ ] Modules 02–11 of the 1.0 Final alpha verifier plan
- [ ] The ID2 verifier plan (1 module) — most likely source of an actual pass
- [ ] Resolve F-05 (`client_metadata` in inline mode) — currently UNVERIFIED
- [ ] `api-test/` running in both `inji-verify` and `inji-certify`; document the existing
      TestNG result shape
- [ ] Push the local commit; fill the fork URLs in README.md
- [ ] Agree the role split (see below) and the JSON contract between the two halves
- [ ] Put Q1–Q7 to mentors

---

## The split, and why

**Agreed 23 September 2026.** Earlier versions of this file carried a placeholder split
that assigned work by language — Python to one of us, Java to the other. That was drawn
before either of us had said what we are actually good at, and it assigned the Java/TestNG
work to the person with no Java background. Replaced with the split below, which follows
the skills.

**Shardul**: AI/MLOps and data engineering. **Mukta**: cloud engineering.

### The seam

The seam is not Python versus Java. It is **the environment and how results are delivered**
against **what gets tested and how it is judged**. Each of us owns one of those end to end,
which means each of us has a complete, demonstrable deliverable rather than a slice of one.

| | Owner | Scope |
|---|---|---|
| **Platform and delivery** | **Mukta** | Everything from a clean machine to a green or red verdict in CI |
| **Conformance engine and evidence** | **Shardul** | Everything from "what do we test" to "is this result acceptable" |

### Mukta — platform and delivery

- The unified `docker-compose.yml` bringing up Inji Certify, Inji Verify and the
  conformance suite together. **Deliverable (a), and the hardest infrastructure piece in
  the project**: three separate compose projects that today cannot see each other's
  localhost, plus Verify's `did:web` identity which must resolve over public HTTPS
- The networking layer — public hostname, inter-project reachability, health checks
- Getting `api-test` to build and run in both `inji-verify` and `inji-certify`: Java 21,
  Maven, `settings.xml` from `mosip-functional-tests`, the `apitest-commons` JAR built
  first. This is build infrastructure, not Java authoring
- `OpenIDConformanceTest` in both repos — the ~250-line mapping from the contract JSON to
  TestNG pass/fail/skip. No protocol logic; it reads a file and reports. It belongs here
  because it lives in code she is already making build, and because CI is what invokes it
- The GitHub Actions workflow — deliverable (d)
- The fresh-clone reproducibility test: does our own README actually work on a machine that
  has never run this?
- Setup, troubleshooting and CI documentation; the demo recording

### Shardul — conformance engine and evidence

- The Python runner driving the conformance suite's REST API: a polling state machine with
  retries, a failure taxonomy, and the interactive handoff
- The contract, result normalisation, the benchmark gate, expected-failures, result diff.
  **This is regression gating on evaluation metrics** — structurally the same problem as
  model-evaluation gating, which is why it sits on this side
- The combined run and the one-command entry point
- Test plan and variant configuration
- The findings catalogue, evidence handling, and upstream issues
- Architecture, automation and self-certification documentation

### Where they meet

Exactly one place: the JSON file described in `docs/CONTRACT.md`. Shardul produces it,
Mukta consumes it. A committed fixture built from real Day 1 data
(`configs/contract/example-run.json`) means **neither side waits for the other** — Mukta
can build and test `OpenIDConformanceTest` against it before the runner exists.

Agree any change to that contract before making it, and keep the daily 15-minute sync.

### The honest risk

**Neither of us is a Java developer**, and `OpenIDConformanceTest` is mandatory task (iii).
It is owned by Mukta by agreement, and it is deliberately small and logic-free to keep that
ownership realistic. Mitigations: the fixture is committed so the work can start in Week 1
if she wants a head start; Shardul has read the existing testrig (`InjiTestRunner`,
`injiverifySuite.xml`, the YAML-per-endpoint pattern) and can pair on it. If it is not
moving by the midpoint of Week 3, escalate rather than absorb it quietly — it gates the
whole submission.

### Contribution split

Both of us contribute roughly equally — **Shardul ~49%, Mukta ~51%** on the estimate below.
That is the outcome of assigning work by skill, not a target we decorated the plan to hit,
and it is recorded here so the division is documented rather than inferred.

**It was not balanced when first drafted.** The initial allocation ran about 60/40 toward
Shardul, because Inji Certify's environment was left unassigned and the reporting-side
good-to-haves had drifted onto the runner. Three corrections fixed it: Certify's environment
standup went to Mukta as infrastructure work, result diff and the consolidated report/badge
moved to delivery, and a contradiction over who owned the benchmark gate was resolved in
favour of the runner.

Effort is estimated in relative points, weighting difficulty and uncertainty rather than
lines of code. Estimates made 23 September and expected to drift; revisit at each week's end.

| Shardul — conformance engine and evidence | pts | | Mukta — platform and delivery | pts |
|---|---|---|---|---|
| Python runner core: suite API, polling, state machine | 5 | | Unified Docker Compose across three projects | 5 |
| The interactive handoff (highest-uncertainty item) | 4 | | Inji Certify environment: PKCS12, DID, auth server, keys | 4 |
| Findings catalogue, evidence handling, upstream issues | 3 | | `OpenIDConformanceTest` in both repos | 4 |
| Verify client and authorisation-request URI builder | 2 | | `api-test` building in both repos | 3 |
| Result normalisation to the contract | 2 | | GitHub Actions workflow | 3 |
| Benchmark gate and expected-failures | 2 | | Result diff, consolidated report and badge | 2 |
| Combined-run orchestration | 2 | | Setup, troubleshooting and CI documentation | 2 |
| Architecture, automation, self-certification docs | 2 | | Demo video and submission slides | 2 |
| Test plan and variant configuration | 1 | | Networking and public-hostname layer | 1 |
| One-command entry point, selective execution | 1 | | Fresh-clone reproducibility test | 1 |
| **Total** | **24** | | **Total** | **27** |

Mapped against the problem statement's own deliverables:

| Deliverable | Owner |
|---|---|
| (a) Docker Compose: Certify + Verify + conformance suite | Mukta |
| (b) Test plan configuration templates | Shardul |
| (c) One-command runner | Shardul |
| (d) GitHub Actions workflow | Mukta |
| (e) Documentation | Split — architecture and automation to Shardul; setup, troubleshooting and CI to Mukta |
| Mandatory (ii) programmatic conformance runner | Shardul |
| Mandatory (iii) per-module api-testrig integration | Mukta |
| Mandatory (iv) combined run | Shardul orchestrates, Mukta reports |

**Let the commit history carry this.** A README claiming a 50/50 split that the git log
contradicts is worse than saying nothing, because anyone assessing the work — judges,
maintainers, an interviewer — can read both. Each of us should commit our own work under
our own identity rather than one person pushing on behalf of both. Where we genuinely pair,
use `Co-Authored-By` so the record is accurate rather than flattering.

### Where the code lives

Decided 23 September:

- **Runner, configs, orchestration, docs** → `mosip-decode-ps1` (this repo)
- **`OpenIDConformanceTest` and its wiring** → branches on our **forks** of `inji-verify`
  and `inji-certify`, shaped so they could be opened as upstream pull requests

The problem statement says to add the class to each module's api-testrig. Note that
`api-test/` lives inside `inji-verify` and `inji-certify` — **not** in
`mosip-functional-tests`, which carries only `apitest-commons`. Working on the forks
satisfies the statement literally and keeps the open-source-contribution path open, which
is worth points and is the reason MOSIP runs this event.

---

## Week 1 — 23–28 September · Close out the baseline, fix the plan

**Goal**: everything pre-kickoff work left open is closed, the design is agreed, and
nothing is left that would surprise us in Week 2.

**Shardul**
- [ ] Modules 02–11 of the 1.0 Final alpha verifier plan. Expect all to interrupt at
      `ExtractDCQLQueryFromAuthorizationRequest` — that uniformity *is* the result, and
      it is the evidence the benchmark rests on
- [ ] The ID2 verifier plan — the draft generation Verify appears to target. The harness
      needs at least one genuinely passing test to prove the pipeline reports passes, not
      just failures
- [ ] Resolve F-05 one way or the other; it cannot go upstream while UNVERIFIED
- [ ] Push the unpushed commit; fill the fork URLs in README.md

**Mukta**
- [ ] `api-test/` building and running in both repos — Java 21, Maven, `settings.xml`
      from `mosip-functional-tests`, `apitest-commons` JAR built locally first. **This is
      the week's priority: everything she owns later sits on top of it**
- [ ] Write down the existing TestNG/Extent result shape, so the contract is designed
      against what the testrig actually consumes rather than what we imagine
- [ ] Review `docs/CONTRACT.md` and raise the four open points at the end of it
- [ ] Claim an ngrok static domain of her own — the domain is per-developer

**Both**
- [ ] Agree the role split; update this file with the real one
- [ ] Agree and write down the runner→testrig JSON contract
- [ ] Post Q1–Q7 to the MOSIP community forum (or raise at the Wednesday session). The forum is a
      only channel — and Q1 (which spec version to benchmark) shapes Weeks 2–4

**Design decision that de-risks Q1**: build the runner so the plan name and variant set are
**configuration, not code**. Then whichever way Q1 is answered — 1.0 Final or ID2 — it's a
config change, not a rewrite. Do this regardless of whether an answer ever arrives.

---

## Week 2 — 29 September – 5 October · The programmatic runner

**Goal**: replace the manual clicking with a script. This is the technical core and the
riskiest week.

**Shardul**
- [ ] Runner built on the suite's own `scripts/conformance.py` (the real one — 465 lines
      with `wait-state` long-polling and `exportjson` — not the 10-line tutorial copy):
      create plan, configure variants, start each module, poll, retrieve results
- [ ] Handle the interactive handoff. Verifier modules wait for the verifier to initiate;
      generate the authorisation request through Verify's own `/vp-session-request` API
      rather than the UI. `build-oid4vp-uri.py` already does the URI construction — promote
      it from a clipboard tool to a library function
- [ ] Watch the 300-second expiry: generate the request *after* the module is WAITING,
      never before
- [ ] Verify's verifier plan working end to end before touching Certify
- [ ] Emit results as the agreed JSON contract

**Mukta**
- [ ] **Unified Docker Compose** — Verify plus the conformance suite in one project first,
      solving the cross-project networking and the public-hostname requirement. Certify
      folds in during Week 3. Scheduled here, after `api-test` builds, so the two hardest
      pieces of her work do not overlap
- [ ] `OpenIDConformanceTest` skeleton against `configs/contract/example-run.json` — the
      committed fixture means this is not blocked on the runner being finished
- [ ] Setup and troubleshooting documentation, written while the pain is fresh

**End-of-week check**: one command produces a structured pass/fail result for the Verify
verifier plan with zero manual UI interaction.

**Known risk — the screenshot gate.** The happy-flow module wants a screenshot upload
before reaching REVIEW. That appears to need `POST /api/log/{id}/images`. If it resists
automation, document a semi-automated flow honestly rather than overclaiming (Q6).

---

## Week 3 — 6–12 October · api-testrig integration and the combined run

**Goal**: results stop being a JSON file we look at and start appearing in the same
Extent/TestNG report MOSIP already uses.

**Mukta (lead)**
- [ ] **Inji Certify environment standing up.** `docker-compose-injistack` needs a PKCS12
      keystore from Mimoto onboarding, a publicly resolvable DID endpoint, an external
      authorisation server and partner API keys. This was previously unassigned and is the
      largest single piece of infrastructure work left in the project
- [ ] Fold Certify into the unified compose project alongside Verify and the suite
- [ ] `OpenIDConformanceTest` in Inji Verify's `api-test`, mapping each conformance module
      to a TestNG pass/fail/skip
- [ ] Same for Inji Certify's `api-test`
- [ ] Consume the gate's verdict in the Extent report — `verdict` for the TestNG result,
      `result` and `checks` rendered so a reader sees what the suite actually said. The gate
      logic itself is Shardul's (see the roles section); this is the reporting half
- [ ] **Result diff between runs** — a CI-facing concern, so it sits with delivery
- [ ] Consolidated cross-module report and status badge for the combined run

**Shardul**
- [ ] Combined-run entry point producing one consolidated cross-module report
- [ ] `run-conformance.sh --component certify | --component verify | --combined`
- [ ] Inji Certify's **issuer plan through the runner**, once Mukta has Certify standing up.
      Scope permitting — see the risk note
- [ ] Architecture and automation documentation

**End-of-week check**: all three invocations work and land in the existing api-testrig
output. **This is the minimum viable submission.** If everything stopped here, we would
still have something demoable that satisfies the mandatory tasks.

---

## Week 4 — 13–19 October · CI/CD, documentation, demo, buffer

**Goal**: turn a working build into a submittable one. Nothing new and risky starts.

**Shardul**
- [ ] Good-to-haves in payoff order: selective component/plan execution → expected-failures
      handling. Result diff sits with Mukta as a CI-facing concern
- [ ] Self-certification documentation; findings written up as upstream issues

**Mukta**
- [ ] GitHub Actions running the full check on push, failing on regression
- [ ] Fresh-clone test on a machine that has never run this, following only our README
- [ ] Demo video and submission slides

**Both — final 2–3 days, buffer only**
- [ ] Fresh clone on a machine that has never run this, following only our own README
- [ ] Final combined run recorded
- [ ] Findings filed as GitHub issues against `mosip/inji-verify`
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
- [ ] 1–2 page overview document **or** 5–7 slide pitch deck (confirm the current
      requirement on the Unstop submission criteria page)
- [ ] Demo video, end to end
- [ ] Interoperability findings filed as upstream issues

On IP: MOSIP can request the source be contributed back, so keep the repo clean and
commented from the start rather than tidying at the end.

---

## Risks and fallbacks

**Limited mentor contact.** The kickoff (23 Sep) was held — we have its recording — and mentors are available at the Wednesday sessions, but Q1–Q7 have no channel
but the community forum, and no guaranteed answer. Mitigation: make every decision Q1 could
overturn a configuration value, and state our assumptions plainly in the submission. A
clearly reasoned assumption is defensible; a silent one is not.

**The DCQL gap dominates everything.** Inji Verify implements Presentation Exchange, not
DCQL, so no module in the OID4VP 1.0 Final verifier plan can pass. This is not a blocker —
the harness's value is orchestration, and the problem statement explicitly asks for
benchmark gating and expected-failures handling, which exist *because* components don't
pass everything. But it must be stated clearly in the submission, and it makes the ID2 plan
important as a source of actual passing tests.

**Interactive tests may resist full automation.** Fallback: document a semi-automated flow
honestly rather than overclaiming.

**Inji Certify setup may consume more time than budgeted.** Its `docker-compose-injistack`
needs a PKCS12 keystore from Mimoto onboarding, a public DID endpoint, an external
authorisation server and partner API keys; its issuer plan has 61 modules against the
verifier plan's 12. Fallback: per-module conformance for Verify alone is a complete,
demoable, mandatory-task-satisfying submission. Certify is valuable but is not what makes
or breaks the demo.

**Two-person coordination.** The split is agreed and the halves meet at one interface, with
a committed fixture so neither blocks the other. The residual risk is the Java class —
see "The honest risk" above.

**What never gets cut**: at least one component's conformance run working end to end, and
documentation good enough that a MOSIP maintainer can run it without asking us a question.
