## release-checklist

Step 1 (`/skill-doctor` sanity check) skipped: the target is a copy in a temp
eval directory, not an installed skill, and the request said to skip it.

Body: 2,898 -> 2,036 chars (-29.7%), 89 -> 69 lines
Moved to references: 0 chars
Listing: 138 chars, unchanged (the frontmatter is never edited)
Links skipped by the snapshot: none

Cuts
- Motivation prose in "Why this skill exists" (releases being an important moment, worth extra care, past rushed releases causing problems, "release with confidence"): 359 chars -- carries no rule, and the reason the skill exists is already stated in the one sentence that remains ("...so that every release follows the same steps in the same order, so that nothing important is forgotten").
- The whole "What a release is" section (a release has a version number, changelog entry, git tag and PyPI build; semantic versioning has three parts): 364 chars -- a definition of terms the model already knows, and the four concrete deliverables it lists are already spelled out by the Steps section.
- The second changelog-entry example (`v1.3.1`) and its "Here is another example" intro line: 139 chars -- a duplicate example that shows no format the first (`v1.4.0`) example did not.

Moved
- none

Optional further cuts (not applied)
- Delete "This skill exists to make sure that every release follows the same steps in the same order, so that nothing important is forgotten." (and the now-empty "Why this skill exists" heading): saves 159 chars; you agree it is motivation, not an instruction. This is the exact sentence `references/what-not-to-cut.md` uses as its own example of a rule word ("nothing") sitting inside a sentence that is really just motivation -- it is gated (`nothing` is a rule word) and can only go with your explicit approval of that exact text.
- Delete the changelog-format menu ("You can write the changelog entry in several ways. You could use Keep a Changelog headings (Added, Changed, Fixed). You could use a flat bullet list. You could write a short paragraph."): saves 185 chars and mechanically passes the gate on its own (none of those sentences carry a rule word), but the very next sentence -- "Any of these works, but a flat bullet list is the default here, and you should use one of the others only if the repository already does." -- would then say "any of these" with no menu left to point at. `references/moving-sections.md` and `references/what-not-to-cut.md` both call this out by name: keep the menu and offer the cut as optional rather than take it automatically. Apply only if you're fine with that dangling reference (the tool cannot reword the sentence to fix it; every rewrite here is cut-only, never rewritten).
- Move "Troubleshooting" to `references/troubleshooting.md`, loaded by "Read `references/troubleshooting.md` when a release step fails.": saves 608 chars from the body. It needs your confirmation because 4 of its sentences are rule sentences (the 403/trusted-publisher note, "do not delete" an existing tag + "ask the maintainer", and the changelog-heading format) that would then live only in the reference file -- verified: moving them makes the gate return `needs_confirmation`, listing each one by name.

Deleted with your approval: none (no deletions needed `--approved`; every cut above is a free deletion of unanchored, non-rule text)

Gate: pass    Requirements: 15 (14 sentences left unprotected on purpose)
Coverage: 15/15    Reverse reconstruction: 15/15 (fresh agent, candidate SKILL.md only, no references to open)
Behaviour: skipped: the target skill ships no `evals/evals.json` and no test prompts were given

Description suggestions (not applied)
- none: the description already says what the skill is for and when to use it ("Use when preparing a release of the Python package..."), and is well under both the 1,024-char Agent Skills spec limit and Claude Code's 1,536-char listing cap.
