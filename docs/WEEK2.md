# Week 2 build plan — the programmatic conformance runner

**Dates**: 29 September – 5 October 2026 (assumes the ~21 October deadline; see PLAN.md)
**Owner**: Shardul
**Goal**: one command produces a structured pass/fail result for the Inji Verify verifier
plan with zero manual UI interaction.

This is the riskiest week and the technical core of the submission. Everything else —
testrig integration, combined run, CI — is plumbing around this.

---

## What already exists, and what has to be built

| Piece | State |
|---|---|
| Suite API client | **Exists.** `conformance-suite/scripts/conformance.py`, 465 lines: `wait_for_state` with `/wait-state` long-polling, `create_test_plan`, `create_test_from_plan_with_variant`, `get_test_log`, `exportjson`, `exporthtml`. Use it; don't reimplement |
| Worked example | **Exists.** The tutorial's `test.py` shows the create-plan → iterate-modules → wait loop. It targets a hosted OP with browser automation, so the shape transfers but the interaction model does not |
| Authorisation-request URI construction | **Exists, partially.** `scripts/build-oid4vp-uri.py`, currently a clipboard filter |
| Request generation via Verify's API | **To build.** Nothing calls `/vp-session-request` yet |
| The interactive handoff | **To build. This is the hard part** |
| Result normalisation to the contract | **To build** |
| Gate / expected-failures evaluation | **To build** |

The honest framing: roughly 40% of this week is wiring existing parts together, and 60% is
the interactive handoff, which has no worked example anywhere because the OpenID Foundation's
own tutorial solves the equivalent problem with Selenium against a browser.

---

## The core problem: verifier plans are inverted

Issuer tests are straightforward — the suite plays the wallet and drives everything. **The
verifier plan is the other way round.** The suite waits, passively, for the verifier to
initiate a presentation request, and expects a human to paste the resulting
`openid4vp://` URI into a web form.

So each module needs this sequence, and the order is not negotiable:

```
1. create module from plan          -> suite returns testId, status CREATED
2. poll until status == WAITING     -> the suite is now listening
3. POST Verify /vp-session-request  -> Verify mints an authorisation request
4. build the openid4vp:// URI       -> from the JSON in step 3
5. submit the URI to the suite      -> the handoff
6. poll until FINISHED / INTERRUPTED
7. fetch + archive the signed log
8. normalise to the contract
```

**Step 2 must complete before step 3.** Verify's authorisation requests expire 300 seconds
after issue (`Constants.DEFAULT_EXPIRY`). Generating the request before the module is
listening burns part of that budget for nothing, and on Day 1 it produced a failure
(`dgeeosZpIfDK1bA`) that was nearly filed as a defect. Generate late, submit immediately.

### Step 5 — RESOLVED 24 September, from source

**The handoff needs no browser.** `AbstractVP1FinalVerifierTest.start()`:

```java
getBrowser().requestUriInput(env.getString("authorization_endpoint"),
    "Paste the openid4vp:// authorization request produced by the verifier under test;
     its query string will be delivered to this test's authorization endpoint.");
```

and `handleHttp()` dispatches on `path.equals("authorize")`. The test publishes
`authorization_endpoint` through `exposeEnvString`, readable at `GET /api/runner/{id}`.

So delivery is an ordinary HTTP GET to that endpoint with the verifier's query parameters.
The suite's paste box is a convenience wrapper over exactly that call. Implemented in
`runner/handoff.py`; the fallback plan is not needed.

**Still unconfirmed against a live suite.** This is read from source, not observed.

### The screenshot gate — RESOLVED 24 September, from source

The suite has a purpose-built automated path. `handleVerificationEvidenceRequest()` serves
an HTML stand-in page, and `fillScreenshotPlaceholderViaBrowserAutomationIfConfigured()`
fills the placeholder when the plan config carries a `browser` entry matching the evidence
URL. The source comment says why it exists: *"in automated runs there is no verifier UI a
human could take a real screenshot of."*

A `browser` block is in `configs/runner.json`. **The match pattern is an educated guess at
the evidence URL and must be validated on a live run** before the submission claims
"fully unattended".

---

## Day plan

Fixed points first, then the parts that can absorb slippage.

### Day 1 (Mon 29 Sep) — DONE EARLY, 24 September

- [x] Read `conformance-suite/` for the endpoint behind the manual paste form
- [x] Same for the screenshot path
- [x] Both answers written into this file
- [x] `runner/` scaffolded
- [ ] **Confirm both against a running instance with `curl -k`** — carried forward; Docker
      was not running when the code was written

