"""
Automated conformance-testing harness for MOSIP's Inji stack.

Drives the OpenID Foundation conformance suite's REST API against Inji Verify
(verifier plans) and Inji Certify (issuer plans), normalises the results into the
contract described in docs/CONTRACT.md, and applies a regression gate so the output
can be consumed by each module's existing api-testrig.

Entry point: python -m runner --component verify|certify|--combined
"""

__version__ = "0.1.0"
