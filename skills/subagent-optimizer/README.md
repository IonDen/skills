# subagent-optimizer: cut the token cost of Claude Code subagents

A subagent optimizer for Claude Code, packaged as an agent skill. It reads your `.claude/agents/*.md` files, reports what each one wastes on every launch, and applies only the fixes you approve. It is plain Markdown plus two Python scripts, so it also runs under OpenAI Codex and anything else that loads `SKILL.md`.

Triggers: "audit my subagents", "optimize my agents", "my agent uses too many tokens", "fix the tools list", "review .claude/agents", "make my agents cheaper".

## Why this exists

Claude Code already tells you how to write a subagent. It does not tell you what one costs. A subagent that omits the `tools` field inherits every tool, and every tool schema is sent on every single launch; agent prompts quietly accumulate boilerplate the harness already injects; a description that never says "use when" fails to trigger at all. None of that shows up in a diff, and `/doctor` covers skills and MCP servers, not agents.

Measured on Claude Code 2.1.278, the same one-line agent cost 18,437 input tokens on Haiku 4.5 with no `tools` field and 10,241 with `Read, Grep, Glob`. On Sonnet 5: 31,882 against 13,401.

## What it checks

| Flag | What it means | Typical fix |
|---|---|---|
| `NO_TOOLS_FIELD` | No `tools` field, so the agent inherits every tool on each launch | The minimal allowlist its body actually uses |
| `WRITE_ON_READONLY` | Body says it never edits code, yet `Edit`/`Write` are granted | Drop them, unless `memory:` is set and needs them |
| `DEAD_TOOL_ENTRY` | Tools a subagent can never use (`AskUserQuestion`, `Workflow`, `EndConversation`, plan and schedule tools) | Remove |
| `LEGACY_TOOL_NAME` | A name from an older release (`Task`, `LS`, `MultiEdit`) | Rename to the current tool |
| `NESTED_AGENT_TOOL` | Lists `Agent`; legitimate only if the body delegates | Asked as a question, never stripped silently |
| `BACKGROUND_STRIPPED` | Tools the harness removes from background subagents | Keep only for a foreground agent |
| `MANY_TOOLS` | More than ten tools on a single-purpose agent | Trim to what the body uses |
| `MEMORY_BOILERPLATE` | A hand-written memory section the harness already injects | One line |
| `WEAK_TRIGGER` | Description without "use when", "after" or a proactive cue | Concrete trigger conditions |
| `LONG_BODY`, `LONG_DESCRIPTION` | Prompt or routing description past the useful size | Cut duplication, keep one worked example |
| `MODEL_INHERIT` | No `model`, so it runs on whatever the session uses | Pin when competence is fixed |
| `OMITS_CLAUDE_MD` | `omitClaudeMd: true`, so body rules may be the only copy | Never trimmed as duplicates |

## What it does not do

It does not write agents for you, invent tools an agent never mentions, or touch a file before you approve the report. It does not measure launch cost: the scanner counts the text of the agent file, and the tool-schema saving is reported as a policy change, not a number. It knows Claude Code subagents, not Codex agent configuration, which is a different format.

## One real before and after

`bash-git-ops`, a real agent of mine, audited and edited by the skill. Frontmatter first:

```diff
 name: bash-git-ops
+version: 1.1.0
-description: "...four worked examples, 1,900 characters..."
+description: "...one worked example, 900 characters..."
+tools: Bash, Read, Grep, Glob, Edit, Write
 model: haiku
 memory: user
```

Then the body: a 46-line "Persistent Agent Memory" section, which the harness injects anyway for a `memory:` agent, became one line that keeps the part the harness does not say.

```diff
-# Persistent Agent Memory
-
-You have a persistent Persistent Agent Memory directory at `~/.claude/agent-memory/bash-git-ops/`.
-... 43 more lines ...
+Consult your agent memory before starting and update it as you learn; session
+transcripts are a slow last resort for past context.
```

145 lines became 102. `Edit` and `Write` stayed, because `memory: user` needs them and stripping them silently breaks memory upkeep. Launched on the same task, before and after, the agent returned the same answer and its first request went from 20,122 to 13,962 input tokens.

![Claude Code subagent launch tokens before and after subagent-optimizer, measured on Claude Code 2.1.278: a no-tools-field agent against a three-tool allowlist on Haiku and Sonnet, and three real agents that dropped 31%, 13% and 3% with equivalent results](https://raw.githubusercontent.com/IonDen/skills/main/docs/images/subagent-optimizer-workflow.svg)

Full method, table and harness: [`evals/recorded/2026-09-19-launch-cost/`](evals/recorded/2026-09-19-launch-cost/).

## Install

```bash
npx skills add IonDen/skills --skill subagent-optimizer -g -a claude-code -y
npx skills add IonDen/skills --skill subagent-optimizer -g -a codex -y   # --copy for real files
```

The `-a claude-code` matters: most agents share `.agents/skills` and the CLI installs there by default, while Claude Code reads `.claude/skills` and is not pre-selected in the interactive picker.

As a plugin, which also keeps it updated:

```text
/plugin marketplace add IonDen/skills        # Claude Code
codex plugin marketplace add IonDen/skills   # Codex
```

By hand: copy this folder into `~/.claude/skills/` or `~/.agents/skills/`.

## Use

- "Audit my subagents": scans `~/.claude/agents/` and reports per agent.
- "Optimize the solution-architect agent": one agent.
- "Make the agents in .claude/agents cheaper": a project directory.

It reports first and stops. Nothing is edited until you say so.

## What ships

```text
subagent-optimizer/
├── SKILL.md                     the workflow: scope, scan, analyse, report, apply
├── agents/openai.yaml           Codex and ChatGPT metadata
├── references/
│   ├── best-practices.md        what each flag means and why
│   └── tool-catalog.md          built-in tools, the subagent blacklist, archetype to tools
├── scripts/
│   ├── scan_agents.py           the scanner: flags, sizes, cross-agent duplicate blocks
│   └── bump_version.py          bumps the version of an edited agent
└── evals/
    ├── evals.json               four prompts with expected outcomes
    ├── fixtures/                the agents they run against
    └── recorded/                measured runs, with the harness that produced them
```

## Sources

The flag list follows Anthropic's own documentation: [subagents](https://code.claude.com/docs/en/sub-agents) for the frontmatter fields, the tool blacklist and nested-subagent rules, [tools reference](https://code.claude.com/docs/en/tools-reference) for current tool names, [costs](https://code.claude.com/docs/en/costs) for what is deferred, and the API [tool-search documentation](https://platform.claude.com/docs/en/agents-and-tools/tool-use/tool-search-tool) for the 55k-token and 85% figures, which were measured for MCP tool definitions.

## Version history

<details>
<summary>Show release notes</summary>

**1.2.1**: Added US-spelling triggers ("optimize my subagents", "subagent optimizer") so the skill loads when people ask in those words. No change to the flags or the scripts.

**1.2.0**: First public release. Compared with the private version: `ExitPlanMode` is kept when the agent sets `permissionMode: plan`; parameterised tools such as `Agent(worker, researcher)` stay one tool; `omitClaudeMd: true` is surfaced so inlined rules are not trimmed as duplicates; the scanner labels its figures as definition text instead of launch cost; model changes are candidates to verify rather than savings. `bump_version.py` preserves quotes and line endings, refuses symlinks and writes atomically.

</details>

## Author and license

By [Denis Ineshin](https://github.com/IonDen). MIT.
