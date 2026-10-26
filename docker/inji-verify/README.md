# Inji Verify configuration used by the conformance stack

Both files are copied from [mosip/inji-verify](https://github.com/mosip/inji-verify) at tag
`v1.0.0-alpha.1` (`docker-compose/`), licensed MPL-2.0, and modified as follows. They are
kept here so the stack runs from a fresh clone with no manual edits to Inji Verify.

## `db-init/init.sql`

The `verify.vp_submission` table is replaced with the canonical schema from
`db_scripts/inji_verify/ddl/verify-vp_submission.sql`. The shipped version lacks the
`response_code` columns, so Inji Verify 1.0 answers every presentation submission with
HTTP 500. This is finding **F-10** (`docs/findings/findings.tex`); an upstream issue is drafted
in `docs/upstream/ISSUE-02-compose-db-init.md`.

## `config.json`

- **Added** the credential *OIDF Conformance PID (SD JWT)*: `pre_registered`, a DCQL query for
  `dc+sd-jwt` with `vct` `urn:eudi:pid:1`. The OpenID Foundation suite's verifier tests always
  present that credential type, so a verifier must ask for it. `pre_registered` makes Inji
  Verify deliver the request inline, which the test variant needs.
- *Mock Identity (SD JWT)* changed from `decentralized_identifier` to `pre_registered`. Unused
  by the conformance runs; kept for comparison with earlier evidence.

Everything else is as shipped.
