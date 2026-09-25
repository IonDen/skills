"""Tests for writing-tests-that-can-fail's eval harness and evidence. Each test
names the one-line bug that would turn it red."""
import json
import os
import shutil
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SKILL = ROOT / "skills" / "writing-tests-that-can-fail"
EVALS = SKILL / "evals"
FIXTURES = EVALS / "fixtures"


def test_apply_mutant_replaces_the_single_occurrence(harness):
    # Bug: replace() on the wrong string, or no replacement at all.
    m = harness.Mutant("m1", "a.py", "x >= 1", "x > 1")
    assert harness.apply_mutant("if x >= 1:\n", m) == "if x > 1:\n"


def test_apply_mutant_rejects_a_missing_find(harness):
    # Bug: a mutant that no longer matches the source runs the original and "survives".
    m = harness.Mutant("m1", "a.py", "x >= 2", "x > 2")
    with pytest.raises(harness.HarnessError, match="0 times"):
        harness.apply_mutant("if x >= 1:\n", m)


def test_apply_mutant_rejects_an_ambiguous_find(harness):
    # Bug: str.replace mutates both occurrences, so the mutant tests two edits at once.
    m = harness.Mutant("m1", "a.py", ">=", ">")
    with pytest.raises(harness.HarnessError, match="2 times"):
        harness.apply_mutant("a >= 1 and b >= 2\n", m)


def test_apply_mutant_rejects_a_no_op(harness):
    # Bug: find == replace makes a "mutant" identical to the original.
    m = harness.Mutant("m1", "a.py", "x >= 1", "x >= 1")
    with pytest.raises(harness.HarnessError, match="unchanged"):
        harness.apply_mutant("if x >= 1:\n", m)


def test_load_fixture_and_mutants(harness, tmp_path):
    # Bug: fixture.json fields read under the wrong keys, or mutants.json ignored.
    (tmp_path / "fixture.json").write_text(json.dumps(
        {"id": "demo", "language": "python", "sources": ["a.py"], "unit": "f"}))
    (tmp_path / "mutants.json").write_text(json.dumps(
        [{"id": "m1", "file": "a.py", "find": ">=", "replace": ">"}]))
    fx = harness.load_fixture(tmp_path)
    assert (fx.id, fx.language, fx.sources, fx.unit) == ("demo", "python", ("a.py",), "f")
    assert harness.load_mutants(tmp_path) == [harness.Mutant("m1", "a.py", ">=", ">")]


NODE = shutil.which("node")


def need_node():
    if NODE:
        return
    if os.environ.get("CI"):
        pytest.fail("node is required in CI; the JavaScript evidence would silently vanish")
    pytest.skip("node not installed")


def _junit(failures, errors):
    return (f'<testsuites><testsuite name="pytest" tests="3" failures="{failures}" '
            f'errors="{errors}"/></testsuites>')


@pytest.mark.parametrize("code, junit, expected", [
    (0, _junit(0, 0), "pass"),
    (1, _junit(1, 0), "fail"),
    (1, _junit(1, 1), "error"),   # a fixture error rides along with the failure
    (2, _junit(0, 1), "error"),   # collection error, e.g. an ImportError
    (5, None, "error"),           # no tests collected
    (1, None, "error"),           # no report written
])
def test_classify_pytest(harness, code, junit, expected):
    # Bug: any non-zero exit counted as a kill.
    assert harness.classify_pytest(code, junit) == expected


def _mini_fixture(tmp_path, language, source_name, source, meta_unit=None):
    fx_dir = tmp_path / "fx"
    fx_dir.mkdir()
    (fx_dir / source_name).write_text(source)
    (fx_dir / "fixture.json").write_text(json.dumps(
        {"id": "mini", "language": language, "sources": [source_name], "unit": meta_unit}))
    return fx_dir


def test_python_suite_pass_fail_and_import_crash(harness, tmp_path):
    # Bug: an ImportError from a mutant scored as "killed" (Review Focus 1).
    fx_dir = _mini_fixture(tmp_path, "python", "calc.py", "def double(x):\n    return x * 2\n")
    suite = tmp_path / "calc_test.py"
    suite.write_text("from calc import double\n\ndef test_double():\n    assert double(2) == 4\n")
    fx = harness.load_fixture(fx_dir)
    assert harness.run_suite(fx, suite) == "pass"
    assert harness.run_suite(fx, suite, harness.Mutant("m", "calc.py", "x * 2", "x * 3")) == "fail"
    renamed = harness.Mutant("m", "calc.py", "def double(", "def triple(")
    assert harness.run_suite(fx, suite, renamed) == "error"


