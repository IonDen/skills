# Agent skills for Claude Code and OpenAI Codex

[![validate](https://github.com/IonDen/skills/actions/workflows/validate.yml/badge.svg)](https://github.com/IonDen/skills/actions/workflows/validate.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

A small catalogue of agent skills I use day to day. Each skill is a folder with a `SKILL.md` that Claude Code and Codex load only when a task needs it. A skill lands here when I could not find a good public equivalent.

## Skills

| Skill | What it does |
|---|---|
| [subagent-optimizer](skills/subagent-optimizer/) | Audits your `.claude/agents/*.md` files and cuts what each agent costs to launch: a tight `tools` allowlist, less prompt bloat, a model that fits the job. One real agent went from 20,122 to 13,962 launch tokens with the same result. |
| [skill-optimizer](skills/skill-optimizer/) | Cuts a skill's `SKILL.md` down without losing an instruction: freezes every rule, anchor and literal in the original, then gates a rewrite against that freeze and rejects or asks rather than guessing. Run on a real skill already in this repository, it cut 8,863 characters to 8,758 (-1.2%) and left the rest exactly as it was. |

## Install

Any agent, with the [skills CLI](https://github.com/vercel-labs/skills). The skills are also listed at [skills.sh/ionden/skills](https://skills.sh/ionden/skills):

```bash
npx skills add IonDen/skills                      # pick skills interactively
npx skills add IonDen/skills --skill subagent-optimizer -g -a claude-code -y
npx skills add IonDen/skills --skill subagent-optimizer -g -a codex -y
npx skills add IonDen/skills --skill skill-optimizer -g -a claude-code -y
npx skills add IonDen/skills --skill skill-optimizer -g -a codex -y
npx skills update
```

Most agents share `.agents/skills`, so the CLI installs there by default. Claude Code reads `.claude/skills` instead, which is why `-a claude-code` is on the lines above: without it the CLI asks which agents you want and Claude Code is not pre-selected. Pass `--copy` if you would rather have real files than symlinks.

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
