"""Guards on the measurement harness. Each test names the bug it catches.

These never launch an agent: every case fails validation before `claude` runs.
"""
import subprocess
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "skills" / "agent-optimiser" / "evals" / "measure" / "measure.sh"


def run(*args, **kw):
    return subprocess.run([str(SCRIPT), *args], capture_output=True, text=True, **kw)


def test_wrong_argument_count_is_usage_error():
    # Bug caught: `set -u` alone aborts with a bash error instead of a usage line.
    r = run("only-one")
    assert r.returncode == 2 and "usage:" in r.stderr


def test_label_cannot_traverse_directories(tmp_path):
    # Bug caught: an unvalidated label lands in `out/<label>.json` and can escape the output dir.
    agent = tmp_path / "a.md"
    agent.write_text("---\nname: a\ndescription: d\n---\nbody\n")
    for bad in ("../escape", "a/b", ".hidden", "sp ace", ""):
        r = run(bad, str(agent), str(tmp_path), "task")
        assert r.returncode == 2, bad
        assert "label" in r.stderr, bad


def test_missing_agent_file_and_task_dir_are_rejected(tmp_path):
    # Bug caught: passing a nonexistent path through to the agent invocation.
    agent = tmp_path / "a.md"
    agent.write_text("---\nname: a\ndescription: d\n---\nbody\n")
    r = run("ok", str(tmp_path / "missing.md"), str(tmp_path), "task")
    assert r.returncode == 2 and "no such agent file" in r.stderr
    r = run("ok", str(agent), str(tmp_path / "missing-dir"), "task")
    assert r.returncode == 2 and "no such task directory" in r.stderr


def test_script_does_not_bypass_permissions():
    # Bug caught: reintroducing --dangerously-skip-permissions, which Socket flagged.
    text = SCRIPT.read_text()
    assert "--dangerously-skip-permissions" not in text
    assert "--permission-mode acceptEdits" in text


def test_summary_path_is_passed_in_not_interpolated():
    # Bug caught: a shell expansion inside the quoted heredoc, which never expands,
    # so the summary was written to a literal "${MEASURE_DIR...}" path.
    text = SCRIPT.read_text()
    heredoc = text.split("<<'PY'", 1)[1]
    assert "MEASURE_DIR" not in heredoc
    assert 'measure_dir = sys.argv[1], sys.argv[2], sys.argv[3]'.split("=")[1].strip() in heredoc
