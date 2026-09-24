# Subagent audit — b-opt-e3/agents

Scope: `agents/bash-git-ops.md`, `agents/code-explorer.md`, `agents/plan-driven-coder.md`,
`agents/plan-reviewer.md`, `agents/solution-architect.md` (5 files; scanner run via
`scripts/scan_agents.py agents --json` from the `subagent-optimizer` skill directory).

Report only — nothing has been edited or version-bumped. All numbers below are the
scanner's definition-text proxy (frontmatter + body, chars/4); it does not see tool
schemas, so it is not a measurement of launch cost, and an allowlist line can make
the raw total slightly *larger* even as the real (unmeasured) tool-schema cost drops.

---

## bash-git-ops  (agents/bash-git-ops.md)
Current: model haiku · no `tools` field (inherits all) · body 137 lines · definition text ~2210 tok
Version: (none) → 1.1.0 if applied

Findings
- [high] NO_TOOLS_FIELD: no `tools` field, so this agent inherits every built-in tool on every launch → add an explicit allowlist.
- [low] LONG_DESCRIPTION: description is ~2006 chars (~502 tok) across 4 worked examples, all illustrating the same two moves (bash file-ops, git commit/branch) → keep 1 example, cut the other 3.
- [med] MEMORY_BOILERPLATE: lines 91–145 (~3054 chars, ~763 tok) are a hand-written "Persistent Agent Memory" section. `memory: user` is set, so the harness already injects the read/write instructions plus the top of `MEMORY.md` — this duplicates that. Trim to one line, e.g. "Consult your agent memory before starting and update it as you learn; session transcripts are a slow last resort." Keep any part that isn't harness-provided (the "search past context" Grep pattern is a nice-to-keep, but is also generic enough to cut without losing behavior).
- [info] This exact agent/section shape matches the worked example in the skill's own `README.md` ("bash-git-ops … 145 lines became 102"), so the trim pattern below has a documented precedent — cited for context only, not as a measured result for *this* file.

Tool policy: inherit-all → `Bash, Read, Grep, Glob, Edit, Write`
  Archetype "Bash / git ops" floor is `Bash, Read, Grep, Glob`; `Edit`+`Write` are kept under the memory exception (`memory: user`), not because the body edits project files — it never does. `NotebookEdit` is correctly omitted (memory files are Markdown).
  (schema cost of dropping inherit-all is not measured by the scanner)

Proposed trims:
- Description: 4 examples → 1 (~502 tok → ~225 tok, ~-277 tok)
- "# Persistent Agent Memory" section, lines 91–145 → 1–2 lines (~763 tok → ~50 tok, ~-713 tok)
- Add `tools:` line (~+11 tok)

Definition text: ~2210 → ~1231 tok (chars/4 of the file; not a launch-cost measurement)
Model: unchanged — haiku suits mechanical bash/git execution, matches the archetype guidance.

---

## code-explorer  (agents/code-explorer.md)
Current: model opus · no `tools` field (inherits all) · body 35 lines · definition text ~390 tok
Version: (none) → 1.1.0 if applied

Findings
- [high] NO_TOOLS_FIELD: no `tools` field. Body is explicitly read-only ("You do not change any code — you only read and report") → add a minimal read-only allowlist.
- [med] WEAK_TRIGGER: description is a single role line ("Explores codebases and reports findings.") with no "use when…", no proactive cue, and no example — this will under-trigger against other explorer/researcher-shaped agents in the same session. Needs concrete conditions, e.g. "Use when you need a read-only map of a feature or an explanation of how existing code works, before editing it or handing it to an implementer. Use proactively when another agent needs codebase context first."
- [med] SCOPE_MISMATCH (not a scanner code — judgement finding): lines 23–32, "Global engineering standards" (~430 chars, ~108 tok), instruct the agent to run linters, write tests, use conventional commit prefixes, follow JS/TS style, and avoid `Co-Authored-By` lines — i.e. rules for an agent that edits and commits code. This agent has no `Edit`/`Write`/`Bash` in the proposed allowlist and its own mandate says it "does not change any code," so none of these rules can ever apply; they contradict the agent's declared scope rather than support it. I could not find a source CLAUDE.md near this file to confirm it as a copy (no `CLAUDE.md` exists anywhere under this eval sandbox), so I'm flagging it as dead/contradictory content rather than as duplication. → propose deleting the whole section.

