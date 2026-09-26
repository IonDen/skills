# 2026-09-24 eval runs, reviewed skill

skill-optimizer as it stood after review (owner decisions of 2026-09-24: more
automatic, but never destructive, so an uncertain cut is kept and listed as
optional rather than applied on its own judgment; and the skill never
recommends disabling or deleting another skill). Skill snapshot `f89943a`. A
fresh Claude Sonnet agent per run, one run per eval, no baseline runs repeated
(the two no-skill baselines that compare against evals 1 and 2 still live
under [`../2026-09-24-evals/`](../2026-09-24-evals/), which holds the runs of
the version before review).

`gate.txt` in each folder is an independent re-run of `verify_rewrite.py`
against the committed `frozen.json` and the run's own original and candidate
(or, where the run applied its result, the applied `SKILL.md`). Each folder's
`report.md` is the unedited text that run produced at the time.

- `eval-0/`: nothing-to-cut. `report.md`, `requirements.md`, `frozen.json`,
  `gate.txt`. No `SKILL.*.md`: the candidate is byte-identical to the
  original, so there is nothing to add beyond the frozen inventory already
  captured.
- `eval-1/`: the full shrink, applied. `report.md`, `requirements.md`,
  `frozen.json`, `SKILL.result.md` (the applied result this run wrote over
  the target file), `gate.txt`.
- `eval-2/`: the refused deletion. `report.md`, `requirements.md`,
  `frozen.json`, `SKILL.candidate.md` (the rejected candidate; never
  applied), `gate.txt` (shows `REJECTED` with the lost rules and literals
  named).
- `eval-3/`: report-only. `report.md`, `requirements.md`, `frozen.json`,
  `SKILL.candidate.md` (the proposed candidate; never applied), `gate.txt`
  (shows `PASS`).
- `eval-5/`: description flagged, body applied. `report.md`,
  `requirements.md`, `frozen.json`, `SKILL.result.md` (the applied result),
  `gate.txt`.

Verdicts, each checked against its own `gate.txt` re-run: eval 0's
`SKILL.md` came back byte-identical. Eval 1 passed the gate, shrinking the body from
2,898 to 2,036 chars (-29.7%) with no stall waiting on a question; the
rule-word motivation sentence and the whole Troubleshooting section stayed in
the body, listed as optional cuts rather than applied, and the
changelog-format option menu was flagged for the dangling "Any of these" its
removal would leave behind; all five numbered steps stayed anchored, and
reverse reconstruction recovered all 15 requirements. Eval 2's requested
deletion of the whole Rules section was rejected (`RULE_LOST`, `ANCHOR_LOST`,
`LITERAL_LOST`, `PROMINENCE_LOST`, `SECTION_CHANGED`), the run never wrote
its own approval file, `SKILL.md` is byte-identical to the original, and the
three lost rules are listed as optional cuts that need the user's explicit,
per-sentence approval before they can go. Eval 3 is report-only: every file
came back byte-identical, the proposed candidate passes the gate on its own
at the same -29.7% shrink as eval 1, the optional cuts are listed, and
reverse reconstruction recovered all 19 requirements. Eval 4 ran against a
real `/skill-doctor` capture taken from the author's own machine; that
capture is not published here because it lists the skills installed on that
machine. The run listed the skills by their listing cost with usage,
recommended neither disabling nor deleting anything, changed nothing, and
asked which skill to optimize. Eval 5 shrank the body from 435 to 151 chars
(-65.3%) with the frontmatter byte-identical, proposed the description
suggestions (1,030 characters, six over the 1,024-character limit, with no
statement of when to use the skill) without applying them, and reverse
reconstruction recovered all 3 requirements.

Every local filesystem path that appeared in a copied file has been replaced
with the placeholder the skill's own documentation already uses for it:
`<work>` for a run's scratch work directory, `<SKILL_DIR>` for the directory
holding the skill under test.
