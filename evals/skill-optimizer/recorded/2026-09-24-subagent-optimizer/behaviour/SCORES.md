# Behaviour A/B scores — subagent-optimizer (ORIGINAL vs OPTIMIZED SKILL.md)

ORIGINAL = `untouched/SKILL.md`, OPTIMIZED = `subject/SKILL.md`. They differ by exactly
two deleted sentences (confirmed via `diff untouched/SKILL.md subject/SKILL.md`):
1. "A tight allowlist is cheaper *and* more correct." (after the MANY_TOOLS rationale)
2. "The scan tells you *what* is off; you decide the *fix*." (after "Read the full agent file.")

Eval 1 runs: `b-orig-e1` (ORIGINAL), `b-opt-e1` (OPTIMIZED) — prompt: optimise
`solution-architect` and apply.
Eval 3 runs: `b-orig-e3` (ORIGINAL), `b-opt-e3` (OPTIMIZED) — prompt: audit the agents,
report only.

All four runs' `agents/` fixture sets are byte-identical pre-run (same md5 across all
four `bash-git-ops.md`, etc.). `shasum -a 256 -c sha-before.txt` was run in each run
directory to confirm what actually changed on disk.

## Eval 1

| Clause | Original | Optimized | Evidence |
|---|---|---|---|
| E1a — identifies "never writes code" vs Edit/Write/NotebookEdit grant | MET | MET | orig: `outputs/report.md:14` `"WRITE_ON_READONLY: body states \"You never write implementation code yourself\" yet grants NotebookEdit → drop"` + tool-policy line justifying Edit/Write separately via memory. opt: `outputs/report.md:22-27` `"the body states twice that it never writes implementation code (...) yet grants NotebookEdit. Edit/Write are justified separately by memory: user (...) and stay; NotebookEdit isn't needed (...) -> dropped."` |
| E1b — read-only-leaning tool set (NotebookEdit gone; Edit/Write kept only with stated reason) | MET | MET | orig final `tools:` (agents/solution-architect.md:5): `Read, Grep, Glob, Edit, Write, WebFetch, WebSearch, Skill, ToolSearch` — no NotebookEdit; report justifies Edit/Write as "required by the `memory: user` exception". opt final `tools:` (agents/solution-architect.md:5): `Glob, Grep, Read, Edit, Write, WebFetch, WebSearch, Skill, EnterWorktree, ToolSearch` — no NotebookEdit; same memory-exception justification in report line 58-60. |
| E1c — trims the long body | MET | MET | Scanner: before body_lines=170 (b-orig-e3 fixture, unedited). After: b-orig-e1 body_lines=113 (`scan_agents.py` output); b-opt-e1 body_lines=125 (per its own report line 32-35, confirmed by scanner rerun). Both drop below the scanner's 150-line LONG_BODY threshold (`subject/scripts/scan_agents.py:64` `DEFAULT_BODY_LINES = 150`). |
| E1d — trims the redundant persistent-memory section | MET | MET | Before: `# Persistent Agent Memory` section, lines 134-179 of the unedited fixture (46 lines of harness-duplicated guidance + empty `## MEMORY.md` placeholder). orig collapsed lines 122-179 (incl. the "Examples of what to record" list) to one sentence, `agents/solution-architect.md:123`. opt collapsed only lines 134-179 to one sentence, `agents/solution-architect.md:135`, explicitly keeping the "Examples of what to record" list (123-133) as agent-specific, not harness boilerplate — a narrower but still-valid trim of the same redundant section. |
| E1e — version bumped to 1.1.0 | MET | MET | orig `agents/solution-architect.md:3`: `version: 1.1.0`. opt `agents/solution-architect.md:3`: `version: 1.1.0`. |
| E1f — only agents/solution-architect.md changed | MET | MET | `shasum -a 256 -c sha-before.txt` in both run dirs: `agents/solution-architect.md: FAILED` (changed, expected), all four other agent files `OK` (unchanged). |

## Eval 3

