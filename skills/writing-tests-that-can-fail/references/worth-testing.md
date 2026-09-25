# Is it worth a test?

Load this when you are deciding which tests to write for a unit, or reviewing a suite that feels padded.

## The rule, per candidate test

1. **Name the bug.** One line: what would a caller or user see go wrong? If you can't name one, don't write the test.
2. **Would this test catch that bug?** Break the line or branch in your head. If the test stays green, it's the wrong test.
3. **Does it go through the public surface?** Call what real callers call and assert what they can observe. Don't assert on call order, private fields or internal helpers.
4. **Would it survive a refactor?** Picture the internals restructured with the same behaviour. A test that breaks there detects change, not bugs.
5. **What kind of code is this?**

   | Code | Tests |
   |---|---|
   | Logic with few collaborators: rules, algorithms, parsers, calculations | Thorough unit tests, every condition |
   | Glue that wires many collaborators together | A few integration tests through the real wiring |
   | Trivial: plain data, pass-through, assign-only constructors | None, unless step 1 named a bug |
   | Complex *and* tangled with many collaborators | Split it first, then test the logic part |

6. **Which dependency level?** Real if it's fast and deterministic. Otherwise a fake, then a stub. Use a mock only for an outgoing side effect other systems see (an email sent, a message published).
7. **Is it deterministic?** Inject the clock, seed randomness, don't depend on test order, don't touch the real network. Wait by polling with a timeout, never a bare sleep.
8. **Is it obvious?** The expected value is a literal you got from the spec, not recomputed with the production code's logic or constants. No loops or branches in the test.
9. **Is a cheaper test already catching this?** Push the test down to the cheapest level that still catches the bug.

## What not to test, and what brings it back

| Don't test | Unless |
|---|---|
| Getters, setters, plain data holders, constructors that only assign fields | They validate, convert, default or derive a value, or this exact mistake has shipped before |
| Framework, library or language behaviour (the ORM saves, `sort` sorts) | It's your configuration or use of it (the mapping, serializer settings, locale), or you rely on a quirk an upgrade could change; then a small contract test |
| Constants and config literals (a test that repeats the constant can only detect a change) | A wrong value would fail silently (a timeout, a limit, a unit conversion); then assert the behaviour the value controls, never the literal |
| Generated code | At the boundary: a round-trip or compatibility test on your schema |
| Pure delegation | The wrapper translates arguments, maps errors, retries, or crosses a boundary you don't own |
| Private methods directly | Never. Test through the public surface. If that hurts, the unit wants splitting |
| Calls to stubs or to your own internal collaborators | Only calls other systems can observe are worth verifying |

Kent Beck's rule of thumb fits here: "If I don't typically make a kind of mistake… I don't test for it… I'm extra careful when I have logic with complicated conditionals." A trivial line comes back in when it has already produced a real bug, or when its failure would be silent and a user would hit it.

## Snapshot and golden tests

A snapshot is a test only if a reviewer can read it, it is normalised (no timestamps, absolute paths or unordered output), and changing it takes a reviewed diff. A large snapshot that gets regenerated whenever it goes red can't fail in any way that matters.

## Sources

- Google, *Software Engineering at Google*, ch. 12 "Unit Testing": test via public APIs, "test state, not interactions", "write a test for each behavior", "Clear tests are trivially correct upon inspection". https://abseil.io/resources/swe-book/html/ch12.html
- Same book, ch. 13 "Test Doubles": "A real implementation is preferred if it is fast, deterministic, and has simple dependencies"; next, "the best option is often to use a fake". https://abseil.io/resources/swe-book/html/ch13.html
- Kent Beck, Test Desiderata: "If the behavior changes, the test result should change"; "tests should not change their result if the structure of the code changes". https://testdesiderata.com/
- Vladimir Khorikov, *Unit Testing Principles, Practices, and Patterns*, ch. 1: "coverage metrics are a good negative indicator but a bad positive one". https://enterprisecraftsmanship.com/files/Unit-Testing-Chapter-1-Excerpt.pdf ; "When to mock": mocks for dependencies you don't control, never assert interactions with stubs. https://enterprisecraftsmanship.com/posts/when-to-mock/
- Ham Vocke, "The Practical Test Pyramid": "You won't gain anything from testing simple getters or setters or other trivial implementations (e.g. without any conditional logic)." https://martinfowler.com/articles/practical-test-pyramid.html
- Martin Fowler, "Eradicating Non-Determinism in Tests": wrap the clock, poll instead of sleeping. https://martinfowler.com/articles/nonDeterminism.html
- Kent C. Dodds, "Effective Snapshot Testing". https://kentcdodds.com/blog/effective-snapshot-testing
