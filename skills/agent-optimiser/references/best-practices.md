# Claude Code subagent best practices

Distilled from the official docs (https://code.claude.com/docs/en/sub-agents,
.../tools-reference, .../costs) and the API tool-search docs
(https://platform.claude.com/docs/en/agents-and-tools/tool-use/tool-search-tool),
checked 2026-09. Each rule is checkable against one agent file. Severity in
brackets. The scan script raises codes in CAPS; this file explains the *why* and
the fix. Claude Code's own `/doctor` reports unused skills, MCP servers and plugins
against their context cost; it does not look at agents, which is the gap this
skill fills.

## Why this matters (token economy)

- A subagent starts fresh: its system prompt + tool schemas + the full CLAUDE.md
  hierarchy + a git snapshot load **on every launch**. Bloat is paid per
  invocation and multiplied across parallel/chained agents.
- What the scanner measures is definition text only (frontmatter + body, chars/4).
  Tool schemas, inherited CLAUDE.md, skills and memory are outside it, so its totals
  rank agents and show a before/after of the file; they are not launch cost.
- Tool definitions are the dominant avoidable cost. Anthropic's tool-search docs
  put a typical multi-server MCP setup at **~55k tokens** of definitions and report
  **over 85%** saved by loading only the tools a task needs. Claude Code defers MCP
  definitions by default; built-in schemas are what an unrestricted agent still pays for.
- It's not only cost: the same docs note tool-selection **accuracy degrades as the
  tool list grows** (tens of tools). A tight allowlist makes the agent *more correct*,
  not just cheaper.
- The scanner's trim point (`MANY_TOOLS`) is more than 10 tools on one agent: a
  single-purpose agent rarely needs more, and every extra schema costs tokens and
  selection accuracy.
- An agent's *result* also costs the parent's context — instruct a concise summary,
  not a dump.

## Frontmatter

**tools**
- `[high] NO_TOOLS_FIELD` — omitting `tools` inherits ALL tools. Always propose an
  explicit minimal allowlist (see tool-catalog.md). This is the headline win.
- `[high] WRITE_ON_READONLY` — `Edit`/`Write`/`NotebookEdit` on an agent whose body
  declares it doesn't write code contradicts that mandate. Drop them unless the body
  truly writes (e.g. an architect that persists a plan file — then keep only `Write`).
  **Memory exception:** an agent with `memory:` set legitimately needs `Edit` **and**
  `Write` to maintain its `MEMORY.md` and topic files — the harness instructs it to
  "use the Write and Edit tools to update your memory files." Never strip `Edit`/`Write`
  from a memory-enabled agent; doing so silently breaks memory upkeep. `NotebookEdit`
  is still droppable (memory files are Markdown, not notebooks).
- `[med] DEAD_TOOL_ENTRY` — tools on the documented subagent blacklist
  (`AskUserQuestion`, `EndConversation`, `EnterPlanMode`, `ScheduleWakeup`, `TaskOutput`,
  `WaitForMcpServers`, `Workflow`, and `ExitPlanMode` unless the agent sets
  `permissionMode: plan`, which the scanner checks). Remove.
- `[med] LEGACY_TOOL_NAME` — a name from an older release (`Task`, `LS`, `MultiEdit`,
  `NotebookRead`, `BashOutput`, `KillShell`). Rename to the current tool after checking
  the installed version.
- `[low] NESTED_AGENT_TOOL` — lists `Agent`. Nested subagents are on by default, so this
  is legitimate for an agent that delegates; it is dead at the depth limit or with
  nesting off. Ask keep-or-drop; never strip silently (see tool-catalog.md).
- `[low] BACKGROUND_STRIPPED` — a tool the harness removes from background subagents
  (`TaskCreate`/`TaskGet`/`TaskUpdate`/`TaskList`, `ListAgents`, `LSP`, MCP resource
  tools). Only useful if the agent is launched in the foreground.
- `[med] MANY_TOOLS` — >10 entries on a single-purpose agent; trim to what the body
  uses, or use `disallowedTools` if intent is "all except writes".
- `[med]` Bash needed only for narrow ops (read-only git, SQL) → keep `Bash` but
  recommend scoping destructive commands via `Bash(...)` permission rules or a
  `PreToolUse` hook rather than widening.

**description** (loads session-wide for routing — keep it earning its tokens)
- `[med] WEAK_TRIGGER` — role-only ("Reviews code") under-triggers. Name concrete
  conditions: "use when…", "after…", "whenever…".
- For agents meant to fire automatically, include a proactive cue: "use proactively"
  / "use immediately after…".
- `[low] LONG_DESCRIPTION` — multi-screen escaped-`\n` example blocks inflate every
  session. Keep the triggers + 1–2 tight examples; cut the rest.

**model** (defaults to `inherit` when omitted)
- `[low] MODEL_INHERIT` — fine if intentional. But pin `haiku` for mechanical
  agents, and pin `sonnet`/`opus`/`fable` for agents whose competence requirement is
  fixed regardless of session model (don't let a planner silently run on Haiku).
- A mechanical agent on `opus` is a downgrade candidate; a read-only agent is not
  automatically one (security review, architecture analysis). Any model change is a
  candidate until compared on the agent's real task.
- Haiku lacks MCP tool-search (`tool_reference`); a Haiku agent relying on many
  deferred MCP tools won't get on-demand loading.

**name / hygiene**
- `[med] NAME_FORMAT` — must be lowercase-hyphenated, unique in its scope (a
  duplicate name in the same scope is silently discarded).
- Only `name` and `description` are required. Documented optional fields: `tools`,
  `disallowedTools`, `model`, `permissionMode`, `maxTurns`, `skills`, `mcpServers`,
  `hooks`, `memory`, `background`, `omitClaudeMd`, `effort`, `isolation`, `color`,
  `initialPrompt`, `experimental`. Anything else is a typo or a leftover.

## Body (system prompt)

- `[high]` **Single responsibility** — one agent, one job. "Writes AND reviews AND
  commits" should be split. Reward explicit negative scoping ("only X; does not Y").
- `[high]` **No CLAUDE.md duplication** — custom subagents inherit the CLAUDE.md
  hierarchy unless `omitClaudeMd: true` is set. Re-pasting rules that are provably
  inherited is dead weight; a rule you cannot find in a loaded CLAUDE.md is not a
  duplicate, and on an `omitClaudeMd` agent (`[info] OMITS_CLAUDE_MD`) the body may be
  the only place those rules exist. Locate the source before cutting.
- `[med] MEMORY_BOILERPLATE` — when `memory:` is set, the harness auto-injects memory
  read/write instructions + the top of `MEMORY.md`. A hand-written "Persistent Agent
  Memory" section (often ~45 lines, and identical across an author's agents) largely
  duplicates that. Trim to a one-line "update your memory as you learn".
- `[med] LONG_BODY` — official single-purpose examples run ~25–45 lines; >150 is
  likely bloated. Target shape: one-line role → numbered "when invoked" steps →
  focused checklist → explicit output format → short closing principle.
- `[low] NO_OUTPUT_FORMAT` — add an output-format / "return a concise summary"
  section so results don't flood the parent.
- `[low] EMPHASIS_DENSITY` — heavy ALL-CAPS MUST/NEVER reads as nagging and rarely
  helps. Explain the *why*; reserve emphasis for the one or two real footguns.
- `[low]` References to local-only working files the agent won't have at runtime → fix.

## Cross-cutting

- Scope: project agents (`.claude/agents/`) should be checked into VCS for the team;
  a user-global agent that hardcodes one project's paths is mis-scoped.
- `Task` is the old name of the `Agent` tool; rename when you touch the file.
- Precedence (high→low): managed → `--agents` CLI → project → user → plugin.

## Tensions / judgement calls

- Description length: detailed enough to trigger reliably vs. lean enough not to tax
  every session. Cap runaway multi-example blocks; don't strip a description down to
  a role line.
- The 55k/85% numbers are measured for MCP tool definitions through the API. Claude
  Code defers MCP tools by default and the docs do not say whether built-in schemas
  are deferred, so "omit `tools` → pays for every built-in schema" is directionally
  certain; treat the exact figure as MCP-derived and quote the scanner's own estimate.
- Conservative default: when unsure whether a tool is used, **flag it for the user**
  rather than removing it. Breaking an agent costs more than a slightly wide allowlist.
