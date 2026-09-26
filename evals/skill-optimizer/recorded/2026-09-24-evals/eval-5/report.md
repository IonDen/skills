## vague-description (changelog-helper skill)

Body: 435 -> 151 chars (-66%), 15 -> 8 lines
Moved to references: 0 chars (nothing needed moving out of this skill)
Listing: 1,030 chars, unchanged (the frontmatter is never edited)

Cuts
- The whole "## Background" section (3 sentences: "Changelogs are how users
  learn what changed between versions." / "A good changelog saves users time
  and builds trust in a project, while a bad one causes confusion and extra
  support requests." / "Many projects neglect their changelog, and this skill
  exists to help with that."): pure motivation, no rule word, no instruction,
  no condition. `extract_requirements.py --dry-run` confirmed all three
  sentences carry no rule word, literal, or anchor before any edit was made.
  Deleting them does not remove anything an agent following the skill would
  need to act on.

Moved
- (none)

Needs your decision
- (none — no rule sentence or anchored sentence was touched, so nothing
  needed a move-or-keep call)

Gate: pass    Requirements: 3 (3 sentences left unprotected on purpose — the
deleted Background sentences)
Coverage: 3/3
Reverse reconstruction: 3/3 — a fresh agent given only the candidate
SKILL.md text (no reference files exist for this skill) listed exactly the
same 3 instructions as requirements.md: read CHANGELOG.md and note its
format, draft the new entry in the same format, never edit released entries.
It also flagged, unprompted, that the frontmatter description claims several
capabilities (automatic format detection, problem reports, drafting from
merged pull requests, monorepo/multi-package support, CI integration, etc.)
that have no matching instruction anywhere in the body -- see the description
note below.
Behaviour: skipped -- this skill ships no `evals/evals.json` and no test
prompts were given, so there is nothing to run the original and candidate
against.

Description suggestions (not applied)
- The description is 1,030 chars, 6 over the Agent Skills spec's 1,024-char
  limit (`measure_skills.py` flags DESCRIPTION_OVER_SPEC_LIMIT on both the
  original and the candidate, since the frontmatter is untouched).
- The description reads as an exhaustive feature list ("what it does") and
  never states when to use the skill. It also promises far more than the body
  delivers: format auto-detection, structural-problem reports (missing dates,
  duplicated versions, unsorted entries, broken links, heading levels),
  drafting from a list of merged PRs, grouping by type, breaking-change
  highlights, version suggestions, monorepo/multi-package support, and CI
  integration are all claimed, but the 3-step body only covers reading the
  existing file's format, drafting one new entry in that format, and never
  touching released entries. Either the description should be cut down to
  match what the skill actually does, or (out of scope for this pass, since
  it would add capability rather than shrink tokens) the body needs the extra
  steps written in.
- Not a description issue, but worth a mention: the frontmatter `name` is
  `vague-description`, which reads like a placeholder rather than the skill's
  real identifier (`changelog-helper` would match the H1). This is inside the
  frontmatter, so it was left untouched per this skill's own rule; flagging it
  here since it may affect how/whether the skill is found.

Result: the candidate was applied to
`<SKILL_DIR>/SKILL.md`.
Step 1 (`/skill-doctor` sanity check) was skipped per the task instruction --
this is a copy under a run directory, not an installed skill.
