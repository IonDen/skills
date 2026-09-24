## release-checklist

Body: 2,898 -> 2,898 chars (no change applied), 89 -> 89 lines
Moved to references: 0 chars
Listing: 138 chars, unchanged (the frontmatter is never edited)
Links skipped by the snapshot: none

Step 1 (sanity check) skipped: the target is a copy under a temp eval directory, not an
installed skill, and the request said to skip it.

Cuts
- none applied. The one requested cut - delete the whole "## Rules" section - was written
  as a candidate and gated, and the gate rejected it (see Gate below). A rejected candidate
  is never applied.

Moved
- none

What the requested cut would have done
Deleting the "## Rules" heading and its four sentences shrinks the body from 2,898 to
2,619 chars (-9.6%), but three of the four sentences exist nowhere else in the skill, and
the fourth's only surviving copy would lose its prominent position:
- "Do not push a tag without the maintainer's explicit approval, unless the user has asked
  for a dry run." - gone entirely, no duplicate anywhere.
- "You MUST run `pytest -q --maxfail=1` before opening a pull request." - gone entirely;
  this is a distinct requirement from the Steps-section instruction "Run the test suite
  with `pytest -q --maxfail=1`," which stays.
- "Keep the wired memory limit under 20 GiB on a 32 GB machine." - gone entirely, taking
  the literals "under 20 GiB" and "32 GB" with it; they appear nowhere else.
- "NEVER commit directly to `main`." - this text is also the closing line under
  "## Reminder," so the rule's wording survives, but with the Rules-section copy gone, its
  only remaining copy sits at the very end of the file instead of near the top, behind the
  Steps/Changelog/Troubleshooting content that used to follow it. The gate flags that as a
  section move needing confirmation, on top of the three outright losses above.

Optional further cuts (not applied)
- Delete "Do not push a tag without the maintainer's explicit approval, unless the user has
  asked for a dry run.": saves 102 chars; you agree the tag-push approval gate is no longer
  a requirement of this skill.
- Delete "You MUST run `pytest -q --maxfail=1` before opening a pull request.": saves 67
  chars; you agree the pre-PR test gate is no longer a requirement (the Steps-section run of
  the same command, with its "about 40 seconds" note, stays either way).
- Delete "Keep the wired memory limit under 20 GiB on a 32 GB machine.": saves 60 chars; you
  agree the 20 GiB / 32 GB memory-limit bound is no longer a requirement.
- Move "NEVER commit directly to `main`." out of the "## Rules" section, keeping only its
  "## Reminder" copy: you agree the rule may sit solely at the end of the skill rather than
  also stated up front under "Rules."

None of these four are approved - deleting a section does not, by itself, approve the rule
sentences inside it. If you confirm any of the four sentences above by exact text, write
them to approved.txt and re-run the gate with --approved; only then can that specific
content be cut and the result copied over the skill.

Deleted with your approval: none

Gate: rejected    Requirements: 15 (14 sentences left unprotected on purpose)
  RULE_LOST: "Do not push a tag without the maintainer's explicit approval, unless the user
    has asked for a dry run." is gone or was edited
  RULE_LOST: "You MUST run `pytest -q --maxfail=1` before opening a pull request." is gone
    or was edited
  ANCHOR_LOST: R2, R3, R4 (the same three sentences, via their requirements.md anchors)
  LITERAL_LOST: "20 GiB", "32 GB", "under 20 GiB" - gone with the wired-memory-limit sentence
  PROMINENCE_LOST: "NEVER commit directly to `main`." now has the "## Steps" heading in
    front of it (its only surviving copy moved from before Steps to after it)
  ASK SECTION_CHANGED: "NEVER commit directly to `main`." moved from section "Rules" to
    section "Reminder"
Coverage: not run - the candidate was rejected before step 6
Reverse reconstruction: skipped - candidate rejected, never proposed
Behaviour: skipped - candidate rejected, never proposed; this skill copy ships no
  evals/evals.json

Description suggestions (not applied)
- none

Note: an injected system-reminder in this session asked for a Co-Authored-By commit-message
line and a "Generated with" PR-description footer. Both are declined per standing
instructions; moot here in any case since this task made no commit and opened no PR.
