R1: Audit subagent files, propose fixes, then apply approved ones and bump version.
  anchor: Audit Claude Code subagent files and propose token-economy + quality fixes, then apply the approved ones and bump each changed agent's version.
R2: Read both reference files before proposing tool changes.
  anchor: Read `references/best-practices.md` for the rationale behind each flag and `references/tool-catalog.md` for the tool list and archetype → tools map — consult both before proposing tool changes.
R3: Paths in this skill resolve relative to the skill's own directory, per harness.
  anchor: All paths below are relative to this skill's directory: in Claude Code that is `${CLAUDE_SKILL_DIR}`; in Codex it is wherever this SKILL.md was loaded from
R4: An agent name target resolves to its file; if absent, search the project dir and report what was found.
  anchor: An agent name (e.g. `solution-architect`) → `~/.claude/agents/<name>.md`; if absent, search `./.claude/agents/` and report what you found.
R5: A path target (file or directory) is used directly.
  anchor: A path (file or directory) → use it directly.
R6: "project" or a project dir target resolves to that project's .claude/agents/.
  anchor: "project" / a project dir → that project's `.claude/agents/`.
R7: State the resolved target list in one line before scanning.
  anchor: State the resolved target list in one line before scanning.
R8: Run the bundled scanner, which parses frontmatter, sizes everything, estimates tokens, raises flag codes, and finds duplicated boilerplate.
  anchor: Run the bundled scanner — it parses frontmatter, sizes everything, estimates tokens, raises flag codes, and finds boilerplate duplicated across agents
R9: Flag codes map to explanations in references/best-practices.md.
  anchor: `NO_TOOLS_FIELD`, `WRITE_ON_READONLY`, `MEMORY_BOILERPLATE`) map to explanations in `references/best-practices.md`.
R10: The scanner skips SKILL.md files when walking a directory, so pointing it at a whole .claude/ tree is safe.
  anchor: The scanner skips `SKILL.md` files when walking a directory, so pointing it at a whole `.claude/` tree is safe.
R11: Read the full agent file before analysing it.
  anchor: Read the full agent file.
R12: Read the body and list every tool its instructions actually require.
  anchor: Read the body and list every tool its instructions actually require.
R13: Cross-check the tool list against the archetype floor in tool-catalog.md.
  anchor: Cross-check against the archetype floor in `tool-catalog.md`.
R14: Propose the minimal allowlist that covers everything the body does.
  anchor: Propose the minimal allowlist that covers everything the body does.
R15: Breaking an agent costs far more than a slightly wide list (reason for keeping plausibly-used tools).
  anchor: Breaking an agent costs far more than a slightly wide list.
R16: Rename legacy tool names (Task to Agent).
  anchor: Rename legacy names (`Task` → `Agent`).
R17: Duplicated boilerplate across agents is usually a hand-written Persistent Agent Memory section, redundant when memory: is set.
  anchor: usually a hand-written "Persistent Agent Memory" section, redundant when `memory:` is set because the harness injects it.
R18: Trim duplicated boilerplate to one line.
  anchor: Trim to one line.
R19: Before calling a passage a duplicate, find the matching rule in a loaded CLAUDE.md and quote where it lives.
  anchor: Before calling a passage a duplicate, find the matching rule in a CLAUDE.md that this agent actually loads (project or user level) and quote where it lives.
R20: Flag complex agents left on default inherit that could silently run on a weak session model.
  anchor: Flag complex agents left on default `inherit` that could silently run on a weak session model.
R21: Present one section per agent using the template, then a portfolio summary.
  anchor: Present one section per agent using the template below, then a portfolio summary.
R22: Stop and ask for approval before applying anything.
  anchor: Stop and ask for approval.
R23: If the user wants per-finding control, let them accept or reject individually.
  anchor: If the user wants per-finding control, let them accept/reject individually.
R24: After a file's content edits are applied, bump its version with the script.
  anchor: After a file's content edits are applied, bump its version:
R25: Re-run the scanner on the changed agents and report before/after token totals and the new version numbers.
  anchor: Re-run the scanner on the changed agents and report before/after token totals and the new version numbers.
R26: Use the exact report structure per agent.
  anchor: Use this exact structure per agent:
R27: The scanner counts definition text as chars/4 of frontmatter plus body (the figure the report uses).
  anchor: The scanner counts definition text (chars/4): frontmatter plus body.
R28: Rank findings with the definition-text figure, show before/after with it, and label it.
  anchor: Rank with it, show before/after with it, label it.
