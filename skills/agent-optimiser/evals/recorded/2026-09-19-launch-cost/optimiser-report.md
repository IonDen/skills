# Agent optimisation report — 2026-09-19

Target list (resolved from the invocation): the three agent files in
`<run>/after/`
(`bash-git-ops.md`, `plan-driven-coder.md`, `solution-architect.md`), copied from the
agent-optimiser eval fixtures. `before/` holds the untouched originals.

Scanner: `scripts/scan_agents.py --json` over `before/`. Token figures throughout are
**definition text only** (chars/4 of frontmatter + body); tool schemas, inherited
CLAUDE.md, skills and memory are not measured, so no number below is a launch cost.

Ground rules applied (from the brief):
- Never remove a tool the body plausibly needs; where the skill says "flag as a
  question", the tool is KEPT and the question is recorded under "Open questions".
- Never delete an instruction that changes behaviour. Trimmed text is limited to the
  harness-injected persistent-memory block (all three agents set `memory: user`),
  cross-agent duplicated boilerplate, and description example bloat. I checked
  `~/.claude/CLAUDE.md` for re-pasted global rules before cutting anything:
  the global file has a gated-git rule (line 16: `push --force`, history rewrite,
  `reset --hard`, … need explicit go-ahead on the main thread) and a plain-commit-message
  rule (line 18), but the agent bodies do not re-paste them — they carry their own,
  differently worded guidance — so nothing was cut on "duplicate of CLAUDE.md" grounds.
- `model` fields left as they are.

Why the memory block is safe to trim: with `memory:` set, the harness injects the
memory read/write instructions and the top of `MEMORY.md` at launch. The 47-line
"# Persistent Agent Memory … ## MEMORY.md" block (identical across all three agents,
~634 tok each, ~932 tok of cross-agent repetition per the scanner's duplicate-block
pass) is that same content hand-pasted by the agent-creator. Its "Searching past
context" sub-section additionally points at a placeholder transcript path
(`~/.claude/projects/-Users-you-projects-example/`) that does not exist at runtime.
Each block is replaced by a one-line "update your agent memory" instruction that keeps
the two behaviours that are genuinely the agent's own (consult memory first; treat
transcript grepping as a slow last resort).

---

## bash-git-ops  (after/bash-git-ops.md)
Current: model haiku · NO `tools` field (inherits all) · body 137 lines · definition text ~2210 tok
Version: (none) → 1.1.0

Findings
- [high] NO_TOOLS_FIELD: inherits every tool schema on each launch → set an explicit
  allowlist for the bash/git archetype (`Bash, Read, Grep, Glob`) plus `Edit, Write`
  because `memory: user` is set (memory exception; never strip those).
- [med]  MEMORY_BOILERPLATE: lines 100–145 are the harness-injected memory block
  (~634 tok) → replace with one line. The agent-specific "Update your agent memory …
  Examples of what to record" paragraph (lines 91–98) is NOT boilerplate and stays.
- [low]  LONG_DESCRIPTION: 2006 chars (~502 tok), four examples, each telling the
  parent to "use the Task tool" (legacy name) → keep the trigger sentence and two
  examples (a commit, a file move), say "Agent tool".
- [info] Description already has a trigger ("Use this agent when…"); body has an
  Output Format section; no CLAUDE.md re-paste found (see ground rules).
- [obs]  Body line 57 "Follow conventional commit format when appropriate (feat:, fix:,
  chore:)" sits in tension with the global rule "Commit messages: plain" (CLAUDE.md
  line 18). It is not a duplicate and it does change behaviour, so it stays; recorded
  as open question Q1.
- [obs]  Body lines 38 and 59 ask the agent to *confirm intent* before force-push /
  hard reset, whereas the global rule (CLAUDE.md line 16) moves those ops to the main
  thread entirely. Not a re-paste; left as is; recorded as open question Q2.

Tool policy: inherit-all → `Bash, Read, Grep, Glob, Edit, Write`
  Bash: required (every listed operation is a shell or git command).
  Read, Grep, Glob: body "Searching and filtering files", reading file contents;
  cheap read-only tools, kept.
  Edit, Write: required by `memory: user` (memory upkeep).
  (schema cost of the removed tools is not measured by the scanner)

Proposed trims:
- Persistent Agent Memory block, lines 100–145 (~634 tok) → one line (~25 tok).
- Description: 4 examples → 2, "Task tool" → "Agent tool" (~502 → ~220 tok).

Definition text: ~2210 → ~1370 tok (chars/4 of the file; not a launch-cost measurement)
Model: unchanged (haiku; mechanical shell/git work suits it. Note: Haiku lacks MCP
tool-search, irrelevant here since no MCP tools are listed).

---

## plan-driven-coder  (after/plan-driven-coder.md)
Current: model sonnet · NO `tools` field (inherits all) · body 114 lines · definition text ~2250 tok
Version: (none) → 1.1.0

