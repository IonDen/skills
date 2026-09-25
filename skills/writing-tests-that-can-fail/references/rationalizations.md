# Rationalizations

The excuses for writing, keeping or "fixing" a test that can't fail, and what is actually true. Load this when you catch yourself arguing for a test you already suspect.

## Writing and keeping tests

| Excuse | Reality |
|---|---|
| "I'll mock it to isolate the unit." | You mocked the behaviour you were meant to test. Isolate from boundaries you don't own, not from your own code. |
| "Coverage is green." | Coverage counts lines run, not bugs caught. A suite can reach 100% coverage and still let almost every mutant through. |
| "It's hard to test without mocking." | That points at the design or the level. Extract the logic into a function, or fake the boundary. |
| "The integration test covers it." | Only if it runs on every change and would fail on this bug. A gated or slow test that doesn't run in CI covers nothing there. |
| "The test passes, so it works." | A test that passed on its first run hasn't shown it can fail. Break the code and watch. |
| "I asserted it was called." | That tests the mock. Assert what the caller sees. |
| "I used the constant so the test stays in sync." | In sync with the bug too. Use the value the spec states. |
| "It's just a getter / config / glue." | Then name the bug a user would hit. If there isn't one, delete the test instead of keeping it for the count. |
| "More tests are safer." | Tests that can't fail cost maintenance and hide the ones that can. |

## When a test goes red

| Excuse | Reality |
|---|---|
| "The test is obviously outdated." | Then the spec says so. Quote it and report. Don't edit it inside the fix. |
| "Just this once, to unblock." | An edited oracle ships the bug with a green badge. |
| "The expected value was a typo." | Maybe. Show where the right value comes from, and change it in a separate, labelled change. |
| "The tolerance was always too tight." | Measure it. If you are widening it to the number you just got, that is the cheat. |
| "I'll special-case this input for now." | The code is now right only for the test. Held-out inputs will show it. |
| "It's flaky, skip it." | Find the nondeterminism (clock, order, network, randomness) and remove it. A skip hides the bug with the flake. |
| "I've tried five times; the test must be wrong." | After three attempts, stop and report what you tried. Repeated failure is when agents start cheating. |

## Red flags: stop and rewrite

- The unit under test is a mock.
- The only assertion is a call check.
- There is no assertion.
- The expected value is computed from the code's constants or logic.
- A snapshot that is too big to read, or gets regenerated on every red.
- Only the happy path is tested.
- A tolerance nobody can justify.
- A test file, skip marker or runner config changed inside a fix.
