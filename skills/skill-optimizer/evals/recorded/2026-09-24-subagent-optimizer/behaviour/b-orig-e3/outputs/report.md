# Subagent audit — b-orig-e3/agents

Scope: `agents/*.md` (5 files) — `bash-git-ops.md`, `code-explorer.md`,
`plan-driven-coder.md`, `plan-reviewer.md`, `solution-architect.md`.
Method: `scripts/scan_agents.py agents --json` (from the `subagent-optimizer`
skill at `<SKILL_DIR>`) plus a full read of each file against
`references/best-practices.md` and `references/tool-catalog.md`.

Report only — nothing has been edited or version-bumped. All numbers below
are definition text (frontmatter + body, chars/4) as the scanner measures it;
they are not launch cost, and tool-schema savings from tightening `tools` are
real but unmeasured.

---

## bash-git-ops  (agents/bash-git-ops.md)
Current: model haiku · no `tools` field (inherits all) · body 137 lines · definition text ~2210 tok
Version: (none) → 1.1.0 if changes below are applied

Findings
- [high] NO_TOOLS_FIELD: no `tools` field → inherits every built-in tool on each launch. Body only ever does shell/git ops plus memory upkeep → propose an explicit allowlist (see below).
- [med] MEMORY_BOILERPLATE: lines 100-145 (`# Persistent Agent Memory` through `## MEMORY.md`) are the generic memory-upkeep section the harness already injects because `memory: user` is set — byte-identical in shape to the same section in `plan-driven-coder.md` and `solution-architect.md` (scanner's `duplicate_blocks`). Trim to one line, e.g. "Update your memory as you learn." Keep lines 91-98 ("Update your agent memory as you discover..." + the bash-git-ops-specific examples: repo names, remote URLs, branch conventions) — that part is genuinely agent-specific, not boilerplate.
- [low] LONG_DESCRIPTION: description is 4 full `<example>` blocks (~502 tok). One covers directory creation (bash) and one covers a commit (git) — the other two (branch creation, moving files) repeat the same pattern each already demonstrates. Keep the intro + 2 examples, cut the other 2.

Tool policy: inherit-all → `Bash, Read, Grep, Glob, Edit, Write`
  (Bash/git-ops archetype: `Bash, Read, Grep, Glob`; `Edit`+`Write` kept for the `memory: user` exception, not because the body edits repo files. No `Agent`, `WebFetch`/`WebSearch`, or `NotebookEdit` — nothing in the body uses them.)
  (schema cost of the removed tools is not measured by the scanner)

Proposed trims:
- Cut description examples 3 ("branch + checkout") and 4 ("move .log files") → ~190 tok
- Collapse the Persistent Agent Memory boilerplate (lines 100-145) to one line → ~625 tok
- Add explicit `tools:` line → +~10 tok

Definition text: ~2210 → ~1405 tok (chars/4 of the file; not a launch-cost measurement)
Model: unchanged (haiku fits mechanical shell/git execution)

---

## code-explorer  (agents/code-explorer.md)
Current: model opus · no `tools` field (inherits all) · body 35 lines · definition text ~390 tok
Version: (none) → 1.1.0 if changes below are applied

Findings
- [high] NO_TOOLS_FIELD: no `tools` field. Body is read-only ("You do not change any code — you only read and report") → propose a minimal read-only allowlist.
- [high] Scope mismatch in "Global engineering standards" (lines 23-32): the section lists coding/commit rules — 2-space JS/TS indentation, `const` over `let`, "run the linter before committing," conventional-commit prefixes, "write tests for every new function," JSDoc on public APIs — for an agent whose own body says it never edits or commits code. None of these can ever apply to what this agent does; they're pure dead weight, not a judgment call about redundancy. Recommend deleting the whole section.
- [med] WEAK_TRIGGER (scanner): description is "Explores codebases and reports findings." — no "use when/after," no proactive cue. Under-triggers against a more specific competitor agent. Propose something like: "Use when you need to understand how an existing feature or module works, trace call paths or data flow, or map dependencies before changes are made. Use proactively when starting work in an unfamiliar part of a codebase."

Tool policy: inherit-all → `Read, Grep, Glob`
  (Read-only explorer archetype. No `Bash` — body never mentions git or shell; no `WebFetch`/`WebSearch` — body scopes to "a codebase," not external research. Flag: if code-explorer is ever expected to follow up a `git log`/`git blame` for history context, `Bash` (read-only) would need to be added back — ask before assuming.)

Proposed trims:
- Delete "## Global engineering standards" block (lines 23-32) → ~107 tok

Definition text: ~390 → ~329 tok net (-107 from the deleted section, +~46 from the `tools:` line and a slightly longer, properly-triggering description — the increase is intentional: a description that actually triggers is worth more than the ~40 tokens it costs)
Model: candidate: sonnet — read-then-summarize is closer to the "mechanical" end than solution-architect's or plan-reviewer's judgment-heavy work, but read-only is explicitly not by itself a downgrade reason; verify on a real exploration task before adopting, don't treat this as a given saving.

---

## plan-driven-coder  (agents/plan-driven-coder.md)
Current: model sonnet · no `tools` field (inherits all) · body 114 lines · definition text ~2250 tok
Version: (none) → 1.1.0 if changes below are applied

Findings
- [high] NO_TOOLS_FIELD: no `tools` field. Body is a strict implementer ("translate well-defined implementation plans into working, high-quality code") → propose the implementer allowlist.
- [med] MEMORY_BOILERPLATE: lines 77-122 are the full generic memory-upkeep section (this file has no agent-specific intro at all before it, unlike bash-git-ops) — identical in shape to the other two `memory: user` agents here, and in the scanner's `duplicate_blocks`. Trim to one line.
- [low] LONG_DESCRIPTION: 3 examples (~582 tok). Example 1 (auth module) and example 2 (data pipeline) both just demonstrate "faithfully implement a concrete numbered plan" — redundant with each other. Example 3 (ambiguous plan → ask for clarification) demonstrates a genuinely different behavior. Keep 1 + 3, cut 2.

Tool policy: inherit-all → `Read, Edit, Write, Grep, Glob, Bash`
  ? `Bash`: the body never explicitly says it runs commands, tests, or a build/linter to verify its own output — only "Ensure code is syntactically correct and logically sound." Implementer work almost always needs to run/verify what it wrote, so I've kept it, but flagging: confirm this agent is expected to execute code, not just author it, before locking this in.
  (schema cost of the removed tools is not measured by the scanner)

Proposed trims:
- Cut description example 2 ("data pipeline") → ~162 tok
- Collapse the Persistent Agent Memory boilerplate (lines 77-122) to one line → ~625 tok
- Add explicit `tools:` line → +~11 tok

Definition text: ~2250 → ~1474 tok (chars/4 of the file; not a launch-cost measurement)
Model: unchanged (sonnet fits general implementation work; no evidence it needs opus-level judgment given the plan-fidelity mandate)

---

## plan-reviewer  (agents/plan-reviewer.md)
Current: model opus · tools: `Read, Grep, Glob, Agent(verifier), ExitPlanMode` · body 17 lines · definition text ~340 tok
Version: unchanged — no changes proposed

Findings: none. This is the tightest file in the set and a reasonable template for the others:
- Explicit minimal `tools:` list already present, and `Agent(verifier)` is confirmed used (step 2 dispatches a verifier subagent per finding) rather than merely plausible — not a "?" case.
- `permissionMode: plan` is set, so `ExitPlanMode` is legitimately listed (the scanner already accounts for this).
- `omitClaudeMd: true` is set and the body correctly carries its own "Repository rules" section as the only copy (`OMITS_CLAUDE_MD`) — right call, don't trim it as a duplicate.
- Description is short, has an explicit "Use proactively on any change that touches..." trigger, and isn't padded with examples.
- Model opus matches a security-review job; not a downgrade candidate.

Nits (informational, not findings that need action):
- Name/description mismatch: the file is named `plan-reviewer` but its actual job, per the description and body, is a security reviewer that happens to draft its remediation output in plan mode ("review a security-sensitive change... traces trust boundaries... drafts a remediation plan"). A user asking to "review this plan" (a design/spec document) could reasonably expect this agent and get a security audit instead, or vice versa. Consider `security-plan-reviewer` or `security-reviewer` if that's a real routing risk in this agent's actual scope.
- Open question, not a proposed change: body says "Read the diff" — worth confirming whether the diff is always supplied by the caller (fine as-is, `Read` covers it) or whether this agent is sometimes expected to produce its own diff via `git diff` (would need `Bash`, read-only-scoped). Not enough evidence in the body to decide either way.

Definition text: ~340 → ~340 tok (no change)
Model: unchanged

---

## solution-architect  (agents/solution-architect.md)
Current: model opus · 15 tools listed · body 170 lines · definition text ~3162 tok
Version: (none) → 1.1.0 if changes below are applied

Findings
- [med] MANY_TOOLS (scanner): 15 tools on a single-purpose planning agent (>10 trim point).
- [med] WRITE_ON_READONLY (scanner): body states "You never write implementation code yourself" (line 10) and "**Never write implementation code.**" (line 103), yet grants `NotebookEdit`. Drop — not needed for memory either (memory files are Markdown).
- [low] BACKGROUND_STRIPPED (scanner): `TaskCreate`, `TaskGet`, `TaskUpdate`, `TaskList` are stripped from background subagents, which is the default launch mode. They only matter if this agent is specifically launched in the foreground — the body never mentions task-list coordination either way. Ask before keeping.
- Granted-but-unused: `EnterWorktree` — nothing in the body mentions worktrees, isolated workspaces, or any reason a pure planning-and-reporting agent (that explicitly never writes code) would need one. Propose drop; flagging rather than silently cutting per the skill's conservative default.
- Granted-but-unused (weaker case, still worth asking): `WebFetch`/`WebSearch` — the body's "Codebase Discovery" phase is entirely internal ("map the directory structure," "read and understand existing patterns"); nothing about researching external docs, libraries, or prior art. `Skill` — never mentioned. `ToolSearch` — never mentioned, though it's zero-permission-cost so low priority either way.
- [med] MEMORY_BOILERPLATE: lines 134-179 are the full generic memory-upkeep section, byte-identical in shape to the same section in `bash-git-ops.md`/`plan-driven-coder.md` (scanner's `duplicate_blocks`). Trim to one line. Keep lines 122-133 ("Update your agent memory as you discover architectural patterns..." + the solution-architect-specific examples: data access patterns, auth mechanisms, module boundaries) — genuinely agent-specific.
- [low] LONG_DESCRIPTION: 3 examples (~691 tok), all illustrating the same trigger shape ("significant architectural change → invoke solution-architect before coding"). Keep example 1 (OAuth2 — the clearest multi-constraint case), cut 2 and 3.
- [med] LONG_BODY (scanner): 170 lines. Most of this is legitimate structure for an architect's output contract (phase template, self-check list) rather than padding; after the memory-boilerplate trim it drops to ~125 lines, which is reasonable for this archetype's actual job — no further structural cuts proposed.

Tool policy: `Glob, Grep, Read, Edit, Write, NotebookEdit, WebFetch, WebSearch, Skill, TaskCreate, TaskGet, TaskUpdate, TaskList, EnterWorktree, ToolSearch` → `Read, Grep, Glob, Edit, Write`
  ? `WebFetch`/`WebSearch`: keep for external research (e.g., evaluating third-party library options) or drop since the body never mentions it?
  ? `Skill`: keep in case the architect is expected to invoke research/planning skills, or drop since none are named in the body?
  ? `TaskCreate`/`TaskGet`/`TaskUpdate`/`TaskList`: keep only if this agent is launched in the foreground; dead weight under the default background launch.
  ? `EnterWorktree`: drop candidate — no body evidence of use, and isolating a worktree sits oddly with an agent that "never writes implementation code."
  ? `ToolSearch`: low-cost either way; keep or drop is a coin flip.
  (`NotebookEdit` is a confirmed drop, not a question — see WRITE_ON_READONLY above.)
  (schema cost of the removed tools is not measured by the scanner)

Proposed trims:
- Cut description examples 2 ("notification system pivot") and 3 ("legacy payment module") → ~371 tok
- Collapse the Persistent Agent Memory boilerplate (lines 134-179) to one line → ~625 tok
- Drop `NotebookEdit` from the tools line → ~3 tok

Definition text: ~3162 → ~2136 tok if all "?" tools above are resolved to "drop" (chars/4 of the file; not a launch-cost measurement); ~2163 tok if only the confirmed `NotebookEdit` drop and prose trims are applied and every "?" tool is kept
Model: unchanged (opus fits multi-constraint architectural judgment)

---

## Summary

5 agents audited · definition text ~8352 → ~5684 tok if every proposed trim and every "?" tool resolves to "drop" (roughly -32%, chars/4, not a launch-cost measurement) · 4 of 5 agents (`bash-git-ops`, `code-explorer`, `plan-driven-coder`, `solution-architect`) move from inherit-all to an explicit allowlist — the larger, unmeasured win is fewer tool schemas loaded and better tool-selection accuracy on every launch, not the token totals above. `plan-reviewer` needed no changes.

Cross-cutting pattern: the `memory: user` boilerplate section (harness-duplicated "Persistent Agent Memory" block) is byte-similar across `bash-git-ops`, `plan-driven-coder`, and `solution-architect` — the single highest-leverage repeated fix in this set (~625 tok x 3 = ~1875 tok). The agent-specific "what to remember" guidance above each boilerplate block is worth keeping in all three; only the generic harness-duplicated tail should go.

Standout finding: `code-explorer.md`'s "Global engineering standards" section is coding/commit-hygiene guidance grafted onto an agent that explicitly never edits or commits code — it cannot ever be acted on. Worth prioritizing regardless of the token count, since dead instructions matching real repo rules can mislead whoever reads this file later into thinking `code-explorer` is expected to write code.

This is a report only — no agent files were edited and no versions were bumped. Apply all / pick per-agent / adjust?
