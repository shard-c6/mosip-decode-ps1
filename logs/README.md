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

### 2026-09-20 — Day 1
| Test ID | Module | Result | Notes |
|---|---|---|---|
| `dgeeosZpIfDK1bA` | happy-flow | FAILED | Request expired; discarded as timing artefact |
| `dMg4B5whxWgShIB` | happy-flow | FAILED | Suite did not dereference `request_uri` under `url_query` variant |
| `MtzpWoD2dVgtic0` | happy-flow | FAILED | **Day 1 baseline.** 20+ checks; findings F-01 to F-05, F-09 |
