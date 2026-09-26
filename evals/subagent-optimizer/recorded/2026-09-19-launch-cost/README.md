# Recorded run, 2026-09-19: launch cost before and after

Three agent definitions were optimised by the skill (a fresh Claude agent following SKILL.md, edits authorised, models left unchanged, every "flag as a question" tool kept), then each version was launched on the same fixed task and the input tokens of the subagent's first API request were read from the session transcript. That first request is the launch cost: system prompt, tool schemas, CLAUDE.md, the agent body, and the task.

Setup: Claude Code 2.1.278 on macOS, `claude -p` with `--agents` built from each file, MCP servers disabled (`--strict-mcp-config`), the user-level CLAUDE.md loaded as usual, one run per cell. The harness is in `../../measure/`, hardened on 2026-09-20 after a Socket audit (it validates the label, refuses to bypass permissions, and no longer mis-resolves the summary path); re-running the `bash-git-ops` before case with the hardened script gave 20,099 tokens against the 20,122 recorded here, the difference being ordinary session-context variation (`md2agent.py`, `measure.sh`, the probe agent definitions); `before/` is `../../fixtures/`, `after/` is in this directory, and `optimizer-report.md` is the report the skill wrote.

## Controlled probe: the tool schemas alone

The same one-line agent, launched with no `tools` field and with a three-tool allowlist. Two runs per cell gave identical counts.

| Model | No `tools` field | `Read, Grep, Glob` | Difference |
|---|---:|---:|---:|
| Haiku 4.5 | 18,437 | 10,241 | −8,196 (−44%) |
| Sonnet 5 | 31,882 | 13,401 | −18,481 (−58%) |

Two more Haiku cells locate the big schemas: adding `Bash, Edit, Write` to the three-tool agent costs 2,577 tokens; adding `Skill` costs 2,970 (it carries the skill catalog of the machine it runs on).

## Three real agents, same task, same model

| Agent (model) | Tools before → after | Body lines | Launch tokens before → after | Task result |
|---|---|---:|---:|---|
| bash-git-ops (Haiku 4.5) | none → `Bash, Read, Grep, Glob, Edit, Write` | 137 → 92 | 20,122 → 13,962 (−31%) | identical: branch, last commit subject, modified and untracked files all correct, nothing changed |
| plan-driven-coder (Sonnet 5) | none → `Read, Edit, Write, Grep, Glob, Bash, Skill` | 114 → 69 | 34,134 → 29,734 (−13%) | identical files, `1 passed` both times |
| solution-architect (Opus 5) | 15 → 10 (dropped `NotebookEdit`, `TaskCreate/Get/Update/List`) | 170 → 125 | 28,688 → 27,893 (−3%) | both plans correct and proportionate; the after plan states the collection-versus-rendering split more precisely |

Tasks: report branch, last commit and working-tree state of a small repository without changing it; implement a two-file plan (`add.py`, one pytest) and run pytest; write a plan for adding a `--json` flag to a ten-line CLI.

One effect the numbers above understate: the before version of plan-driven-coder, which inherited `Agent`, delegated the pytest step to a nested `bash-git-ops` subagent that the task did not need. That nested launch cost another 24,333 tokens. The after version, with an allowlist and no `Agent`, ran the tests itself.

## Where the remaining cost is

On Sonnet 5 and Opus 5 the base prompt is larger than on Haiku, and any agent that lists `Skill` carries the skill catalog. The after versions of plan-driven-coder and solution-architect keep `Skill` because their bodies route through skills, so most of their launch cost is base prompt plus catalog, not the agent file. The definition-text estimate from the scanner (chars/4 of the file) moved 7,622 → 5,176 across the three files; that is the part the skill edits directly.

## Reproduce

```bash
cd evals/subagent-optimizer/measure
# controlled probe: probe-agents.json holds probe-all / probe-min on Haiku;
# probe-agents-2.json holds the Sonnet pair and the Bash/Edit/Write and Skill cells (swap the agent name in the prompt)
claude -p "Use the Agent tool to launch the probe-all agent with the prompt 'say ok'. Then reply with the single word done." \
  --model haiku --agents "$(cat probe-agents.json)" --strict-mcp-config --mcp-config '{"mcpServers":{}}' --max-turns 4 --output-format json < /dev/null > /dev/null
# then read the subagent transcript under ~/.claude/projects/<cwd-slug>/<session>/subagents/*.jsonl:
# the first assistant message's usage (input + cache_creation + cache_read) is the launch cost.
# real agents: ./measure.sh <label> <agent.md> <task-dir> "<task prompt>"
```

The launch cost depends on the model, the Claude Code version, the user's CLAUDE.md and, for `Skill`, the installed skill catalog, so expect different absolute numbers on another machine; the before/after gap for the same agent on the same machine is the stable part.
