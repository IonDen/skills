# Agent skills for Claude Code and OpenAI Codex

[![skills.sh](https://skills.sh/b/IonDen/skills)](https://skills.sh/IonDen/skills)
[![validate](https://github.com/IonDen/skills/actions/workflows/validate.yml/badge.svg)](https://github.com/IonDen/skills/actions/workflows/validate.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

Agent skills I use day to day with Claude Code and OpenAI Codex, published when I could not find a good public equivalent. The first one, [agent-optimiser](skills/agent-optimiser/), audits Claude Code subagents and cuts what they cost to launch: on a real agent, measured launch tokens went from 20,122 to 13,962 with the same result.

An agent skill is a folder with a `SKILL.md` file: a name, a description that tells the agent when to use it, and instructions, plus any references, scripts and evals it needs. Claude Code and Codex load the description up front and read the rest only when a task matches, so a skill costs almost nothing until it is used.

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

## Skills

| Skill | Use when |
|---|---|
| [agent-optimiser](skills/agent-optimiser/) | Your Claude Code subagents (`.claude/agents/*.md`) cost too many tokens to launch or trigger unreliably. The skill works as a subagent optimizer: it audits every agent for a missing or bloated `tools` allowlist, dead tool entries, duplicated boilerplate, weak descriptions and an over- or under-provisioned model, then applies the fixes you approve and bumps each edited agent's version. |

![Claude Code subagent launch cost before and after agent-optimiser, measured on Claude Code 2.1.278: on Haiku a no-tools-field agent costs 18,437 tokens against 10,241 with a three-tool allowlist; on Sonnet 31,882 against 13,401; three real agents optimised by the skill dropped 31%, 13% and 3% with equivalent task results](docs/images/agent-optimiser-workflow.svg)

## Development

```bash
python3 -m pytest tests -q
```

The skill's own scripts are plain Python 3.10+ with no dependencies. The repository validator and the tests need `pyyaml` and `pytest`. Every test names the one-line bug that would make it fail.

## License

MIT.
