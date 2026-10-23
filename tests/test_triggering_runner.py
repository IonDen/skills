"""The trigger-eval runner: session command, run matrix, budget, resume, records."""
import json
import os
import signal
import subprocess
import sys
import time
from collections import defaultdict
from pathlib import Path

import pytest

WT, SO = "writing-tests-that-can-fail", "subagent-optimizer"
TRIGGER_DIR = Path(__file__).resolve().parent.parent / "evals" / "triggering"


def toy_prompts():
    def p(pid, skill, kind, half, fixture="wt-pricing-py"):
        return {"id": pid, "skill": skill, "kind": kind, "half": half, "fixture": fixture, "text": f"do {pid}", "control": False}
    return [p("a", WT, "should", "dev"), p("b", WT, "should", "heldout"), p("c", WT, "near", "heldout"),
            p("d", SO, "should", "heldout", "opt-claude"), p("f", WT, "near", "fresh")]


def test_command_has_isolation_flags(trigger_runner, tmp_path):
    cmd = trigger_runner.build_command("hello", "sonnet", [tmp_path / "p1", tmp_path / "p2"], 1.5)
    joined = " ".join(cmd)
    assert cmd[:3] == ["claude", "-p", "hello"]
    assert cmd[cmd.index("--model") + 1] == "sonnet"
    for flag in ("--output-format stream-json", "--verbose", "--setting-sources project,local",
                 '--strict-mcp-config --mcp-config {"mcpServers":{}}',
                 "--max-budget-usd 1.5", "--no-session-persistence", "--permission-mode acceptEdits",
                 f"--plugin-dir {tmp_path / 'p1'} --plugin-dir {tmp_path / 'p2'}"):
        assert flag in joined, flag
    assert "--disallowedTools" not in cmd and "--disallowed-tools" not in cmd
    assert "--output-format json" not in joined
    assert cmd[cmd.index("--max-turns") + 1] == str(trigger_runner.TURN_CAP)


def test_matrix_phase1_counts(trigger_runner):
    cells = trigger_runner.matrix(1, toy_prompts())
    by = defaultdict(int)
    for c in cells:
        by[(c.model, c.prompt_id, c.arm)] += 1
    assert len(cells) == 42
    assert by[("sonnet", "a", "current+snippet")] == 3 and by[("sonnet", "d", "current")] == 3
    assert ("opus", "a", "current") not in by  # dev prompts are screened on sonnet only
    assert by[("opus", "b", "current-crowded")] == 3
    crowded = {(c.model, c.prompt_id) for c in cells if c.arm == "current-crowded"}
    assert crowded == {("opus", "b"), ("opus", "c")}
    assert not [c for c in cells if c.prompt_id == "d" and c.arm != "current"]


def test_matrix_phase1_skips_fresh_prompts(trigger_runner):
    assert "f" not in {c.prompt_id for c in trigger_runner.matrix(1, toy_prompts())}


def phase2(trigger_runner, gaps):
    by = defaultdict(int)
    for c in trigger_runner.matrix(2, toy_prompts(), gaps=gaps):
        assert c.model == "opus"
        by[(c.prompt_id, c.arm)] += 1
    return dict(by)


def test_matrix_phase2_runs_candidate_for_gap_skills_and_snippet2_for_writing_tests(trigger_runner):
    assert phase2(trigger_runner, {WT}) == {
        ("b", "current"): 3, ("b", "candidate"): 3, ("b", "current+snippet2"): 3,
        ("c", "current"): 5, ("c", "candidate"): 5, ("c", "current+snippet2"): 5,
        ("f", "current"): 5, ("f", "current+snippet2"): 5}


def test_matrix_phase2_without_a_gap_still_measures_snippet2(trigger_runner):
    assert phase2(trigger_runner, set()) == {
        ("b", "current"): 3, ("b", "current+snippet2"): 3, ("c", "current"): 5, ("c", "current+snippet2"): 5,
        ("f", "current"): 5, ("f", "current+snippet2"): 5}


def test_matrix_phase2_optimizer_gap_gets_no_snippet(trigger_runner):
    by = phase2(trigger_runner, {SO})
    assert by[("d", "current")] == 3 and by[("d", "candidate")] == 3
    assert ("b", "candidate") not in by


