# Changelog

## 2026-09-19 (discoverability)

- READMEs lead with what the repository and `agent-optimiser` are for, in the terms people search with (Claude Code, OpenAI Codex, subagent optimizer, token cost), and carry the measured launch-cost figures up front. `agent-optimiser` 1.2.1 adds US-spelling triggers ("optimize my subagents", "subagent optimizer") to its description. Plugin manifests get fuller descriptions and keywords. A 1280×640 social preview card is in `docs/images/`.

## 2026-09-19

- `agent-optimiser`: measured launch cost. A controlled probe on Claude Code 2.1.278 puts a no-`tools`-field subagent at 18,437 input tokens on Haiku 4.5 and 31,882 on Sonnet 5, against 10,241 and 13,401 with a three-tool allowlist. Three real agents optimised by the skill dropped 31%, 13% and 3% on the same task with equivalent results. Table, harness and the optimised files are under `evals/recorded/2026-09-19-launch-cost/`; the README diagram now shows these numbers.
- `agent-optimiser`: `ExitPlanMode` is honoured when the agent sets `permissionMode: plan`; parameterised tools such as `Agent(worker, researcher)` stay one tool with their arguments intact; quoted `name`/`description` scalars are decoded before validation; `omitClaudeMd: true` is reported (`OMITS_CLAUDE_MD`) and the skill no longer trims inlined rules as duplicates without locating the inherited source; the scanner labels its figures as definition text rather than launch cost and the report template separates the tool-policy change from the token delta; model changes are presented as candidates to verify, not savings; a fourth, report-only eval with a conditional-capabilities fixture. Codex install notes corrected: skills load from `~/.agents/skills/` and `.agents/skills/`, and symlinked folders are supported. The repository validator now parses YAML (needs `pyyaml`).

## 2026-09-18

- Add `agent-optimiser` 1.2.0: audits Claude Code subagent definitions for token cost and trigger quality. Ships the scanner, the version bumper, references, three evals with fixtures, a Codex sidecar, and tests. Script paths are relative to the skill directory, the tool catalog and the subagent tool blacklist follow the September 2026 docs (`Agent` is treated as a question because nested subagents are on by default; legacy names such as `Task`, `LS` and `MultiEdit` get a rename flag; tools stripped from background subagents get their own flag), the scanner skips `SKILL.md` files and symlinks when walking a directory, and the version bumper preserves quotes and line endings, refuses symlinks and replaces files atomically.
