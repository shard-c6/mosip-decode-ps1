# The runner → testrig contract

**Status**: draft, 23 September 2026. Roles agreed; the contract shape still needs Mukta's
review — see the open points at the end.
**Producer**: Shardul — the Python runner emits this file
**Consumer**: Mukta — `OpenIDConformanceTest` reads it and reports TestNG results

Mukta can begin against `configs/contract/example-run.json` immediately; it is real output
shape built from the Day 1 log, so no part of her work waits on the runner.

---

## Why this document exists first

The project splits into a Python half that drives the conformance suite and a Java half
that reports results inside MOSIP's existing `api-testrig`. Those halves meet at exactly
one place: a JSON file. If its shape is agreed now, both sides can be built in parallel
against a fixture and integrate in an afternoon. If it isn't, Week 3 becomes a merge
negotiation under deadline.

**Both sides should be able to start work the moment this is agreed.** The Java side works
against `configs/contract/example-run.json`, which is committed and real — it is built from
the actual Day 1 log of `MtzpWoD2dVgtic0`, not invented.

---

## Design rules

**1. Record what the suite said, separately from what we do about it.**
`result` is the conformance suite's own verdict, untouched. `verdict` is what TestNG should
report after the expected-failures gate has been applied. Keeping them in separate fields
is what lets a known failure be reported as a TestNG pass without the artefact ever
claiming the suite passed. Collapsing them into one field would mean losing the evidence.

**2. Every value the Java side needs is present; it never re-reads the suite.**
The testrig should not need credentials for, or network access to, the conformance suite.
It reads one file. This also means a run can be replayed, diffed, and archived.

**3. Names mirror the suite's own vocabulary.**
`src`, `result`, `msg`, `requirements`, `testId`, `testName`, `variant` are the suite's
field names, carried through unchanged. Renaming them would mean maintaining a translation
table for no benefit and would make log entries harder to trace back.

**4. Additive evolution only.** `schemaVersion` is present from the start. Consumers ignore
unknown fields; producers never repurpose an existing one.

---

## Top-level shape

```
{
  "schemaVersion": "1.0",
  "run":        { ... }        // one per invocation
  "components": [ { ... } ],   // one per component; two in a combined run
  "gate":       { ... }        // the benchmark decision for the whole run
}
```

### `run`

| Field | Type | Notes |
|---|---|---|
| `runId` | string | Unique per invocation. `<mode>-<UTC timestamp>` is fine |
| `mode` | enum | `verify` · `certify` · `combined` — mirrors `run-conformance.sh` |
| `startedAt` / `finishedAt` | ISO 8601 UTC | |
| `durationMs` | integer | |
| `harnessVersion` | string | Our git describe or tag — so a report identifies the code that made it |
| `conformanceSuite` | object | `version`, `revision`, `baseUrl` |

### `components[]`

One entry per component exercised. A `--combined` run has two; a `--component verify` run
has one. **The Java side reads only the entry for its own module**, which is what keeps the
per-module gates independent as the problem statement requires.

| Field | Type | Notes |
|---|---|---|
| `component` | enum | `inji-verify` · `inji-certify` |
| `role` | enum | `verifier` · `issuer` |
| `version` | string | e.g. `0.18.2` |
| `endpoint` | string | The same `env.endpoint` the testrig already targets |
| `plan` | object | `planId`, `planName`, `alias`, `specification`, `variant`, `planUrl` |
| `summary` | object | Counts, below |
| `modules` | array | One per conformance module |

`summary` carries `total`, `passed`, `failed`, `warning`, `skipped`, `expectedFailures`,
`unexpectedFailures`, `newPasses`. The last three are the gate's working, exposed so a
human reading the report can see why it passed or failed without recomputing anything.

### `components[].modules[]`

The unit that becomes one TestNG test.

| Field | Type | Notes |
|---|---|---|
| `moduleName` | string | The suite's `testName`, e.g. `oid4vp-1final-verifier-happy-flow` |
| `testId` | string | The suite's `testId` — the key for fetching the log |
| `variant` | object | Per-module variant as the plan assigned it |
| `status` | enum | Suite lifecycle: `CREATED` · `WAITING` · `RUNNING` · `FINISHED` · `INTERRUPTED` |
| `result` | enum | **Suite's verdict, untouched**: `PASSED` · `FAILED` · `WARNING` · `REVIEW` · `SKIPPED` |
| `verdict` | enum | **What TestNG reports**: `PASS` · `FAIL` · `SKIP` — after the gate |
| `expected` | enum/null | From the expected-failures file: the result recorded as the baseline |
| `regression` | boolean | True when `result` is worse than `expected`. This is what fails a build |
| `improvement` | boolean | True when better than `expected`. Never fails a build; prompts a baseline update |
| `counts` | object | `success`, `failure`, `warning`, `info` — from the log entries |
| `checks` | array | Every non-`SUCCESS` log entry (below) |
| `startedAt` / `durationMs` | | |
| `logUrl` | string | Deep link into the local suite, for a human |
| `logFile` / `logSignatureFile` | string | Repo-relative paths to the archived evidence |