def test_matrix_keeps_arms_of_a_group_adjacent(trigger_runner):
    cells = trigger_runner.matrix(1, toy_prompts())
    seen, last = set(), None
    for c in cells:
        g = (c.model, c.prompt_id, c.rep)
        if g != last:
            assert g not in seen, g
            seen.add(g)
            last = g


def test_estimate_sums_session_prices(trigger_runner):
    cells = [trigger_runner.Cell("a", "current", "opus", 0), trigger_runner.Cell("a", "current", "sonnet", 0)]
    assert trigger_runner.estimate(cells, {"opus": 0.3, "sonnet": 0.1}) == pytest.approx(0.4)


def fake_launch(cost=0.25, load_for=(), error_first=0, extra_turns=0):
    """A stand-in for `claude -p`: emits init, optionally a Skill load and `extra_turns` more assistant
    turns, then a result with `cost`. Like the real launcher it feeds each line to `stop` and quits
    when told to, so a stopped session never reports its cost. `true_cost` sums what every session
    would have cost, reported or not."""
    calls, consumed = [], []

    def launch(cmd, cwd, stop, timeout):
        text = cmd[2]
        calls.append(text)
        launch.true_cost += cost
        lines = [json.dumps({"type": "system", "subtype": "init", "model": "claude-opus-5-5", "cwd": str(cwd)})]
        if any(f"do {pid}" == text for pid in load_for):
            lines.append(json.dumps({"type": "assistant", "parent_tool_use_id": None, "message": {"content": [
                {"type": "tool_use", "id": "t1", "name": "Skill", "input": {"skill": f"ionden-skills:{WT}"}}]}}))
        lines += [json.dumps({"type": "assistant", "parent_tool_use_id": None, "message": {"content": [
            {"type": "text", "text": "thinking"}]}})] * extra_turns
        if len(calls) <= error_first:
            lines.append(json.dumps({"type": "result", "subtype": "success", "is_error": True, "total_cost_usd": cost,
                                     "result": "API Error: 429 rate_limit_error"}))
        else:
            lines.append(json.dumps({"type": "result", "subtype": "success", "is_error": False, "total_cost_usd": cost}))
        out = []
        for line in lines:
            out.append(line + "\n")
            if stop(out):
                consumed.append(len(out))
                return out, True
        consumed.append(len(out))
        return out, False
    launch.calls, launch.consumed, launch.true_cost = calls, consumed, 0.0
    return launch


def silent_launch(cmd, cwd, stop, timeout):
    """`claude` exiting before it prints anything (logged out, bad flag)."""
    return [], False


def records(out):
    f = out / "verdicts.jsonl"
    return [json.loads(l) for l in f.read_text().splitlines()] if f.exists() else []


def test_refuses_when_estimate_over_cap(trigger_runner, tmp_path):
    launch = fake_launch()
    with pytest.raises(SystemExit):
        trigger_runner.run_phase(1, cap=1.0, out=tmp_path, prompts=toy_prompts(), launch_fn=launch,
                                 prices={"opus": 0.3, "sonnet": 0.15}, cli_version="test")
    assert launch.calls == [] and records(tmp_path) == []


def test_run_records_one_verdict_per_cell(trigger_runner, tmp_path):
    launch = fake_launch(cost=0.01, load_for=("b",))
    trigger_runner.run_phase(1, cap=100, out=tmp_path, prompts=toy_prompts(), launch_fn=launch,
                             prices={"opus": 0.3, "sonnet": 0.15}, cli_version="test")
    rs = records(tmp_path)
    assert len(rs) == 42
    b = [r for r in rs if r["prompt_id"] == "b"]
    assert {r["outcome"] for r in b} == {"hit"} and {r["load_via"] for r in b} == {"skill"}
    assert {r["outcome"] for r in rs if r["prompt_id"] == "c"} == {"no-load"}
    assert {r["outcome"] for r in rs if r["prompt_id"] == "d"} == {"miss"}
    assert {r["resolved_model"] for r in rs} == {"claude-opus-5-5"} and {r["cli_version"] for r in rs} == {"test"}


