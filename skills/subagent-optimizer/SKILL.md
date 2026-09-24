---
name: subagent-optimizer
description: >-
  Optimizes Claude Code subagents (.claude/agents/*.md) and Codex custom agents
  (.codex/agents/*.toml); agent skills (SKILL.md folders) are handled by
  skill-optimizer. Use when asked to audit, optimise, slim down, or fix those
  agents: set a proper `tools` allowlist on a Claude subagent (one with no
  `tools` field inherits every tool on each launch), remove Claude keys that make
  Codex skip an agent, cut bloated or duplicated system prompts, tighten
  descriptions so they trigger reliably, and right-size the model and reasoning
  effort. Triggers: "optimize my subagents", "optimise my agents", "audit my
  subagents", "subagent optimizer", "audit my codex agents", "my agent uses too
  many tokens", "fix my agent's tools list", "review .claude/agents", "review
  .codex/agents", "make my agents cheaper".
license: MIT
metadata:
  version: "1.4.0"
  author: IonDen
---

# Subagent optimizer

Audit Claude Code subagent files and Codex custom agent files, propose
token-economy + quality fixes, then apply the approved ones and bump each changed
Claude agent's version (Codex agent files have no version field).

**The biggest win** is the `tools` field: an agent with no `tools` inherits *every*
tool available to subagents, loading all schemas on every launch, and every extra
schema costs tokens and selection accuracy. Read `references/best-practices.md` for
the rationale behind each flag and `references/tool-catalog.md` for the tool list
and archetype → tools map — consult both before proposing tool changes.

All paths below are relative to this skill's directory: in Claude Code that is
`${CLAUDE_SKILL_DIR}`; in Codex it is wherever this SKILL.md was loaded from
(`~/.agents/skills/subagent-optimizer/`, a project's `.agents/skills/subagent-optimizer/`,
or the older `~/.codex/skills/`). Resolve scripts from that directory, not from a
guessed home path.

## Workflow

Default mode is **report, then apply on approval** — never edit agent files before
the user approves the report.

### 1. Resolve scope from the invocation

- **No argument** → audit all user agents: `~/.claude/agents/*.md` and
  `~/.codex/agents/**/*.toml`.
- **An agent name** (e.g. `solution-architect`) → `~/.claude/agents/<name>.md`; if
  absent, search `./.claude/agents/` and the `.codex/agents/` folders (a Codex agent
  is identified by its `name` key, not the filename) and report what you found.
- **A path** (file or directory) → use it directly.
- **"project" / a project dir** → that project's `.claude/agents/` and `.codex/agents/`.

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
It reads Codex `.toml` agents with Python 3.11+ (`tomllib`); on 3.10, and for
symlinked or malformed files, it lists them under "not scanned" (`skipped` in JSON)
instead: say so in the report rather than auditing them by eye.

### 3. Analyse each agent (judgement on top of the scan)

Read the full agent file.

**Tool allowlist (conservative + flag).** Claude Code only: Codex has no per-agent
tool list, so never propose one for a Codex agent. This is the priority. Read the body and
list every tool its instructions actually require. Cross-check against the archetype
floor in `tool-catalog.md`. Then:
- Propose the minimal allowlist that covers everything the body does.
- Keep anything *plausibly* used — when in doubt, keep it and **flag it as a question**
  ("body never edits files — drop `Edit`/`Write`? keep `Bash`?") rather than removing
  silently. Breaking an agent costs far more than a slightly wide list.
- Remove dead entries (`AskUserQuestion`, `Workflow`, `EndConversation`,
  `ScheduleWakeup`, `EnterPlanMode`) outright — subagents can never use them. Rename
  legacy names (`Task` → `Agent`). Two tools are conditional, not dead: `ExitPlanMode`
  is valid when the agent sets `permissionMode: plan` (the scanner already honours
  this), and `Agent` is valid when the body delegates — nested subagents are on by
  default, so keep it in that case and ask otherwise. A parameterised form such as
  `Agent(worker, researcher)` is one tool that also restricts which subagents may be
  spawned; never split or drop its arguments.
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
- CLAUDE.md / global rules re-pasted into the body. Before calling a passage a
  duplicate, find the matching rule in a CLAUDE.md that this agent actually loads
  (project or user level) and quote where it lives. If the agent sets
  `omitClaudeMd: true` (the scanner reports `OMITS_CLAUDE_MD`), it inherits nothing
  and the body may hold the only copy: keep it. A section merely titled "global
  rules" with no matching inherited source is not a duplicate.
- Over-long bodies (>~150 lines for a single-purpose agent), over-explaining,
  excessive ALL-CAPS MUST/NEVER, contradictions, signposting filler.
- Preserve meaning. Trimming must not drop a real instruction; if unsure whether a
  passage is load-bearing, flag it, don't cut it.

**Description.** Ensure concrete triggers ("use when…/after…"), a proactive cue if
it should auto-fire, and no runaway multi-example bloat (it loads session-wide).

**Model and effort.** Recommend them together, from the agent's job. `haiku` suits
mechanical work (formatting, mechanical checks, lookups); read-only is not by itself
a reason to downgrade — a security review or an architecture analysis reads only and
still needs a strong model. `effort` (`low` to `max`) sets how hard the model
reasons; without it the agent runs at the session's level. Starting points:
read-only search or filter workers get `haiku` (no effort field) or a larger model
at low or medium; implementation workers medium; planners, architects and security
reviewers a strong model at high; `xhigh` or `max` only for long-running or the
hardest work, and only if the user confirms the job needs it. Levels depend on the
model (see `best-practices.md`); never recommend a level for a model that does not
support effort, such as Haiku. Flag complex agents left on default `inherit` that
could silently run on a weak session model. Present any model or effort change as a
candidate to verify on the agent's real task, not as a saving; without a
before/after comparison on that task it is a guess.

For a Codex agent the keys are `model` and `model_reasoning_effort`; set both, and
only to a level the model offers (the scanner's table is dated; the live catalog is
per account). Starting points from the Codex docs: `gpt-6-sol` at medium for
demanding or review work, `gpt-6-luna` at high for narrow, repeatable, read-heavy
work, high for reviewer or security agents, low when speed matters most; avoid
`max` and `ultra` unless the user confirms the job needs them. Effort names do not
map across model generations or to Claude's scale. For fleet-wide defaults, suggest
`[agents] default_subagent_model` / `default_subagent_reasoning_effort` in
`config.toml` instead of pinning every file. Same rule: candidates to verify.

**Codex agents: what not to claim.** No per-agent tool allowlist exists (only
disable-only `[features]` switches); `sandbox_mode`, `approval_policy` and
`mcp_servers` in an agent file do not take effect in Codex 0.149 and later; the
default model depends on the account; custom agents run in local Codex clients,
not Codex cloud. Required keys are `name`, `description` and
`developer_instructions`, and any Claude key (`tools`, `effort`, `permissionMode`
and the rest) makes Codex skip the whole agent.

**Frontmatter hygiene.** Claude: name lowercase-hyphenated; required fields
present; tool names valid (treat unknown names as possibly MCP/plugin — verify,
don't assume typo). Codex names may use underscores (the docs do).

### 4. Report and STOP

Present one section per agent using the template below, then a portfolio summary.
Stop and ask for approval. No agent file changes before that answer, even when the
request sounds like "make them cheaper"; only an explicit "apply" (or a prompt that
authorises edits up front) moves to step 5. If the user wants
per-finding control, let them accept/reject individually.

### 5. Apply approved changes, then bump versions

- Edit only the approved changes. Keep edits surgical; don't reflow untouched prose.
- Codex `.toml` files: change only the specific key lines, never re-serialise the
  file, keep top-level keys above the first `[table]` header, keep
  `developer_instructions` a TOML string, and never add a key Codex does not know,
  which is why they get no version bump (`bump_version.py` refuses them).
- After a Claude agent's content edits are applied, bump its version:
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
Current: model <model> · effort <effort> · <tools state> · body <N> lines · definition text ~<T> tok
Version: <current> → <proposed>   (Codex: n/a, no version field)

Findings
- [high] <code>: <issue> → <proposed fix>
- [med]  <code>: <issue> → <proposed fix>
  ...

Tool policy: <old: "inherit-all" or N tools> → <proposed comma list>   (Claude only)
  ? <uncertain tool>: keep or drop? — <reason it's uncertain>
  (schema cost of the removed tools is not measured by the scanner)

Proposed trims: <bullet list of sections/lines to cut, with ~definition-text tokens each>

Definition text: ~<old> → ~<new> tok (chars/4 of the file; not a launch-cost measurement)
Model and effort: <unchanged | candidate: <model>, effort <level>, verify on the agent's task before adopting>
  (Codex: `model` + `model_reasoning_effort`, a level the model offers)
```

End with:

```
## Summary
<n> agents audited · definition text ~<old> → ~<new> tok · <k> agents move from
inherit-all to an allowlist (tool-schema savings real but unmeasured here)
Apply all / pick per-agent / adjust?
```

The two numbers are different things: definition text is what the scanner measures
(and an allowlist makes it slightly *larger*, since the `tools` line adds characters);
the tool-schema reduction is the larger runtime effect and is reported as a policy
change, not a token figure, unless you measured it.

## Principles

- **Conservative on tools, aggressive on dead weight.** Never strip a tool the agent
  might need without flagging it; freely cut duplicated boilerplate and re-pasted
  global rules.
- **Measure, don't guess, and say what was measured.** The scanner counts definition
  text (chars/4): frontmatter plus body. It does not see tool schemas, inherited
  CLAUDE.md, loaded skills or memory, so never present its total as launch cost or
  its delta as savings. Rank with it, show before/after with it, label it.
- **Preserve behaviour.** The optimised agent must do the same job — just leaner.
- **One agent, one job.** If an agent does several jobs, say so and suggest splitting,
  but don't split without the user's go-ahead.
- **Context budget ≠ context window.** Bloat isn't only token cost — focused context
  outperforms large context, and tool-selection accuracy degrades as the tool list
  grows. Keep an agent's standing instructions tight: if removing a section wouldn't
  change the agent's behaviour, cut it.
