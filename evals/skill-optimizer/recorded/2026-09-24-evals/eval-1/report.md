## release-checklist

Body: 2,898 -> 1,851 chars (-37%), 89 -> 66 lines (~724 -> ~462 tokens est.)
Moved to references: 0 chars (no section was moved in the applied candidate)
Listing: 138 chars, unchanged (the frontmatter is never edited)

Cuts
- "Why this skill exists" narrative (3 of 4 sentences: "Releases are one of the
  most important moments...", "...it is worth taking a little extra care.",
  "In the past, releases that were rushed...", "Following the checklist below
  lets you release with confidence."): motivation that carries no rule — the
  agent doesn't need convincing why releases matter in order to follow the
  steps. The one sentence in this section that does carry a rule word
  ("nothing") was kept — see Needs your decision below.
- The whole "What a release is" section (what a release consists of, plus the
  semantic-versioning major/minor/patch explainer): a definition of things the
  model already knows — this is the exact "semantic versioning" example the
  skill's own what-not-to-cut reference names as usually safe to cut.
- The second changelog example (the v1.3.1 block) and its intro sentence
  ("Here is another example..."): a second example that shows nothing the
  first one didn't — both illustrate the same flat-bullet-list format.
- The changelog-format option menu ("You can write the changelog entry in
  several ways... Keep a Changelog headings... a flat bullet list... a short
  paragraph."): an option menu where the sentence that states the default
  already does the job on its own ("a flat bullet list is the default here,
  and you should use one of the others only if the repository already does"),
  kept verbatim.

Moved
- (none in the applied candidate — see the Troubleshooting move under Needs
  your decision, which was verified but not applied)

Needs your decision
- "This skill exists to make sure that every release follows the same steps
  in the same order, so that nothing important is forgotten." reads as pure
  motivation but carries the rule word "nothing," so it wasn't auto-cut. This
  is the literal example the skill's own what-not-to-cut reference calls out
  as needing your explicit sign-off. Deleting it saves ~159 more characters
  (1,851 -> ~1,692 chars, another ~9%). Kept in the body for now.
- Move "## Troubleshooting" (4 condition-then-fix pairs, 2 of which contain a
  MUST/"do not" rule) into a new `references/troubleshooting.md`, loaded by
  the line "Read `references/troubleshooting.md` when a release step or the
  publish workflow fails." This is the single biggest remaining saving: I
  built and gated this variant and it verifies clean (`needs_confirmation`,
  not `rejected`) — every rule and anchored sentence survives intact in the
  reference, just not in the body. It would take the body from 1,851 to 1,331
  chars (a further -28%, ~55% off the original 2,898). Troubleshooting is
  read-when-a-step-fails material, exactly the kind of section the skill's
  moving-sections guidance calls a good candidate to move. Not applied — a
  move needs your confirmation even when the gate doesn't reject it.

Gate: pass    Requirements: 21 (13 sentences left unprotected on purpose — the
cut motivational/definitional/duplicate sentences listed above)
Coverage: 21/21 (every requirement's anchor still resolves in the candidate;
the gate would have raised ANCHOR_LOST otherwise)
Reverse reconstruction: 21/21 — a fresh agent given only the candidate
SKILL.md (no other file, no other context) listed every rule, step, command,
threshold and troubleshooting pair independently, including the intentional
duplicate closing reminder ("NEVER commit directly to `main`.")
Behaviour: skipped — this skill ships no `evals/evals.json` and no test
prompts were given

Description suggestions (not applied)
- (none — the listing is 138 chars, well under both the 1,024-char spec limit
  and Claude Code's 1,536-char default listing cap; measure_skills.py raised
  no notes)
