# Trigger eval

This eval checks whether the right skill loads at the right moment in a real Claude Code session. It runs Claude Code on small fixture projects and records, for each session, whether the skill loaded before the agent started the work the skill is for. The results set two things in plugin 0.8.5. The skill descriptions stay as they are. The `writing-tests-that-can-fail` README gets two sentences for `CLAUDE.md` that make the skill load far more reliably.

Running it uses real model time. Phase 1 is 354 sessions and Phase 2 is 197. An Opus session that ran to its last line cost about $0.13 on average (Sonnet about $0.05), and each phase took a little over an hour.

## What one session is

Each session starts from a fresh temporary copy of one fixture project. The fixtures are a small JavaScript cart, a small Python pricing module, a folder of Claude Code subagents and a folder of Codex custom agents. The session gets one prompt from `prompts.json`, one model (Opus or Sonnet) and one arm (below). The runner starts Claude Code like this:

```bash
claude -p "<prompt>" --model <model> --output-format stream-json --verbose \
  --setting-sources project,local --strict-mcp-config --mcp-config '{"mcpServers":{}}' \
  --permission-mode acceptEdits --allowedTools <test runners, ls, cat> \
  --max-turns 20 --max-budget-usd 2 --no-session-persistence \
  --plugin-dir plugins/ionden-skills
```

`--setting-sources project,local` keeps the user's own settings, `CLAUDE.md` and plugins out of the session, so the fixture and the arm are the only inputs. A probe checked this before Phase 1 (`recorded/2026-10-22/probe.txt`). `--strict-mcp-config` with an empty config keeps MCP servers out. `acceptEdits` lets the agent write files without stopping for permission.

This is a custom runner rather than `claude plugin eval` for one reason: that command isolates sessions so fully that no project `CLAUDE.md` loads, and the snippet arms need one.

## Arms

- `current`: the plugin as published.
- `current+snippet`: the same, plus a project `CLAUDE.md` that holds only the text of `snippet.md`.
- `current+snippet2`: the same with `snippet2.md`, the wording that shipped.
- `current-crowded`: the same as `current`, plus other plugins and a filler plugin with 60 unrelated skills. It checks whether a long skill list hides ours.
- `candidate`: `writing-tests-that-can-fail` with the longer description in `candidates/`, frozen by hash before the run.

## How a session is scored

`trigger.py` reads the session's event stream and gives each session one outcome:

| Outcome | Meaning |
|---|---|
| hit | The skill loaded before the first test file was written. For an optimizer, it loaded at all. For the hand-off prompt, the request to the subagent names the skill. |
| miss | A test file was written first. For an optimizer, the session ended without loading it. |
| n/a | A test-writing prompt ended without loading the skill and without touching a test. These runs are left out of the counts. |
| no-load, false-load | Near-miss prompts: the skill should not load, and it did not (no-load) or did (false-load). |

The runner stops a session as soon as its outcome is decided. A session that hits the turn or budget cap counts as inconclusive. One that hits an API or usage error, or ends without a final result line, counts as invalid and is run again, up to three tries; five invalid sessions in a row stop the run. There were no inconclusive or invalid sessions in either run.

## Prompts and halves

`prompts.json` holds 49 prompts. Each skill has "should" prompts, where it ought to load, and near-miss prompts that sit close to its job but don't need it. The prompts are split into halves:

- **dev:** used to write the candidate description. These results do not decide anything.
- **heldout:** decides.
- **fresh:** five near-miss prompts for `writing-tests-that-can-fail`, written after Phase 1 and frozen before Phase 2. The `snippet2.md` wording was chosen after seeing the Phase 1 held-out results, so its result on the held-out should prompts is not a blind test, and its near-miss check also counts prompts it was never tuned on.

## Decision rules

The rules sit in `criteria.json` and were fixed before any run. Only Opus runs decide.

- **Gap:** a skill has a gap when at least 3 held-out prompts miss in at least 2 of their 3 runs.
- **Ship:** compared with `current` on the held-out should prompts, a new arm must do better on at least 3 more prompts than it does worse on.[^net] It also needs at least 6 more hits in total.[^pooled] On near-miss prompts, a new description may not load on Opus at all and may load at most once across models. A snippet may not load more often than `current` does.

`decide.py` applies the rules. `python3 decide.py recorded/2026-10-22/verdicts.jsonl` reproduces `decision.json`, and a repository test checks that every stored decision still reproduces.

## Results

Held-out should prompts, hits out of scored runs (n/a left out):

