# Finding edge cases and covering every condition

Load this when a unit has inputs with ranges, compound conditions, states, several interacting parameters, or error paths.

## Checklist for one unit

1. **List the inputs and state:** arguments, fields read, environment, clock, files, network. Each is a dimension to test.
2. **Partition each dimension.** Valid classes (one per distinct behaviour the spec names) and invalid ones (wrong type, out of range, malformed). Cover every partition, the invalid ones included. Put one invalid value in each test, so one rejection can't hide another.
3. **Test the boundaries of every ordered partition with three values:** just below, on, and just above (x-1, x, x+1). Two values miss a `<=` written as `==`.
4. **Check every condition, not just every branch.** For each part of a compound decision, write a pair of tests that differ only in that part and give different outcomes. A decision with n conditions needs about n+1 tests. Branch coverage can be reached with two tests that prove none of this.
5. **Rule combinations:** a decision table, one column per feasible rule, a test per column.
6. **Stateful units:** cover every valid transition; for critical code also each invalid transition, one per test.
7. **Many interacting parameters:** cover every pair first; go to three-way where the risk is high.
8. **Run the edge set below** against each dimension.
9. **Error paths:** inject each failure the unit can see and assert what the caller observes: the error is raised or returned, state is rolled back, the caller is told. "It didn't crash" is not an assertion. An empty handler, a handler that only logs, a catch-all that aborts, or a TODO in a handler is a finding in itself.
10. **Properties**, where a spec exists: round-trip (`decode(encode(x)) == x`), invariants on the output, comparison with a simple model, metamorphic relations (how a change to the input should change the output).
11. **Prove the tests can fail:** mutate by hand or with a mutation tool (see SKILL.md).

## Worked example: `(a and b) or c`

| a | b | c | result | pair it belongs to |
|---|---|---|---|---|
| T | T | F | T | with FTF shows `a` matters; with TFF shows `b` matters |
| F | T | F | F | with TTF shows `a` matters |
| T | F | F | F | with TTF shows `b`; with TFT shows `c` |
| T | F | T | T | with TFF shows `c` matters |

Four tests, and each condition has a pair that flips only it and changes the result. Delete any one condition from the code and at least one test goes red. Now combine this with boundaries: if `a` is `age >= 18`, its true and false rows should sit at 18 and 17.

## The edge set

| Area | Values to try |
|---|---|
| Size | empty, null / none / nil, zero, one, many, the maximum |
| Numbers | type minimum and maximum, negative, overflow and underflow, NaN, ±infinity, -0.0 |
| Text | Unicode (combining marks, characters outside the basic plane, right-to-left), invalid encoding, leading, trailing or only whitespace |
| Collections | duplicates, already sorted versus reversed, whether ordering is stable |
| Time | time zones, the DST gap and overlap, leap day, leap second, the epoch |
| Concurrency | concurrent calls, re-entrancy |
| Idempotency | calling twice gives the same result as calling once |
| Resources | file, network or allocation failure; timeouts |

## Techniques

| Technique | Use when | Cost |
|---|---|---|
| Equivalence partitioning | Always; the first pass on any input | One test per partition |
| Boundary values (3-value) | Any ordered partition: numbers, lengths, dates, indices | Three tests per boundary |
| Decision table | Business rules over combinations of conditions | Grows fast; cut infeasible columns |
| State transition | Protocols, lifecycles, parsers | Every transition at least once |
| Condition pairs (MC/DC) | Compound boolean decisions | About n+1 tests instead of 2^n |
| Pairwise | Many configuration or parameter dimensions | Small for two-way |
| Property-based | Pure functions with a spec, a model or an inverse | You design generators and properties |
| Mutation testing | Proving the tests can fail | Compute-heavy; run it on the changed code |

## Why these

- Three-value boundaries: the ISTQB Foundation syllabus (v4.0, §4.2.2) shows that with `x <= 10` coded as `x == 10`, the two-value set {10, 11} can't detect the defect, while 9 does. https://astqb.org/4-2-black-box-test-techniques/
- Condition pairs need "a minimum of n+1 test cases for a decision with n inputs", against 2^n for every combination. NASA TM-2001-210876. https://ntrs.nasa.gov/api/citations/20010057789/downloads/20010057789.pdf
- Most faults need one or two interacting parameters: in NIST's data, one- and two-way interactions triggered 66% / 97% of faults in medical devices and 68% / 93% at NASA, and no fault needed more than four to six. https://csrc.nist.rip/groups/SNS/acts/software_failures.html
- Error paths: in a study of 198 catastrophic failures in five distributed systems, "almost all (92%) … are the result of incorrect handling of non-fatal errors", and 58% "could easily have been detected through simple testing of error handling code". Yuan et al., OSDI 2014. https://www.usenix.org/system/files/conference/osdi14/osdi14-paper-yuan.pdf
- Properties: John Hughes found that validity properties missed five of eight seeded bugs, while "every bug is found by at least one postcondition, metamorphic property, and model-based property". "How to Specify It!", TFP 2019. https://research.chalmers.se/publication/517894/file/517894_Fulltext.pdf