### `components[].modules[].checks[]`

Carried through from the suite's log, filtered to entries that are not `SUCCESS` — those
are the ones a failure message needs to quote. Shape follows the suite exactly:

| Field | Notes |
|---|---|
| `src` | The check class, e.g. `ExtractDCQLQueryFromAuthorizationRequest` |
| `result` | `FAILURE` · `WARNING` · `INFO` · `INTERRUPTED` |
| `msg` | The suite's own message, verbatim |
| `requirements` | Array of spec refs as the suite emits them, e.g. `["OID4VP-1FINAL-6"]` |
| `detail` | Object — the remaining suite-supplied keys (`actual`, `expected`, `invalid_chars`, …) |
| `findingRef` | *Ours.* Links to the findings catalogue, e.g. `F-03`. Null when unmapped |

`findingRef` is the one field we add rather than carry through. It is what turns a CI
failure message into "this is F-03, the known DCQL gap, documented with evidence" instead
of a raw stack of check names — and it keeps the findings document connected to the
running system rather than drifting into a separate artefact.

### `gate`

| Field | Notes |
|---|---|
| `policy` | `regression-from-baseline` (our default) or `absolute-pass-rate` |
| `baselineFile` | Path to the expected-failures file used |
| `baselineUpdatedAt` | So a stale baseline is visible |
| `passed` | boolean — **this is what the build fails on** |
| `regressions` | Array of `{component, moduleName, expected, actual}` |
| `improvements` | Same shape. Reported, never fatal |
| `unknownModules` | In the run but not in the baseline. Policy: warn, don't fail |

---

## How the verdict is decided

Given the suite's `result` and the baseline's `expected`:

| `expected` | `result` | `verdict` | `regression` | Why |
|---|---|---|---|---|
| `PASSED` | `PASSED` | `PASS` | no | Still good |
| `PASSED` | `FAILED` | `FAIL` | **yes** | A real regression. This is the case the gate exists for |
| `FAILED` | `FAILED` | `PASS` | no | Known, documented failure — no worse than baseline |
| `FAILED` | `PASSED` | `PASS` | no | Improvement; flagged so the baseline gets updated |
| absent | anything | `SKIP` | no | Unknown module — surfaced, not fatal |

**The third row is the one that needs explaining in the submission.** Reporting a known
conformance failure as a TestNG pass looks wrong until you see the alternative: with
Inji Verify's current DCQL gap, every module fails, so an absolute gate makes the build
permanently red and therefore ignored. A gate nobody can act on is not a gate. The suite's
true verdict is preserved in `result` and printed in the Extent report regardless, so
nothing is hidden — the build simply fails on *change*, not on *state*.

This is Q4 to mentors. If MOSIP wants the absolute reading instead, `gate.policy` switches
and nothing else moves.

---

## The expected-failures file

`configs/contract/expected-failures.json` — under version control, reviewed like code.
Changing it is how a baseline moves, and the diff is the audit trail.

```json
{
  "schemaVersion": "1.0",
  "updatedAt": "2026-09-20T06:13:23Z",
  "note": "Baseline from the Day 1 evidenced run. See docs/findings/findings.tex.",
  "components": {
    "inji-verify": {
      "oid4vp-1final-verifier-test-plan": {
        "oid4vp-1final-verifier-happy-flow": {
          "expected": "FAILED",
          "reason": "F-03 — no DCQL support; terminates at ExtractDCQLQueryFromAuthorizationRequest",
          "evidence": "logs/2026-09-20/...MtzpWoD2dVgtic0.json"
        }
      }
    }
  }
}
```

Every entry carries a `reason` and an `evidence` path. An expected failure without a
documented reason is a silenced test, and silenced tests are how gates rot.

---

## Open points for Mukta

1. Does the Extent report want the `checks` array rendered as a table, or is the first
   `FAILURE` entry's `msg` enough for the TestNG assertion message?
2. Should `SKIP` or `FAIL` be reported for a module the suite left `WAITING` because the
   interactive handoff failed? It is a harness fault, not a component fault — I lean `SKIP`
   with a loud message, but the testrig's conventions should decide.
3. Is there an existing MOSIP convention for the TestNG test name, or is
   `conformance.<component>.<moduleName>` acceptable?
4. Anything in the Extent/`apitest-commons` result model this shape can't populate?
