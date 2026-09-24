# Changelog

## 2026-09-24

- Add `skill-optimizer` 1.0.0: cuts a skill's token cost without losing an instruction. It freezes every rule, anchor, literal and code block in the original `SKILL.md` before any rewrite exists, then gates the candidate deterministically: a rule sentence, an anchored sentence, a literal or a strong rule's position can't disappear or move without the gate rejecting the candidate outright or asking for approval, and only a human sign-off can delete a rule sentence or confirm a section's move into `references/`. What passes the gate is not itself a claim that behaviour is unchanged: catching that needs a reverse-reconstruction read and, where the skill ships evals, a same-prompt run against both versions, and the report has to state whether that step ran or was skipped and why. Run against a copy of this repository's own `subagent-optimizer`, it cut the body from 8,863 to 8,758 characters (-1.2%), left two rule-carrying sentences as flagged decisions instead of removing them, and both of `subagent-optimizer`'s own evals came back with the same 13 of 13 expected clauses met on the optimized copy as on the original. The skill was already tight, and the optimizer said so instead of forcing a bigger number.

## 2026-09-20 (rename)

- The skill is now `subagent-optimizer`, was `agent-optimiser`, and the version goes to 1.3.0. Searching the skills directory showed the old name was findable only by people who already knew it: it surfaced for "optimiser" and for nothing else, while "subagent", "optimizer", "claude code subagents" and "audit agents" all returned other authors' skills. Names weigh far more than descriptions in that ranking, and the American spelling is what most people type. Install it as `npx skills add IonDen/skills --skill subagent-optimizer`; the old name is gone rather than aliased, because two installs were not worth a permanent second identity.

## 2026-09-20 (harness safety)

- Hardened `evals/measure/measure.sh` after a Socket audit on skills.sh flagged it. It validated nothing, so a crafted label could write outside the output directory; it passed `--dangerously-skip-permissions`; and a shell expansion sat inside a quoted heredoc, so the summary path never resolved and the script failed at its last step. It now validates the label and both paths, uses the `acceptEdits` permission mode, passes the output directory to Python as an argument, and documents that it runs an agent against a throwaway copy. Five tests cover the guards.

## 2026-09-20 (later)

- Dropped the skills.sh badge from the README. That endpoint renders an install count, and until skills.sh attaches one to this repository it returns a "resource not found" badge. The listing is linked in the install section instead; the badge can come back once a count appears.

## 2026-09-20

- The `subagent-optimizer` README is rebuilt around what a stranger needs: why the skill exists, a table of every flag with its typical fix, an explicit list of what it does not do, one real before-and-after of an agent it edited, the trigger phrases in quotes, the file tree, the documentation it follows, and a collapsed version history. `.codex-plugin/plugin.json` makes `codex plugin marketplace add` resolve natively instead of through the Claude path, and CI validates the skill against the Agent Skills spec with the `skills-ref` reference validator.

## 2026-09-19 (discoverability)

- The repository README is now a short catalogue: what the repository is, the skills table first, then install. The `subagent-optimizer` README leads with what the skill is for, in the terms people search with (Claude Code, OpenAI Codex, subagent optimizer, token cost), and carries the launch-cost diagram and figures. `subagent-optimizer` 1.2.1 adds US-spelling triggers ("optimize my subagents", "subagent optimizer") to its description. Plugin manifests get fuller descriptions and keywords. A 1280×640 social preview card is in `docs/images/`.

## 2026-09-19

- `subagent-optimizer`: measured launch cost. A controlled probe on Claude Code 2.1.278 puts a no-`tools`-field subagent at 18,437 input tokens on Haiku 4.5 and 31,882 on Sonnet 5, against 10,241 and 13,401 with a three-tool allowlist. Three real agents optimised by the skill dropped 31%, 13% and 3% on the same task with equivalent results. Table, harness and the optimised files are under `evals/recorded/2026-09-19-launch-cost/`; the README diagram now shows these numbers.
- `subagent-optimizer`: `ExitPlanMode` is honoured when the agent sets `permissionMode: plan`; parameterised tools such as `Agent(worker, researcher)` stay one tool with their arguments intact; quoted `name`/`description` scalars are decoded before validation; `omitClaudeMd: true` is reported (`OMITS_CLAUDE_MD`) and the skill no longer trims inlined rules as duplicates without locating the inherited source; the scanner labels its figures as definition text rather than launch cost and the report template separates the tool-policy change from the token delta; model changes are presented as candidates to verify, not savings; a fourth, report-only eval with a conditional-capabilities fixture. Codex install notes corrected: skills load from `~/.agents/skills/` and `.agents/skills/`, and symlinked folders are supported. The repository validator now parses YAML (needs `pyyaml`).

## 2026-09-18

- Add `subagent-optimizer` 1.2.0: audits Claude Code subagent definitions for token cost and trigger quality. Ships the scanner, the version bumper, references, three evals with fixtures, a Codex sidecar, and tests. Script paths are relative to the skill directory, the tool catalog and the subagent tool blacklist follow the September 2026 docs (`Agent` is treated as a question because nested subagents are on by default; legacy names such as `Task`, `LS` and `MultiEdit` get a rename flag; tools stripped from background subagents get their own flag), the scanner skips `SKILL.md` files and symlinks when walking a directory, and the version bumper preserves quotes and line endings, refuses symlinks and replaces files atomically.
