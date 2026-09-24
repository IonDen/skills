"""skill-optimizer verify_rewrite.py (the gate). Each test names the one-line bug that would make it fail."""
import json
import shutil

import pytest

ORIGINAL = (
    "# Guide\n\n"
    "This paragraph explains at some length why conventions matter, because\n"
    "conventions differ between repositories and guessing wastes time.\n\n"
    "Read the repository conventions before starting work.\n\n"
    "NEVER force-push to `main`.\n\n"
    "Do not edit `generated/`, unless the user asks.\n\n"
    "Keep the wired limit under 20 GiB.\n\n"
    "## Troubleshooting\n\n"
    "If the build fails with `No module named build`, run `python3 -m pip install build`.\n\n"
    "## Reminder\n\n"
    "Do not skip the gate.\n"
)
REQS = (
    "R1: Read the conventions first.\n"
    "  anchor: Read the repository conventions before starting work\n"
)
TROUBLESHOOTING = ("## Troubleshooting\n\n"
                   "If the build fails with `No module named build`, run `python3 -m pip install build`.\n\n")
EXPLANATION = ("This paragraph explains at some length why conventions matter, because\n"
               "conventions differ between repositories and guessing wastes time.\n\n")


@pytest.fixture
def run(freezer, gate, make_skill, tmp_path):
    """Freeze ORIGINAL, write a candidate, return the gate's result."""
    def _run(body=None, files=None, frontmatter=None, edit_original=None, approved=None):
        orig = make_skill(ORIGINAL)
        frozen = freezer.freeze(orig, REQS)
        cand = tmp_path / "candidate"
        shutil.rmtree(cand, ignore_errors=True)   # each call starts from a fresh copy
        shutil.copytree(orig, cand)
        if body is not None or frontmatter is not None:
            text = (cand / "SKILL.md").read_text(encoding="utf-8")
            fm, old = text.split("---\n", 2)[1:]
            fm_block = frontmatter if frontmatter is not None else f"---\n{fm}---\n"
            (cand / "SKILL.md").write_text(fm_block + (body if body is not None else old), encoding="utf-8")
        for rel, text in (files or {}).items():
            p = cand / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(text, encoding="utf-8")
        if edit_original:
            (orig / "SKILL.md").write_text("changed\n", encoding="utf-8")
        return gate.verify(frozen, cand, orig, approved)
    return _run


def codes(result):
    return {f["code"] for f in result["rejected"]}


def test_identical_candidate_is_unchanged_not_rejected(run):
    # Bug caught: a size check with >=, which rejects a candidate that changed
    # nothing and makes "nothing to cut" look like a failure.
    r = run()
    assert r["status"] == "unchanged" and r["rejected"] == []


def test_honest_trim_passes(run):
    # Bug caught: a gate so strict that no legitimate cut can pass.
    r = run(body=ORIGINAL.replace(EXPLANATION, ""))
    assert r["status"] == "pass", r["rejected"]


def test_trim_after_a_rule_keeps_its_prominence(run):
    # Bug caught: measuring position relative to file length, so deleting text
    # below a rule looks like demoting it.
    body = ORIGINAL.replace(TROUBLESHOOTING, "Read `references/troubleshooting.md` when a build fails.\n\n")
    r = run(body=body, files={"references/troubleshooting.md": TROUBLESHOOTING})
    assert r["status"] == "pass", r["rejected"]


@pytest.mark.parametrize("old,new,code", [
    ("NEVER force-push to `main`.", "NEVER change the logo.", "RULE_LOST"),             # rule swapped
    ("NEVER force-push", "Avoid force-pushing", "RULE_LOST"),                           # rule weakened
    (", unless the user asks.", ".", "RULE_LOST"),                                      # exception dropped
    ("Do not edit", "Edit", "RULE_LOST"),                                               # negation flipped
    ("under 20 GiB", "over 20 GiB", "LITERAL_LOST"),                                    # bound reversed
    ("`python3 -m pip install build`", "`python3 -m pip install builds`", "LITERAL_LOST"),  # command changed
    ("Read the repository conventions before starting work.\n\n", "", "ANCHOR_LOST"),  # plain instruction
])
def test_each_loss_is_rejected_by_name(run, old, new, code):
    # Bug caught: counting rules instead of matching them, or substring literals,
    # so a same-size swap or a lookalike token passes.
    assert old in ORIGINAL
    r = run(body=ORIGINAL.replace(EXPLANATION, "").replace(old, new))
    assert r["status"] == "rejected" and code in codes(r), r["rejected"]


