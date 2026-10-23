"""Scoring of skill loads from `claude -p --output-format stream-json` events.

Each sample under evals/triggering/samples/ is a hand-written session with a
known right answer; paths use /WS for the workspace and /PLUGIN for the plugin."""
from pathlib import Path

import pytest

SAMPLES = Path(__file__).resolve().parent.parent / "evals" / "triggering" / "samples"
PLUGIN_SKILLS = "/PLUGIN/skills"
WT = "writing-tests-that-can-fail"


def events(trigger, name):
    lines = (SAMPLES / f"{name}.jsonl").read_text(encoding="utf-8").splitlines()
    return trigger.parse_events(lines, PLUGIN_SKILLS)


def outcome(trigger, name, skill=WT, kind="should", capped=False):
    return trigger.classify(events(trigger, name), skill, kind, capped)


def test_skill_call_with_plugin_prefix_is_a_load(trigger):
    assert outcome(trigger, "skill_prefixed_load") == "hit"


def test_load_of_another_skill_is_not_a_load(trigger):
    assert outcome(trigger, "optimizer_load", skill="skill-optimizer") == "miss"
    assert outcome(trigger, "optimizer_load", skill="subagent-optimizer") == "hit"


def test_read_of_plugin_skill_md_is_a_load(trigger):
    assert outcome(trigger, "read_plugin_skill_md") == "hit"


def test_read_of_fixture_skill_md_is_not_a_load(trigger):
    assert outcome(trigger, "read_fixture_skill_md", skill="skill-optimizer") == "miss"


def test_test_write_before_load_is_a_miss(trigger):
    assert outcome(trigger, "test_write_before_load") == "miss"


def test_bash_heredoc_into_test_path_is_a_test_write(trigger):
    assert outcome(trigger, "bash_heredoc_test_write") == "miss"


def test_no_test_work_and_no_load_is_na(trigger):
    assert outcome(trigger, "no_test_work") == "n/a"


def test_capped_before_either_event_is_inconclusive(trigger):
    assert outcome(trigger, "capped", capped=True) == "inconclusive"


def test_max_turns_result_is_not_an_error_event(trigger):
    assert not [e for e in events(trigger, "capped") if e.kind == "error"]


def test_near_miss_load_is_false_load(trigger):
    assert outcome(trigger, "skill_prefixed_load", kind="near") == "false-load"


def test_near_miss_without_load_is_no_load(trigger):
    assert outcome(trigger, "no_test_work", kind="near") == "no-load"


def test_subagent_load_does_not_count_as_main_thread_hit(trigger):
    evs = events(trigger, "subagent_load_then_main_write")
    assert any(e.kind == "skill" and e.subagent for e in evs)
    assert trigger.classify(evs, WT, "should", False) == "miss"


def test_delegate_brief_naming_skill_is_a_hit(trigger):
    assert outcome(trigger, "delegate_names_skill", kind="delegate") == "hit"


def test_delegate_brief_without_skill_is_a_miss(trigger):
    assert outcome(trigger, "delegate_without_skill", kind="delegate") == "miss"


def test_delegate_prompt_without_delegation_is_na(trigger):
    assert outcome(trigger, "no_test_work", kind="delegate") == "n/a"


def test_rate_limit_error_is_invalid(trigger):
    assert outcome(trigger, "rate_limit") == "invalid"


def test_result_cost_is_kept(trigger):
    result = [e for e in events(trigger, "skill_prefixed_load") if e.kind == "result"]
    assert [float(e.text) for e in result] == [0.1]


def test_should_stop_at_first_load_or_test_write(trigger):
    evs = events(trigger, "no_test_work")
    assert not trigger.should_stop(evs, WT, "should")
    load_only = events(trigger, "skill_prefixed_load")[:1]
    assert [e.kind for e in load_only] == ["skill"]
    assert trigger.should_stop(load_only, WT, "should")
    assert trigger.should_stop(events(trigger, "optimizer_load"), "subagent-optimizer", "should")
    assert trigger.should_stop(events(trigger, "bash_heredoc_test_write")[:2], WT, "should")


def test_delegate_prompt_stops_at_the_hand_off(trigger):
    # Bug caught: the delegate prompt running to the turn cap because should_stop ignores hand-offs.
    assert trigger.should_stop(events(trigger, "delegate_without_skill"), WT, "delegate")


def test_bash_cat_of_plugin_skill_md_is_a_load(trigger):
    # Bug caught: dropping the Bash `cat` load path, so a skill read through cat scores as no load.
    assert outcome(trigger, "bash_cat_plugin_skill_md") == "hit"


def test_bash_cat_of_fixture_skill_md_is_not_a_load(trigger):
    # Bug caught: matching any .../skills/<name>/SKILL.md on the Bash path, not only the plugin's.
    assert outcome(trigger, "bash_cat_fixture_skill_md", skill="skill-optimizer") == "miss"


def test_near_miss_never_stops_early(trigger):
    assert not trigger.should_stop(events(trigger, "skill_prefixed_load"), WT, "near")


@pytest.mark.parametrize("path", [
    "/WS/tests/test_pricing.py", "tests/conftest.py", "/WS/test/cart.js", "src/__tests__/a.js",
    "spec/models/user_spec.rb", "/WS/test_pricing.py", "pkg/pricing_test.py", "pkg/pricing_test.go",
    "cart.test.js", "cart.test.ts", "cart.test.tsx", "cart.test.mjs", "cart.spec.ts", "cart.spec.jsx",
    "src/PricingTest.java", "src/PricingTest.kt", "Sources/PricingTests.swift",
])
def test_is_test_path(trigger, path):
    assert trigger.is_test_path(path)


@pytest.mark.parametrize("path", [
    "src/testing_utils.py", "docs/test-plan.md", "contest.py", "/WS/pricing.py", "latest.py", "/dev/null",
])
def test_is_not_test_path(trigger, path):
    assert not trigger.is_test_path(path)
