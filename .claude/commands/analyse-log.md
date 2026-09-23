---
description: Analyse an exported conformance log and propose findings
argument-hint: [path to log JSON]
---

Analyse the conformance suite log at **$1** (ask for the path if not given, or use the most
recent file under `logs/`).

Use the `conformance-analyst` agent for this — it holds the full analysis discipline.

Produce:

**1. Outcome summary** — counts of SUCCESS / FAILURE / WARNING / INFO, and where the test
terminated.

**2. What passed** — briefly. Progress matters: reaching twenty checks before failing is a
different result from failing at three.

**3. Each FAILURE and WARNING**, with:
   - the `src` (check name) and exact `msg`
   - the spec section from `requirements`
   - relevant evidence fields (`effective_authorization_endpoint_request`,
     `incoming_query_string_params`, `actual`/`expected`, `invalid_chars`)
   - **whether it is a defect in the system under test, or an artefact of our variant
     choice, setup or timing** — this distinction is the whole point

**4. Mapping to the existing catalogue** — does this confirm an existing F-NN in
`docs/findings/findings.tex`, or is it new? Never renumber existing findings.

**5. Proposed status** for anything new: `CONFIRMED` only with reproducible evidence and an
understood root cause. Otherwise `UNVERIFIED`, with the specific check needed to settle it.

Do not edit `findings.tex` as part of this command. Report, and let the user decide what
gets written down.
