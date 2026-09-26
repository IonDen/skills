# Shrink report — release-checklist SKILL.md

Size: 93 lines / 3082 bytes -> 69 lines / 2276 bytes (26% smaller).

## Note on "the gate"

This copy of the skill (`.../eval-1/skill/`) contains only `SKILL.md` — no
gate script, eval, or other tooling shipped alongside it, and I was told not
to load any skill (so I couldn't reach the real skill-optimizer gate either).
With no literal gate to run, I used a conservative stand-in: I only
auto-applied edits with **zero unique-information loss** — exact duplication
of a rule already stated elsewhere, or prose that carried no instruction,
threshold, or fact anywhere else in the file. Anything that would trim actual
unique content went to "Needs your decision" instead, unapplied.

## Applied (zero information loss — treated as gate-passing)

1. **Deleted the "Why this skill exists" section** (was between the title and
   "What a release is"). Pure motivational narrative — no instruction,
   threshold, or fact used anywhere else in the skill.
2. **Deleted the duplicate changelog example** ("Here is another example of a
   good changelog entry…", the `v1.3.1` patch-release sample). It illustrated
   the same heading+bullet format as the kept `v1.4.0` example and added no
   new formatting information.
3. **Deleted the "Reminder" section at the end** ("NEVER commit directly to
   `main`."). Verbatim duplicate of the first line under "Rules" — the rule
   itself is still present, just stated once.
4. **Tightened the "Changelog format" paragraph** from five sentences
   ("You could... You could... You could...") to two, keeping all three
   format options and the default-format guidance intact, just less
   repetitive. This is a reword, not a deletion — no content was dropped,
   only word count.

## Needs your decision (not applied)

1. **"## What a release is" section** (semver major/minor/patch definitions +
   the list "version number, changelog entry, git tag, build uploaded to
   PyPI"). This is generic, well-known background knowledge that the Steps
   section already covers concretely in action form (branch, changelog entry,
   test, PR, tag+push, build). I lean toward cutting it entirely, since
   nothing in Rules/Steps/Troubleshooting depends on the definitions being
   spelled out — but unlike the four cuts above, removing it does drop some
   stated content (the semver definitions aren't restated anywhere else), so
   I left it in place pending your call. Options:
   - Cut the whole section (my lean).
   - Cut only the semver-definitions sentences, keep the one-line list of
     release components as a short lead-in to Steps.
   - Leave as is.

## Not touched (judged load-bearing, no candidate cuts)

- **Rules** — four short, distinct mandatory constraints; kept as-is.
- **Steps** — the core numbered checklist plus the build command; kept as-is.
- **Troubleshooting** — four distinct, specific failure modes with fixes (403
  Forbidden / missing `build` module / existing remote tag / changelog-heading
  mismatch); no duplication, kept as-is.
- Frontmatter (`name`, `description`) — required for skill triggering; kept
  as-is.
