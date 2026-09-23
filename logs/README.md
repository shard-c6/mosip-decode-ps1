# Conformance logs

Exported logs from the OpenID Foundation conformance suite, organised by date.

Export from the suite's test page using **Download all Logs**, or via the API:

```bash
curl -k https://localhost.emobix.co.uk:8443/api/log/<testId> \
  -o logs/<date>/<testname>-<testId>.json
```

The suite also produces a `.sig` file alongside each export — a signature over the log
content. Commit both; the signature is what makes the log verifiable evidence rather than
a text file we could have edited.

Naming: `<testname>-<testId>.json`

## Index

The suite exports each run as a folder containing `.json`, `.html` and a `.sig` for each.
Commit all of them — the signature is what makes a log verifiable evidence rather than a
text file we could have edited.

### 2026-09-20 — Day 1

| Test ID | Module | Result | Notes |
|---|---|---|---|
| `dgeeosZpIfDK1bA` | happy-flow | FAILED | Not exported. Request had expired; discarded as a timing artefact |
| `dMg4B5whxWgShIB` | happy-flow | FAILED | Suite never dereferenced `request_uri` under the `url_query` variant — variant mismatch, not a defect |
| `MtzpWoD2dVgtic0` | happy-flow | FAILED | **Day 1 baseline.** Reached 20+ checks; source of findings F-01, F-02, F-03, F-04, F-05, F-09. Terminated at `ExtractDCQLQueryFromAuthorizationRequest` |

Variant for all three: `credential_format=sd_jwt_vc, client_id_prefix=redirect_uri,
request_method=url_query, vp_profile=plain_vp, response_mode=direct_post`