Tool policy: inherit-all → `Read, Grep, Glob`
  Matches the "Read-only explorer / researcher" archetype floor exactly; the body never mentions git, external URLs, or search-the-web, so `Bash`/`WebFetch`/`WebSearch` are not proposed.

Proposed trims:
- Delete "## Global engineering standards" section, lines 23–32 (~108 tok)
- Add `tools:` line (~+6 tok)
- Description grows slightly to add real triggers (quality fix, not a cost cut) — call it ~+20 tok

Definition text: ~390 → ~310 tok (chars/4 of the file; not a launch-cost measurement)
Model: candidate: sonnet, verify on the agent's task before adopting. The job (find files, read, trace call paths, report) is not inherently opus-tier reasoning, but this is a guess until compared on a real trace-heavy task — not a saving.

---

## plan-driven-coder  (agents/plan-driven-coder.md)
Current: model sonnet · no `tools` field (inherits all) · body 114 lines · definition text ~2250 tok
Version: (none) → 1.1.0 if applied

Findings
- [high] NO_TOOLS_FIELD: no `tools` field → add an explicit allowlist matching the implementer archetype.
- [low] LONG_DESCRIPTION: ~2327 chars (~582 tok), 3 worked examples that all illustrate the same "implements exactly, asks when ambiguous" behavior → keep 1, cut the other 2.
- [med] MEMORY_BOILERPLATE: lines 77–122 (~2557 chars, ~639 tok) duplicate the harness-injected memory instructions (`memory: user` is set) — same pattern and same fix as `bash-git-ops`. Trim to one line.
- [info] This body is one of the tightest of the three memory-enabled agents outside the boilerplate — Steps 1–4 and the edge-case handling read as genuinely differentiated content, not filler. No further body cuts proposed beyond the memory section.

Tool policy: inherit-all → `Read, Edit, Write, Grep, Glob, Bash`
  Matches the "Implementer / coder" archetype. `Bash` is a judgement call: the body never explicitly says "run tests" or "run the build," but an implementer that can't execute anything it writes is a plausible gap — keeping it and flagging it per the conservative-on-tools rule.
  ? `Bash`: keep or drop? — body never mentions running commands; if this agent is meant to hand code to a separate test-runner agent, drop it.

Proposed trims:
- Description: 3 examples → 1 (~582 tok → ~200 tok, ~-382 tok)
- Memory section, lines 77–122 → 1 line (~639 tok → ~50 tok, ~-589 tok)
- Add `tools:` line (~+11 tok)

Definition text: ~2250 → ~1290 tok (chars/4 of the file; not a launch-cost measurement)
Model: unchanged — sonnet is a reasonable fit for an implementer; no evidence it needs opus-tier judgment (the whole point of the role is to *not* exercise architectural judgment).

---

## plan-reviewer  (agents/plan-reviewer.md)
Current: model opus · tools `Read, Grep, Glob, Agent(verifier), ExitPlanMode` · body 17 lines · definition text ~340 tok
Version: (none) → unchanged unless the Bash question below is resolved