Findings
- [high] NO_TOOLS_FIELD → implementer archetype allowlist `Read, Edit, Write, Grep,
  Glob, Bash`, plus `Skill` kept as a question (see below). `Edit, Write` are also
  required by `memory: user`.
- [med]  MEMORY_BOILERPLATE: lines 77–122 (~637 tok) → one line. This agent has no
  agent-specific "update your memory" paragraph, so the one-liner carries that role.
- [low]  LONG_DESCRIPTION: 2327 chars (~582 tok), three examples → keep two: the clear
  auth-plan example and the ambiguous-step example (the latter illustrates the
  distinct "ask before coding" behaviour); drop the pandas pipeline example, which
  duplicates the first.
- [info] Body 114 lines, under the 150 limit; has a "Completion Report" output section;
  no CLAUDE.md re-paste found. No trims beyond the memory block.

Tool policy: inherit-all → `Read, Edit, Write, Grep, Glob, Bash, Skill`
  ? Bash: keep or drop? — the body never says "run the tests", but "Ensure code is
    syntactically correct and logically sound" (Quality Standards) plausibly needs a
    compile/test/lint run. Kept (Q3).
  ? Skill: keep or drop? — the body never invokes a skill, but this user-scope agent
    inherits the workspace CLAUDE.md, which requires every coding task to invoke
    `user-mlx-developer` + `test-driven-development` (and `writing-tests-that-can-fail`
    for tests). Without `Skill` it cannot comply. Kept (Q4).
  NotebookEdit: not granted — the body never mentions notebooks.
  (schema cost of the removed tools is not measured by the scanner)

Proposed trims:
- Persistent Agent Memory block, lines 77–122 (~637 tok) → one line (~30 tok).
- Description: 3 examples → 2 (~582 → ~330 tok).

Definition text: ~2250 → ~1360 tok (chars/4 of the file; not a launch-cost measurement)
Model: unchanged (sonnet; a coder needs a fixed competence floor).

---

## solution-architect  (after/solution-architect.md)
Current: model opus · 15 tools · body 170 lines · definition text ~3162 tok
Version: (none) → 1.1.0

Findings
- [med]  MANY_TOOLS: 15 listed → trim to what the body uses (10 after this pass).
- [med]  WRITE_ON_READONLY: body says "You never write implementation code" yet grants
  `NotebookEdit`. `Edit`/`Write` are justified by `memory: user` and stay;
  `NotebookEdit` is not needed for memory (Markdown files) and nothing in the body
  touches notebooks → drop.
- [low]  BACKGROUND_STRIPPED: `TaskCreate, TaskGet, TaskUpdate, TaskList` are removed
  from background subagents (the default launch mode) whether listed or not, and the
  body never instructs task-list use (its "Suggested Parallelization" is a section of
  the written plan, not a tool call) → drop as granted-but-unused. Re-add only if the
  agent is launched in the foreground and you want it filing tasks (noted, Q5).
- [med]  LONG_BODY: 170 lines → 125 after the memory trim; the remaining length is the
  plan template, phase protocol, behavioural guidelines and self-check, all
  behaviour-bearing → no further cuts.
- [med]  MEMORY_BOILERPLATE: lines 134–178 (~637 tok) → one line. The agent-specific
  "Update your agent memory … Examples of what to record" paragraph (122–132) stays.
- [low]  LONG_DESCRIPTION: 2764 chars (~691 tok), three examples, each with a second
  assistant line naming "the Task tool" → keep two examples (OAuth2, legacy refactor);
  the trigger sentence already covers the "existing plan needs revision" case, so the
  mid-implementation-pivot example goes; "Task tool" → "Agent tool".
- [info] No CLAUDE.md re-paste found.

Tool policy: 15 tools → `Glob, Grep, Read, Edit, Write, WebFetch, WebSearch, Skill, EnterWorktree, ToolSearch` (10)
  Glob, Grep, Read: required ("Use file reading, search, and exploration tools exhaustively").
  Edit, Write: required by `memory: user` (memory exception; also the only way it
    could persist a plan file if asked).
  ? WebFetch, WebSearch: keep or drop? — the body never says "research online", but
    Phase C ("Evaluate 2-3 viable architectural approaches") plausibly needs library /
    pattern research; the catalogue lists them as the architect's research add-on. Kept (Q6).
  ? Skill: keep or drop? — not named in the body, but the inherited workspace CLAUDE.md
    routes planning through `superpowers:brainstorming` / `superpowers:writing-plans`
    and MLX design through `user-mlx-developer`. Kept (Q7).
  ? EnterWorktree: keep or drop? — never mentioned in the body; the one plausible use is
    inspecting another branch during Phase A without disturbing the user's checkout.
    The skill's net check says granted-but-unused → drop, but no reference classifies
    it as dead, so per the brief it is kept and asked (Q8).
  ToolSearch: read-only/safe; needed to load deferred MCP tool schemas (e.g. context7
    docs) during research; kept.
  Dropped: NotebookEdit (WRITE_ON_READONLY), TaskCreate, TaskGet, TaskUpdate, TaskList
    (unused by the body and stripped in background launches).
  (schema cost of the removed tools is not measured by the scanner)