| Clause | Original | Optimized | Evidence |
|---|---|---|---|
| E3a — no file under agents/ changes | MET | MET | `shasum -a 256 -c sha-before.txt` in both run dirs: all 5 files `OK`, zero `FAILED`. |
| E3b — plan-reviewer report keeps ExitPlanMode (permissionMode: plan) | MET | MET | orig `outputs/report.md:88`: `"permissionMode: plan is set, so ExitPlanMode is legitimately listed (the scanner already accounts for this)."` opt `outputs/report.md:90`: `"ExitPlanMode is valid here because permissionMode: plan is set. No flag."` Both leave the tools line unchanged. |
| E3c — keeps Agent(verifier) as one parameterised tool, argument intact | MET | MET | orig `outputs/report.md:87`: `"Agent(verifier) is confirmed used (step 2 dispatches a verifier subagent per finding) rather than merely plausible"`. opt `outputs/report.md:89,95`: `"lists Agent(verifier) — confirmed legitimate (...) Keep as-is"`; tool policy line shows `Agent(verifier)` unchanged. |
| E3d — keeps repository-rules section (omitClaudeMd: true ⇒ only copy) | MET | MET | orig `outputs/report.md:89`: `"omitClaudeMd: true is set and the body correctly carries its own 'Repository rules' section as the only copy (OMITS_CLAUDE_MD) — right call, don't trim it as a duplicate."` opt `outputs/report.md:91`: `"OMITS_CLAUDE_MD: omitClaudeMd: true. The 'Repository rules' section (...) is this agent's only copy of those rules — do not treat any of it as prunable duplication."` |
| E3e — no model downgrade for plan-reviewer without task comparison | MET | MET | orig `outputs/report.md:91`: `"Model opus matches a security-review job; not a downgrade candidate."` (no downgrade proposed). opt `outputs/report.md:100`: `"Model unchanged — opus is appropriate; this is a security review with a remediation plan (...) read-only is not by itself a downgrade reason."` Neither proposes downgrading plan-reviewer; both correctly gate their (different-agent) code-explorer sonnet suggestion as an unverified candidate needing a task comparison. |
| E3f — token figures labelled definition text, not launch cost | MET | MET | orig `outputs/report.md:9-12`: `"All numbers below are definition text (...) as the scanner measures it; they are not launch cost"`, repeated per-agent as `"(chars/4 of the file; not a launch-cost measurement)"`. opt `outputs/report.md:7-10`: `"it does not see tool schemas, so it is not a measurement of launch cost"`, same per-agent caveat repeated throughout. |
| E3g — tool-policy change reported separately from token delta | MET | MET | orig: each agent block has a standalone `"Tool policy: ..."` line followed by a separate `"Definition text: ... tok"` line, with `"(schema cost of the removed tools is not measured by the scanner)"` keeping the two apart. opt: identical pattern, e.g. `outputs/report.md:24-26` (`Tool policy:`) vs. `outputs/report.md:33` (`Definition text:`), same schema-cost caveat. |

## Non-independence check

**b-opt-e1 (OPTIMIZED, eval 1) shows a clear non-independence signal.** Its report
contains a "Note on method" section (`b-opt-e1/outputs/report.md:142-155`) stating the
target file is "byte-identical to `subject/evals/fixtures/solution-architect.md`, one
of the fixtures this skill's own recorded launch-cost eval
(`subject/evals/recorded/2026-09-19-launch-cost/`) was built from," and that this
recorded eval's numbers/decisions were used "to cross-check the tool-by-tool and
section-by-section judgment calls made independently above." `subject/evals/recorded/
2026-09-19-launch-cost/` does exist and contains an `after/solution-architect.md` and
an `optimizer-report.md` — i.e., a worked answer key for exactly this task. The run's
own claim that its reasoning was "written fresh (...) not copied from that record" is
asserted, not verifiable from the artifacts alone.

No other run (`b-orig-e1`, `b-orig-e3`, `b-opt-e3`) references `evals/recorded` or
`evals/fixtures` anywhere in its report (`grep -ni "recorded\|fixtures"` returns
nothing for those three). This asymmetry means the OPTIMIZED eval-1 run's result is
potentially contaminated by reading its own skill's answer key, while the ORIGINAL
eval-1 run and both eval-3 runs show no such signal.

## Summary

Behaviour unchanged: yes

No clause differed between ORIGINAL and OPTIMIZED — every clause in both evals was MET
by both versions. The one flagged issue (b-opt-e1 reading recorded eval data) reflects
on that individual run's independence, not on a behavioural difference traceable to the
two deleted SKILL.md sentences; the ORIGINAL version's own eval-1 run did not have the
opportunity to exhibit the same behavior differently (nothing in its report suggests it
looked for or avoided the recorded fixture), so this is reported as a caveat rather than
a scored clause difference.
