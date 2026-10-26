# Inji Certify configuration used by the conformance stack

Copied from [mosip/inji-certify](https://github.com/mosip/inji-certify) branch `release-1.0.x`
(head `203b143`), `docker-compose/docker-compose-injistack/`, licensed MPL-2.0. The image is
MOSIP's QA build of that branch, `injistackqa/inji-certify-with-plugins`, pinned by digest in
`docker/docker-compose.yml`: the published `1.0.0-alpha.1` has no DPoP, which the OpenID
Foundation issuer plan's FAPI 2.0 base requires. Mimoto and Inji Web are left out — they are
the wallet side, and in conformance testing the suite is the wallet.

## Changes from upstream

| File | Change | Why |
|---|---|---|
| `config/certify-default.properties` | `mosip.certify.authorization.url` → `https://${PUBLIC_HOST}` | For the pre-authorized grant Certify is its own authorisation server; upstream points at MOSIP's remote esignet-mock sandbox |
| `config/certify-default.properties` | `mosip.certify.authn.issuer-uri` → `https://${PUBLIC_HOST}`; `authn.jwk-set-uri` → Certify's own JWKS | Its credential endpoint must validate the tokens Certify itself issues. Changing `authorization.url` alone left these on eSignet and every credential request failed with 401 |
| `config/certify-csvdp-farmer.properties` | `did-url` → `did:web:${PUBLIC_HOST}` | Shipped with a leftover developer ngrok hostname |

`${PUBLIC_HOST}` is filled from the container's environment (see `docker/.env`).

## Added at start-up

`sd-jwt-credential-config.json` — MOSIP's own SD-JWT credential example, taken from the
Postman collection in `docs/postman_collections/` of inji-certify. Certify ships only an
`ldp_vc` credential, and the OID4VCI 1.0 issuer plan tests only `dc+sd-jwt` and `mso_mdoc`.
`scripts/stack.sh up certify` registers it through Certify's `/credential-configurations` API
unless it is already there.

## Test shim — in `docker/gateway/nginx.conf`, not here

Certify's authorisation-server metadata cannot contain `authorization_endpoint` (finding
F-12), and the suite's issuer plan requires it. The gateway injects it into that one
document so the rest of the plan can be measured. Results obtained through it are reported
as such.
