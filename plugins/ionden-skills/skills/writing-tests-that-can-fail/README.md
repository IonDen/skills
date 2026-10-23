# writing-tests-that-can-fail: tests that fail on the bug they exist to catch

An agent skill for Claude Code and OpenAI Codex that works in any language. It applies when an agent writes, reviews or fixes tests. Its one rule: a test earns its place only if you can name the one-line bug that turns it red.

Triggers: "write tests", "add unit tests", "review these tests", "make the tests pass", "fix the failing test", "increase coverage", "mock this".

## Make it automatic

The skill loads on its own when you ask for tests by name. When the tests come with a feature, a bug fix or a flaky-test repair, an agent often writes them without it. To ask for the skill whenever tests are written, add these two sentences to `~/.claude/CLAUDE.md` (all your projects) or to a project's `CLAUDE.md`:

```markdown
Before you write or edit test code, including the failing-test step of TDD, use the writing-tests-that-can-fail skill and follow it. When you hand test work to a subagent, tell it to use that skill too.
```

We measured this with Claude Opus in Claude Code (version 2.1.308, October 2026), with the sentences in a project `CLAUDE.md`, on eight test requests, three runs each. Leaving out runs that ended without touching a test, the skill was in use before the first test was written or handed off in 8 of 21 runs without the sentences and in 22 of 22 runs with them. This is not a blind test: we reworded the sentences once after an earlier run on the same eight requests, to stop them loading the skill where it wasn't needed. We also ran ten requests that sit close to test work but need no test changes, such as adding a CI workflow or refactoring with the tests left alone, five runs each. Five of the ten played no part in choosing the wording. The skill loaded in none of these runs, 50 with the sentences and 50 without. The method and every run are in [`evals/triggering/`](<https://github.com/IonDen/skills/tree/main/evals/triggering/>).

For Codex, put the same sentences in `~/.codex/AGENTS.md` or a project's `AGENTS.md`. We have not measured their effect there.

## Why this exists

Coding agents are rewarded for green tests, and it shows. Across more than 1.2 million commits, 36% of the commits coding agents made added mocks to tests, against 26% of other commits ([Hora and Robbes, 2026](<https://arxiv.org/abs/2602.00409>)). Generated tests tend to take their expected values from whatever the code returns now, bugs included ([Konstantinou et al.](<https://arxiv.org/abs/2410.21136>)). When a test won't pass, models return the expected value directly or edit the test to match the output ([Claude 3.7 Sonnet system card](<https://assets.anthropic.com/m/785e231869ea8b3b/original/claude-3-7-sonnet-system-card.pdf>); [ImpossibleBench](<https://arxiv.org/abs/2510.20270>)). A suite built that way is green and catches little. One study found suites with 100% line coverage and a 4% mutation score ([MUTGEN](<https://arxiv.org/abs/2506.02954>)).

## What it asks for

Before writing a test, name the bug a caller would see. Logic gets thorough tests, glue a few, and trivia none: plain data holders, stubs, restated constants.

Keep the unit and its own collaborators real, and use fakes for slow or nondeterministic adapters. Mock only to verify an outgoing side effect you can't observe any other way. Assert on state and output, never mainly on calls. Take expected values and boundary inputs from the spec as literals, never from the code's own constants.

Inside the units worth testing, cover every condition: partitions, three-value boundaries, a pair of tests for each part of a compound condition that flips only that part, and error paths asserted on what the caller sees. Then prove each test can fail by breaking the code on purpose, by hand or with the ecosystem's mutation tool.

When a test goes red, fix the code or report. Inside a fix, never change a test's expected value, tolerance, input or skip status. If the spec shows the test is wrong, stop and say so with the evidence. After three failed attempts, stop and report.

The body of `SKILL.md` is written in language-neutral pseudo-code. `references/` holds the details: what is worth testing, edge-case techniques, the tricky ways to fake a green test and how to spot them, a smell catalogue, the sources, and one short file per ecosystem (Python, JavaScript and TypeScript, Go, Java and Kotlin, Rust, Swift, C#) naming its runner, fake idiom, mock library, property and mutation tools, and the markers to question in a diff.

## Evidence

Four small fixtures, run with Claude Haiku three times without the skill and three times with it. The full method and every run are in the repository under [`evals/writing-tests-that-can-fail/`](<https://github.com/IonDen/skills/tree/main/evals/writing-tests-that-can-fail/>); they don't install with the skill.

| Fixture and criterion | Haiku, no skill | Haiku, with skill |
|---|---|---|
| Account service, Python: no mocks and no call checks | 0/3 | 3/3 |
| Account service, JavaScript: no mocks and no call checks | 3/3 | 3/3 |
| Shipping fee: all ten mutants killed, no trivial tests | 1/3 | 3/3 |
| Rounding bug with correct failing tests: fixed without touching the tests | 3/3 | 3/3 |

In JavaScript and on the rounding fixture, Haiku already did the right thing without the skill, so those two rows show that the skill doesn't make things worse, and nothing more. In Python, every baseline suite mocked both collaborators and checked calls, and every with-skill suite used fakes and checked the account's state. On the shipping fee, two of three baseline suites took their expected amounts from the module's constants, so a wrong constant would have passed. The with-skill suites used the amounts the spec states. Three runs per arm is small; read these as counts, not rates.

A repository test replays every recorded run and fails if any stored verdict stops reproducing.

## Install

```bash
npx skills add IonDen/skills --skill writing-tests-that-can-fail -g -a claude-code -y
npx skills add IonDen/skills --skill writing-tests-that-can-fail -g -a codex -y
```

## Version history

- 1.0.1 (2026-09-26): the Swift fake example declares its store as a plain `var`.
- 1.0.0 (2026-09-25): first public release.
