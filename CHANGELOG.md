# Changelog

## 2026-09-19

- `agent-optimiser`: `ExitPlanMode` is honoured when the agent sets `permissionMode: plan`; parameterised tools such as `Agent(worker, researcher)` stay one tool with their arguments intact; quoted `name`/`description` scalars are decoded before validation; `omitClaudeMd: true` is reported (`OMITS_CLAUDE_MD`) and the skill no longer trims inlined rules as duplicates without locating the inherited source; the scanner labels its figures as definition text rather than launch cost and the report template separates the tool-policy change from the token delta; model changes are presented as candidates to verify, not savings; a fourth, report-only eval with a conditional-capabilities fixture. Codex install notes corrected: skills load from `~/.agents/skills/` and `.agents/skills/`, and symlinked folders are supported. The repository validator now parses YAML (needs `pyyaml`).

## 2026-09-18

- Add `agent-optimiser` 1.2.0: audits Claude Code subagent definitions for token cost and trigger quality. Ships the scanner, the version bumper, references, three evals with fixtures, a Codex sidecar, and tests. Script paths are relative to the skill directory, the tool catalog and the subagent tool blacklist follow the September 2026 docs (`Agent` is treated as a question because nested subagents are on by default; legacy names such as `Task`, `LS` and `MultiEdit` get a rename flag; tools stripped from background subagents get their own flag), the scanner skips `SKILL.md` files and symlinks when walking a directory, and the version bumper preserves quotes and line endings, refuses symlinks and replaces files atomically.