Findings
- [low] NESTED_AGENT_TOOL: lists `Agent(verifier)` — confirmed legitimate, not just plausible: the body's own Workflow step 2 says "dispatch a `verifier` subagent with the file, the line range and the claim." Keep as-is; no action needed.
- [info] `ExitPlanMode` is valid here because `permissionMode: plan` is set. No flag.
- [info] OMITS_CLAUDE_MD: `omitClaudeMd: true`. The "Repository rules" section (git-push/reset --hard ban, untrusted-checkpoint handling) is this agent's *only* copy of those rules — do not treat any of it as prunable duplication.
- [med] Possible body/tools gap (not a scanner code — judgement finding): Workflow step 1 says "Read the diff and every caller of the changed functions," but the allowlist has no way to *produce* a diff (no `Bash` for `git diff`, and nothing says the diff arrives pre-pasted from the caller). If this agent is expected to pull its own diff, it's missing a tool; if the diff is always handed to it as input, the current allowlist is correct as-is. Flagging as a question rather than proposing an add.
  ? `Bash`: does this agent fetch its own diff (`git diff`/`git log -p`), or is the diff always supplied by whoever invokes it? Add `Bash` (read-only git use) only in the first case.

Tool policy: `Read, Grep, Glob, Agent(verifier), ExitPlanMode` → unchanged (pending the `Bash` question above)

Proposed trims: none — this is the tightest-shaped agent in the set (17-line body: role → repo rules → workflow → output format), already matching the target shape from the best-practices reference.

Definition text: ~340 tok, no change proposed (chars/4 of the file; not a launch-cost measurement)
Model: unchanged — opus is appropriate; this is a security review with a remediation plan, not mechanical work, and read-only is not by itself a downgrade reason.

---

## solution-architect  (agents/solution-architect.md)
Current: model opus · tools `Glob, Grep, Read, Edit, Write, NotebookEdit, WebFetch, WebSearch, Skill, TaskCreate, TaskGet, TaskUpdate, TaskList, EnterWorktree, ToolSearch` (15) · body 170 lines · definition text ~3162 tok
Version: (none) → 1.1.0 if applied

Findings
- [med] MANY_TOOLS: 15 tools listed; more than the ~10-entry trim point for a single-purpose agent.
- [med] WRITE_ON_READONLY: body states "Never write implementation code… If you find yourself writing functions, classes, or executable logic beyond pseudocode, stop and redirect to planning," yet `NotebookEdit` is granted. `Edit`/`Write` are legitimate under the memory exception (`memory: user`) regardless of whether the body persists a plan file to disk — but `NotebookEdit` serves neither the "writes only prose plans" mandate nor memory upkeep (memory files are Markdown). → propose dropping `NotebookEdit`.
- [low] BACKGROUND_STRIPPED + granted-but-unused (net check): `TaskCreate`, `TaskGet`, `TaskUpdate`, `TaskList` are (a) stripped automatically on a background-launched subagent (the default), and (b) never referenced anywhere in the 170-line body — no mention of creating or tracking a task list. → propose dropping all four unless this agent is specifically launched in the foreground and expected to manage tracked tasks.
- [low] Granted-but-unused (net check): `EnterWorktree` is not mentioned in the body either. → flagging as a question rather than a silent drop.
  ? `EnterWorktree`: keep or drop? — no reference in the body to working in an isolated worktree.
  ? `ToolSearch`: keep or drop? — not referenced directly, but plausible if this agent's research phase ever needs a deferred/MCP tool; low cost either way.
- [low] LONG_DESCRIPTION: ~2764 chars (~691 tok), 3 worked examples that all illustrate the same "invoke before/during a complex build" trigger → keep 1, cut the other 2.
- [med] LONG_BODY: 170 lines vs. the ~150-line bloat threshold for a single-purpose agent. This role is inherently more complex than a single-purpose critic (it owns discovery, requirement analysis, a 7-phase plan template, an output format, behavioral guidelines, *and* a quality checklist), so some extra length is defensible — but there's real trim room:
  - The Quality Self-Check checklist (lines 111–121) restates points already covered by "Behavioral Guidelines" just above it — largely redundant, propose cutting or merging into one line ("re-read the plan against the Behavioral Guidelines before delivering it").
  - The "Typical Phase Progression" list (lines 57–64) and the earlier "Execution Plan Structure" fields overlap conceptually; could be tightened but is closer to load-bearing template content — flagging, not proposing a cut, since it's plausibly the actual output contract other agents rely on.
