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

## Outstanding

Modules 02–11 of the 1.0 Final alpha verifier plan, and the ID2 verifier plan, are not yet
run. Scheduled in Week 1 — see `docs/PLAN.md`.
