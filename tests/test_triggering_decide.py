"""Pre-registered decision rules over trigger-eval verdict records."""
import json
from pathlib import Path

import pytest

CRITERIA = Path(__file__).resolve().parent.parent / "evals" / "triggering" / "criteria.json"
WT = "writing-tests-that-can-fail"


@pytest.fixture
def crit():
    return json.loads(CRITERIA.read_text(encoding="utf-8"))


def rec(pid, outcome, arm="current", model="opus", half="heldout", kind="should", skill=WT, rep=0):
    return {"prompt_id": pid, "skill": skill, "kind": kind, "half": half, "arm": arm,
            "model": model, "rep": rep, "outcome": outcome}


def reps(pid, outcomes, **kw):
    return [rec(pid, o, rep=i, **kw) for i, o in enumerate(outcomes)]


def test_criteria_values_are_the_registered_ones(crit):
    assert crit == {"reps": 3, "near_reps_candidate": 5, "gap_min_prompts": 3, "gap_miss_reps": 2,
                    "ship_net_improved": 3, "ship_pooled_hits": 6, "near_false_opus": 0,
                    "near_false_total": 1, "decision_model": "opus"}


def test_gap_needs_three_prompts_missing_two_of_three(decide, crit):
    two = reps("p1", ["miss", "miss", "hit"]) + reps("p2", ["miss", "miss", "miss"]) + reps("p3", ["miss", "hit", "hit"])
    assert decide.gap(two, WT, crit=crit) == {"gap": False, "prompts": ["p1", "p2"]}
    three = two + reps("p4", ["hit", "miss", "miss"])
    assert decide.gap(three, WT, crit=crit) == {"gap": True, "prompts": ["p1", "p2", "p4"]}


def test_gap_ignores_dev_half_and_screen_model(decide, crit):
    rs = []
    for p in ("a", "b", "c"):
        rs += reps(p, ["miss"] * 3, half="dev") + reps(p + "s", ["miss"] * 3, model="sonnet")
    assert decide.gap(rs, WT, crit=crit)["gap"] is False


def test_gap_counts_delegate_prompts(decide, crit):
    rs = reps("a", ["miss"] * 3) + reps("b", ["miss"] * 3) + reps("c", ["miss"] * 3, kind="delegate")
    assert decide.gap(rs, WT, crit=crit)["gap"] is True


def test_gap_excludes_invalid_and_na_from_reps(decide, crit):
    rs = reps("a", ["miss", "miss", "invalid"]) + reps("b", ["miss", "hit", "n/a"])
    assert decide.gap(rs, WT, crit=crit)["prompts"] == ["a"]


def test_gap_only_looks_at_the_named_skill_and_arm(decide, crit):
    rs = []
    for p in ("a", "b", "c"):
        rs += reps(p, ["miss"] * 3, skill="skill-optimizer") + reps(p, ["miss"] * 3, arm="current+snippet")
    assert decide.gap(rs, WT, crit=crit)["gap"] is False


def paired(new_hits, old_hits, **kw):
    """One held-out prompt per pair; new_hits/old_hits of 3 reps each."""
    rs = []
    for i, (n, o) in enumerate(zip(new_hits, old_hits)):
        rs += reps(f"p{i}", ["hit"] * n + ["miss"] * (3 - n), arm="candidate", **kw)
        rs += reps(f"p{i}", ["hit"] * o + ["miss"] * (3 - o), arm="current", **kw)
    return rs


def test_ship_requires_both_thresholds(decide, crit):
    # net +3, pooled +5
    low = paired([2, 2, 2, 1], [0, 0, 1, 1])
    out = decide.ship(low, WT, "candidate", "current", crit)
    assert (out["net_improved"], out["pooled_delta"], out["ship"]) == (3, 5, False)
    # net +3, pooled +6
    ok = paired([2, 2, 3, 1], [0, 0, 1, 1])
    out = decide.ship(ok, WT, "candidate", "current", crit)
    assert (out["net_improved"], out["pooled_delta"], out["ship"]) == (3, 6, True)


def test_ship_needs_net_improved_prompts_not_just_pooled_hits(decide, crit):
    # pooled +6 from two prompts only: net +2
    out = decide.ship(paired([3, 3, 1], [0, 0, 1]), WT, "candidate", "current", crit)
    assert (out["net_improved"], out["pooled_delta"], out["ship"]) == (2, 6, False)