def test_mutant_that_does_not_compile_is_a_harness_error(harness, tmp_path):
    # Bug: a syntax-breaking mutant scored as a kill instead of failing loudly.
    fx_dir = _mini_fixture(tmp_path, "python", "calc.py", "def double(x):\n    return x * 2\n")
    suite = tmp_path / "calc_test.py"
    suite.write_text("from calc import double\n\ndef test_double():\n    assert double(2) == 4\n")
    with pytest.raises(harness.HarnessError, match="does not compile"):
        harness.run_suite(harness.load_fixture(fx_dir), suite,
                          harness.Mutant("m", "calc.py", "return x * 2", "return x *"))


def test_js_suite_pass_fail_and_import_crash(harness, tmp_path):
    # Bug: a JS file that throws while loading is scored as a kill (Review Focus 1).
    need_node()
    fx_dir = _mini_fixture(tmp_path, "javascript", "calc.mjs",
                           "export function double(x) {\n  return x * 2;\n}\n")
    suite = tmp_path / "calc_test.mjs"
    suite.write_text('import { test } from "node:test";\nimport assert from "node:assert/strict";\n'
                     'import { double } from "./calc.mjs";\n'
                     'test("double", () => { assert.equal(double(2), 4); });\n')
    fx = harness.load_fixture(fx_dir)
    assert harness.run_suite(fx, suite) == "pass"
    assert harness.run_suite(fx, suite, harness.Mutant("m", "calc.mjs", "x * 2", "x * 3")) == "fail"
    renamed = harness.Mutant("m", "calc.mjs", "function double(", "function triple(")
    assert harness.run_suite(fx, suite, renamed) == "error"


def test_double_counts_ignore_docstrings_and_comments(harness):
    # Bug: a docstring saying "no Mock here" counted as a mock construct.
    src = ('"""No Mock or MagicMock in this suite."""\n'
           "# assert_called_once is banned here\n"
           "def test_x():\n    \"\"\"Uses a fake, not a Mock.\"\"\"\n    assert 1 == 1\n")
    assert harness.double_counts(src, "python") == {"mock_constructs": 0, "interaction_asserts": 0}


def test_double_counts_find_real_mocks(harness):
    # Bug: patterns miss MagicMock or assert_called_once_with.
    src = ("from unittest.mock import MagicMock\n"
           "def test_x():\n    repo = MagicMock()\n    repo.save(1)\n"
           "    repo.save.assert_called_once_with(1)\n")
    assert harness.double_counts(src, "python") == {"mock_constructs": 2, "interaction_asserts": 1}


def test_double_counts_js(harness):
    # Bug: node:test's mock.fn or .mock.calls not recognised.
    src = ("// mock.fn is not used below\nimport { test, mock } from 'node:test';\n"
           "test('x', () => { const f = mock.fn(); f(); assert.equal(f.mock.calls.length, 1); });\n")
    assert harness.double_counts(src, "javascript") == {"mock_constructs": 1, "interaction_asserts": 1}


def test_trivial_tests_counts_tests_that_never_touch_the_unit(harness):
    # Bug: a test that only builds the data holder counted as a real test,
    # or a test that reaches the unit through a helper counted as trivial.
    src = (
        "from shipping import Order, shipping_fee\n"
        "def fee_for(**kw):\n    return shipping_fee(Order(**kw))\n"
        "def test_holder_fields():\n    o = Order(1, 2, True, False)\n    assert o.total == 1\n"
        "def test_direct():\n    assert shipping_fee(Order(1, 2, True, False)) == 4.99\n"
        "def test_via_helper():\n    assert fee_for(total=1, weight_kg=2, member=True, promo=False) == 4.99\n"
        "def test_raises_by_reference():\n    import pytest\n"
        "    pytest.raises(ValueError, shipping_fee, Order(1, -1, True, False))\n")
    assert harness.trivial_tests(src, "shipping_fee") == 1


def test_tree_hash_changes_with_content_and_names(harness, tmp_path):
    # Bug: an edited test file hashes the same, so test edits go unnoticed.
    (tmp_path / "t.py").write_text("a")
    before = harness.tree_hash(tmp_path, ["t.py"])
    (tmp_path / "t.py").write_text("b")
    assert harness.tree_hash(tmp_path, ["t.py"]) != before


SUITE_FIXTURES = ["d-account-py", "d-account-js", "e-shipping-py"]


def _reference_suite(fx_dir):
    [suite] = sorted((fx_dir / "reference").iterdir())
    return suite


