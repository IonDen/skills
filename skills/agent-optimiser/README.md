# agent-optimiser

Audits Claude Code subagent files (`.claude/agents/*.md`) and proposes fixes that make each agent cheaper to launch and more likely to trigger correctly: a minimal `tools` allowlist, trimmed system prompts, sharper descriptions, a model that fits the job. It reports first and edits only what you approve.

![How agent-optimiser works and what to expect: a scan, judge, report-then-stop, apply pipeline, and a before/after of one agent from a recorded run](https://raw.githubusercontent.com/IonDen/skills/main/docs/images/agent-optimiser-workflow.svg)

The lower half of the picture is one agent from a recorded run. The token figures are definition text, characters divided by four over the agent file; the allowlist also stops every unused tool schema loading at launch, which the scanner does not count.

## Install

```bash
npx skills add IonDen/skills --skill agent-optimiser -g -a claude-code -y
npx skills add IonDen/skills --skill agent-optimiser -g -a codex -y          # add --copy for real files instead of symlinks
```

## Use

- "Audit my subagents" — scans `~/.claude/agents/` and reports per agent.
- "Optimise the solution-architect agent" — one agent.
- "Make the agents in .claude/agents cheaper" — a project directory.

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
