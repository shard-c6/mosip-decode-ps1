# Demo video script (2–5 minutes)

A shot list for the submission video, about four minutes. Record the screen at 1080p; speak
over it. Everything shown runs from this repository on a machine set up per the README.

**Before recording:** ngrok running for your domain; `scripts/stack.sh up combined` already
done (bringing the stack up takes a few minutes, which the video should not show); a
terminal at the repository root, large font; the deck open on the architecture slide.

| Time | On screen | Say |
|---|---|---|
| 0:00–0:20 | Deck: cover | Who we are; problem statement 1. Today the OpenID conformance suite is driven by hand, one component and one click at a time. |
| 0:20–0:50 | Deck: architecture slide | One command brings up the suite, Inji Verify and Inji Certify, runs both test plans, and makes the move a person used to make: asking the component for its request or offer and handing it to the waiting test. |
| 0:50–1:50 | Terminal: `./run-conformance.sh --combined --output results/conformance.json --report results/report` | Let it run (under a minute). Point at a verifier module and an issuer module as they go by, and at the final `GATE PASSED` line. Mention the exit status is what CI fails on. |
| 1:50–2:30 | Browser: `results/report/report.html` | The badge; the summary table for both components; scroll to one Certify module whose suite result is FAILED but whose gate verdict is PASS, and read its reason: a known, documented gap, not a regression. |
| 2:30–3:10 | Terminal: the Certify testrig class, then its report | `java -DconformanceResultFile=… -cp <testrig jar> org.testng.TestNG -testclass …OpenIDConformanceTest` (from the Certify api-test folder). 16 of 16 in MOSIP's own TestNG report: conformance inside the existing testrig. |
| 3:10–3:30 | Terminal: `python -m runner.diff` of two runs | "No differences across 26 modules": the result is reproducible; the same command shows exactly what a new release changed. |
| 3:30–3:50 | Deck: findings slide | What the harness found: F-10 (Inji Verify's database script, fix written) and F-12 to F-15 on Inji Certify. |
| 3:50–4:10 | Deck: run-it-yourself slide | The one command, the repository, thanks. |

**Do not show** `docker/.env`, `configs/runner.local.json` or anything under `configs/keys/`
or `evidence/`: they hold the ngrok token and test private keys.
