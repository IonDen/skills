"""Prompts, fixtures and workspaces of the trigger eval."""
import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TRIG = ROOT / "evals" / "triggering"
SKILLS = ROOT / "plugins" / "ionden-skills" / "skills"
WT = "writing-tests-that-can-fail"


def prompts():
    return json.loads((TRIG / "prompts.json").read_text(encoding="utf-8"))


def by_id(pid):
    return next(p for p in prompts()["prompts"] if p["id"] == pid)


def test_prompt_ids_unique_and_halves_balanced():
    ps = prompts()["prompts"]
    assert len({p["id"] for p in ps}) == len(ps)
    halves = Counter((p["skill"], p["kind"], p["half"]) for p in ps)
    for skill, kind in {(p["skill"], p["kind"]) for p in ps}:
        assert abs(halves[(skill, kind, "dev")] - halves[(skill, kind, "heldout")]) <= 1, (skill, kind)


def test_prompt_counts_match_the_design():
    ps = prompts()["prompts"]
    wt = [p for p in ps if p["skill"] == WT]
    opt = [p for p in ps if p["skill"] != WT]
    assert len([p for p in wt if p["kind"] in ("should", "delegate")]) == 16
    assert len([p for p in wt if p["kind"] == "near" and p["half"] != "fresh"]) == 10
    assert len([p for p in opt if p["kind"] == "should"]) == 12
    assert len([p for p in opt if p["kind"] == "near"]) == 6
    assert {p["half"] for p in ps if p["kind"] == "delegate"} == {"dev", "heldout"}
    fresh = [p for p in ps if p["half"] == "fresh"]
    assert len(fresh) == 5 and {(p["skill"], p["kind"]) for p in fresh} == {(WT, "near")}


def test_every_prompt_names_an_existing_fixture():
    for p in prompts()["prompts"]:
        assert (TRIG / "fixtures" / p["fixture"]).is_dir(), p["id"]


def test_wt_fixtures_have_no_claude_dir_or_agents_md():
    for name in {p["fixture"] for p in prompts()["prompts"] if p["skill"] == WT}:
        fx = TRIG / "fixtures" / name
        assert not list(fx.rglob(".claude")) and not list(fx.rglob("AGENTS.md")) and not list(fx.rglob("CLAUDE.md")), name


def test_optimizer_fixture_skill_not_under_claude_skills():
    for name in {p["fixture"] for p in prompts()["prompts"] if p["skill"] != WT}:
        for md in (TRIG / "fixtures" / name).rglob("SKILL.md"):
            assert ".claude/skills" not in md.as_posix(), md


def test_snippet_arm_writes_claude_md_and_current_arm_does_not(trigger_runner, tmp_path):
    p = by_id(next(q["id"] for q in prompts()["prompts"] if q["skill"] == WT))
    snip = trigger_runner.prepare_workspace(p, "current+snippet", tmp_path / "a")
    assert (snip / "CLAUDE.md").read_text(encoding="utf-8") == (TRIG / "snippet.md").read_text(encoding="utf-8")
    cur = trigger_runner.prepare_workspace(p, "current", tmp_path / "b")
    assert not (cur / "CLAUDE.md").exists()
    assert sorted(x.name for x in cur.iterdir()) == sorted(x.name for x in (TRIG / "fixtures" / p["fixture"]).iterdir())


def test_snippet2_arm_writes_the_second_snippet(trigger_runner, tmp_path):
    p = by_id("wt-n08")
    ws = trigger_runner.prepare_workspace(p, "current+snippet2", tmp_path / "a")
    assert (ws / "CLAUDE.md").read_text(encoding="utf-8") == (TRIG / "snippet2.md").read_text(encoding="utf-8")
    assert (TRIG / "snippet2.md").read_text(encoding="utf-8") != (TRIG / "snippet.md").read_text(encoding="utf-8")


def test_workspace_has_no_ancestor_claude_md(trigger_runner, tmp_path):
    p = prompts()["prompts"][0]
    ws = trigger_runner.prepare_workspace(p, "current", tmp_path / "ws")
    for parent in ws.parents:
        assert not (parent / "CLAUDE.md").exists() and not (parent / "AGENTS.md").exists(), parent


def descriptions():
    out = {}
    for md in SKILLS.glob("*/SKILL.md"):
        fm = md.read_text(encoding="utf-8").split("---")[1]
        out[md.parent.name] = re.sub(r"\s+", " ", fm.split("description:", 1)[1].split("\nmetadata:")[0]).lower()
    return out


def test_shipped_descriptions_avoid_guard_words():
    words = prompts()["guard_words"]
    assert len(words) >= 6
    for name, text in descriptions().items():
        hits = [w for w in words if re.search(rf"\b{re.escape(w.lower())}\b", text)]
        assert not hits, (name, hits)


def test_guard_words_come_from_the_prompts():
    text = " ".join(p["text"] for p in prompts()["prompts"]).lower()
    for w in prompts()["guard_words"]:
        assert w.lower() in text, w


def test_readme_snippet_matches_measured_snippet():
    # Bug caught: the README offering snippet wording the Phase 2 eval never measured.
    snippet = (TRIG / "snippet2.md").read_text(encoding="utf-8").strip()
    assert snippet in (SKILLS / WT / "README.md").read_text(encoding="utf-8")
