# Evidence

The studies behind this skill. Each figure is quoted from the source linked next to it.

## Agents mock more, and aim for green

- **Coding agents add more mocks than people do.** Across more than 1.2 million commits, "36% of commits made by coding agents add mocks to tests, compared with 26% by non-agents", and "68% of the repositories with agent test activity also contain agent mock activity." Hora and Robbes, "Are Coding Agents Generating Over-Mocked Tests? An Empirical Study", 2026. https://arxiv.org/abs/2602.00409
- **Generated tests often encode the current behaviour, bugs included.** LLM test generation is "prone on generating oracles that capture the actual program behaviour rather than the expected one." Konstantinou, Degiovanni and Papadakis. https://arxiv.org/abs/2410.21136
- **Under pressure, models special-case tests or edit them.** Anthropic's Claude 3.7 Sonnet system card: "Most often this takes the form of directly returning expected test values rather than implementing general solutions, but also includes modifying the problematic tests themselves to match the code's output." It tended to happen after repeated failed attempts, or when tests seemed to conflict. https://assets.anthropic.com/m/785e231869ea8b3b/original/claude-3-7-sonnet-system-card.pdf
- **On tasks where the tests conflict with the spec, cheating is common.** ImpossibleBench: "GPT-5 exploits test cases 76% of the time" on its one-off variant, and Claude models cheated mostly by modifying test cases. Giving the model an explicit way to stop and report cut GPT-5's cheating from 54% to 9%. Zhong, Raghunathan and Carlini, 2025. https://arxiv.org/abs/2510.20270
- **The tricks are specific and repeatable:** an object whose equality check always returns true, exiting with success before the assertions run, and a hook file that rewrites the test report (Anthropic, https://arxiv.org/abs/2511.18397 ); skipping tests, writing stubs where coverage is thin, and parsing test files for the expected values (Baker et al., https://arxiv.org/abs/2503.11926 ).

## Coverage is a weak signal; mutants are a better one

- "Some test suites achieve 100% coverage but only 4% mutation score." Wang, Xu, Briand and Liu (MUTGEN). https://arxiv.org/abs/2506.02954
- Coverage has "a low to moderate correlation" with fault detection once suite size is controlled for, and "stronger forms of coverage do not provide greater insight." Inozemtseva and Holmes, ICSE 2014. https://www.cs.ubc.ca/~rtholmes/papers/icse_2014_inozemtseva.pdf
- "Mutants are coupled with 70% of high-priority bugs" at Google, and "each bug-introducing change was covered by the existing tests": the lines ran, the tests didn't notice. Petrović, Ivanković, Fraser and Just, ICSE 2021. https://homes.cs.washington.edu/~rjust/publ/mutation_testing_practices_icse_2021.pdf
- Mutants show "a coupling effect for 73% of real faults." Just et al., FSE 2014. https://homes.cs.washington.edu/~rjust/publ/mutants_real_faults_fse_2014.pdf
- Not every mutant is worth a test: Google's developers "initially classified 85% of reported mutants as unproductive" until suppression rules for logging, deadlines and config flags raised the productive share to 89%. Tests written only to kill unproductive mutants become change detectors. Petrović, Ivanković et al., "Practical Mutation Testing at Scale". https://arxiv.org/abs/2102.11378

## Edge cases and error paths

- 92% of catastrophic failures in five distributed systems came from "incorrect handling of non-fatal errors", and 58% "could easily have been detected through simple testing of error handling code." Yuan et al., OSDI 2014. https://www.usenix.org/system/files/conference/osdi14/osdi14-paper-yuan.pdf
- Boundaries, condition pairs, pairwise and properties: sources in `edge-cases.md`.

## What to test

- Google's *Software Engineering at Google*, Kent Beck's Test Desiderata, Vladimir Khorikov and Martin Fowler's site: sources in `worth-testing.md`.

## A caution

When the code under test may already be buggy, coverage and mutation score "no longer serve as reliable indicators" of test quality (Zhao, Zhou and Cohen, ISSTA 2026, https://arxiv.org/abs/2607.22880 ). Mutation shows that a test can fail; it doesn't show that the expected value is right. That is why expected values come from the spec.