def test_literal_hidden_in_a_longer_token_is_lost(run):
    # Bug caught: "20 GiB" surviving inside "2026" or "120 GiB".
    body = ORIGINAL.replace(EXPLANATION, "").replace("under 20 GiB", "reasonable (reviewed 2026, max 120 GiB)")
    lost = [f["detail"] for f in run(body=body)["rejected"] if f["code"] == "LITERAL_LOST"]
    assert any(d.startswith("'20 GiB'") for d in lost), lost


def test_rule_pushed_down_loses_prominence(run):
    # Bug caught: not checking position, so a strong rule can sink below text
    # that used to stand behind it.
    body = ORIGINAL.replace("Keep the wired limit under 20 GiB.\n\n", "").replace(
        "Read the repository conventions", "Keep the wired limit under 20 GiB.\n\nRead the repository conventions")
    assert "PROMINENCE_LOST" in codes(run(body=body))


def test_rule_demoted_while_the_text_in_front_shrinks(run):
    # Bug caught: comparing offsets, so cutting a long paragraph in front of a rule
    # hides moving another rule above it.
    body = ORIGINAL.replace(EXPLANATION, "").replace("Do not edit `generated/`, unless the user asks.\n\n", "")
    body = body.replace("NEVER force-push", "Do not edit `generated/`, unless the user asks.\n\nNEVER force-push")
    assert "PROMINENCE_LOST" in codes(run(body=body))


def test_closing_rule_must_stay_at_the_end(run):
    # Bug caught: dropping the deliberate end-of-file reminder by moving it up.
    body = ORIGINAL.replace(EXPLANATION, "").replace("## Reminder\n\nDo not skip the gate.\n", "")
    body = body.replace("# Guide\n\n", "# Guide\n\nDo not skip the gate.\n\n")
    assert "TERMINAL_MOVED" in codes(run(body=body))


def test_frontmatter_is_frozen(run):
    # Bug caught: comparing bodies only, so a description or name change passes.
    r = run(body=ORIGINAL.replace(EXPLANATION, ""),
            frontmatter="---\nname: demo\ndescription: Use when testing a lot.\n---\n")
    assert "FRONTMATTER_CHANGED" in codes(r)


def test_other_files_are_frozen(run, make_skill):
    # Bug caught: checking only SKILL.md, so an existing reference is rewritten unchecked,
    # or a script is added beside the skill.
    r = run(body=ORIGINAL.replace(EXPLANATION, ""), files={"scripts/new.py": "print(1)\n"})
    assert "UNEXPECTED_FILE" in codes(r)


def test_existing_reference_may_not_change(freezer, gate, make_skill, tmp_path):
    # Bug caught: treating an edited existing reference as a new one.
    orig = make_skill(ORIGINAL, files={"references/a.md": "Original.\n"})
    frozen = freezer.freeze(orig, REQS)
    cand = tmp_path / "candidate"
    shutil.copytree(orig, cand)
    (cand / "references" / "a.md").write_text("Edited.\n", encoding="utf-8")
    assert "FILE_CHANGED" in codes(gate.verify(frozen, cand, orig))


def test_new_reference_must_be_linked(run):
    # Bug caught: accepting a moved section nothing tells the agent to read.
    body = ORIGINAL.replace(EXPLANATION, "")
    r = run(body=body, files={"references/extra.md": "Background.\n"})
    assert "REFERENCE_UNLINKED" in codes(r)