- [med] MEMORY_BOILERPLATE: lines 134–179 are the same harness-duplicating "# Persistent Agent Memory" section found in `bash-git-ops` and `plan-driven-coder` (confirmed by the scanner's cross-agent duplicate-block list, ~466 tok of exact-match text shared across all three). Trim to one line.
  - Lines 122–132 ("Examples of what to record": domain modules, data access patterns, auth mechanisms, etc.) are *not* part of the cross-agent duplicate — they're customized to an architecture role and arguably carry real value (they tell the agent what's worth saving, differently from a bash-ops or coder agent). Flagging as a judgement call rather than folding it into the same one-line cut: keep this short customized list, cut only the generic harness-duplicating block below it.

Tool policy: `Glob, Grep, Read, Edit, Write, NotebookEdit, WebFetch, WebSearch, Skill, TaskCreate, TaskGet, TaskUpdate, TaskList, EnterWorktree, ToolSearch` (15) → `Glob, Grep, Read, Edit, Write, WebFetch, WebSearch, Skill, ToolSearch` (9, confirmed) + 2 pending questions
  ? `EnterWorktree`: keep or drop? — unused in body, see above.
  ? `ToolSearch`: keep or drop? — unused in body, see above.
  (schema cost of trimming 15 → 9–11 tools is not measured by the scanner)

Proposed trims:
- Description: 3 examples → 1 (~691 tok → ~225 tok, ~-466 tok)
- Memory section, lines 134–179 → 1 line, keep lines 122–132 (~816 tok section → ~65 tok + kept custom list, net ~-700 tok)
- Quality Self-Check checklist → 1 line (~small, not separately quantified)
- Tools list: drop `NotebookEdit` + 4 Task* tools (~-12 tok on the frontmatter line; real savings are in the dropped schemas, unmeasured)

Definition text: ~3162 → ~1930 tok (chars/4 of the file; not a launch-cost measurement)
Model: unchanged — opus fits: this is a planning/architecture role where the competence bar should hold regardless of session model, matching the best-practices guidance not to downgrade this kind of agent by default.

---

## Summary
5 agents audited · definition text ~8350 → ~5060 tok (chars/4 proxy; not launch cost) · 3 agents
(`bash-git-ops`, `code-explorer`, `plan-driven-coder`) move from inherit-all to an explicit
allowlist — real tool-schema savings, unmeasured here. `solution-architect` already had an
explicit list and drops from 15 to 9 confirmed tools (2 more pending answers).
`plan-reviewer` needed no tool changes; its `Agent(verifier)` use was confirmed by its own
body, and its `omitClaudeMd: true` rules were correctly left alone as non-duplicative.

Cross-cutting: all three `memory: user` agents (`bash-git-ops`, `plan-driven-coder`,
`solution-architect`) carry the same ~46–58-line hand-written "Persistent Agent Memory"
section that the harness already injects for a memory-enabled agent — the scanner's
`duplicate_blocks` confirms ~1,866 chars (~466 tok) of exact-match text repeated across
all three. This is the single largest and most mechanical win in the set.

Open questions needing your input before anything is applied:
1. `plan-driven-coder` — keep or drop `Bash`? (body never mentions running code)
2. `plan-reviewer` — does it pull its own `git diff`, or is the diff always handed to it? (decides whether to add `Bash`)
3. `solution-architect` — keep or drop `EnterWorktree` and `ToolSearch`? (both unreferenced in the body)
4. `solution-architect` — keep the customized "what to record" memory bullets (lines 122–132) alongside the one-line trim, or cut those too?
5. `code-explorer` and `solution-architect` model downgrades (sonnet) are unverified candidates, not recommendations — worth a before/after comparison on a real task before adopting, not something to apply blind.

Nothing has been changed on disk. Apply all / pick per-agent / adjust?
