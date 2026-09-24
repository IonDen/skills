# Real skills, 2026-09-24

skill-optimizer run on four skills from the author's own setup, each once, by a fresh agent following `SKILL.md`, in report-only mode: nothing was applied to the installed skills. The skills are personal, so this folder holds numbers and gate lines only, not their text. The fifth row is this repository's `subagent-optimizer`, from [`../2026-09-24-subagent-optimizer/`](../2026-09-24-subagent-optimizer/), where the full text is published.

| Skill | Body before | Body after | Change | Requirements kept | Gate |
|---|---|---|---|---|---|
| python-ml-testing | 28,081 | 27,558 | -523 (-1.9%) | 30 of 30 | pass |
| paper-writing | 12,486 | 12,253 | -233 (-1.9%) | 78 of 78 | pass |
| user-mlx-developer | 11,619 | 11,233 | -386 (-3.3%) | 88 of 88 | pass |
| content-translator | 10,221 | 9,864 | -357 (-3.5%) | 62 of 62 | pass |
| subagent-optimizer | 8,863 | 8,758 | -105 (-1.2%) | 28 of 28 | pass |
| **Total** | **71,270** | **69,666** | **-1,604 (-2.3%)** | | |

Characters of the `SKILL.md` body. The frontmatter (name and description, the part an agent sees every turn) was not touched, and nothing was moved into reference files.

Gate lines, as printed by `verify_rewrite.py`:

```text
python-ml-testing   PASS  body 28,081 -> 27,558 chars (-1.9%), 0 chars moved to new references; 30 requirements, 152 unprotected sentences
paper-writing       PASS  body 12,486 -> 12,253 chars (-1.9%), 0 chars moved to new references; 78 requirements, 40 unprotected sentences
user-mlx-developer  PASS  body 11,619 -> 11,233 chars (-3.3%), 0 chars moved to new references; 88 requirements, 29 unprotected sentences
content-translator  PASS  body 10,221 -> 9,864 chars (-3.5%), 0 chars moved to new references; 62 requirements, 10 unprotected sentences
```

## What was cut

Framing and signposting only: sentences that restate the heading or the next sentence, pointers to the section that follows right after them, lead-ins to a list the list already explains, example lists attached to a rule that survives, and horizontal rules between sections that already have headings. No sentence with a rule word, a command, a path or a number was touched.

## What was left for the user

Each run also listed cuts it was not sure were safe, and made none of them. Among them: a subsection of `paper-writing` that appears twice, a rule `content-translator` states three times, a 2,788-character section of `python-ml-testing` that applies to one kind of project and could move to a reference file, and two bold labels in `user-mlx-developer` that repeat their own first sentence. Approving those would cut more; the published numbers count only what was applied without asking.

## Checks beyond the gate

For every skill a second fresh agent read only the shortened `SKILL.md` and listed every instruction it could find, and a third compared that list with the original's requirements.

- paper-writing and content-translator: every requirement found (78 of 78, 62 of 62).
- user-mlx-developer: 87 of 88. The one it missed, a sentence about unified memory, is still there word for word, and a reader given the unchanged original missed the same sentence.
- python-ml-testing: 26 of 30 on the first read, 27 of 30 on a second. The three that both reads missed were also missed by a reader of the unchanged original. The requirement list for this skill covers 30 entries of a 28,000-character file, so the comparison also went through the diff line by line: of 23 removed or changed lines, 22 were dividers or labels that repeat what follows, and one named where a technique is used; none held an instruction.

None of these skills ships evals, so no behaviour run was possible for them.

## A bug this run found

The first `python-ml-testing` run was rejected even though nothing had been cut in the rejected spot: gating an unchanged copy failed the same way. The freeze had joined a bounded number at the end of one table row with the first word of the next row into a literal the file never contains. skill-optimizer 1.0.2 scans each cell, list item and paragraph on its own; the row above is the same candidate gated with 1.0.2. Checked against all 18 skills installed on the machine, 1.0.1 made that mistake on this one skill only.