def test_moving_a_rule_needs_the_users_decision(run):
    # Bug caught: letting a rule leave the body silently, where an agent only sees
    # it if it happens to open the reference.
    body = ORIGINAL.replace(EXPLANATION, "").replace(
        "Do not edit `generated/`, unless the user asks.\n\n",
        "Read `references/editing.md` before editing generated files.\n\n")
    r = run(body=body, files={"references/editing.md": "Do not edit `generated/`, unless the user asks.\n"})
    assert r["status"] == "needs_confirmation", r["rejected"]
    assert [c["code"] for c in r["confirm"]] == ["MOVED_TO_REFERENCE"]


def test_candidate_must_be_smaller(run):
    # Bug caught: accepting a "rewrite" that grew.
    r = run(body=ORIGINAL + "\nMore text.\n")
    assert "NOT_SMALLER" in codes(r)


def test_frozen_file_is_bound_to_the_live_skill(run):
    # Bug caught: gating against a stale freeze after the skill changed on disk.
    r = run(body=ORIGINAL.replace(EXPLANATION, ""), edit_original=True)
    assert "ORIGINAL_CHANGED" in codes(r)


def test_cli_exit_codes(freezer, gate, make_skill, tmp_path, capsys):
    # Bug caught: printing REJECTED but exiting 0, which is the only thing the
    # workflow can enforce on.
    orig = make_skill(ORIGINAL)
    frozen_path = tmp_path / "frozen.json"
    frozen_path.write_text(json.dumps(freezer.freeze(orig, REQS)), encoding="utf-8")
    cand = tmp_path / "candidate"
    shutil.copytree(orig, cand)
    args = ["--frozen", str(frozen_path), "--original", str(orig), "--candidate", str(cand)]
    assert gate.main(args) == 0
    skill = cand / "SKILL.md"
    skill.write_text(skill.read_text(encoding="utf-8").replace("NEVER force-push", "Avoid force-pushing"),
                     encoding="utf-8")
    assert gate.main(args) == 1
    skill.write_text(skill.read_text(encoding="utf-8").replace("Avoid force-pushing", "NEVER force-push")
                     .replace("Do not edit `generated/`, unless the user asks.", "See `references/e.md`.")
                     .replace(EXPLANATION, ""), encoding="utf-8")
    (cand / "references").mkdir()
    (cand / "references" / "e.md").write_text("Do not edit `generated/`, unless the user asks.\n",
                                             encoding="utf-8")
    assert gate.main(args) == 3
    assert gate.main(["--frozen", str(tmp_path / "missing.json")] + args[2:]) == 2
    capsys.readouterr()


def test_cli_percentage_is_not_rounded_up(gate):
    # Bug caught: floor division on a negative change, which prints -36.1% as -37%
    # and makes every saving look about a point bigger than it is.
    assert gate.percent_change(2898, 1851) == "-36.1%"
    assert gate.percent_change(8863, 8758) == "-1.2%"
    assert gate.percent_change(435, 151) == "-65.3%"
    assert gate.percent_change(0, 0) == ""


def test_invented_sentence_is_new_text(run):
    # Bug caught: checking only that frozen items survive, so a sentence the
    # original never had (one that contradicts a rule, even) passes.
    body = ORIGINAL.replace(EXPLANATION, "You may skip the tests when in a hurry.\n\n")
    assert "NEW_TEXT" in codes(run(body=body))


def test_invented_reference_is_new_text(run):
    # Bug caught: not reading new reference files, so a summary replaces the moved text.
    body = ORIGINAL.replace(TROUBLESHOOTING, "Read `references/troubleshooting.md` when a build fails.\n\n")
    r = run(body=body, files={"references/troubleshooting.md": "Reinstall the build tool when it breaks.\n"})
    assert "NEW_TEXT" in codes(r)


def test_qualifier_dropped_from_an_anchored_sentence(freezer, gate, make_skill, tmp_path):
    # Bug caught: protecting only the anchor's words, so "in a monorepo" can go.
    orig = make_skill(EXPLANATION + "Read the repository conventions before starting work in a monorepo.\n")
    frozen = freezer.freeze(orig, "R1: Conventions.\n  anchor: Read the repository conventions\n")
    cand = tmp_path / "candidate"
    shutil.copytree(orig, cand)
    (cand / "SKILL.md").write_text((orig / "SKILL.md").read_text(encoding="utf-8")
                                   .replace(EXPLANATION, "").replace(" in a monorepo", ""), encoding="utf-8")
    assert "ANCHOR_LOST" in codes(gate.verify(frozen, cand, orig))


