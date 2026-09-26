## vague-description

Body: 435 -> 151 chars (-65.3%), 15 -> 8 lines
Moved to references: 0 chars (nothing moved)
Listing: 1,030 chars, unchanged (the frontmatter is never edited)
Links skipped by the snapshot: none

Cuts
- The whole "## Background" section (3 sentences: "Changelogs are how users
  learn what changed between versions." / "A good changelog saves users time
  and builds trust in a project, while a bad one causes confusion and extra
  support requests." / "Many projects neglect their changelog, and this skill
  exists to help with that."): pure motivation for why the skill exists, no
  rule, no instruction, no condition, no reason attached to a rule. The dry
  run of extract_requirements.py independently flagged all three sentences
  as carrying no rule word, no literal and no anchor, confirming none of them
  protects an instruction.

Moved
- (none)

Optional further cuts (not applied)
- (none identified: after the Background section, the body is just the
  "# Changelog helper" title, the "## Steps" heading, and the three numbered
  steps -- each step is either a plain instruction with no rule word (needs
  to stay whole so its content is findable) or carries the "Do not edit
  released entries." rule word "not", so nothing further can be cut without
  losing an instruction)

Deleted with your approval: (not applicable -- the request already said to
apply, and the gate never asked for a deletion approval: no rule sentence or
anchored sentence was removed, only the three unprotected Background
sentences)

Gate: pass    Requirements: 3 (3 sentences left unprotected on purpose --
the deleted Background sentences)
Coverage: 3/3
Reverse reconstruction: 3/3 (a fresh agent given only the candidate
SKILL.md, told not to read any other file, listed exactly the three Steps
instructions -- read CHANGELOG.md and note its format first, draft the new
entry in that same format, never edit released entries -- and nothing else;
it correctly treated the frontmatter description as non-actionable prose)
Behaviour: skipped -- the skill ships no evals/evals.json and the user gave
no test prompts to run against both versions

Description suggestions (not applied)
- The description is 1,030 chars, over the Agent Skills spec's 1,024-char
  limit (flagged by measure_skills.py as DESCRIPTION_OVER_SPEC_LIMIT).
  Trimming the feature list would fix that on its own.
- The description reads as marketing copy (repeated superlatives: "A
  comprehensive, powerful and flexible toolkit... designed to be fast,
  reliable and easy to extend") and never states a concrete "use when"
  trigger -- no example phrasing a user or agent would say ("update the
  changelog", "draft a changelog entry for this PR") that would make the
  skill surface at the right moment. A description built around when to use
  the skill, not an exhaustive feature list, would trigger more reliably.

## Notes on the run

- Step 1 (/skill-doctor sanity check) was skipped per the task instruction:
  this is a copy under
  `<SKILL_DIR>`, not an
  installed skill.
- Work directory (snapshots, requirements.md, frozen.json, candidate):
  `<work>` (also
  written to outputs/workdir.txt).
- The result was applied: SKILL.md at
  `<SKILL_DIR>/SKILL.md`
  now holds the trimmed body; the frontmatter is byte-for-byte the original
  (frontmatter is never edited by this tool).
