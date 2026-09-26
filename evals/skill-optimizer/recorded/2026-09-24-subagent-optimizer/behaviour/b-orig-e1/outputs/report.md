# Subagent optimization report

Target: `agents/solution-architect.md` (single agent, resolved directly from the
path given). Scanned with `scripts/scan_agents.py`, analysed by hand against
`references/best-practices.md` and `references/tool-catalog.md`, changes applied
and version bumped with `scripts/bump_version.py`.

## solution-architect  (agents/solution-architect.md)
Current: model opus · 15 tools (explicit list, no `inherit-all`) · body 170 lines · definition text ~3162 tok
Version: (none) → 1.1.0

Findings
- [med] MANY_TOOLS: 15 tools listed for a single-purpose planning agent (rule of thumb: >10 needs trimming) → cut to what the body actually exercises.
- [med] WRITE_ON_READONLY: body states "You never write implementation code yourself" yet grants `NotebookEdit` → drop (memory files are Markdown, not notebooks, so the `memory:` exception doesn't cover it).
- [low] BACKGROUND_STRIPPED: `TaskCreate`/`TaskGet`/`TaskUpdate`/`TaskList` are stripped from background subagents (the default launch mode) and the body never manages a task list anyway → drop.
- [low] unused tool: `EnterWorktree` is never referenced by the body (no worktree workflow described) → drop.
- [med] LONG_BODY: 170 lines vs. the ~25-45 line norm for a single-purpose agent.
- [med] MEMORY_BOILERPLATE: `memory: user` is set, so the harness already injects memory read/write mechanics + the top of `MEMORY.md`. The body additionally hand-wrote a ~58-line "Persistent Agent Memory" section (generic guidelines, what-to-save/what-not-to-save, a "searching past context" grep recipe, and an empty `## MEMORY.md` placeholder) that duplicates that injected behavior almost line for line -> collapsed to one sentence.
- [low] LONG_DESCRIPTION: description was 2764 chars (~691 tok) - 3 full worked examples with repeated "I'll now use the Task tool to launch..." confirmation lines. It loads session-wide for routing, so this is paid every session, not just when the agent fires. Also: two of those confirmation lines named the tool by its old name, `Task` (now `Agent`) - a second, independent reason to touch that prose.

Tool policy: 15 tools (`Glob, Grep, Read, Edit, Write, NotebookEdit, WebFetch, WebSearch, Skill, TaskCreate, TaskGet, TaskUpdate, TaskList, EnterWorktree, ToolSearch`) -> `Read, Grep, Glob, Edit, Write, WebFetch, WebSearch, Skill, ToolSearch` (9 tools)
  - Dropped outright (unused / dead weight): `NotebookEdit` (contradicts the "never write code" mandate, not needed for Markdown memory files), `TaskCreate`, `TaskGet`, `TaskUpdate`, `TaskList` (background-stripped by default and never invoked in the body), `EnterWorktree` (never referenced).
  - Kept for memory upkeep (required by the `memory: user` exception, even though the body never edits *code*): `Edit`, `Write`.
  - `Read`, `Grep`, `Glob` - clearly required: the body's entire "Phase A - Codebase Discovery" step is built on reading and searching the codebase.
  - `ToolSearch` - kept; harmless read-only lookup tool, no reason to drop.
  - ? `WebFetch`, `WebSearch` - kept, flagged as a question. Nothing in the current body instructs external research (no mention of fetching docs, library references, or prior art); the archetype table lists these as add-ons "for research." If this architect never actually looks anything up externally in practice, they're droppable - but planning agents plausibly benefit from checking library docs/best practices when picking between architectural approaches (Phase C), so I kept rather than silently removed. Confirm with real usage.
  - ? `Skill` - kept, flagged as a question. Not referenced anywhere in the body (no instruction to invoke a skill). Worth keeping if you want this architect able to pull in domain-specific skills (e.g. a framework or stack-specific skill) during analysis; drop if it never does.
  - (schema cost of the removed tools is not measured by the scanner - the win here is proportionally larger than the definition-text delta below, since 6 of 15 tool schemas no longer load on every launch)

Proposed trims (all applied):
- Memory section (was lines 122-179, ~58 lines: hand-written "Persistent Agent Memory" guidelines, save/don't-save lists, a "searching past context" grep recipe, and an empty `## MEMORY.md` placeholder) -> 1 line pointing at the memory directory and what's worth recording. ~2059 definition-text chars cut.
- Description (3 worked examples with repeated confirmation lines, one example ~500 chars each) -> 1 tight example, trigger sentence kept. ~2264 chars cut, and it drops the two stale `Task`-tool-name references in the process.
- Left intact, flagged rather than cut: "Behavioral Guidelines" (7 bullets) and "Quality Self-Check" (7 checklist items) - these partially echo the earlier Analysis Protocol/Execution Plan sections (e.g. "Flag all assumptions" vs. Phase B's "Identify assumptions... flag any that need confirmation"), but each serves a distinct rhetorical role (imperative guardrails vs. process steps vs. a pre-delivery checklist) and none is a literal duplicate of harness-injected content. Cutting further risks losing real instructions on ambiguous grounds, so this is a flag, not a change - "Never write implementation code" in particular is the one load-bearing guardrail that distinguishes this agent from an implementer and should not be touched.

Definition text: ~3162 -> ~1960 tok (chars/4 of the file; not a launch-cost measurement - tool schemas, inherited CLAUDE.md, and memory are outside what the scanner sees)
Model: unchanged - `opus`. This is a planning/architecture agent producing exhaustively detailed multi-phase plans other engineers build from; read-only is not a downgrade signal on its own, and nothing in the task suggests this needs verifying against a cheaper model. Not a candidate.

## Summary
1 agent audited · definition text ~3162 -> ~1960 tok (~38% smaller by this measure) · tool allowlist 15 -> 9 (real launch-time savings - 6 fewer tool schemas loaded every invocation - are not captured by the definition-text number above)
Rescan after applying: 0 flags remain (`MANY_TOOLS`, `WRITE_ON_READONLY`, `BACKGROUND_STRIPPED`, `LONG_BODY`, `MEMORY_BOILERPLATE`, `LONG_DESCRIPTION` all cleared).
Version bumped: (none) -> 1.1.0 via `scripts/bump_version.py`.

Applied in full (the request pre-authorized applying the changes, so this ran through report + apply in one pass rather than stopping for a separate approval step).

Open questions to confirm, not blocking:
1. Does this architect ever do external research (docs, prior art) when evaluating architectural options? If never in practice, drop `WebFetch`/`WebSearch`.
2. Does this architect ever invoke another skill mid-analysis? If never, drop `Skill`.
