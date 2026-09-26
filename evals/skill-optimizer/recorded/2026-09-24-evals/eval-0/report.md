## lean

Step 1 (`/skill-doctor` sanity check) skipped: target is a copy in a temp
directory, not an installed skill, and the harness explicitly said to skip
triage.

Body: 91 -> 91 chars (+0%), 2 -> 2 lines
Moved to references: 0 chars
Listing: 66 chars, unchanged (the frontmatter is never edited)

Cuts
- none — every sentence in the body is a load-bearing instruction

Moved
- none — the body has no troubleshooting section, rarely-used mode, or
  reference material to move into `references/`

Needs your decision
- none

Gate: unchanged    Requirements: 2 (0 sentences left unprotected on purpose)
Coverage: n/a — gate reported `unchanged`, so step 6 (coverage, reverse
  reconstruction, behaviour) is skipped per the workflow table ("Nothing
  could be cut without loss. Report that and stop.")

Description suggestions (not applied)
- none — the description already states both what the skill does ("Runs the
  fast tests first") and when to use it ("when committing in this
  repository"), and `measure_skills.py` flagged no length issue (66 chars)

## What was checked

The skill's whole body is two sentences:

1. `Run \`make test-fast\` before committing.`
2. `If it fails, fix the failure before you continue.`

Both were written up as requirements (R1, R2), each anchored to its exact
sentence in the original, frozen with `extract_requirements.py`
(`da093bb9fafa`), and gated with `verify_rewrite.py` against an unedited copy
of the skill. The gate returned `UNCHANGED` (exit 0): `body 91 -> 91 chars
(+0%), 0 chars moved to new references; 2 requirements, 0 unprotected
sentences`.

There is no preamble, motivation, definition of a term the model already
knows, option menu, duplicate instruction, or second example to delete —
every word in the body is either the command to run, the inline code literal
`make test-fast` (protected as a literal, per `references/what-not-to-cut.md`),
or part of the failure-handling instruction. There is also nothing to move
into `references/`: nothing here is a troubleshooting path, a rarely-used
mode, or reference material consulted for one step — the two sentences are
the entire workflow and are needed on every run, which
`references/moving-sections.md` lists as the case to keep in the body.

## Outcome

Per the workflow's step 5 table, an `unchanged` gate result means stop and
report — no candidate is proposed and nothing was applied to the skill. The
skill at
`<SKILL_DIR>`
is unmodified.