def test_regressed_prompt_reduces_net_improved(decide, crit):
    out = decide.ship(paired([3, 3, 2, 2, 0], [1, 1, 0, 0, 1]), WT, "candidate", "current", crit)
    assert out["net_improved"] == 3


def test_ship_uses_decision_model_only(decide, crit):
    rs = paired([3, 3, 3, 3], [0, 0, 0, 0], model="sonnet")
    assert decide.ship(rs, WT, "candidate", "current", crit)["ship"] is False


ok_pairs = [3, 3, 3, 3], [0, 0, 0, 0]


def test_ship_blocked_by_one_opus_false_load(decide, crit):
    rs = paired(*ok_pairs) + [rec("n1", "false-load", arm="candidate", kind="near")]
    out = decide.ship(rs, WT, "candidate", "current", crit)
    assert (out["near_false_opus"], out["ship"]) == (1, False)


def test_ship_allows_one_sonnet_false_load_but_not_two(decide, crit):
    one = paired(*ok_pairs) + [rec("n1", "false-load", arm="candidate", kind="near", model="sonnet")]
    assert decide.ship(one, WT, "candidate", "current", crit)["ship"] is True
    two = one + [rec("n2", "false-load", arm="candidate", kind="near", model="sonnet")]
    assert decide.ship(two, WT, "candidate", "current", crit)["ship"] is False


def test_near_false_loads_on_dev_half_do_not_count(decide, crit):
    rs = paired(*ok_pairs) + [rec("n1", "false-load", arm="candidate", kind="near", half="dev")]
    assert decide.ship(rs, WT, "candidate", "current", crit)["ship"] is True


def test_relative_near_rule_allows_false_loads_the_old_arm_already_had(decide, crit):
    old_fl = [rec("n1", "false-load", arm="current", kind="near")]
    new_fl = [rec("n1", "false-load", arm="candidate", kind="near")]
    rs = paired(*ok_pairs) + old_fl + new_fl
    assert decide.ship(rs, WT, "candidate", "current", crit)["ship"] is False
    assert decide.ship(rs, WT, "candidate", "current", crit, relative_near=True)["ship"] is True
    rise = rs + [rec("n2", "false-load", arm="candidate", kind="near")]
    assert decide.ship(rise, WT, "candidate", "current", crit, relative_near=True)["ship"] is False


def test_report_snippet_only_for_writing_tests(decide, crit):
    rs = paired([3, 3, 3, 3], [0, 0, 0, 0])
    for r in rs:
        if r["arm"] == "candidate":
            r["arm"] = "current+snippet"
    # the lure already loads the skill without the snippet: no rise, so the claim stands
    rs += [rec("n1", "false-load", arm="current", kind="near"),
           rec("n1", "false-load", arm="current+snippet", kind="near")]
    out = decide.report(rs, crit)
    assert set(out) == {WT, "skill-optimizer", "subagent-optimizer"}
    assert out[WT]["snippet"]["ship"] is True
    assert "snippet" not in out["skill-optimizer"]


def test_report_adds_phase2_keys_only_when_those_arms_ran(decide, crit):
    out = decide.report(paired([3, 3, 3, 3], [0, 0, 0, 0]), crit)
    assert "candidate" in out[WT] and "snippet" not in out[WT] and "snippet2" not in out[WT]
    assert out[WT]["candidate"]["ship"] is True
    assert "candidate" not in out["skill-optimizer"]


def test_snippet2_counts_fresh_near_false_loads_relative_to_current(decide, crit):
    rs = paired([3, 3, 3, 3], [0, 0, 0, 0])
    for r in rs:
        if r["arm"] == "candidate":
            r["arm"] = "current+snippet2"
    assert decide.report(rs, crit)[WT]["snippet2"]["ship"] is True
    fresh = rs + [rec("f1", "false-load", arm="current+snippet2", kind="near", half="fresh")]
    out = decide.report(fresh, crit)[WT]["snippet2"]
    assert out["ship"] is False and out["near_false_opus"] == 1
    both = fresh + [rec("f1", "false-load", arm="current", kind="near", half="fresh")]
    assert decide.report(both, crit)[WT]["snippet2"]["ship"] is True