@pytest.mark.parametrize("cap", [5.8, 11.8])  # runs out during the sonnet sessions / at the first opus group
def test_budget_stop_never_splits_a_prompt_group(trigger_runner, tmp_path, cap):
    launch = fake_launch(cost=0.5)
    # sessions really cost 0.5, five times the price list: the runner must budget from what it observes
    trigger_runner.run_phase(1, cap=cap, out=tmp_path, prompts=toy_prompts(), launch_fn=launch,
                             prices={"opus": 0.1, "sonnet": 0.1}, cli_version="test")
    rs = records(tmp_path)
    assert 0 < len(rs) < 42
    assert sum(r["cost_usd"] for r in rs) <= cap
    expected = defaultdict(set)
    for c in trigger_runner.matrix(1, toy_prompts()):
        expected[(c.model, c.prompt_id, c.rep)].add(c.arm)
    got = defaultdict(set)
    for r in rs:
        got[(r["model"], r["prompt_id"], r["rep"])].add(r["arm"])
    for g, arms in got.items():
        assert arms == expected[g], g


def test_resume_skips_recorded_cells(trigger_runner, tmp_path):
    kw = dict(out=tmp_path, prompts=toy_prompts(), prices={"opus": 0.01, "sonnet": 0.01}, cli_version="test")
    trigger_runner.run_phase(1, cap=2.0, launch_fn=fake_launch(cost=0.2), **kw)
    first = len(records(tmp_path))
    second = fake_launch(cost=0.2)
    trigger_runner.run_phase(1, cap=100, launch_fn=second, **kw)
    assert len(second.calls) == 42 - first
    assert len(records(tmp_path)) == 42
    assert len({(r["model"], r["prompt_id"], r["arm"], r["rep"]) for r in records(tmp_path)}) == 42


def test_invalid_cells_are_requeued(trigger_runner, tmp_path):
    launch = fake_launch(cost=0.01, error_first=2)
    one = [toy_prompts()[3]]
    trigger_runner.run_phase(1, cap=100, out=tmp_path, prompts=one, launch_fn=launch,
                             prices={"opus": 0.1, "sonnet": 0.1}, cli_version="test")
    rs = records(tmp_path)
    assert [r["outcome"] for r in rs][:3] == ["invalid", "invalid", "miss"]
    assert len([r for r in rs if r["outcome"] != "invalid"]) == 6  # 3 sonnet + 3 opus cells


def test_cell_gives_up_after_three_invalid_attempts(trigger_runner, tmp_path):
    launch = fake_launch(cost=0.01, error_first=3)
    one = [dict(toy_prompts()[3], half="dev")]  # three sonnet cells
    trigger_runner.run_phase(1, cap=100, out=tmp_path, prompts=one, launch_fn=launch,
                             prices={"opus": 0.1, "sonnet": 0.1}, cli_version="test")
    assert len(launch.calls) == 5
    assert [r["outcome"] for r in records(tmp_path)] == ["invalid"] * 3 + ["miss"] * 2
    again = fake_launch(cost=0.01)
    trigger_runner.run_phase(1, cap=100, out=tmp_path, prompts=one, launch_fn=again,
                             prices={"opus": 0.1, "sonnet": 0.1}, cli_version="test")
    assert again.calls == []


def test_run_aborts_after_five_invalid_sessions_in_a_row(trigger_runner, tmp_path):
    # Bug caught: a usage-limit outage retiring every remaining cell as invalid x3 with exit code 0.
    launch = fake_launch(cost=0.01, error_first=99)
    rc = trigger_runner.run_phase(1, cap=100, out=tmp_path, prompts=toy_prompts(), launch_fn=launch,
                                  prices={"opus": 0.1, "sonnet": 0.1}, cli_version="test")
    assert rc == 1 and len(launch.calls) == 5


def test_resume_retries_a_cell_recorded_only_as_invalid(trigger_runner, tmp_path):
    # Bug caught: resume treating any recorded cell as done, so an interrupted retry is never made.
    one = [dict(toy_prompts()[3], half="dev")]
    kw = dict(out=tmp_path, prompts=one, prices={"opus": 0.1, "sonnet": 0.1}, cli_version="test")
    trigger_runner.run_phase(1, cap=100, launch_fn=fake_launch(cost=0.01, error_first=1), **kw)
    with (tmp_path / "verdicts.jsonl").open() as f:
        kept = [l for l in f if json.loads(l)["rep"] != 0 or json.loads(l)["outcome"] == "invalid"]
    (tmp_path / "verdicts.jsonl").write_text("".join(kept))  # as if stopped right after rep 0's first try
    again = fake_launch(cost=0.01)
    trigger_runner.run_phase(1, cap=100, launch_fn=again, **kw)
    assert len(again.calls) == 1
    assert [r["outcome"] for r in records(tmp_path) if r["rep"] == 0] == ["invalid", "miss"]


