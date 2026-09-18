# Evals

`evals.json` holds three prompts with expected outcomes; `fixtures/` holds the four agent files they run against (two with no `tools` field, one with a 15-tool list that contradicts its read-only mandate, all three memory-enabled ones carrying the same 46-line hand-written memory section). Placeholders: `<AGENTS_DIR>` is a copy of `fixtures/`, `<AGENT_FILE>` one file in it, `<OUTPUTS_DIR>` where the report goes.

To run one by hand: copy `fixtures/` somewhere writable, give a fresh agent the skill and the prompt, then check the expected outcome against the edited files and the scanner's before/after totals.

Last recorded run (2026-09-18, eval 0 `full-audit`, skill 1.2.0, fresh Claude subagent): 8/8 expectations met; scanner total 8,012 → 4,377 estimated tokens per launch across the four fixtures; every memory-enabled agent kept `Edit` + `Write`; no dead tool entries; duplicated memory boilerplate removed.
