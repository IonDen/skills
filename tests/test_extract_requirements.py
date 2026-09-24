"""skill-optimizer extract_requirements.py (the freeze). Each test names the one-line bug that would make it fail."""
import os
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parent.parent / "skills" / "skill-optimizer" / "scripts" / "extract_requirements.py"

BODY = (
    "# Guide\n\n"
    "Read the repository conventions before\nstarting work.\n\n"
    "NEVER force-push to `main`.\n\n"
    "Tests are not optional, unless the user asks for a dry run.\n\n"
    "Explain each commit in a sentence.\n"
)
REQS = (
    "R1: Read the conventions first.\n"
    "  anchor: Read the repository conventions before starting work\n"
    "R2: Never force-push to main.\n"
    "  anchor: NEVER force-push to `main`.\n"
)


def test_requirement_list_is_parsed_strictly(freezer):
    # Bug caught: skipping lines it does not understand, so a requirement written
    # in the wrong shape silently drops out of the contract.
    assert [r["id"] for r in freezer.parse_requirements(REQS)] == ["R1", "R2"]
    for bad in ("R1: Read.\n  anchor: Read\n1. A stray line in the wrong shape.\n", "R1: No anchor here.\n",
                "R1: a\n  anchor: x\nR1: b\n  anchor: y\n", ""):
        with pytest.raises(freezer.FreezeError):
            freezer.parse_requirements(bad)


def test_anchor_must_exist_in_the_original(freezer, make_skill):
    # Bug caught: accepting an invented anchor, which would let the list describe
    # a skill that is not the one on disk.
    d = make_skill(BODY)
    with pytest.raises(freezer.FreezeError, match="R1"):
        freezer.freeze(d, "R1: Invented.\n  anchor: Always deploy on Fridays.\n")


def test_anchor_matches_across_a_line_wrap_and_emphasis(freezer, make_skill):
    # Bug caught: matching anchors against raw lines, so an anchor copied from a
    # wrapped or bolded sentence is refused.
    d = make_skill(BODY.replace("NEVER force-push", "**NEVER** force-push"))
    frozen = freezer.freeze(d, REQS)
    assert [r["id"] for r in frozen["requirements"]] == ["R1", "R2"]


def test_anchor_rules(freezer, make_skill):
    # Bug caught: accepting an anchor that is too short to identify an instruction,
    # that matches two different sentences, or that spans two sentences, so the
    # gate protects the wrong text or none.
    d = make_skill(BODY + "\nExplain each commit in a pull request.\n\nKeep commits small. Say why in the message.\n")
    for anchor, why in (("Read the", "shorter than"), ("Explain each commit", "occurs 2 times"),
                        ("commits small. Say why", "single sentence")):
        with pytest.raises(freezer.FreezeError, match=why):
            freezer.freeze(d, f"R1: x.\n  anchor: {anchor}\n")


def test_anchor_protects_its_whole_sentence(freezer, make_skill):
    # Bug caught: protecting only the quoted words, so a qualifier outside the
    # quote ("in a monorepo") can be dropped while the anchor still matches.
    d = make_skill("Read the repository conventions before starting work in a monorepo.\n")
    frozen = freezer.freeze(d, "R1: Conventions first.\n  anchor: Read the repository conventions\n")
    assert frozen["requirements"][0]["protects"] == [
        {"kind": "sentence", "key": "Read the repository conventions before starting work in a monorepo"}]


def test_unprotected_sentences_are_listed(freezer, make_skill):
    # Bug caught: saying nothing about sentences no check covers, so a condition or
    # a plain step can be cut without anyone deciding it may go.
    d = make_skill("If the build fails, ask the maintainer.\n\nRun `make`.\n\nNEVER push.\n\n"
                   "Read the repository conventions before starting work.\n")
    frozen = freezer.freeze(d, REQS.split("R2")[0])
    assert frozen["unprotected"] == ["If the build fails, ask the maintainer."]


def test_caches_and_vcs_files_are_not_frozen(freezer, make_skill):
    # Bug caught: hashing __pycache__ or .git, so running the skill's own scripts
    # between freeze and apply makes the gate report an unexpected file.
    d = make_skill(BODY, files={"scripts/__pycache__/x.pyc": "x", ".git/HEAD": "ref", "scripts/a.py": "1\n"})
    assert set(freezer.freeze(d, REQS)["files"]) == {"SKILL.md", "scripts/a.py"}


def test_rules_terminal_and_files_are_recorded(freezer, make_skill):
    # Bug caught: freezing only upper-case modals, or missing the closing rule,
    # or not hashing the files a rewrite must leave alone.
    d = make_skill(BODY + "\n## Reminder\n\nDo not skip the gate.\n", files={"references/x.md": "Ref.\n"})
    frozen = freezer.freeze(d, REQS)
    rules = {r["key"]: r["strong"] for r in frozen["rules"]}
    assert rules == {"NEVER force-push to `main`": True,
                     "Tests are not optional, unless the user asks for a dry run": False,
                     "Do not skip the gate": True}
    assert frozen["terminal"] == ["Do not skip the gate"]
    assert set(frozen["files"]) == {"SKILL.md", "references/x.md"}
    assert frozen["frontmatter"].startswith("---\nname: demo")


def test_frozen_json_is_identical_across_processes(make_skill, tmp_path):
    # Bug caught: an unsorted set reaching the JSON. Set order is stable inside one
    # process, so only two processes with different hash seeds can see it.
    d = make_skill(BODY + "\nUse `a -b`, `c -d`, `e -f`, `g -h` and --flag-one --flag-two.\n")
    req = tmp_path / "req.md"
    req.write_text(REQS, encoding="utf-8")
    outs = []
    for seed in ("1", "2"):
        out = tmp_path / f"frozen-{seed}.json"
        subprocess.run([sys.executable, str(SCRIPT), str(d),
                        "--requirements", str(req), "-o", str(out)],
                       check=True, capture_output=True, env={**os.environ, "PYTHONHASHSEED": seed})
        outs.append(out.read_bytes())
    assert outs[0] == outs[1]


def test_cli_refuses_with_exit_2(freezer, make_skill, tmp_path, capsys):
    # Bug caught: writing a frozen file even though an anchor was missing.
    d = make_skill(BODY)
    req = tmp_path / "req.md"
    req.write_text("R1: Invented.\n  anchor: not in the skill\n", encoding="utf-8")
    out = tmp_path / "frozen.json"
    assert freezer.main([str(d), "--requirements", str(req), "-o", str(out)]) == 2
    assert not out.exists() and "not inside the original" in capsys.readouterr().err


def test_freeze_happens_once(freezer, make_skill, tmp_path, capsys):
    # Bug caught: letting the agent re-freeze after the candidate exists, e.g. to
    # drop a requirement the gate says was lost.
    d = make_skill(BODY)
    req = tmp_path / "req.md"
    req.write_text(REQS, encoding="utf-8")
    out = tmp_path / "frozen.json"
    assert freezer.main([str(d), "--requirements", str(req), "--dry-run"]) == 0
    assert not out.exists()
    assert freezer.main([str(d), "--requirements", str(req), "-o", str(out)]) == 0
    before = out.read_bytes()
    assert freezer.main([str(d), "--requirements", str(req), "-o", str(out)]) == 2
    assert out.read_bytes() == before and "Freeze once" in capsys.readouterr().err
