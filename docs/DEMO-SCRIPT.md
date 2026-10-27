# Demo video script (2–5 minutes)

About four and a half minutes. Record the screen at 1080p and speak over it. Every command
below runs from the repository root on a machine set up per the README, and was checked on
27 October against the stack the video shows.

## Before recording (about 10 minutes, not in the video)

1. Start ngrok for your domain: `ngrok http --url=https://sphere-dust-sandlot.ngrok-free.dev 3000`
2. Start the stack and wait for every line to say `up`: `scripts/stack.sh up combined`
3. Do one run first, so the video has an earlier result to compare against:
   `./run-conformance.sh --combined --output results/before.json`
4. Delete the old report so the one in the video is clearly fresh: `rm -rf results/report`
5. Open, ready to switch to:
   - the slide deck, on the cover slide, in presenter view;
   - a terminal at the repository root, font at least 20 pt, a clean screen (`clear`);
   - a browser tab you will use for the report.
6. Close everything else: no notifications, no other terminals, no editor showing files.

**Never on screen:** `docker/.env`, `configs/runner.local.json`, anything in `configs/keys/`
or `evidence/`. They hold the ngrok token and test private keys. If one appears by accident,
re-record that part.

## The script

| Time | On screen | Do | Say |
|---|---|---|---|
| 0:00–0:20 | Deck: cover | — | "We are team ___, for MOSIP Decode problem statement 1: automated conformance testing for Inji Certify and Inji Verify against the OpenID conformance suite." |
| 0:20–0:45 | Deck: problem slide | — | "Today the OpenID Foundation's suite is driven by hand: one component, one test, one click at a time, and someone pastes the request from Inji into the waiting test. That cannot gate a release." |
| 0:45–1:10 | Deck: architecture slide | — | "One command brings up the suite, Inji Verify and Inji Certify in Docker, runs both test plans, and does the step a person used to do: it asks the component for its request or credential offer and hands it to the test." |
| 1:10–2:00 | Terminal | Type `./run-conformance.sh --combined --output results/conformance.json --report results/report` and press Enter. Let it run (under a minute). | While it runs: "These are the verifier tests running against Inji Verify… and now the issuer tests against Inji Certify. 26 tests in all." When it ends, point at `GATE PASSED`: "The gate passes. Its exit code is what CI fails on. Note the line under it: one known defect, F-16, reported on every run." |
| 2:00–2:40 | Browser: open `results/report/report.html` | Scroll slowly from the top. Stop at one Inji Certify test whose suite result is FAILED but whose gate verdict is PASS. | "The report: a badge, a summary for each component, and at the top the known defect. Here is a test the suite fails, but the gate passes, because it is a known gap with a written reason and a finding behind it. Anything new or worse would turn the gate red." |
| 2:40–3:15 | Terminal, then browser | Paste `java -DconformanceResultFile=results/conformance.json -cp ../inji-certify-testrig/api-test/target/apitest-injicertify-1.0.0-rc.1-SNAPSHOT-jar-with-dependencies.jar org.testng.TestNG -d results/testng -testclass io.inji.testrig.apirig.injicertify.testscripts.OpenIDConformanceTest`. Then open `results/testng/index.html`. | "The same results inside MOSIP's own api-testrig: a TestNG class we added to the Inji Certify and Inji Verify testrigs. 15 of 15: one test per conformance module, plus the gate." |
| 3:15–3:35 | Terminal | `python3 -m runner.diff results/before.json results/conformance.json` | "Comparing two runs: no differences across 26 tests. The result is repeatable, and when MOSIP ships a new build, this shows exactly what changed. We used it to move to Inji Verify's newest build: identical results." |
| 3:35–4:05 | Deck: findings slide | — | "What the harness found. Most important, F-16: Inji Verify accepts a revoked credential, because status checks for SD-JWT credentials are not implemented and the gap fails open. Caught by a test the suite added this month, and traced to its cause in MOSIP's code. Also a database script fix for Verify, and four issues in Inji Certify." |
| 4:05–4:30 | Deck: run-it-yourself slide | — | "It all runs on GitHub Actions too, on demand and weekly. The repository and both forks are linked in our submission. Thank you." |

If a step goes wrong, stop and redo just that step; the parts can be cut together afterwards.
The run at 1:10–2:00 can be sped up 2× in editing if it runs long.

## After recording

- Watch it once for anything secret on screen (see the list above).
- Check the length: 2 to 5 minutes.
- `scripts/stack.sh down combined`, then stop ngrok.
- Upload it (YouTube unlisted, or the cloud folder) and put the link in the submission email.
