# Agent skills for Claude Code and OpenAI Codex

[![validate](<https://github.com/IonDen/skills/actions/workflows/validate.yml/badge.svg>)](<https://github.com/IonDen/skills/actions/workflows/validate.yml>)
[![License: MIT](<https://img.shields.io/badge/license-MIT-blue.svg>)](LICENSE)
[![skills.sh](<https://skills.sh/b/IonDen/skills>)](<https://skills.sh/IonDen/skills>)
[![Claude plugin directory: listed](<https://img.shields.io/badge/Claude_plugin_directory-listed-0d9488>)](<https://claude.ai/customize/plugins/id/ca97a97b-2635-413b-8e0e-e7fa82076699%40anthropic-plugin-directory>)

Agent definitions and skills (folders with a `SKILL.md`) load into your coding agent's context each time, and a Claude agent with no `tools` list loads every tool: both cost tokens. Tests an agent writes can pass without testing anything: they mock away what they should exercise, or copy expected values from the code.

You need this if you use Claude Code or Codex and want cheaper agents and skills, or tests that catch real bugs.

- [subagent-optimizer](plugins/ionden-skills/skills/subagent-optimizer/): cuts the tokens a Claude Code subagent or Codex custom agent loads at launch.
- [skill-optimizer](plugins/ionden-skills/skills/skill-optimizer/): shrinks a skill without dropping an instruction.
- [writing-tests-that-can-fail](plugins/ionden-skills/skills/writing-tests-that-can-fail/): keeps the tests your agent writes real: each can fail on the bug it covers.

```bash
npx skills add IonDen/skills
```

The CLI asks which skills and agents to install; Claude Code users: tick it, as it is not pre-selected. Your agent can load a skill when a task matches it.

## Skills

| Skill | What it does |
|---|---|
| [subagent-optimizer](plugins/ionden-skills/skills/subagent-optimizer/) | Audits `.claude/agents/*.md` and `.codex/agents/*.toml`: sets a tight `tools` allowlist on Claude agents, removes keys that make Codex skip an agent, trims prompt bloat, and suggests a fitting model and reasoning effort. One real agent went from 20,122 to 13,962 launch tokens with the same result. |
| [skill-optimizer](plugins/ionden-skills/skills/skill-optimizer/) | Fewer tokens per load: records every rule, anchor and literal of the original, then checks the rewrite against that record; rejects or asks rather than guessing. On five real skills it cut 1.2% to 3.5% of the body, 2.3% overall, kept every requirement it extracted, and listed the cuts it was unsure of instead of making them ([evidence](evals/skill-optimizer/recorded/2026-09-24-real-skills/)). |
| [writing-tests-that-can-fail](plugins/ionden-skills/skills/writing-tests-that-can-fail/) | In any language, tests exercise real behaviour rather than mocks, fail on the bug they exist to catch, and stay untouched when the code is what's wrong. Given the same prompts, Claude Haiku without the skill mocked both collaborators in 3 of 3 Python suites and copied expected values from the code's constants in 2 of 3; with the skill, 0 of 3 did either ([evidence](evals/writing-tests-that-can-fail/)). In our Claude Code tests, two sentences in `CLAUDE.md` made it load far more often when tests were written ([how](plugins/ionden-skills/skills/writing-tests-that-can-fail/README.md#make-it-automatic)). |

## Install

Any agent, with the [skills CLI](<https://github.com/vercel-labs/skills>):

```bash
npx skills add IonDen/skills                      # pick skills interactively
npx skills add IonDen/skills --skill subagent-optimizer -g -a claude-code -y
npx skills add IonDen/skills --skill subagent-optimizer -g -a codex -y
npx skills add IonDen/skills --skill skill-optimizer -g -a claude-code -y
npx skills add IonDen/skills --skill skill-optimizer -g -a codex -y
npx skills add IonDen/skills --skill writing-tests-that-can-fail -g -a claude-code -y
npx skills add IonDen/skills --skill writing-tests-that-can-fail -g -a codex -y
npx skills update
```

Most agents share `.agents/skills`, so the CLI installs there by default. Claude Code reads `.claude/skills`, so these lines pass `-a claude-code`: without it the CLI asks which agents you want, and Claude Code is not pre-selected. Add `--copy` for real files instead of symlinks.

Claude plugin directory: the plugin is [listed there](<https://claude.ai/customize/plugins/id/ca97a97b-2635-413b-8e0e-e7fa82076699%40anthropic-plugin-directory>). Add it on claude.ai to use it in Claude Code sessions.

Claude Code, as a plugin:

```text
/plugin marketplace add IonDen/skills
/plugin install ionden-skills@ionden
```

Codex, as a plugin:

```bash
codex plugin marketplace add IonDen/skills
codex plugin add ionden-skills@ionden
```

## Development

Releasing a plugin: the [publishing instructions](docs/publishing.md) cover the upload ZIP and the OpenAI directory steps.

```bash
python3 -m pytest tests -q
```

The skills' scripts are plain Python 3.10+ with no dependencies. The repository validator and the tests need `pyyaml` and `pytest`.

## License

MIT.
