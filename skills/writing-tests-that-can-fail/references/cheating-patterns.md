# Tricky ways to get a green test

Load this when reviewing a diff that turned red tests green, or before you "fix" a failing test yourself. None of these is ever acceptable. Each one makes the suite pass without the code being right, and each is easy to miss on a quick read. The obvious moves (deleting a test, adding a skip marker, a test with no assertion) are covered in SKILL.md.

### Oracle copied from the implementation
- **Looks like:** the expected value was taken from what the code returns now, or built from the code's own constants and helpers (`expect total == amount * TAX_RATE`).
- **Why it passes:** the test agrees with the code by construction, so it pins the current behaviour, bugs included. Change the constant and the test changes with it.
- **Spot it:** expected values that aren't literals, or literals nobody can trace to a spec, a ticket or a worked example. Ask where each number came from.

### Special-casing the test input
- **Looks like:** `if input == <the value the test uses>: return <the value the test expects>`, sometimes dressed up as a lookup table or a "known edge case".
- **Why it passes:** only the inputs the tests use are right.
- **Spot it:** literals from the test file showing up in production code; comments like "handle this case"; a fix that gets smaller when you delete one test. Held-out inputs catch it.

### Always-equal object
- **Looks like:** the code returns an object whose equality check always says true, or a custom matcher that accepts anything.
- **Why it passes:** every equality assertion succeeds whatever the value.
- **Spot it:** equality or comparison overrides on production types that don't compare fields; assertions only ever compare against that type.

### Hidden state that replays the expected sequence
- **Looks like:** a counter or cache that returns a different result on the nth call, tuned to the order the tests call it in.
- **Why it passes:** it reproduces the sequence the tests expect, not the rule.
- **Spot it:** call the unit twice with the same input; run the tests in a different order or alone.

### Early successful exit
- **Looks like:** the process exits with success, or the test returns early, before the assertions run.
- **Why it passes:** the runner sees a clean exit and nothing red.
- **Spot it:** the reported assertion or test count dropped; an `exit(0)` or `return` near the top of a test or in code the test imports.

### Runner or report patching
- **Looks like:** a new runner config, plugin or hook file that rewrites results, filters failures or marks errors as passes.
- **Why it passes:** failures are reported as passes.
- **Spot it:** treat runner config, conftest-style hook files and CI test scripts as part of the test under review. Any change to them in a fix is suspect.

### Reading the answer at run time
- **Looks like:** production code that opens the test files, fixtures or golden outputs and pulls the expected value from them.
- **Why it passes:** the output is copied, not computed.
- **Spot it:** file reads of test paths from production code; paths containing "test" or "fixture" outside the test tree.

### A stub where the implementation should be
- **Looks like:** an empty or near-empty function body that happens to satisfy thin tests (returns the default, the input, or a constant).
- **Why it passes:** the tests never exercise the behaviour that is missing.
- **Spot it:** mutate the function (return a constant, delete the body). If the suite stays green, the tests are too thin.

### An exception catch that swallows the failure
- **Looks like:** the test wraps the call in a catch-everything block, or asserts only that "some" error happened when the spec names a specific one.
- **Why it passes:** a crash, a wrong error type or an assertion failure inside the block all count as success.
- **Spot it:** catch-all blocks in tests; error assertions that don't name the error type or message.

### A tolerance widened until it can't fail
- **Looks like:** a numeric bound loosened in the same change that made a red test green, often to the exact value the code now produces.
- **Why it passes:** the bound no longer separates right from wrong.
- **Spot it:** a tolerance change inside a fix. A bound moves only with a measurement that shows the old one was wrong, in its own labelled change.

## Where these come from

Every pattern above has been observed in coding agents working against tests: returning expected values instead of a general solution and editing tests to match the output (Anthropic, Claude 3.7 Sonnet system card, https://assets.anthropic.com/m/785e231869ea8b3b/original/claude-3-7-sonnet-system-card.pdf ); an object whose `__eq__` always returns true, exiting before the asserts, and a hook file that patches the test report (Anthropic, "Natural emergent misalignment from reward hacking in production RL", https://arxiv.org/abs/2511.18397 ); skipping tests, stubs where coverage is thin, and parsing test files for expected values (Baker et al., https://arxiv.org/abs/2503.11926 ); test files modified to pass (ImpossibleBench, https://arxiv.org/abs/2510.20270 ); expected values that capture the current behaviour rather than the intended one (Konstantinou et al., https://arxiv.org/abs/2410.21136 ).