Brought forward from Week 2 into Week 1 because the answers were cheap to obtain and
everything else depended on them. The scaffolding and most of Days 2–5 followed on the same
day; what remains is the live validation, which is the real exit condition.

### Day 2 (Tue 30 Sep) — Verify's side

- [ ] `verify_client.py`: `POST /vp-session-request`, return the parsed response
- [ ] Promote `build-oid4vp-uri.py` to a library function, keeping the CLI entry point
      working — it is still the fastest manual debugging tool we have
- [ ] Liveness check against `/vp-request/{id}` before submitting, per the runbook
- [ ] **Resolve F-05 while in this code.** The current script never emits `client_metadata`,
      so the suite's complaint about its absence may be our artefact rather than Verify's
      defect. Compare the actual QR payload from the UI against our reconstruction. This is
      a five-minute check that decides whether F-05 goes upstream

**Exit condition**: a fresh, live authorisation request URI from a Python function call.

### Day 3 (Wed 1 Oct) — the loop, one module

- [ ] Wire steps 1–7 for `oid4vp-1final-verifier-happy-flow` alone
- [ ] Archive the log and its `.sig` to `logs/<date>/` automatically. The signature is what
      makes a log evidence rather than a file we could have edited
- [ ] Handle the failure modes explicitly: module never reaches WAITING; request expires
      mid-handoff; suite returns INTERRUPTED. Each needs a distinguishable error, because
      "the run failed" is useless in CI

**Exit condition**: one module, end to end, no human. Reproducible twice in a row.

### Day 4 (Thu 2 Oct) — the whole plan

- [ ] Iterate all 12 modules; per-module variants from the plan, as the tutorial does
- [ ] Sequential first. **Parallelism is a bonus task — do not attempt it this week**;
      Verify is a single instance and concurrent presentation requests are an untested
      interaction
- [ ] Plan name and variants read from config, never hard-coded — this is what keeps Q1
      (1.0 Final vs ID2) a config change rather than a rewrite
- [ ] Run the **ID2 verifier plan** through the same runner. It is one module and the most
      likely source of an actual pass, which is what proves the pipeline reports passes and
      not just failures

**Exit condition**: `python -m runner --component verify` runs the plan unattended.

### Day 5 (Fri 3 Oct) — the contract and the gate

- [ ] Emit `docs/CONTRACT.md`'s shape. Validate against `configs/contract/example-run.json`
- [ ] Implement the gate: load `expected-failures.json`, compute `verdict`, `regression`,
      `improvement`, populate `gate`
- [ ] Extend the baseline to all 12 modules now that they have been run, each with its
      reason and evidence path
- [ ] Hand Mukta a real generated file to replace the hand-made fixture

**Exit condition**: the Java side is unblocked on real output.

### Days 6–7 (Sat–Sun) — buffer

Deliberately empty. Week 2 is the week most likely to overrun; if it doesn't, start the
GitHub Actions workflow early, since that de-risks Week 4.

---

## Shape of the code

```
runner/
  __init__.py
  config.py        # plan names, variants, endpoints - all of it data
  suite.py         # thin wrapper over the suite's conformance.py
  verify_client.py # Verify's /vp-session-request; the openid4vp:// URI builder
  handoff.py       # the interactive step, isolated so a fallback swaps in cleanly
  normalise.py     # suite log -> contract JSON
  gate.py          # expected-failures evaluation
  __main__.py      # python -m runner --component verify|certify|combined
```

`handoff.py` is deliberately its own module. It is the piece most likely to need a
semi-automated fallback, and isolating it means that fallback is a swapped implementation
rather than a rewrite.

`run-conformance.sh` is a thin wrapper over `python -m runner`, because the problem
statement asks for that entry point by name. It should contain no logic worth testing.

---

## Definition of done

- [ ] `python -m runner --component verify` completes the plan with no human interaction,
      or with exactly one documented manual step whose necessity has been demonstrated
- [ ] Output validates against the contract
- [ ] The gate returns `passed: true` against the recorded baseline, and `false` when the
      baseline is deliberately altered to simulate a regression — **test the gate's failure
      path, not just its success path**
- [ ] Signed logs archived automatically under `logs/<date>/`
- [ ] Mukta has real runner output to build against
- [ ] Q1's answer, if it arrives, would cost a config edit and nothing more

---

## What is explicitly not in this week

Inji Certify (Week 3), the api-testrig Java classes (Mukta), the combined run (Week 3),
GitHub Actions (Week 4, or buffer), parallel execution (bonus, last), result diff between
runs (Week 4). Adding any of these to Week 2 risks the one thing that must work.
