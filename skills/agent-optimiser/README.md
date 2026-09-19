# agent-optimiser: cut the token cost of Claude Code subagents

A subagent optimizer for Claude Code, packaged as an agent skill for Claude Code and OpenAI Codex. It audits subagent files (`.claude/agents/*.md`) and proposes fixes that make each agent cheaper to launch and more likely to trigger correctly: a minimal `tools` allowlist, trimmed system prompts, sharper descriptions, a model that fits the job. It reports first and edits only what you approve.

The biggest saving is usually the `tools` field. A subagent without one inherits every tool, and every tool schema is sent on every launch. On Claude Code 2.1.278 a one-line agent with no `tools` field cost 18,437 input tokens on Haiku 4.5 and 31,882 on Sonnet 5; with `Read, Grep, Glob` it cost 10,241 and 13,401.

![Claude Code subagent launch tokens before and after agent-optimiser, measured on Claude Code 2.1.278: a no-tools-field agent against a three-tool allowlist on Haiku and Sonnet, and three real agents that dropped 31%, 13% and 3% with equivalent results](https://raw.githubusercontent.com/IonDen/skills/main/docs/images/agent-optimiser-workflow.svg)

The bars are input tokens of the subagent's first API request, read from the session transcript. The top pair is a controlled probe: the same one-line agent with no `tools` field and with a three-tool allowlist. The lower three are real agents optimised by the skill, launched on the same task with the same model before and after; all three produced equivalent results. Method, table and the harness are in `evals/recorded/2026-09-19-launch-cost/`.

## Install

```bash
npx skills add IonDen/skills --skill agent-optimiser -g -a claude-code -y
npx skills add IonDen/skills --skill agent-optimiser -g -a codex -y          # add --copy for real files instead of symlinks
```

## Use

- "Audit my subagents": scans `~/.claude/agents/` and reports per agent.
- "Optimize the solution-architect agent": one agent.
- "Make the agents in .claude/agents cheaper": a project directory.

## What ships

| Path | Purpose |
|---|---|
| `SKILL.md` | The workflow: scope, scan, analyse, report, apply on approval |
| `scripts/scan_agents.py` | Deterministic scanner: frontmatter, token estimates, flag codes, cross-agent duplicate blocks. `--json` for structured output |
| `scripts/bump_version.py` | Bumps the `version` field of an edited agent |
| `references/best-practices.md` | What each flag means and why |
| `references/tool-catalog.md` | Built-in tools, the subagent blacklist, archetype → tools map |
| `evals/` | Three eval prompts and the fixture agents they run against |

Tests live at the repository root under `tests/`.