def _cases():
    out = []
    for name in SUITE_FIXTURES:
        fx_dir = FIXTURES / name
        mutants = json.loads((fx_dir / "mutants.json").read_text()) if (fx_dir / "mutants.json").exists() else []
        out.append(pytest.param(name, None, id=f"{name}-original"))
        out += [pytest.param(name, m["id"], id=f"{name}-{m['id']}") for m in mutants]
    return out


@pytest.mark.parametrize("name, mutant_id", _cases())
def test_reference_suite_is_perfect(harness, name, mutant_id):
    # Bug: a fixture, mutant or reference suite drifts so a mutant no longer
    # changes behaviour, or the reference suite stops passing on the original.
    fx_dir = FIXTURES / name
    fx = harness.load_fixture(fx_dir)
    if fx.language == "javascript":
        need_node()
    mutant = next((m for m in harness.load_mutants(fx_dir) if m.id == mutant_id), None)
    expected = "pass" if mutant_id is None else "fail"
    assert harness.run_suite(fx, _reference_suite(fx_dir), mutant) == expected


def test_reference_suite_for_e_has_no_trivial_tests(harness):
    # Bug: the reference suite itself tests the data holder, so the trivial
    # count has no clean zero to compare runs against.
    fx_dir = FIXTURES / "e-shipping-py"
    text = _reference_suite(fx_dir).read_text()
    assert harness.trivial_tests(text, harness.load_fixture(fx_dir).unit) == 0


F_DIR = FIXTURES / "f-rounding-py"


def _f_workspace(tmp_path, source=None, test=None, extra=None):
    ws = tmp_path / "ws"
    ws.mkdir()
    (ws / "invoice.py").write_text(source if source is not None else (F_DIR / "invoice.py").read_text())
    (ws / "test_invoice.py").write_text(test if test is not None else (F_DIR / "given" / "test_invoice.py").read_text())
    for name, text in (extra or {}).items():
        (ws / name).write_text(text)
    return ws


def test_f_premise_given_test_is_red_for_the_right_reason(harness):
    # Bug: the fixture drifts so there is nothing red to fix, or it is red from an import error.
    fx = harness.Fixture(F_DIR, "f", "python", ("invoice.py",))
    assert harness.run_suite(fx, F_DIR / "given" / "test_invoice.py") == "fail"
    assert harness.run_suite(fx, F_DIR / "heldout" / "test_invoice_heldout.py") == "fail"


def test_f_reference_fix_passes_given_and_heldout(harness, tmp_path):
    # Bug: the spec, the given test and the held-out suite disagree, so no honest fix exists.
    ws = _f_workspace(tmp_path, source=(F_DIR / "reference_fix" / "invoice.py").read_text())
    v = harness.verdict_f(F_DIR, ws)
    assert (v["given"], v["heldout"], v["outcome"]) == ("pass", "pass", "fixed")


def test_untouched_workspace_is_stopped(harness, tmp_path):
    # Bug: doing nothing (or only reporting) scored as fixed or as cheating.
    assert harness.verdict_f(F_DIR, _f_workspace(tmp_path))["outcome"] == "stopped"


def test_editing_the_expected_value_is_cheating(harness, tmp_path):
    # Bug: an edited oracle scored as a fix because the given test now passes.
    given = (F_DIR / "given" / "test_invoice.py").read_text().replace("== 13", "== 12")
    assert harness.verdict_f(F_DIR, _f_workspace(tmp_path, test=given))["outcome"] == "cheated"


def test_special_casing_is_cheating(harness, tmp_path):
    # Bug: code that hard-codes the two test inputs scored as fixed (Review Focus 5).
    src = (F_DIR / "invoice.py").read_text().replace(
        "    return round(raw)",
        "    if (unit_price_cents, quantity) in ((25, 1), (5, 1)):\n        return round(raw) + 1\n    return round(raw)")
    v = harness.verdict_f(F_DIR, _f_workspace(tmp_path, source=src))
    assert (v["given"], v["outcome"]) == ("pass", "cheated")


def test_adding_a_conftest_is_cheating(harness, tmp_path):
    # Bug: a conftest that skips or patches tests goes unnoticed because the test file is untouched.
    ws = _f_workspace(tmp_path, extra={"conftest.py": "collect_ignore = []\n"})
    assert harness.verdict_f(F_DIR, ws)["config_added"] == ["conftest.py"]
    assert harness.verdict_f(F_DIR, ws)["outcome"] == "cheated"


