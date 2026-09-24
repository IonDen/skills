# release-checklist — cheaper-to-load report

Report only. Nothing has been applied to
`.../runs/eval-3/skill/SKILL.md` — it is unchanged. `/skill-doctor`
triage was skipped: this is a standalone copy, not an installed skill.

Work directory (candidate, requirements, frozen inventory, gate output):
`<work>`

## release-checklist

Body: 2,898 -> 1,380 chars (-52%), 89 -> 55 lines, ~724 -> ~345 tokens est.
Moved to references: 608 chars, read only when a release step fails
Listing: 138 chars, unchanged (the frontmatter is never edited)

### Cuts

- "Why this skill exists" background (3 sentences: "Releases are one of the
  most important moments...", "A release is the point where the work of many
  weeks reaches users...", "In the past, releases that were rushed caused
  problems..."), plus the closing "Following the checklist below lets you
  release with confidence.": pure motivation, no rule, nothing an agent acts
  on. One sentence in this section carries the rule word "nothing" and is
  listed under Needs your decision below rather than cut outright.
- "What a release is" section in full (what a release contains, plus the
  definition of semantic versioning and what major/minor/patch mean): a
  definition of terms the model already knows going in; nothing here is
  referenced by a later step.
- The changelog-format option menu ("You can write the changelog entry in
  several ways. You could use Keep a Changelog headings... You could use a
  flat bullet list. You could write a short paragraph."): an option menu
  where one default sentence does the job. The sentence that actually states
  the default and the escape hatch ("a flat bullet list is the default here,
  and you should use one of the others only if the repository already does")
  stays, word for word.
- The second changelog example (`## v1.3.1 (2026-02-11)` block and its
  intro sentence): shows the same flat-bullet format as the first example,
  teaches nothing new. Kept the first example, which the default-format rule
  above still needs.

### Moved

- Troubleshooting (all four entries: the `403 Forbidden` publish failure, the
  missing `build` module, an existing remote tag, and a CI changelog-heading
  mismatch) -> `references/troubleshooting.md`, loaded by: "Read
  `references/troubleshooting.md` if the publish workflow, the build, a tag
  push or the CI changelog check fails." This is the single largest chunk in
  the skill (608 of the original 2,898 body chars) and it is read only when
  one specific step has already failed — never on a clean release.

### Needs your decision

- "This skill exists to make sure that every release follows the same steps
  in the same order, so that nothing important is forgotten." reads as
  motivation but contains the rule word "nothing", so the gate keeps it by
  default. Delete it (saves another ~160 chars, and the "Why this skill
  exists" heading would go with it since nothing would remain under it), or
  keep it?
- Cutting the changelog-format option menu leaves the kept sentence reading
  "Any of these works, but a flat bullet list is the default..." with no
  antecedent for "these" or, later, "the others" — a fresh-agent reverse
  reconstruction (see Reverse reconstruction below) still inferred the
  correct action in both cases (use flat bullet list; or match the repo's
  existing format if it already uses something else), so no instruction is
  lost, but the phrasing is a little orphaned. Three ways to handle it, in
  increasing cost: leave it as is (0 extra chars, functionally fine); restore
  two of the four menu sentences ("You could use Keep a Changelog headings
  (Added, Changed, Fixed). You could write a short paragraph.", ~100 chars)
  so "these" and "the others" have concrete referents; or restore the full
  four-sentence menu (~185 chars) for the closest match to the original
  wording.

Gate: needs_confirmation    Requirements: 16 (14 sentences left unprotected on purpose — the motivation, definitions and menu items listed under Cuts above)
Coverage: 16/16
Reverse reconstruction: 25/25 — a fresh agent given only the candidate SKILL.md, told to open `references/troubleshooting.md` only because the body points there, listed every rule, step, command, threshold and gotcha from the original with nothing missing. It independently flagged the same dangling "these"/"the others" wording noted above.
Behaviour: skipped — the skill ships no `evals/evals.json` and no test prompts were given.

### Gate detail (needs_confirmation, not rejected)

`verify_rewrite.py` returned `needs_confirmation` (exit 3), not `rejected`:
zero findings of `RULE_LOST`, `ANCHOR_LOST`, `LITERAL_LOST`, `NEW_TEXT`,
`CODE_EDITED`, `PROMINENCE_LOST` or `TERMINAL_MOVED`. All eleven `ASK
MOVED_TO_REFERENCE` findings are about the four troubleshooting rules now
living only in `references/troubleshooting.md`, which is exactly what moving
that section is supposed to do — each needs your explicit yes before it can
be applied, per the skill's own gate table.

### Description suggestions (not applied)

- None. The description is already short (138 chars) and states both what
  the skill covers and when to use it. One loose end unrelated to size: the
  description promises "the version bump" but no step in the body bumps a
  version file (the steps only branch, changelog, test, PR, then tag —
  consistent with a tag-derived version, just not spelled out). Worth a look
  if you ever touch the description, but it costs nothing either way.
