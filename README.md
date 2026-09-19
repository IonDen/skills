# Agent skills for Claude Code and OpenAI Codex

[![skills.sh](https://skills.sh/b/IonDen/skills)](https://skills.sh/IonDen/skills)
[![validate](https://github.com/IonDen/skills/actions/workflows/validate.yml/badge.svg)](https://github.com/IonDen/skills/actions/workflows/validate.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

A small catalogue of agent skills I use day to day. Each skill is a folder with a `SKILL.md` that Claude Code and Codex load only when a task needs it. A skill lands here when I could not find a good public equivalent.

## Skills

| Skill | What it does |
|---|---|
| [agent-optimiser](skills/agent-optimiser/) | A subagent optimizer for Claude Code. It audits your `.claude/agents/*.md` files and cuts what each agent costs to launch: a tight `tools` allowlist, less prompt bloat, a model that fits the job. One real agent went from 20,122 to 13,962 launch tokens with the same result. |

## Install

Any agent, with the [skills CLI](https://github.com/vercel-labs/skills):

```bash
npx skills add IonDen/skills                      # pick skills interactively
npx skills add IonDen/skills --skill agent-optimiser -g -a claude-code -y
npx skills add IonDen/skills --skill agent-optimiser -g -a codex -y
npx skills update
```

Codex reads skills from `~/.agents/skills/` (user) and `.agents/skills/` (project) and follows symlinked skill folders; pass `--copy` if you would rather have real files.

Claude Code, as a plugin:

```text
/plugin marketplace add IonDen/skills
/plugin install ionden-skills@ionden
```

## Development

```bash
python3 -m pytest tests -q
```

The skills' own scripts are plain Python 3.10+ with no dependencies. The repository validator and the tests need `pyyaml` and `pytest`. Every test names the one-line bug that would make it fail.

## License

MIT.