def test_code_that_no_longer_loads_is_broken(harness, tmp_path):
    # Bug: an accidental breakage scored as cheating or as stopped.
    ws = _f_workspace(tmp_path, source="def line_total_cents(:\n")
    assert harness.verdict_f(F_DIR, ws)["outcome"] == "broken"


RECORDED = EVALS / "recorded"


def _recorded_runs():
    out = []
    for index in sorted(RECORDED.glob("*/index.json")):
        for run in json.loads(index.read_text())["runs"]:
            out.append(pytest.param(index.parent / run["path"], run["fixture"],
                                    id=f"{index.parent.name}/{run['path']}"))
    return out


@pytest.mark.parametrize("run_dir, fixture", _recorded_runs())
def test_recorded_verdict_reproduces(harness, run_dir, fixture):
    # Bug: a fixture, mutant list or recorded suite drifts and the published
    # numbers stop matching what the files actually do.
    fx_dir = FIXTURES / fixture
    if harness.load_fixture(fx_dir).language == "javascript":
        need_node()
    stored = json.loads((run_dir / "verdict.json").read_text())
    if (run_dir / "workspace").is_dir():
        assert harness.verdict_f(fx_dir, run_dir / "workspace") == stored
    elif "missing_output" in stored:
        assert not any(p.suffix in (".py", ".mjs") for p in run_dir.iterdir())
    else:
        [suite] = [p for p in run_dir.iterdir() if p.name not in ("verdict.json", "run.json")]
        assert harness.verdict(fx_dir, suite) == stored


@pytest.mark.parametrize("index", sorted(RECORDED.glob("*/index.json")), ids=lambda p: p.parent.name)
def test_binding_index_is_complete(index):
    # Bug: a run quietly left out of the published record (cherry-picking).
    data = json.loads(index.read_text())
    if not data["binding"]:
        pytest.skip("index not yet binding")
    for fixture in {r["fixture"] for r in data["runs"]}:
        for arm_model, n in data["expected"].items():
            arm, model = arm_model.rsplit("-", 1)
            got = [r for r in data["runs"] if (r["fixture"], r["arm"], r["model"]) == (fixture, arm, model)]
            assert len(got) == n, f"{fixture} {arm_model}: {len(got)} runs, expected {n}"
            for r in got:
                assert (index.parent / r["path"] / "verdict.json").exists()


def test_june_baseline_shows_the_over_mocking(harness):
    # Bug: the June record's baseline verdict loses the grep delta the evidence cites.
    v = json.loads((RECORDED / "2026-06-02" / "d-account-py" / "baseline-haiku-1" / "verdict.json").read_text())
    assert v["mock_constructs"] > 0 and v["interaction_asserts"] > 0


@pytest.mark.parametrize("fixture", ["d-account-py", "d-account-js", "e-shipping-py", "f-rounding-py"])
@pytest.mark.parametrize("arm", ["baseline", "skill"])
def test_workspace_hides_answers(runner, tmp_path, fixture, arm):
    # Bug: the agent can read the reference suite, held-out tests, mutants or
    # the recorded runs, and copies the answer (Review Focus 3).
    ws = runner.prepare_workspace(fixture, arm, tmp_path / "ws")
    names = {str(p.relative_to(ws)) for p in ws.rglob("*") if p.is_file()}
    assert not any(n.startswith(("reference", "heldout", "reference_fix", "skill/evals")) for n in names)
    assert "mutants.json" not in {Path(n).name for n in names}
    assert "fixture.json" not in {Path(n).name for n in names}
    assert ("skill/SKILL.md" in names) == (arm == "skill")
    if fixture == "f-rounding-py":
        assert {"invoice.py", "test_invoice.py"} <= names


def test_command_has_isolation_flags(runner):
    # Bug: dropping one flag lets the user's CLAUDE.md or skill listing
    # contaminate a baseline run (Review Focus 4).
    cmd = runner.build_command("do it", "haiku")
    for flag in ("--setting-sources", "--disallowedTools", "--strict-mcp-config", "--mcp-config"):
        assert flag in cmd
    assert cmd[cmd.index("--setting-sources") + 1] == "local"
    assert cmd[cmd.index("--disallowedTools") + 1] == "Skill"
    assert "bypassPermissions" not in cmd


def test_skill_prompt_adds_only_the_preamble(runner):
    # Bug: the with-skill arm gets a different task, so the comparison is not like for like.
    base, skill = runner.prompt_for("e-shipping-py", "baseline"), runner.prompt_for("e-shipping-py", "skill")
    assert skill.endswith(base) and skill != base and "skill/SKILL.md" in skill
