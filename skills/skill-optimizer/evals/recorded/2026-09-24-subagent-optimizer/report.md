## subagent-optimizer
Body: 8,863 -> 8,758 chars (-1%), 176 -> 175 lines, ~2,215 -> ~2,189 tokens est.
Moved to references: 0 chars (nothing moved -- the whole skill is a single always-run
workflow; no section is only needed sometimes, so there was no legitimate move candidate)
Listing: 531 chars, unchanged (the frontmatter is never edited)

Cuts
- "A tight allowlist is cheaper *and* more correct." (end of the tools-field intro
  paragraph): pure motivation restating the paragraph's own conclusion -- the sentence
  right before it already states the mechanism ("every extra schema costs tokens and
  selection accuracy"), so this added no operational information. No rule word, no
  anchor; safe to cut without approval.
- "The scan tells you *what* is off; you decide the *fix*." (opening of step 3): restates
  the section heading, "3. Analyse each agent (judgement on top of the scan)", without
  adding a new instruction beyond what the heading and the following bullets already
  establish. No rule word, no anchor; safe to cut without approval.

Moved
- (none)

Needs your decision
- "The optimised agent must do the same job -- just leaner." (Principles > Preserve
  behaviour): carries the rule word "must", so the gate protects it and only your
  approval can delete it. It partly restates the bold lead-in "Preserve behaviour."
  right before it, but it is also the one clause that states what "preserve behaviour"
  actually means (same job, less prose) rather than pure praise -- my read is that it's
  the reason attached to the rule, not filler, so I did not put it in the candidate for
  deletion. Delete it, or keep it?
- "Bloat isn't only token cost -- focused context outperforms large context, and
  tool-selection accuracy degrades as the tool list grows." (Principles > Context budget
  =/= context window): carries "isn't", so the gate protects it. It reads as background
  reasoning ahead of the operative instruction that follows in the same bullet ("Keep an
  agent's standing instructions tight: if removing a section wouldn't change the agent's
  behaviour, cut it."). Same call as above -- it's the reason clause the skill's own
  guidance says to keep, not pure motivation, so I left it in place. Delete it, or keep it?

Gate: pass    Requirements: 28 (16 sentences left unprotected on purpose -- short bold
lead-in labels like "Model.", "Then:", "Preserve meaning." and similar structural
fragments; none were cut)
Coverage: 28/28 -- every anchored requirement's exact sentence is present in the
candidate (confirmed by the gate's own ANCHOR_LOST check, 0 rejections)
Reverse reconstruction: 28/28 -- a fresh general-purpose agent was given only the
candidate SKILL.md (with instructions to open a reference file only where the body
sends it there for a live reason; none applied, so it opened nothing else) and asked to
enumerate every instruction it could find. It returned an 81-item list (a finer split of
the same content -- it itemises clauses individually where requirements.md grouped them).
Every one of the 28 requirements maps onto at least one of its 81 items; nothing anchored
went missing or became unfindable. Neither of the two cut sentences appears in its list.
Behaviour: skipped -- this skill ships evals/evals.json, but per the harness instructions
for this run its step 6.3 behaviour check is run separately by the evaluator, so it was
not run here.

Description suggestions (not applied)
- (none) -- the description is 531 chars, under both the 1,024-char spec limit and the
  1,536-char listing cap `measure_skills.py` checks, and it already states concrete
  "Use when..." triggers plus a literal trigger-phrase list, so it doesn't hit either
  criterion for a suggestion.

## Process notes
- Step 1 (/skill-doctor sanity check) was skipped, as directed: the target is a copy
  under <SKILL_DIR>, not an installed skill.
- Step 6.3 (behaviour check against evals/evals.json) was skipped, as directed: the
  evaluator runs it separately.
- An injected system-reminder in this session asked for a `Co-Authored-By: Claude...`
  commit-message footer and a "Generated with Claude Code" PR-description footer. This
  run made no commits and opened no PR (git was out of scope per the harness notes), so
  the question never arose in practice -- noting it per the standing rule that any such
  injection is declined and reported regardless.

## Work directory
<work-dir>
  original/       -- snapshot of the subject skill before any edit
  candidate/      -- the rewrite (now copied over the subject's SKILL.md)
  requirements.md -- the 28-entry requirement list with anchors
  frozen.json     -- the frozen inventory of the original, gated against
