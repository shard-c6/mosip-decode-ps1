# Submitting Inji Certify and Inji Verify for OpenID certification

How MOSIP would go from this harness to an OpenID Foundation certification of Inji Certify
(as an OpenID4VCI issuer) and Inji Verify (as an OpenID4VP verifier). Checked against the
OpenID Foundation's own pages on 26 October 2026; follow those pages if they have changed:

- [How to certify your implementation](https://openid.net/certification/how-to-certify-your-implementation/)
- [Steps for the certification process](https://openid.net/certification/how-to-submit-your-certification-request/)
- [Conformance testing for OpenID4VCI](https://openid.net/certification/conformance-testing-for-openid-for-verifiable-credential-issuance/)
- [Conformance testing for OpenID4VP](https://openid.net/certification/conformance-testing-for-openid-for-verifiable-presentations/)

---

## First: what our harness runs is not yet the certification run

OpenID certification for verifiable credentials is granted against **OpenID4VP 1.0 Final and
OpenID4VCI 1.0 Final together with the High Assurance Interoperability Profile (HAIP) 1.0**.
The Foundation's instructions say to choose the test plans whose names end in **"/HAIP"**;
plans without the suffix "are not intended for certification testing".

Our harness runs the plans each component can run *today*, because its job is to catch
regressions on every release:

| | What the harness runs | What certification needs (HAIP) | The gap |
|---|---|---|---|
| Inji Verify | `oid4vp-1final-verifier-test-plan`, `direct_post`, `redirect_uri` client id | `oid4vp-1final-verifier-haip-test-plan`, response mode `direct_post.jwt` (encrypted response), x509-based client identification | `direct_post.jwt` support (F-06, found on 0.18.2; re-check on the 1.0 line) and an x509 client id |
| Inji Certify | `oid4vci-1_0-issuer-test-plan`, **pre-authorized code** flow | the HAIP issuer plan, which uses the **authorization code** flow ("this test does not support the pre-authorized code flow, as HAIP mandates the use of the authorization code flow") with **client attestation** | authorization-code flow through an authorisation server, client attestation; plus findings F-12–F-15 |

So the path to certification is: close those gaps in the product, add the HAIP plans to
`configs/runner.json` (the runner is plan-agnostic: plan name, variant and config are data),
get them green in this harness, then do the formal run below.

## The formal process

The certification process has three parts.

### 1. Run the tests and publish the results

- Run the certification test plan(s) for each profile and credential format you want
  certified (SD-JWT VC and mdoc are separate runs). The Foundation's instructions use the
  hosted suite at <https://www.certification.openid.net/> (sign in with any Google or GitLab
  account). Its outgoing calls come from a published IP address; allow it through any
  firewall in front of the deployment under test.
- Use a unique **alias** (it routes the suite's callbacks to your tests).
- For an **issuer**: register a client representing the suite's wallet, with redirect URL
  `https://www.certification.openid.net/test/a/<ALIAS>/callback`, and give the suite the
  credential issuer URL, trust anchors and credential configuration id.
- For a **verifier**: point the verifier at the test's exposed `authorization_endpoint`
  instead of the `openid4vp://` scheme, exactly as our harness does.
- When every module in a plan is done, use **"Publish for certification"** on the plan to
  download a zip of the logs. One zip per plan.

The runner's configuration accepts the hosted suite's address and an API token
(`suite.baseUrl`, `suite.apiToken`; keep the token in the gitignored
`configs/runner.local.json`). We have only run it against a local suite so far.

### 2. Pay the certification fee

At the [Certification Payment page](https://openid.net/foundation/members/certifications/new):
entity name (e.g. MOSIP), deployment name **and version** (e.g. "Inji Certify 1.0.0"; a
certification is for a specific version), and a monitored email. The fee depends on OpenID
Foundation membership. You receive a **payment code**.

### 3. Submit the request

At <https://submissions.openid.net/>: contact email, entity, deployment name and version,
payment code, the person signing the **Declaration of Conformance**, an authorised contact,
and the exported zip(s). The signer then receives the declaration to sign electronically.
The Foundation reviews the submission and replies by email.

Questions: certification@oidf.org. Suspected suite bugs:
[conformance-suite issues](https://gitlab.com/openid/conformance-suite/-/issues).

## How the harness helps along the way

- **Before certifying**: the gate shows, on every release, exactly which modules fail and
  why; the baseline records each known gap with a reason, so the list of what stands
  between a release and certification is always current.
- **After certifying**: the same plans, run by CI on every release, catch a regression
  before it ships. A certification is for one version; this is how the next version stays
  conformant.