def test_session_with_no_output_is_invalid(trigger_runner):
    # Bug caught: a CLI that dies before printing anything recorded as inconclusive and never retried.
    rec = trigger_runner.run_cell(trigger_runner.Cell("d", "current", "sonnet", 0), toy_prompts()[3],
                                  silent_launch, [], [], "test")
    assert rec["outcome"] == "invalid"


def test_session_ending_on_the_turn_cap_is_inconclusive(trigger_runner):
    def capped(cmd, cwd, stop, timeout):
        return [json.dumps({"type": "result", "subtype": "error_max_turns", "is_error": True,
                            "total_cost_usd": 0.4}) + "\n"], False
    rec = trigger_runner.run_cell(trigger_runner.Cell("d", "current", "sonnet", 0), toy_prompts()[3],
                                  capped, [], [], "test")
    assert rec["outcome"] == "inconclusive"


def test_run_cell_stops_the_session_at_the_load(trigger_runner):
    # Bug caught: run_cell's stop callback never firing, so every session runs to the turn cap.
    launch = fake_launch(cost=0.01, load_for=("b",), extra_turns=5)
    rec = trigger_runner.run_cell(trigger_runner.Cell("b", "current", "opus", 0), toy_prompts()[1],
                                  launch, [], [], "test")
    assert launch.consumed == [2]  # init, then the Skill call
    assert rec["outcome"] == "hit" and rec["cost_usd"] == 0


def test_sessions_stopped_early_still_count_against_the_cap(trigger_runner, tmp_path):
    # Bug caught: early-stopped sessions report no cost, so the cap never trips however many run.
    prompts = [dict(toy_prompts()[3], half="heldout"), toy_prompts()[1]]  # SO reports its cost; WT b stops early
    launch = fake_launch(cost=0.5, load_for=("b",))
    trigger_runner.run_phase(1, cap=3.0, out=tmp_path, prompts=prompts, launch_fn=launch,
                             prices={"opus": 0.1, "sonnet": 0.1}, cli_version="test")
    assert launch.true_cost <= 3.0


def test_retries_are_checked_against_the_cap(trigger_runner, tmp_path):
    # Bug caught: the cap checked once per group, so three invalid tries of one cell can pass it.
    launch = fake_launch(cost=0.3, error_first=99)
    one = [dict(toy_prompts()[3], half="dev")]
    trigger_runner.run_phase(1, cap=0.5, out=tmp_path, prompts=one, launch_fn=launch,
                             prices={"opus": 0.1, "sonnet": 0.1}, cli_version="test")
    assert launch.true_cost <= 0.5


def test_record_has_no_paths_or_text(trigger_runner, tmp_path):
    trigger_runner.run_phase(1, cap=100, out=tmp_path, prompts=toy_prompts()[:1], launch_fn=fake_launch(cost=0.01),
                             prices={"opus": 0.1, "sonnet": 0.1}, cli_version="test")
    assert trigger_runner.scrub_problems(tmp_path) == []
    text = (tmp_path / "verdicts.jsonl").read_text()
    assert "do a" not in text
    assert set(json.loads(text.splitlines()[0])) == {
        "prompt_id", "skill", "kind", "half", "arm", "model", "resolved_model", "rep", "outcome", "load_turn",
        "first_test_write_turn", "load_via", "cost_usd", "cli_version", "crowd", "date"}


def test_scrub_problems_finds_local_paths(trigger_runner, tmp_path):
    (tmp_path / "a.jsonl").write_text('{"x": "/Users/someone/x"}\n')
    (tmp_path / "b.txt").write_text("cwd /private/var/folders/x\n")
    assert len(trigger_runner.scrub_problems(tmp_path)) == 2


def test_candidate_arm_applies_candidate_description(trigger_runner, tmp_path):
    cand = tmp_path / "candidates"
    cand.mkdir()
    (cand / f"{WT}.md").write_text("Use when testing new candidate wording for the eval.\n")
    dirs = trigger_runner.plugin_dirs("candidate", tmp_path / "work", [], candidates=cand)
    md = (dirs[0] / "skills" / WT / "SKILL.md").read_text()
    orig = (trigger_runner.PLUGIN / "skills" / WT / "SKILL.md").read_text()
    assert trigger_runner.description_of(md) == "Use when testing new candidate wording for the eval."
    assert md.split("\n---\n", 1)[1] == orig.split("\n---\n", 1)[1]  # body untouched
    assert "metadata:" in md.split("\n---\n", 1)[0]
    other = (dirs[0] / "skills" / SO / "SKILL.md").read_text()
    assert other == (trigger_runner.PLUGIN / "skills" / SO / "SKILL.md").read_text()


