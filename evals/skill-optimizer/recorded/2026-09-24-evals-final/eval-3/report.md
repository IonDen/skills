## release-checklist

Body: 2,898 -> 2,036 chars (-29.7%), 89 -> 69 lines
Moved to references: 0 chars (no move applied - see Optional further cuts)
Listing: 138 chars, unchanged (the frontmatter is never edited)
Links skipped by the snapshot: none

### Cuts

- "Why this skill exists" trimmed from 490 to 131 chars (saved 359): deleted four sentences of pure
  motivation ("Releases are one of the most important moments...", "A release is the point where...",
  "In the past, releases that were rushed...", "Following the checklist below lets you release with
  confidence.") - none of them carries a rule, a condition or a reason beyond what the one remaining
  sentence already says. Kept, word for word, the one sentence in that section that carries a rule word
  ("nothing"): "This skill exists to make sure that every release follows the same steps in the same
  order, so that nothing important is forgotten." It reads as motivation but the gate protects it
  mechanically, so it stays unless you approve cutting that exact sentence (listed below).
- "## What a release is" section deleted whole (saved 362): a definition of what a release is and of
  semantic versioning (major/minor/patch) - general knowledge the model already has, no instruction
  in it.
- Second changelog example deleted (saved 137): "Here is another example of a good changelog entry:"
  plus its v1.3.1 code fence. It shows the same heading and bullet-list format as the first example,
  just with one bullet instead of two - nothing the first example didn't already teach. The first
  example (v1.4.0) stays.

### Moved

(none - the one strong move candidate needs your approval first; see below)

### Optional further cuts (not applied)

- Move "## Troubleshooting" (607 chars: the 403/PyPI-publisher case, the missing-build-module case,
  the existing-remote-tag case, and the changelog-heading-format case) to references/troubleshooting.md,
  loaded by a line such as "Read references/troubleshooting.md when a release step fails." You'd be
  agreeing it's needed only when a release step actually fails, not on a normal run. This is the
  single biggest remaining saving, but every sentence in that section carries a rule word ("do not
  delete it", "must be `## vX.Y.Z (YYYY-MM-DD)`"), so the gate stops on needs_confirmation until you
  approve moving each one - it won't apply silently.
- Trim the changelog-format "option menu" (184 chars: "You can write the changelog entry in several
  ways. You could use Keep a Changelog headings (Added, Changed, Fixed). You could use a flat bullet
  list. You could write a short paragraph.") down to just the sentence that states the default: "a flat
  bullet list is the default here, and you should use one of the others only if the repository already
  does." Caveat: that default sentence opens with "Any of these works," pointing back at the very list
  you'd be cutting - deleting the list without also rewording "Any of these" leaves a dangling
  reference, and this tool only deletes, it doesn't reword. Applying this one cleanly needs your own
  touch-up to that transition, not just an approval.
- De-duplicate the pytest instruction (up to 78 chars): "Run the test suite with pytest -q
  --maxfail=1. It takes about 40 seconds." (Steps, item 3) says the same thing as "You MUST run
  pytest -q --maxfail=1 before opening a pull request." (Rules) - the MUST-worded version already
  covers it and the gate keeps it either way. Dropping the Steps-list sentence would renumber steps 4
  and 5 down to 3 and 4, which touches the step order/count, so it's flagged rather than applied.

### Not touched, on purpose

- "## Rules", "## Steps" (all five, in order), the python3 -m build command, the first changelog
  example, the "## Changelog format" default sentence, all four troubleshooting conditions, and the
  closing "## Reminder" repeat of "NEVER commit directly to main." - every one carries a rule word,
  a command, a URL, a version pin or a date, or is the closing reminder the skill deliberately repeats.

Gate: pass    Requirements: 19 (15 sentences left unprotected on purpose - the deleted motivation and
definitions above)
Coverage: 19/19
Reverse reconstruction: 19/19 (a fresh agent given only the candidate SKILL.md, with no other context,
listed all 19 requirements back, including both appearances of the "never commit to main" rule and the
troubleshooting condition/action pairs)
Behaviour: skipped - this skill ships no evals/evals.json and no test prompts were given for it

### Description suggestions (not applied)

- None. The description (138 chars) is well under both the spec limit (1,024) and Claude Code's
  listing cap (1,536), and it already states when to use the skill ("Use when preparing a release of
  the Python package in this repository...") as well as what it covers.

### Status

Report only - nothing was decided or applied. The candidate above lives only in a scratch work
directory; the skill at
`<SKILL_DIR>`
was not modified. /skill-doctor triage was skipped because this is a repository copy, not an
installed skill, per the request.
