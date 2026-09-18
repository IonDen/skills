# Changelog

## 2026-09-18

- Add `agent-optimiser` 1.2.0: audits Claude Code subagent definitions for token cost and trigger quality. Ships the scanner, the version bumper, references, three evals with fixtures, a Codex sidecar, and tests. Script paths are relative to the skill directory, the tool catalog and the subagent tool blacklist follow the September 2026 docs (`Agent` is treated as a question because nested subagents are on by default; legacy names such as `Task`, `LS` and `MultiEdit` get a rename flag; tools stripped from background subagents get their own flag), the scanner skips `SKILL.md` files and symlinks when walking a directory, and the version bumper preserves quotes and line endings, refuses symlinks and replaces files atomically.