def test_code_blocks_survive_whole_or_not_at_all(freezer, gate, make_skill, tmp_path):
    # Bug caught: comparing code line by line, so one line of a kept config block can change.
    body = EXPLANATION + "Use this config:\n\n```yaml\nretries: 3\ntimeout: 30\n```\n\nOr this example:\n\n```markdown\n- one\n```\n"
    orig = make_skill(body)
    frozen = freezer.freeze(orig, "R1: Use the config.\n  anchor: Use this config\n")
    cand = tmp_path / "candidate"
    shutil.copytree(orig, cand)
    fm = "---\nname: demo\ndescription: Use when testing.\n---\n"
    (cand / "SKILL.md").write_text(fm + body.replace(EXPLANATION, "").replace("timeout: 30", "timeout: 60"), encoding="utf-8")
    assert "CODE_EDITED" in codes(gate.verify(frozen, cand, orig))
    (cand / "SKILL.md").write_text(fm + body.replace(EXPLANATION, "").replace("Or this example:\n\n```markdown\n- one\n```\n", ""), encoding="utf-8")
    assert gate.verify(frozen, cand, orig)["status"] == "pass"


def test_reflow_and_list_conversion_pass(run):
    # Bug caught: treating a change of layout as a change of words.
    body = ORIGINAL.replace(EXPLANATION, "").replace(
        "NEVER force-push to `main`.\n\nDo not edit `generated/`, unless the user asks.\n",
        "- NEVER force-push to `main`.\n- Do not edit `generated/`,\n  unless the user asks.\n")
    assert run(body=body)["status"] == "pass", run(body=body)["rejected"]


def test_closing_rule_moved_into_a_reference_is_rejected(run):
    # Bug caught: asking about a moved closing reminder instead of refusing it.
    body = ORIGINAL.replace("## Reminder\n\nDo not skip the gate.\n", "See `references/gate.md`.\n")
    r = run(body=body, files={"references/gate.md": "Do not skip the gate.\n"})
    assert "TERMINAL_MOVED" in codes(r)


def test_rule_heading_is_protected(freezer, gate, make_skill, tmp_path):
    # Bug caught: protecting sentences only, so "## Never on Fridays" can be deleted.
    orig = make_skill(EXPLANATION + "## Never on Fridays\n\nDeploy with the script.\n")
    frozen = freezer.freeze(orig, "R1: Deploy.\n  anchor: Deploy with the script\n")
    cand = tmp_path / "candidate"
    shutil.copytree(orig, cand)
    (cand / "SKILL.md").write_text((orig / "SKILL.md").read_text(encoding="utf-8")
                                   .replace(EXPLANATION, "").replace("## Never on Fridays\n\n", ""), encoding="utf-8")
    assert "RULE_LOST" in codes(gate.verify(frozen, cand, orig))


def test_caches_in_the_candidate_are_ignored(run):
    # Bug caught: running the skill's own scripts between freeze and gate making
    # the gate report an unexpected file.
    r = run(body=ORIGINAL.replace(EXPLANATION, ""), files={"scripts/__pycache__/x.cpython-312.pyc": "x"})
    assert r["status"] == "pass", r["rejected"]


def test_rule_deleted_only_with_approval(run):
    # Bug caught: no way for the user to let a rule-word sentence go, or approval
    # letting through sentences the user did not approve.
    body = ORIGINAL.replace("Do not edit `generated/`, unless the user asks.\n\n", "")
    assert "RULE_LOST" in codes(run(body=body))
    r = run(body=body, approved=["Do not edit `generated/`, unless the user asks."])
    assert "RULE_LOST" not in codes(r) and r["approved_deletions"] == ["Do not edit `generated/`, unless the user asks"]
