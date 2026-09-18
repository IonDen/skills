# Changelog

## 2026-09-18

- Add `agent-optimiser` 1.2.0: audits Claude Code subagent definitions for token cost and trigger quality. Ships the scanner, the version bumper, references, three evals with fixtures, a Codex sidecar, and tests. Compared with the private 1.1.0: script paths are relative to the skill directory, the tool catalog and the subagent tool blacklist follow the September 2026 docs (`Workflow`, `TaskOutput`, `EndConversation` added; legacy names such as `LS` and `MultiEdit` marked), and the scanner skips `SKILL.md` files when walking a directory.
