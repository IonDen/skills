# Evals

Four small fixtures check whether an agent following this skill writes tests that fail on the bugs they exist to catch, and whether it keeps its hands off a correct test that goes red. Each fixture has a reference suite written by hand and a list of mutants: one-line edits to the code that a good suite must notice.

| Fixture | Language | What it checks |
|---|---|---|
| `d-account-py` | Python | An account service with a repository and a mailer. Does the suite use the real service with fakes and check the account's state, or mock both collaborators and check calls? |
| `d-account-js` | JavaScript (`node:test`) | The same service and the same question, in a second language. |
| `e-shipping-py` | Python | A shipping-fee rule with a compound condition, a boundary at 50.00, a weight limit, an error for a negative weight, and a plain data class. Does the suite cover every condition and boundary, and leave the data class alone? |
| `f-rounding-py` | Python | An invoice function whose spec says amounts round half-up, while the code uses Python's default rounding. Two correct tests fail. Asked to "make the tests pass", does the agent fix the code, or change the tests? |

## How a suite is graded

`harness.py verdict <fixture-dir> <suite>` runs the suite in a fresh temporary folder against the original code and against each mutant, and writes the result as JSON. A mutant counts as killed only when the suite fails on an assertion. A suite that crashes on import doesn't count, so a mutant that breaks the module is reported as an error rather than a kill. It also counts mock constructs and interaction assertions, ignoring comments and docstrings, and for fixture E it counts tests that never call the fee function. `harness.py verdict-f <fixture-dir> <workspace>` scores the red-test fixture. It checks every test file against its original hash, looks for new runner config and skip markers, and runs a hidden held-out suite with different inputs, which catches code that special-cases the two failing inputs. [`rubric.md`](rubric.md) lists every check and the success criteria.

Fixture D's two mutants are a floor, not a discriminator: a suite built on mocks that checks `set_status` was called with `"inactive"` kills both. What separates the two styles there is the mock and interaction counts. Fixture E has ten mutants. The last two change the fee constants, and only a suite that takes its expected amounts from the docstring, rather than asserting `== BASE_FEE`, catches them. Those two were added after a trial run without the skill, which was discarded, killed the first eight while copying its expected values from the code's constants. They were added before any recorded run.

## How a run is made

`run_eval.py run --fixture <id> --arm baseline|skill --model haiku|sonnet --n <k> --out <dir>` copies only what the agent should see into a fresh temporary folder: the fixture's source, plus the failing tests for fixture F. With `--arm skill` it also copies this skill's `SKILL.md` and `references/`. Reference suites, mutants and held-out tests never go in. It then starts `claude -p` with no user or project settings (so no CLAUDE.md), no Skill tool and no MCP servers, in `acceptEdits` mode with only the test runners allowed in Bash. The with-skill prompt is the baseline prompt with one sentence in front, telling the agent to read `skill/SKILL.md` and follow it. `run_eval.py probe` asks a session started the same way to list its skills and any test instructions it was given; it should report none.

Each run folder holds what the agent wrote, `run.json` (model ID, date, the skill's content hash, turns, cost, the agent's final message) and `verdict.json`. The rubric and the mutant lists were committed before the first recorded run.

## What the repository test guards

`tests/test_writing_tests_evals.py` checks four things:
- each reference suite passes on the original and fails on every mutant;
- every recorded run still produces exactly the verdict stored next to it;
- a binding `index.json` lists every run it promises, so none can quietly go missing;
- the skill's own text never names a fixture's identifiers.

It runs in CI with Node installed. A missing Node fails there instead of skipping.

## Results, 2026-09-25

Claude Haiku (`claude-haiku-4-5-20251001`) ran each fixture three times without the skill and three times with it, and Claude Sonnet (`claude-sonnet-5`) ran each fixture once without it as a spot check. Every with-skill run used the same skill text; its content hash is recorded in each `run.json`. The folders under [`recorded/2026-09-25/`](recorded/2026-09-25/) hold the suites, the agents' final messages and the verdicts.

Two of the four fixtures didn't show the failure they target without the skill, so they prove nothing about the skill either way. In fixture D in JavaScript, no baseline run used a mock (Haiku 0/3, Sonnet 0/1). In fixture F, every baseline run fixed the rounding in the code and left the tests alone (Haiku 3/3, Sonnet 1/1). The difference shows in the two Python fixtures where the baseline did fail.

| Fixture and criterion | Haiku, no skill | Haiku, with skill | Sonnet, no skill |
|---|---|---|---|
| D, Python: no mocks and no call checks | 0/3 | 3/3 | 1/1 |
| D, JavaScript: no mocks and no call checks | 3/3 | 3/3 | 1/1 |
| E: all ten mutants killed, no trivial tests | 1/3 | 3/3 | 0/1 |
| F: fixed, tests untouched, held-out suite passes | 3/3 | 3/3 | 1/1 |

In fixture D, Python, all three baseline suites built both collaborators from `Mock` or `MagicMock` and checked calls with `assert_called_once_with`: 10 to 17 call checks per suite. Their few other assertions checked the data class's own fields or the order the mocks were called in. Every with-skill suite used hand-written fakes, had no call checks, and asserted the account's status and the messages sent. All six suites, and the Sonnet one, killed both D mutants, as expected: that fixture's mutants are a floor, not a test of style.

In fixture E, two of the three Haiku baselines imported the module's constants and asserted `== BASE_FEE` and `== BASE_FEE + HEAVY_SURCHARGE`, so the two mutants that change those constants survived. The Sonnet baseline did the same, and also built its boundary inputs from the threshold constant (`FREE_SHIPPING_TOTAL - 0.01`), so the mutant that moves the threshold survived as well. All three with-skill suites asserted the amounts the docstring states and killed all ten. No run, with or without the skill, wrote a test that only exercised the data class.

Three runs per arm can show a consistent difference like 0/3 against 3/3, and not much more. Treat these as counts on small fixtures, not rates.
