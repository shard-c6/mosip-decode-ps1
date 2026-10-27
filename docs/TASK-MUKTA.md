# A task for Mukta, before 31 October

Hi Mukta. The harness is finished and passing; the submission goes in on 1 November. One of
the two tasks below would really help, and either one makes you a named contributor to the
repository. Pick whichever fits your time. Reply to Shardul with what you find.

## Option A — read it as a judge would (about 30 minutes, nothing to install)

1. Open the repository: https://github.com/shard-c6/mosip-decode-ps1
2. Read the **README** from the top, as if you had never seen the project.
3. Open `docs/ARCHITECTURE.md` and look at the diagram.
4. Note anything that is unclear, wrong, missing, or takes more than one read to understand.
   Typos count. "I didn't understand this sentence" counts.
5. Send Shardul the list, or open a pull request fixing what you can.

## Option B — set it up from scratch (about 1–2 hours)

This checks that someone other than Shardul can run it, which nobody has done yet, especially
on Windows if that is what you use.

1. You need Docker Desktop (running), Python 3.11 or newer, git, and a free ngrok account with
   its free static domain (dashboard.ngrok.com → Domains).
2. Clone the repository and follow **only the README**, section by section: *Per-developer
   settings*, then *Quick start*. Use your own ngrok domain, never Shardul's.
3. Write down every place you got stuck, had to guess, or had to search for something, with
   the exact error message if there was one.
4. If it works, the last line says `GATE PASSED`. Send Shardul that line and your notes.
5. When you finish, stop the stack (`scripts/stack.sh down combined`) and ngrok.

Do not commit or share `docker/.env`, `configs/runner.local.json` or `configs/keys/`.

Whatever you send, Shardul will commit the fixes with you named on the commit.
