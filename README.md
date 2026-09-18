# skills

[![skills.sh](https://skills.sh/b/IonDen/skills)](https://skills.sh/IonDen/skills)

Agent skills I use day to day with Claude Code and Codex. Each skill is a folder under `skills/` with a `SKILL.md`, and any references, scripts and evals it needs. They are published here when I could not find a good public equivalent.

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
| [agent-optimiser](skills/agent-optimiser/) | You want your Claude Code subagents (`.claude/agents/*.md`) cheaper to launch and more reliable to trigger: it audits every agent for a missing or bloated `tools` allowlist, dead tool entries, duplicated boilerplate, weak descriptions and an over- or under-provisioned model, then applies the fixes you approve and bumps each edited agent's version. |

## Development

```bash
python3 -m pytest tests -q
```

The skill's own scripts are plain Python 3.10+ with no dependencies. The repository validator and the tests need `pyyaml` and `pytest`. Every test names the one-line bug that would make it fail.

## License

MIT.
