# Fixture D, 2026-06-02 (previous skill version)

Two suites Claude Haiku wrote on 2026-06-02 for fixture D, the account service, from the same short prompt. One run had no skill. The other followed the previous version of this skill, which leaned on a separate test-driven-development skill for the basic mocking rules.

The docstring at the top of the with-skill suite named the skill it followed, so it was cut down to one neutral line. That way a grader reading the suite can't tell which run wrote it. Nothing else was changed.

Both suites kill both fixture D mutants. The difference between them is in the mocking: the baseline builds its collaborators from `MagicMock` and checks calls with `assert_called*`, while the with-skill suite uses hand-written fakes and checks the account's state and the emails sent. `verdict.json` in each folder records the counts, and the repository test replays both.
