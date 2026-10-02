# Draft upstream issue — Docker Compose database script is out of date (1.0)

**Target**: `mosip/inji-verify` · **Covers**: F-10 · **Status**: draft, not filed
**Present on**: `v1.0.0-alpha.1` and `release-1.0.x` head (`6a6ab3b`, 1 October 2026)
**Do not file until**: Shardul has read it through, and the mentors have confirmed where Inji
issues should go (GitHub issues, or another tracker).

> Everything below the line is the issue text. Title first, then body — paste as-is.

---

## Title

`Docker Compose quick start: every VP submission fails with HTTP 500 (db-init/init.sql out of date with 1.0 schema)`

## Body

### What happens

If you run Inji Verify 1.0 the documented way, with Docker Compose, every attempt to submit
a presentation fails. The wallet's `POST /v2/vp-submission/direct-post` gets HTTP 500, so no
verification can ever succeed.

The service log shows why:

```
org.postgresql.util.PSQLException: ERROR: column v1_0.response_code does not exist
  at io.inji.verify.services.impl.VerifiablePresentationRequestServiceImpl
      .getCurrentRequestStatus(VerifiablePresentationRequestServiceImpl.java:126)
```

### Why

The Compose stack sets up its database from `docker-compose/db-init/init.sql`. That file
creates the `verify.vp_submission` table like this:

```sql
CREATE TABLE IF NOT EXISTS verify.vp_submission(
    request_id character varying(40) NOT NULL,
    vp_token VARCHAR NOT NULL,
    presentation_submission text NOT NULL,
    error character varying(100) NULL,
    error_description character varying(200) NULL
);
```

But the real schema, in `db_scripts/inji_verify/ddl/verify-vp_submission.sql`, has three more
columns the 1.0 service needs — `response_code`, `response_code_expiry_at` and
`response_code_used` — and also makes `vp_token` and `presentation_submission` optional and
adds a primary key.

So the service expects a column the Compose database never created.

### How to fix

Make `init.sql` match `db_scripts`. For `vp_submission` that means:

```sql
CREATE TABLE IF NOT EXISTS verify.vp_submission(
    request_id character varying(40) NOT NULL,
    vp_token VARCHAR NULL,
    presentation_submission text NULL,
    error character varying(100) NULL,
    error_description character varying(200) NULL,
    response_code character varying(200) NULL,
    response_code_expiry_at TIMESTAMP WITH TIME ZONE NULL,
    response_code_used boolean DEFAULT false,
    CONSTRAINT pk_vp_submission_request_id PRIMARY KEY (request_id),
    CONSTRAINT uq_vp_submission_response_code UNIQUE (response_code)
);
```

We made exactly this change locally and the 500 went away: submissions were processed
normally, and the OpenID Foundation's verifier happy-flow test then passed every automated
check.

Longer term it may be worth generating `init.sql` from `db_scripts`, or checking the two
against each other in CI, so they can't drift apart again.

### How we confirmed it

- Fresh database: the Postgres data volume was created minutes before the test, and the
  Postgres log shows `init.sql` running. So this isn't left-over data from an older version.
- The live `vp_submission` table matched `init.sql` column for column.
- After the fix, using only the corrected `init.sql`, everything worked.

Found while running the OpenID Foundation conformance suite (5.3.1, OID4VP 1.0 Final
verifier plan) against `injistack/inji-verify-service:1.0.0-alpha.1`.

### How to reproduce

1. `cd docker-compose` on `release-1.0.x` (or tag `v1.0.0-alpha.1`), set the public host, and
   `docker compose up -d`.
2. Create a VP request and submit any presentation to
   `/v1/verify/v2/vp-submission/direct-post`.
3. You get HTTP 500, and the error above in `docker logs verify-service`.

### Context

We are a team working on MOSIP Decode 2026, building automated OpenID conformance testing for
Inji Certify and Inji Verify. Happy to open a pull request with the `init.sql` change if that
would help.

---

## Notes for us (not part of the issue)

- This is the finding to lead with upstream: present on the branch head, root cause understood,
  fix proven by a run. Unlike ISSUE-01 (nonce), it is not already fixed on 1.0.
- It is a packaging gap, not a service bug — the issue says so. Maintainers will take the
  distinction seriously.
- Offer the PR in the issue, but wait for them to say yes before opening it.
- Only `vp_submission` is evidenced. Other tables may also have drifted; we have not compared
  them all, so the issue does not claim it.
