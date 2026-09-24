# Result: skill-optimizer on subagent-optimizer

## What ran

skill-optimizer 1.0.0 optimized a copy of this repository's `subagent-optimizer`
skill (its SKILL.md body only). A fresh Claude Sonnet agent followed the skill
end to end, with approval given in advance for any cut the gate would pass.

## Size and gate

| Metric | Before | After | Change |
|---|---|---|---|
| Body chars | 8,863 | 8,758 | -105 (-1.2%) |
| Body lines | 176 | 175 | -1 |
| Chars moved to references | - | 0 | nothing moved |

Gate status: pass, re-run independently against the frozen original.
`gate.txt` holds that re-run. It was produced by the gate as it stood on
2026-09-24 at commit 38bf812, before the last round of gate fixes. The current
gate reads only a `frozen.json` written by the current `extract_requirements.py`,
so it refuses this older one instead of checking it.

Requirements extracted: 28 (16 sentences were left unprotected on purpose:
short bold lead-in labels such as "Model.", "Then:", and similar structural
fragments; none of those were cut).

Coverage: 28/28 requirements present in the candidate.

Reverse reconstruction: a separate fresh agent, given only the optimized
SKILL.md and asked to list every instruction it could find, returned an
81-item list, a finer split of the same content. Every one of the 28
requirements mapped onto at least one of its 81 items, and neither of the two
cut sentences appeared in its list.

## Cuts and open decisions

Two sentences were cut. Both are plain restatements, with no rule word and no
anchor:

1. "A tight allowlist is cheaper *and* more correct." The sentence right
   before it already gives the mechanism (extra tool schemas cost tokens and
   selection accuracy), so this one just cheered for a conclusion already
   made.
2. "The scan tells you *what* is off; you decide the *fix*." This sits right
   after "Read the full agent file" and restates the section heading that
   follows it.

Two more sentences carry a rule word ("must", "isn't"), so the gate protects
them and only a human sign-off can remove them. The agent read both as the
stated reason behind a rule rather than filler, so it left them in the
candidate and flagged them as a decision instead:

- "The optimised agent must do the same job -- just leaner." (under "Preserve
  behaviour")
- "Bloat isn't only token cost -- focused context outperforms large context,
  and tool-selection accuracy degrades as the tool list grows." (under
  "Context budget =/= context window")

## What it means

The skill was already tight. Run against a real document instead of a
synthetic fixture, the optimizer found almost nothing it could cut without
loss, and said so rather than forcing a number.

## Behaviour check

Method: subagent-optimizer's eval 1 (`architect-tools`) and eval 3
(`report-only-conditional`), each run once against the original SKILL.md and
once against the optimized copy, each run by a fresh agent on a fresh copy of
the fixtures.

| Clause | Original | Optimized |
|---|---|---|
| E1a -- identifies "never writes code" vs Edit/Write/NotebookEdit grant | MET | MET |
| E1b -- read-only-leaning tool set (NotebookEdit gone; Edit/Write kept only with stated reason) | MET | MET |
| E1c -- trims the long body | MET | MET |
| E1d -- trims the redundant persistent-memory section | MET | MET |
| E1e -- version bumped to 1.1.0 | MET | MET |
| E1f -- only agents/solution-architect.md changed | MET | MET |
| E3a -- no file under agents/ changes | MET | MET |
| E3b -- plan-reviewer report keeps ExitPlanMode (permissionMode: plan) | MET | MET |
| E3c -- keeps Agent(verifier) as one parameterised tool, argument intact | MET | MET |
| E3d -- keeps repository-rules section (omitClaudeMd: true means only copy) | MET | MET |
| E3e -- no model downgrade for plan-reviewer without task comparison | MET | MET |
| E3f -- token figures labelled definition text, not launch cost | MET | MET |
| E3g -- tool-policy change reported separately from token delta | MET | MET |

Behaviour unchanged: 13 of 13 expected clauses met by both versions. None
differed.

The scoring and the four runs' own reports are in `behaviour/`: `SCORES.md`,
and one `outputs/report.md` per run (`b-orig-*` used the original skill,
`b-opt-*` the optimized copy). In `SCORES.md`, `untouched/` is the original
skill and `subject/` the optimized copy. The list of items the
reverse-reconstruction agent returned was not kept; only its outcome above was.

Caveat: one of the four runs, the optimized copy's eval 1, noted in its own
report that its target agent file is byte-identical to a fixture behind one
of this skill's own recorded eval records, and said it cross-checked its
judgment calls against that record. The other three runs show no such
signal. That bears on the independence of that one run, not on any behaviour
difference traceable to the two deleted sentences. Nothing in the original
version's own eval-1 run suggests it faced the same situation and behaved
differently.
