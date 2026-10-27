# Submission checklist — what Shardul does before 2 November

Everything technical is done and checked: both components on their newest `release-1.0.x`
builds, the suite pinned, the gate passing locally and on GitHub Actions (27 Oct, run
40472405298), the deck updated. What is left needs you: your voice, your decisions, your
accounts. In order:

## 1. Review the slide deck (about 15 min) — by 29 Oct

- [ ] Open the deck (private claude.ai link, Inji OpenID Conformance Harness) and click through all 12 slides.
- [ ] Findings slide: it now has six rows (F-16 added at the top). Check nothing is cut off at the bottom.
- [ ] Export a PDF copy for the cloud folder (the deck's download menu).

## 2. Record the video (about 1 hour with retakes) — by 30 Oct

- [ ] Follow [DEMO-SCRIPT.md](DEMO-SCRIPT.md): setup first, then the script, line by line.
- [ ] Fill in the team name in the first line you say.
- [ ] Watch it back for anything secret on screen (`docker/.env`, `configs/runner.local.json`, `configs/keys/`, `evidence/`).
- [ ] Length between 2 and 5 minutes.
- [ ] Upload it: YouTube (unlisted) or the cloud folder. Keep the link.

## 3. Contribution record — done 27 Oct

README credits the team without roles; PLAN.md keeps the September split as the plan of record.
Mukta has a short task, [TASK-MUKTA.md](TASK-MUKTA.md): send her the link. If she does it, her
fixes are committed with her named on the commit (muktavarak@gmail.com).

## 4. College IDs (10 min) — by 31 Oct

- [ ] Your college ID, scanned or photographed, both sides if needed.
- [ ] Mukta's college ID. Ask her now; it is the one thing that depends on her.

## 5. Cloud folder (20 min) — by 31 Oct

Google Drive (or similar), shared as "anyone with the link can view". Put in:

- [ ] The five signed result exports from `evidence/` (`plan-*-export.zip`). They are the suite's own signed proof of each run.
- [ ] The video (if not on YouTube).
- [ ] The deck as PDF.
- [ ] Both college IDs.
- [ ] `docs/findings/findings.pdf` and `docs/handbook/handbook.pdf` (optional, but they show the work).

## 6. After sharing the folder: replace the test keys (5 min)

The exports contain our **test** private keys (the suite does not redact them, and a signed
export cannot be edited). They are test-only, but once shared, retire them:

- [ ] Regenerate them as in README → *Per-developer settings*, then run once to confirm the gate still passes.

## 7. Send the submission email — by 1 Nov (deadline 2 Nov)

To **decode@mosip.io**. Do **not** use the Unstop button. Include:

- [ ] Team name, and both members' names
- [ ] Problem statement: PS1, Automated Conformance Testing for Inji Certify and Inji Verify against the OpenID suite
- [ ] Main repository: https://github.com/shard-c6/mosip-decode-ps1
- [ ] Testrig classes: https://github.com/shard-c6/inji-verify/tree/feature/openid-conformance-test/api-test and https://github.com/shard-c6/inji-certify/tree/feature/openid-conformance-test/api-test
- [ ] Video link
- [ ] Cloud folder link
- [ ] Deck (PDF in the folder, or a link)

Claude can draft the email text; you send it.

## Optional, any time

- [ ] Decide whether to report F-10 and F-16 to MOSIP. F-10's report is drafted in `docs/upstream/`;
      F-16 would be new. Both are confirmed in the source. Worth asking a mentor where Inji issues should go.
- [ ] Mention F-16 in the email as the headline finding: it is a real security defect in the newest build.
