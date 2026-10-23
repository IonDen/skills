"""Recorded trigger-eval runs: complete, free of local paths, and the stored
decision follows from the stored verdicts."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TRIG = ROOT / "evals" / "triggering"
RECORDED = TRIG / "recorded"


def index():
    return json.loads((TRIG / "index.json").read_text(encoding="utf-8"))


def verdicts(folder):
    return [json.loads(l) for l in (RECORDED / folder / "verdicts.jsonl").read_text(encoding="utf-8").splitlines() if l]


def test_index_lists_a_phase1_baseline():
    assert any(entry["phase"] == 1 for entry in index())


def test_recorded_has_no_local_paths(trigger_runner):
    assert RECORDED.is_dir() and trigger_runner.scrub_problems(RECORDED) == []


def test_index_lists_every_recorded_cell(trigger_runner):
    prompts = trigger_runner.load_prompts()
    for entry in index():
        cells = trigger_runner.matrix(entry["phase"], prompts, set(entry.get("gaps", [])))
        recorded = {(r["model"], r["prompt_id"], r["arm"], r["rep"]) for r in verdicts(entry["folder"])}
        missing = [c for c in cells if (c.model, c.prompt_id, c.arm, c.rep) not in recorded]
        assert not missing, (entry["folder"], missing[:5])


def test_decision_json_reproduces(decide):
    for entry in index():
        stored = json.loads((RECORDED / entry["folder"] / entry["decision"]).read_text(encoding="utf-8"))
        assert decide.report(verdicts(entry["folder"]), decide.load_criteria()) == stored