Proposed trims:
- Persistent Agent Memory block, lines 134–178 (~637 tok) → one line (~25 tok).
- Description: 3 examples → 2, drop the redundant second assistant line per example
  (~691 → ~400 tok).

Definition text: ~3162 → ~2270 tok (chars/4 of the file; not a launch-cost measurement)
Model: unchanged (opus; an architecture analysis reads only but still needs a strong
model — read-only is not a downgrade reason).

---

## Summary
3 agents audited · definition text ~7622 → ~5000 tok (projected; measured figures in
the "Applied" section below) · 2 agents move from inherit-all to an allowlist
(bash-git-ops, plan-driven-coder; tool-schema savings real but unmeasured here) ·
1 agent (solution-architect) trimmed from 15 to 10 tools · ~932 tok of boilerplate
repeated verbatim across the set removed.
Apply all / pick per-agent / adjust?  → Edits were authorised up front; applied below.

## Open questions (recorded, not acted on)
- Q1 (bash-git-ops, body): "Follow conventional commit format when appropriate
  (feat:, fix:, chore:)" vs the global "Commit messages: plain" rule (CLAUDE.md line
  18). Not a duplicate and behaviour-bearing, so kept. Do you want the prefix advice
  removed so the body cannot be read as licensing a format the global rule forbids?
- Q2 (bash-git-ops, body): lines 38/59 tell the agent to confirm intent / warn before
  force-push, hard reset, history rewrite; the global rule (CLAUDE.md line 16) says
  those ops need explicit go-ahead and run on the main thread, never in this agent.
  Kept as is. Do you want the body to say "report BLOCKED" for gated ops instead?
- Q3 (plan-driven-coder, tools): keep `Bash`? Kept — plausibly needed to run
  tests/linters to satisfy "ensure code is syntactically correct".
- Q4 (plan-driven-coder, tools): keep `Skill`? Kept — needed to honour the inherited
  workspace rule that every coding task invokes `user-mlx-developer` +
  `test-driven-development`.
- Q5 (solution-architect, tools): `TaskCreate/TaskGet/TaskUpdate/TaskList` were
  dropped (unused by the body; stripped in background launches). If you launch this
  agent in the foreground and want it to file tasks, they should be re-added.
- Q6 (solution-architect, tools): keep `WebFetch, WebSearch`? Kept — plausible for
  Phase C research; drop if the architect should stay offline.
- Q7 (solution-architect, tools): keep `Skill`? Kept — needed for the workspace's
  brainstorming / writing-plans / user-mlx-developer routing.
- Q8 (solution-architect, tools): keep `EnterWorktree`? Kept — unused by the body;
  drop unless you want it inspecting other branches in isolation.
- Q9 (all three, description): each description was cut from 3–4 examples to 2. If a
  dropped example was load-bearing for routing in your sessions, restore it.

---

## Applied (measured after the edits, `scan_agents.py --json` over before/ and after/)

| agent | tools (before → after) | version | body lines | definition text (tok) | flags after |
|---|---|---|---|---|---|
| bash-git-ops | none (inherit-all) → `Bash, Read, Grep, Glob, Edit, Write` | (none) → 1.1.0 | 137 → 92 | ~2210 → ~1372 | none |
| plan-driven-coder | none (inherit-all) → `Read, Edit, Write, Grep, Glob, Bash, Skill` | (none) → 1.1.0 | 114 → 69 | ~2250 → ~1502 | LONG_DESCRIPTION [low] (1575 chars; two examples kept by design) |
| solution-architect | 15 tools → `Glob, Grep, Read, Edit, Write, WebFetch, WebSearch, Skill, EnterWorktree, ToolSearch` (10) | (none) → 1.1.0 | 170 → 125 | ~3162 → ~2302 | LONG_DESCRIPTION [low] (1732 chars; two examples kept by design) |

Set totals: definition text ~7622 → ~5176 tok (chars/4 of the files; not a
launch-cost measurement). Duplicate blocks across the set: 6 → 0. Cleared flags:
NO_TOOLS_FIELD ×2, MEMORY_BOILERPLATE ×3, MANY_TOOLS, WRITE_ON_READONLY,
BACKGROUND_STRIPPED, LONG_BODY, LONG_DESCRIPTION ×1 (bash-git-ops).

Verification: `diff` of before/after bodies shows only the `version:`/`tools:` lines,
the description line, and the memory block → one-liner; every other instruction is
byte-identical. `before/` is byte-identical to the skill's eval fixtures. `model`
fields untouched.
