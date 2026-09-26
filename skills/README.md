# ionden-skills

Three agent skills for Claude Code and OpenAI Codex. Each one loads only when a task needs it.

- `subagent-optimizer` audits Claude Code subagents and Codex custom agents. It sets a tight `tools` allowlist, removes keys that make Codex skip an agent, cuts prompt bloat, and picks a model and effort that fit the job. It reports first and edits nothing until you say so.
- `skill-optimizer` shortens a skill's `SKILL.md` without losing an instruction. It freezes every rule, command and threshold before rewriting, and a gate rejects any rewrite that drops one.
- `writing-tests-that-can-fail` keeps tests honest in any language: each test exercises real behaviour and fails on the bug it exists to catch.

## What runs

`subagent-optimizer` and `skill-optimizer` include Python scripts that the agent runs locally with `python3`. They read the agent and skill files you point them at. They write only a working copy of a skill, the reports you ask for, and, once you approve an edit, the agent file itself with its version bumped. They make no network requests and install nothing. `writing-tests-that-can-fail` is instructions only.

Source, evals and measured results: https://github.com/IonDen/skills
