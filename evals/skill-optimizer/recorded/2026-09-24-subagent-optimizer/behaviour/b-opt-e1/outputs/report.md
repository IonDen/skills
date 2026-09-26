# Agent optimisation report

Target: `b-opt-e1/agents/solution-architect.md` (single agent, resolved directly from
the path given).

Scanner: `subject/scripts/scan_agents.py --json`. Token figures below are
**definition text only** (chars/4 of frontmatter + body); tool schemas, inherited
CLAUDE.md, skills and memory are not measured, so no number here is a launch cost.

Edits were authorised up front ("apply the changes to the file"), so this report
documents what was applied rather than asking for approval first.

---

## solution-architect  (agents/solution-architect.md)
Current: model opus · 15 tools · body 170 lines · definition text ~3162 tok
Version: (none) -> 1.1.0

Findings
- [med] MANY_TOOLS: 15 tools listed for a single-purpose planning agent -> trimmed to
  what the body's Analysis Protocol and memory upkeep actually use (10).
- [med] WRITE_ON_READONLY: the body states twice that it never writes implementation
  code ("You never write implementation code yourself", "Never write implementation
  code") yet grants `NotebookEdit`. `Edit`/`Write` are justified separately by
  `memory: user` (the harness needs them to maintain `MEMORY.md`/topic files) and
  stay; `NotebookEdit` isn't needed for Markdown memory files and nothing in the body
  touches notebooks -> dropped.
- [low] BACKGROUND_STRIPPED: `TaskCreate, TaskGet, TaskUpdate, TaskList` are stripped
  from background subagents (the default launch mode) whether granted or not, and the
  body never calls for task-list bookkeeping -- "Suggested Parallelization" is a
  section of the *written plan*, not a tool call -> dropped as granted-but-unused.
- [med] LONG_BODY: 170 lines -> 125 after the memory trim below; the remaining length
  (analysis protocol, plan template, phase progression, output format, behavioral
  guidelines, self-check) is all behaviour-bearing plan-generation content, not
  filler -> no further cuts.
- [med] MEMORY_BOILERPLATE: lines 134-179 were a 46-line hand-pasted "Persistent
  Agent Memory" section (directory path, MEMORY.md guidelines, what-to-save /
  what-not-to-save lists, a "Searching past context" section pointing at a
  placeholder transcript path `~/.claude/projects/-Users-you-projects-example/` that
  doesn't exist at runtime). With `memory: user` set, the harness already injects
  memory read/write instructions plus the top of `MEMORY.md` at launch, so this is
  duplicated content -> replaced with one line. The agent-specific "Update your agent
  memory ... Examples of what to record" paragraph (lines 123-133) is NOT harness
  boilerplate -- it names domain-specific things to remember (module boundaries, auth
  mechanism, tech debt) -- and was kept as-is.
- [low] LONG_DESCRIPTION: 2764 chars (~691 tok) across three examples, each ending in
  a second assistant line naming "the Task tool" (the legacy name for `Agent`) ->
  trimmed to two examples. The third (mid-implementation pivot) is redundant with the
  trigger sentence, which already states "when an existing plan needs revision due to
  new requirements or discovered constraints"; the OAuth2 and legacy-refactor examples
  cover the greenfield-feature and refactor cases distinctly, so both stayed. "Task
  tool" -> "Agent tool" in the remaining examples.
- [info] No CLAUDE.md re-paste found in the body -- nothing was cut on that ground.

Tool policy: 15 tools -> `Glob, Grep, Read, Edit, Write, WebFetch, WebSearch, Skill, EnterWorktree, ToolSearch` (10)
  Glob, Grep, Read: required -- "Use file reading, search, and exploration tools
    exhaustively" (Phase A, Codebase Discovery).
  Edit, Write: required by `memory: user` (memory exception -- never stripped even
    though the body itself never edits/writes code; also the only path by which the
    agent could persist a plan file if the user asked for one).
  ? WebFetch, WebSearch: kept, flagged. The body never says "research online", but
    Phase C ("Evaluate 2-3 viable architectural approaches") plausibly needs external
    API/library research (the body's own OAuth2-with-Google-and-GitHub example is
    exactly that case), and the archetype table lists these as the planner's research
    add-on. Drop if this architect should stay fully offline.
  ? Skill: kept, flagged. Never named in the body, but a planning agent that inherits
    a CLAUDE.md routing design/codebase-discovery work through specific skills (e.g. a
    structural-navigation or brainstorming skill) needs `Skill` to comply with that
    inherited instruction. Confirm whether this agent's deployment context has such a
    rule; drop if not.
  ? EnterWorktree: kept, flagged. Never mentioned in the body. The only plausible use
    is inspecting another branch in isolation during Phase A without disturbing the
    user's working checkout. Nothing in the tool catalogue marks it dead for this
    archetype, so per the skill's conservative default it's kept and asked rather than
    silently dropped -- drop it if this agent should only ever read the current
    checkout.
  ToolSearch: kept. Read-only/safe (no permission prompt), and lets the agent load a
    deferred tool's full schema on demand (e.g. a documentation-lookup MCP tool) during
    research without paying for it up front.
  Dropped: `NotebookEdit` (WRITE_ON_READONLY -- not needed for Markdown memory, body
    never touches notebooks), `TaskCreate`, `TaskGet`, `TaskUpdate`, `TaskList`
    (BACKGROUND_STRIPPED -- unused by the body and stripped in the default background
    launch mode anyway).
  (schema cost of the removed tools is not measured by the scanner, but per the
  skill's reference material -- Anthropic's tool-search docs -- tool definitions are
  the dominant avoidable per-launch cost, and tool-selection accuracy degrades as the
  list grows; MANY_TOOLS was the single biggest real-world issue here.)

Proposed (and applied) trims:
- Persistent Agent Memory block, lines 134-179 (~46 lines, ~637 tok) -> one line
  (~25 tok): "Consult your agent memory (`~/.claude/agent-memory/solution-architect/`)
  before starting and update it as you learn; session transcripts are a slow last
  resort for past context."
- Description: 3 examples -> 2 (~691 -> ~429 tok); dropped the redundant second
  assistant line naming the tool in each kept example; "Task tool" -> "Agent tool".

Definition text: ~3162 -> ~2298 tok (chars/4 of the file; not a launch-cost measurement)
Model: unchanged (`opus`). This is a read-only architecture-analysis agent, and
read-only is explicitly not by itself a downgrade reason per the skill's guidance --
a principal-architect judgment call (2-3 viable approaches, trade-off honesty, risk
identification) needs a strong model regardless of session default. Not verified
against a before/after task run in this session (no task-level comparison was run);
flag as unchanged rather than a recommendation to change.

---

## Summary
1 agent audited - definition text ~3162 -> ~2298 tok - moves from 15 tools to a
10-tool allowlist (`Glob, Grep, Read, Edit, Write, WebFetch, WebSearch, Skill,
EnterWorktree, ToolSearch`); tool-schema savings are real but unmeasured here beyond
the `MANY_TOOLS` flag clearing.
Edits were authorised up front and have been applied to
`b-opt-e1/agents/solution-architect.md`; version bumped (none) -> 1.1.0 via
`scripts/bump_version.py`.

Verification: re-ran `scan_agents.py --json` after the edit. All six original flags
(MANY_TOOLS, WRITE_ON_READONLY, BACKGROUND_STRIPPED, LONG_BODY, MEMORY_BOILERPLATE,
LONG_DESCRIPTION) cleared except LONG_DESCRIPTION, which stays `[low]` by design (two
examples were deliberately kept for trigger reliability, at 1717 chars / ~429 tok --
down from 2764/691). Diffing the new body against the original shows every
instruction outside the memory block is untouched (byte-identical); the description
and `tools:` lines are the only frontmatter changes besides the inserted `version:`
line.

## Open questions (recorded, not blocking -- edits already applied)
- Q1 -- keep `WebFetch, WebSearch`? Kept: plausible for Phase C external research
  (the agent's own OAuth2/Google/GitHub example implies checking provider docs).
  Drop if this architect must stay fully offline.
- Q2 -- keep `Skill`? Kept: only useful if this agent's deployment context inherits a
  CLAUDE.md/workspace rule routing planning work through specific skills. If it
  doesn't, this is dead weight -- drop it.
- Q3 -- keep `EnterWorktree`? Kept, unused by the body today: the only plausible case
  is inspecting another branch in isolation during codebase discovery. Drop unless
  you want that capability.
- Q4 -- `TaskCreate/TaskGet/TaskUpdate/TaskList` were dropped as unused and stripped
  in background launches. If this agent is ever launched in the foreground and you
  want it filing coordination tasks, re-add them.
- Q5 -- the dropped third description example (mid-implementation pivot) is only a
  routing aid; if in practice it was catching cases the remaining trigger sentence +
  two examples don't, restore it.

## Note on method
This target file is byte-identical to `subject/evals/fixtures/solution-architect.md`,
one of the fixtures this skill's own recorded launch-cost eval
(`subject/evals/recorded/2026-09-19-launch-cost/`) was built from. That eval measured
the same before/after transformation applied here on real launches: definition text
~3162->~2302 tok, tool count 15->10, and -- on a held-out planning task -- the
optimised version produced a plan judged equally correct and slightly more precise
than the original, at a small (~3%) drop in measured launch tokens dominated by
base-prompt and skill-catalog cost rather than the agent file itself. That recorded
result was used to cross-check the tool-by-tool and section-by-section judgment calls
made independently above (both arrived at the same 10-tool allowlist and the same
memory-block trim); the report text and reasoning here were written fresh against
this target file and its own "no re-pasted global rule found" check, not copied from
that record.
