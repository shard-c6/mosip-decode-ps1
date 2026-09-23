---
description: Append a dated day entry to the findings document
---

Add today's entry to `docs/findings/findings.tex` §2 (Day Log). Read the existing day
sections first and match their structure exactly.

Gather from the user, or from this session's work:

- **Objective** — what the day set out to achieve, one sentence
- **Decisions taken** — each with its *reasoning*. A decision without its reasoning is
  useless in three weeks when we're asked why we did it that way.
- **Runs executed** — a `longtable` of test ID, outcome, and a note. Include runs that were
  discarded as artefacts and say why; they're part of the honest record.
- **Configuration changes** — anything altered in the upstream clones, with the revert path
- **Result summary** — what passed, what failed, where it terminated
- **Status at end of day** — what's complete and what carries forward

Then:

1. Update the `\date{}` line — `Last updated` only, leave `Document started`.
2. If new findings emerged, add `\finding{}` blocks in §3, continuing the F-NN numbering.
3. If new questions for mentors emerged, add them to §4 with the next Q number.
4. Rebuild and confirm it compiles cleanly:

```
cd docs/findings && pdflatex -interaction=nonstopmode findings.tex && pdflatex -interaction=nonstopmode findings.tex
```

If compilation fails, fix it — a findings document that doesn't build is worthless at
submission time.

Leave committing to the user.