| Skill | Arm | Opus | Sonnet |
|---|---|---|---|
| writing-tests-that-can-fail | current (Phase 1) | 8 / 21 | 2 / 16 |
| writing-tests-that-can-fail | current+snippet | 24 / 24 | 24 / 24 |
| writing-tests-that-can-fail | current-crowded | 12 / 24 | not run |
| writing-tests-that-can-fail | current (Phase 2) | 8 / 21 | not run |
| writing-tests-that-can-fail | candidate | 9 / 21 | not run |
| writing-tests-that-can-fail | current+snippet2 | 22 / 22 | not run |
| subagent-optimizer | current | 9 / 9 | 4 / 9 |
| skill-optimizer | current | 6 / 9 | 6 / 9 |

Near-miss prompts, false loads out of runs:

| Skill | Arm | Opus | Sonnet |
|---|---|---|---|
| writing-tests-that-can-fail | current (Phase 1) | 0 / 15 | 0 / 15 |
| writing-tests-that-can-fail | current+snippet | 2 / 15 | 0 / 15 |
| writing-tests-that-can-fail | current-crowded | 0 / 15 | not run |
| writing-tests-that-can-fail | current (Phase 2, held-out + fresh) | 0 / 50 | not run |
| writing-tests-that-can-fail | candidate (held-out) | 0 / 25 | not run |
| writing-tests-that-can-fail | current+snippet2 (held-out + fresh) | 0 / 50 | not run |
| subagent-optimizer | current | 0 / 3 | 0 / 3 |
| skill-optimizer | current | 0 / 6 | 0 / 6 |

The dev half ran on Sonnet only: `writing-tests-that-can-fail` 3 of 14 hits (24 of 24 with the snippet), `subagent-optimizer` 9 of 12, `skill-optimizer` 3 of 6. There were no false loads.

**Phase 1** (2026-10-22, Claude Code 2.1.308, 354 sessions, Opus and Sonnet) found a gap for `writing-tests-that-can-fail` only. Four held-out prompts missed on Opus: adding a feature to code with tests, fixing a bug, fixing a flaky test, and giving tests their own data. The optimizers had no gap. The first snippet raised hits a lot (net 5 prompts, 13 more hits). It also loaded on 2 near-miss Opus runs, one about running tests in parallel and one about a refactor that left the tests alone, so it did not ship. A crowded skill list did not lower the hit rate.

**Phase 2** (2026-10-23, same version, Opus only, 197 sessions) tested a longer description and a narrower snippet. The longer description won two prompts and lost one, a net gain of one prompt and one hit, short of the rule, so the shipped descriptions stay unchanged. The narrower snippet (`snippet2.md`) gained 5 prompts and 13 hits and loaded on none of the 50 near-miss runs, so it ships in the skill's README.

The CLI reports cost only for sessions that reach their last line, and the runner stops most sessions early. The recorded totals, $12.83 and $16.66, are therefore lower bounds. The runner's budget caps were $100 for Phase 1 and $50 for Phase 2. Against the cap, the runner now charges a session that reported no cost the average cost of a full session.

## Not measured

- Codex. The README suggests the same sentences for `AGENTS.md` but makes no claim about their effect there.
- Claude apps other than Claude Code, such as claude.ai.
- How many people add the sentences to their own `CLAUDE.md`.
- Haiku, and Claude Code versions other than 2.1.308.

## Files and commands

- `trigger.py` scores a session. `samples/` holds hand-labelled event streams for its tests.
- `run_trigger.py` plans and runs a phase. It resumes by skipping sessions already in `verdicts.jsonl`.
- `decide.py` and `criteria.json` hold the decision rules.
- `prompts.json`, `fixtures/`, `snippet.md`, `snippet2.md` and `candidates/` are the inputs.
- `recorded/<date>/` holds one verdict line per session (no paths, no transcripts), the decision file and the probe. `index.json` lists the phases.

```bash
python3 run_trigger.py probe --out recorded/<date>
python3 run_trigger.py plan --phase 1
python3 run_trigger.py run --phase 1 --cap 100 --out recorded/<date> --crowd <plugin dir>
python3 run_trigger.py run --phase 2 --cap 50 --out recorded/<date> --gap writing-tests-that-can-fail
python3 decide.py recorded/<date>/verdicts.jsonl
```

[^net]: Per prompt, the arm with more hits out of its 3 runs wins. The net count is prompts won minus prompts lost.
[^pooled]: Hits summed over the prompts that have scored runs in both arms, which is why the figure can be smaller than the difference of the table totals.