def test_current_arm_uses_the_repo_plugin(trigger_runner, tmp_path):
    assert trigger_runner.plugin_dirs("current+snippet", tmp_path, [tmp_path / "x"]) == [trigger_runner.PLUGIN]


def test_crowded_arm_adds_competitors_and_filler(trigger_runner, tmp_path):
    crowd = [tmp_path / "superpowers"]
    dirs = trigger_runner.plugin_dirs("current-crowded", tmp_path / "work", crowd)
    assert dirs[:2] == [trigger_runner.PLUGIN, crowd[0]]
    assert len(list((dirs[2] / "skills").glob("*/SKILL.md"))) == 60


def test_filler_plugin_is_deterministic(trigger_runner, tmp_path):
    a = trigger_runner.make_filler_plugin(tmp_path / "a", 5)
    b = trigger_runner.make_filler_plugin(tmp_path / "b", 5)
    files = sorted(p.relative_to(a) for p in a.rglob("*") if p.is_file())
    assert files == sorted(p.relative_to(b) for p in b.rglob("*") if p.is_file())
    assert all((a / f).read_text() == (b / f).read_text() for f in files)
    assert (a / ".claude-plugin" / "plugin.json").exists()


GRANDCHILD = (  # a session that starts a tool process which ignores SIGTERM, then keeps printing
    "import subprocess, sys, time\n"
    "g = subprocess.Popen([sys.executable, '-c', 'import signal, time\\n"
    "signal.signal(signal.SIGTERM, signal.SIG_IGN)\\nprint(1, flush=True)\\ntime.sleep(300)'],\n"
    "                     stdout=subprocess.PIPE)\n"
    "g.stdout.readline()\n"  # wait until it ignores SIGTERM
    "print(g.pid, flush=True)\n"
    "while True:\n    print('x', flush=True)\n    time.sleep(0.01)\n")


def gone(pid, within=5.0):
    end = time.monotonic() + within
    while time.monotonic() < end:
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return True
        time.sleep(0.05)
    return False


def test_launch_kills_the_whole_group_on_stop(trigger_runner, tmp_path):
    # Bug caught: escalation ending once the session process exits, leaving its tool processes running.
    lines, stopped = trigger_runner.launch([sys.executable, "-c", GRANDCHILD], tmp_path,
                                           lambda ls: len(ls) >= 3, timeout=20)
    assert stopped is True and len(lines) == 3
    assert gone(int(lines[0]))


def test_launch_stops_at_timeout(trigger_runner, tmp_path):
    cmd = [sys.executable, "-c", "import time\nprint('x', flush=True)\ntime.sleep(30)"]
    started = time.monotonic()
    lines, stopped = trigger_runner.launch(cmd, tmp_path, lambda ls: False, timeout=1)
    assert stopped is False and lines == ["x\n"]
    assert time.monotonic() - started < 10


def test_sigterm_to_the_runner_kills_the_running_session(tmp_path):
    # Bug caught: `kill <runner>` exiting without the finally, leaving `claude -p` running and spending.
    pidfile = tmp_path / "session.pid"
    session = f"import os, time\nopen({str(pidfile)!r}, 'w').write(str(os.getpid()))\ntime.sleep(300)\n"
    script = (f"import sys\nsys.path.insert(0, {str(TRIGGER_DIR)!r})\nimport run_trigger\n"
              "run_trigger.install_stop_handlers()\n"
              f"run_trigger.launch([sys.executable, '-c', {session!r}], {str(tmp_path)!r}, lambda ls: False, 60)\n")
    runner = subprocess.Popen([sys.executable, "-c", script])
    end = time.monotonic() + 10
    while not pidfile.exists() and time.monotonic() < end:
        time.sleep(0.05)
    session_pid = int(pidfile.read_text())
    runner.send_signal(signal.SIGTERM)
    runner.wait(timeout=15)
    assert gone(session_pid)
