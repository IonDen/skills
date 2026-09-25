# Python (pytest, unittest)

This file maps the skill's rules onto Python's test runners, fakes, mock library, property and mutation tools, and the diff markers to check in review.

## Runner

pytest is the usual runner. The standard library ships unittest, and pytest also runs unittest-style `TestCase` classes.

- One file: `pytest tests/test_users.py`. One test: `pytest tests/test_users.py::test_rejects_empty_name`.
- unittest: `python -m unittest tests/test_users.py`. The file must be importable as a module.

Source: https://docs.pytest.org/en/stable/how-to/usage.html; https://docs.python.org/3/library/unittest.html

## Writing a fake

Duck typing is enough. Declare the adapter's interface as a `typing.Protocol` so a type checker confirms the fake matches it, then write a small class that keeps its state in memory. Hand it in through the constructor or a fixture. Don't patch it in by module path.

```python
class UserStore(Protocol):
    def save(self, user: User) -> None: ...
    def get(self, user_id: str) -> User | None: ...

class InMemoryUserStore:
    def __init__(self) -> None:
        self.users: dict[str, User] = {}
    def save(self, user: User) -> None:
        self.users[user.id] = user
    def get(self, user_id: str) -> User | None:
        return self.users.get(user_id)
```

A `FixedClock` with a `now()` that returns a set `datetime` follows the same pattern. The test asserts on `store.users` or on what `get` returns, not on calls.

Source: https://docs.python.org/3/library/typing.html#typing.Protocol

## Mocking library (last resort)

`unittest.mock` is in the standard library. pytest-mock's `mocker` fixture (`mocker.patch`, `mocker.spy`, `mocker.stub`) is a thin wrapper around the same API. Use a mock only to verify an unavoidable outgoing side effect at a boundary you don't own. When you do, build it with `create_autospec(...)` or `patch(..., autospec=True)` so it rejects calls the real object would reject.

To spot interaction assertions in review, look for `assert_called`, `assert_called_once`, `assert_called_with`, `assert_called_once_with`, `assert_any_call`, `assert_has_calls`, `assert_not_called`, the `assert_awaited*` family on `AsyncMock`, and reads of `called`, `call_count`, `call_args`, `call_args_list`, `method_calls` or `mock_calls`. A `patch("yourpkg.module.Name")` that replaces the unit under test or one of its own in-process helpers is a finding.

Source: https://docs.python.org/3/library/unittest.mock.html; https://pytest-mock.readthedocs.io/en/latest/

## Property-based testing

Hypothesis is maintained, with releases in September 2026. Use `@given(...)` with strategies from `hypothesis.strategies`. Pin known edge cases with `@example(...)` so they run on every build.

Source: https://hypothesis.readthedocs.io/en/latest/

## Mutation testing

mutmut is maintained (3.8.0, September 2026). Run `mutmut run`, then open the surviving mutants with `mutmut browse`. Configuration goes under `[tool.mutmut]` in `pyproject.toml`. It needs `fork`, so on Windows it only runs inside WSL. cosmic-ray (8.7.0, August 2026) is a maintained alternative.

Source: https://github.com/boxed/mutmut; https://pypi.org/project/cosmic-ray/

## Red flags in a diff

- Skip and expected-failure markers: `@pytest.mark.skip`, `@pytest.mark.skipif`, `@pytest.mark.xfail`, `pytest.skip()`, `pytest.xfail()`, `pytest.importorskip()`, `@unittest.skip`, `@unittest.skipIf`, `@unittest.skipUnless`, `@unittest.expectedFailure`, `self.skipTest(...)`, `raise unittest.SkipTest`.
- Focus-only markers: pytest has none built in. The third-party pytest-only plugin adds `@pytest.mark.only`, and its last release was in 2024. A new `-k` expression, `--deselect`, `--ignore` or `--ignore-glob` in a script or in `addopts` has the same effect.
- Snapshot updates: syrupy's `--snapshot-update` and `--snapshot-update-new-only`, and changed files under `__snapshots__/`. For inline-snapshot, look for `--inline-snapshot=fix`, `update`, `create` or `trim`, and for edited `snapshot(...)` literals.
- Tolerances: changed `rel=` or `abs=` in `pytest.approx`, `places=` or `delta=` in `assertAlmostEqual`, and changed `rel_tol` or `abs_tol` in `math.isclose`.
- Runner config: `pytest.toml`, `.pytest.toml`, `pytest.ini`, `.pytest.ini`, `[tool.pytest]` or `[tool.pytest.ini_options]` in `pyproject.toml`, `[pytest]` in `tox.ini`, `[tool:pytest]` in `setup.cfg`. Also watch any `conftest.py` that adds hooks, `collect_ignore` or `collect_ignore_glob`, plus `xfail_strict` turned off and `-p no:<plugin>` in `addopts`.

Source: https://docs.pytest.org/en/stable/how-to/skipping.html; https://docs.pytest.org/en/stable/reference/customize.html; https://docs.pytest.org/en/stable/example/pythoncollection.html; https://syrupy-project.github.io/syrupy/; https://15r10nk.github.io/inline-snapshot/latest/pytest/
