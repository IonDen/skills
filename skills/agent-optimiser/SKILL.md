---
name: agent-optimiser
description: >-
  Use when asked to audit, optimise, slim down, or fix Claude Code subagent
  definitions (.claude/agents/*.md) — set a proper `tools` allowlist (an agent
  with no `tools` field inherits every tool on each launch), cut bloated or
  duplicated system prompts, tighten descriptions so they trigger reliably, and
  right-size the model. Triggers: "optimise my agents", "audit my subagents",
  "my agent uses too many tokens", "fix the tools list", "review .claude/agents",
  "make my agents cheaper".
license: MIT
metadata:
  version: "1.2.0"
  author: IonDen
---

# Agent Optimiser

Audit Claude Code subagent files and propose token-economy + quality fixes, then
apply the approved ones and bump each changed agent's version.

**The biggest win** is the `tools` field: an agent with no `tools` inherits *every*
tool available to subagents, loading all schemas on every launch, and every extra
schema costs tokens and selection accuracy. A tight allowlist is cheaper *and* more
correct. Read `references/best-practices.md` for the rationale behind each flag and
`references/tool-catalog.md` for the tool list and archetype → tools map — consult
both before proposing tool changes.

All paths below are relative to this skill's directory (in Claude Code that is
`${CLAUDE_SKILL_DIR}`; in Codex, the `agent-optimiser/` folder under `~/.codex/skills/`
or the project's `.agents/skills/`).

## Workflow

Default mode is **report, then apply on approval** — never edit agent files before
the user approves the report.

### 1. Resolve scope from the invocation

- **No argument** → audit all user agents: `~/.claude/agents/*.md`.
- **An agent name** (e.g. `solution-architect`) → `~/.claude/agents/<name>.md`; if
  absent, search `./.claude/agents/` and report what you found.
- **A path** (file or directory) → use it directly.
- **"project" / a project dir** → that project's `.claude/agents/`.

State the resolved target list in one line before scanning.

### 2. Scan (deterministic measurements)

Run the bundled scanner — it parses frontmatter, sizes everything, estimates tokens,
raises flag codes, and finds boilerplate duplicated across agents:

```bash
python3 scripts/scan_agents.py <targets> --json
```

Use `--json` for structured data to reason over; run without `--json` for a readable
view. The flag codes (e.g. `NO_TOOLS_FIELD`, `WRITE_ON_READONLY`, `MEMORY_BOILERPLATE`)
map to explanations in `references/best-practices.md`. The scanner skips `SKILL.md`
files when walking a directory, so pointing it at a whole `.claude/` tree is safe.

### 3. Analyse each agent (judgement on top of the scan)

Read the full agent file. The scan tells you *what* is off; you decide the *fix*.

**Tool allowlist (conservative + flag).** This is the priority. Read the body and
list every tool its instructions actually require. Cross-check against the archetype
floor in `tool-catalog.md`. Then:
- Propose the minimal allowlist that covers everything the body does.
- Keep anything *plausibly* used — when in doubt, keep it and **flag it as a question**
  ("body never edits files — drop `Edit`/`Write`? keep `Bash`?") rather than removing
  silently. Breaking an agent costs far more than a slightly wide list.
- Remove dead entries (`AskUserQuestion`, `Workflow`, `EndConversation`, plan/schedule
  tools) outright — subagents can never use them. Rename legacy names (`Task` →
  `Agent`). `Agent` itself is a question, not a removal: nested subagents are on by
  default, so keep it when the body delegates and ask when it doesn't.
- **Memory exception:** if frontmatter sets `memory:`, the agent needs `Edit` + `Write`
  to maintain its memory files — keep them even on an otherwise read-only agent. Never
  propose stripping them; it silently breaks memory upkeep. (`NotebookEdit` is still
  droppable.)
- Net check: a tool granted but never used → propose drop; an action the body requires
  but no tool covers → propose add (and note the body/tools mismatch).

**Token / prose trims.**
- Duplicated boilerplate across agents (the scanner lists it) — usually a hand-written
  "Persistent Agent Memory" section, redundant when `memory:` is set because the
  harness injects it. Trim to one line.
- CLAUDE.md / global rules re-pasted into the body — subagents already inherit
  CLAUDE.md; remove.
- Over-long bodies (>~150 lines for a single-purpose agent), over-explaining,
  excessive ALL-CAPS MUST/NEVER, contradictions, signposting filler.
- Preserve meaning. Trimming must not drop a real instruction; if unsure whether a
  passage is load-bearing, flag it, don't cut it.

**Description.** Ensure concrete triggers ("use when…/after…"), a proactive cue if
it should auto-fire, and no runaway multi-example bloat (it loads session-wide).

**Model.** Match to job: `haiku` for mechanical/read-only, `sonnet`/`opus`/`fable`
where competence is fixed; flag read-only agents pinned to `opus`, and complex agents left
on default `inherit` that could silently run on a weak session model.

**Frontmatter hygiene.** Name lowercase-hyphenated; required fields present; tool
names valid (treat unknown names as possibly MCP/plugin — verify, don't assume typo).

### 4. Report and STOP

Present one section per agent using the template below, then a portfolio summary
with total estimated token savings. Stop and ask for approval. If the user wants
per-finding control, let them accept/reject individually.

### 5. Apply approved changes, then bump versions

- Edit only the approved changes. Keep edits surgical; don't reflow untouched prose.
- After a file's content edits are applied, bump its version:
  ```bash
  python3 scripts/bump_version.py <agent.md>
  ```
  No `version` field → becomes `1.1.0`; existing `X.Y.Z` → minor bump `X.(Y+1).0`.
  Only bump agents you actually changed.
- Re-run the scanner on the changed agents and report before/after token totals and
  the new version numbers.

## Report template

Use this exact structure per agent:

```
## <agent-name>  (<path>)
Current: model <model> · <tools state> · body <N> lines · ~<T> tokens/launch
Version: <current> → <proposed>

Findings
- [high] <code>: <issue> → <proposed fix>
- [med]  <code>: <issue> → <proposed fix>
  ...

Proposed `tools`: <comma list>   (was: <old or "inherit-all">)
  ? <uncertain tool>: keep or drop? — <reason it's uncertain>

Proposed trims: <bullet list of sections/lines to cut, with ~token savings>

Est. savings: ~<X> tokens/launch  (<old> → <new>)
```

End with:

```
## Summary
<n> agents audited · est. total savings ~<X> tokens/launch
Apply all / pick per-agent / adjust?
```

## Principles

- **Conservative on tools, aggressive on dead weight.** Never strip a tool the agent
  might need without flagging it; freely cut duplicated boilerplate and re-pasted
  global rules.
- **Measure, don't guess.** Lead with the scanner's numbers; quote token deltas. The
  estimate is chars/4 — good enough to rank and to show a before/after, not a bill.
- **Preserve behaviour.** The optimised agent must do the same job — just leaner.
- **One agent, one job.** If an agent does several jobs, say so and suggest splitting,
  but don't split without the user's go-ahead.
- **Context budget ≠ context window.** Bloat isn't only token cost — focused context
  outperforms large context, and tool-selection accuracy degrades as the tool list
  grows. Keep an agent's standing instructions tight: if removing a section wouldn't
  change the agent's behaviour, cut it.
