"""skill-optimizer verify_rewrite.py (the gate). Each test names the one-line bug that would make it fail."""
import json
import re
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
    assert "RULE_LOST" not in codes(r) and r["approved_deletions"] == [
        "Do not edit `generated/`, unless the user asks", "literal: generated/"]


def _secret(tmp_path):
    secret = tmp_path / "secret.md"
    secret.write_text("PRIVATE KEY\n", encoding="utf-8")
    return secret


def test_symlinked_skill_md_is_refused(freezer, gate, make_skill, tmp_path, capsys):
    # Bug caught: following a symlinked SKILL.md in the original or the candidate,
    # so the gate reads, hashes and may quote a file outside the skill.
    orig = make_skill(ORIGINAL)
    frozen_path = tmp_path / "frozen.json"
    frozen_path.write_text(json.dumps(freezer.freeze(orig, REQS)), encoding="utf-8")
    cand = tmp_path / "candidate"
    shutil.copytree(orig, cand)
    (cand / "SKILL.md").unlink()
    (cand / "SKILL.md").symlink_to(_secret(tmp_path))
    args = ["--frozen", str(frozen_path), "--original", str(orig), "--candidate", str(cand)]
    assert gate.main(args) == 2
    err = capsys.readouterr().err
    assert "symlink" in err and "PRIVATE" not in err and len(err.strip().splitlines()) == 1


def test_symlinks_in_the_candidate_are_rejected(freezer, gate, make_skill, tmp_path):
    # Bug caught: skipping a link in the candidate without a word, so a frozen file
    # swapped for a link, or a new reference that is a link, reaches the apply step unchecked.
    orig = make_skill(ORIGINAL, files={"references/a.md": "Original.\n"})
    frozen = freezer.freeze(orig, REQS)
    cand = tmp_path / "candidate"
    shutil.copytree(orig, cand)
    (cand / "SKILL.md").write_text((orig / "SKILL.md").read_text(encoding="utf-8").replace(EXPLANATION, ""),
                                   encoding="utf-8")
    assert gate.verify(frozen, cand, orig)["status"] == "pass"
    (cand / "references" / "a.md").unlink()
    (cand / "references" / "a.md").symlink_to(orig / "references" / "a.md")
    (cand / "references" / "b.md").symlink_to(_secret(tmp_path))
    r = gate.verify(frozen, cand, orig)
    details = [(f["code"], f["detail"]) for f in r["rejected"]]
    assert ("FILE_CHANGED", "references/a.md is missing") in details
    assert sum(1 for c, d in details if c == "UNEXPECTED_FILE" and "symlink" in d) == 2
    assert not any("PRIVATE" in d for _, d in details)


def gate_on(freezer, gate, make_skill, tmp_path, original, reqs, candidate, approved=None):
    """Freeze `original` (a body) with `reqs`, gate `candidate` (a body) against it."""
    orig = make_skill(original)
    frozen = freezer.freeze(orig, reqs)
    cand = tmp_path / "candidate"
    shutil.rmtree(cand, ignore_errors=True)
    shutil.copytree(orig, cand)
    fm = "---\nname: demo\ndescription: Use when testing.\n---\n"
    (cand / "SKILL.md").write_text(fm + candidate, encoding="utf-8")
    return gate.verify(frozen, cand, orig, approved)


TAG = "R1: Tag after the merge.\n  anchor: Tag the release after the merge\n"
HEADED = ("# Guide\n\n" + EXPLANATION + "## Never Skip Tests\n\nRun the whole suite each time.\n\n"
          "## Release\n\nTag the release after the merge.\n")


@pytest.mark.parametrize("candidate", [
    # moved to the end at the same depth
    "# Guide\n\n## Release\n\nTag the release after the merge.\n\n## Never Skip Tests\n\nRun the whole suite each time.\n",
    # left in place under a deeper marker
    "# Guide\n\n#### Never Skip Tests\n\nRun the whole suite each time.\n\n## Release\n\nTag the release after the merge.\n",
    # both: the reproduction from the review
    "# Guide\n\n## Release\n\nTag the release after the merge.\n\n#### Never Skip Tests\n\nRun the whole suite each time.\n",
])
def test_rule_heading_keeps_its_prominence(freezer, gate, make_skill, tmp_path, candidate):
    # Bug caught: checking the position of rule sentences only, so "## Never Skip Tests"
    # can sink behind text that stood after it, or under a deeper marker.
    r = gate_on(freezer, gate, make_skill, tmp_path, HEADED, TAG, candidate)
    assert "PROMINENCE_LOST" in codes(r), r["rejected"]
    honest = HEADED.replace(EXPLANATION, "")
    assert gate_on(freezer, gate, make_skill, tmp_path, HEADED, TAG, honest)["status"] == "pass"


MOTIVATION = "This skill exists so that nothing important is forgotten."
WHY_REQS = TAG + "R2: Why the skill exists.\n  anchor: nothing important is forgotten\n"


def test_approval_reaches_an_anchored_rule_sentence(freezer, gate, make_skill, tmp_path):
    # Bug caught: approval checked for RULE_LOST only, so an anchored motivation
    # sentence the user agreed to delete still fails with ANCHOR_LOST, a dead end
    # because the freeze cannot be redone.
    original = EXPLANATION + MOTIVATION + "\n\nTag the release after the merge.\n"
    candidate = "Tag the release after the merge.\n"
    r = gate_on(freezer, gate, make_skill, tmp_path, original, WHY_REQS, candidate)
    assert {"ANCHOR_LOST", "RULE_LOST"} <= codes(r)
    r = gate_on(freezer, gate, make_skill, tmp_path, original, WHY_REQS, candidate, approved=[MOTIVATION])
    assert r["status"] == "pass", r["rejected"]
    assert r["approved_deletions"] == ["This skill exists so that nothing important is forgotten"]


NUKE = "Do not run `make nuke` on a shared host."
VAULT = EXPLANATION + NUKE + "\n\nNever touch `prod.cfg` by hand.\n\nKeep `prod.cfg` in the vault.\n\nTag the release after the merge.\n"


def test_approval_reaches_a_literal_only_in_approved_sentences(freezer, gate, make_skill, tmp_path):
    # Bug caught: LITERAL_LOST ignoring approval, so deleting an approved sentence
    # that holds the only copy of a literal can never pass.
    r = gate_on(freezer, gate, make_skill, tmp_path, VAULT, TAG, VAULT.replace(EXPLANATION, "").replace(NUKE, ""),
                approved=[NUKE])
    assert r["status"] == "pass", r["rejected"]
    assert r["approved_deletions"] == ["Do not run `make nuke` on a shared host", "literal: make nuke"]


def test_a_literal_is_approved_only_when_every_copy_was(freezer, gate, make_skill, tmp_path):
    # Bug caught: approving a literal when any sentence holding it is approved, so a
    # second, unapproved sentence carrying the same literal can go with it.
    candidate = (VAULT.replace(EXPLANATION, "").replace("Never touch `prod.cfg` by hand.\n\n", "")
                 .replace("Keep `prod.cfg` in the vault.\n\n", ""))
    r = gate_on(freezer, gate, make_skill, tmp_path, VAULT, TAG, candidate,
                approved=["Never touch `prod.cfg` by hand."])
    assert [f["detail"] for f in r["rejected"] if f["code"] == "LITERAL_LOST"] == ["'prod.cfg' is gone or changed"]


def test_a_literal_in_code_is_never_approved_through_a_sentence(freezer, gate, make_skill, tmp_path):
    # Bug caught: counting only sentences that hold the literal, so a literal that
    # also (or only) sits in a runnable code block counts as approved when its
    # sentences are, and the command is lost unasked.
    original = VAULT + "\n```bash\nmake nuke\n```\n\n```bash\nmake wipe\n```\n"
    candidate = VAULT.replace(EXPLANATION, "").replace(NUKE, "")
    r = gate_on(freezer, gate, make_skill, tmp_path, original, TAG, candidate, approved=[NUKE])
    lost = sorted(f["detail"] for f in r["rejected"] if f["code"] == "LITERAL_LOST")
    assert lost == ["'make nuke' is gone or changed", "'make wipe' is gone or changed"]


def test_approved_heading_may_carry_its_marker(freezer, gate, make_skill, tmp_path):
    # Bug caught: an approval line copied with "## " never matching the heading it names.
    original = EXPLANATION + "Tag the release after the merge.\n\n## Never on Fridays\n\nThe office is closed then.\n"
    candidate = "Tag the release after the merge.\n"
    assert "RULE_LOST" in codes(gate_on(freezer, gate, make_skill, tmp_path, original, TAG, candidate))
    r = gate_on(freezer, gate, make_skill, tmp_path, original, TAG, candidate, approved=["## Never on Fridays"])
    assert r["status"] == "pass", r["rejected"]


SECTIONS = ("# Linux\n\n" + EXPLANATION + "Use the apt package only on Debian hosts.\n\n"
            "# macOS\n\nInstall the tool with Homebrew on a clean machine.\n")
BREW = "R1: Install with Homebrew.\n  anchor: Install the tool with Homebrew\n"


@pytest.mark.parametrize("candidate,moved", [
    ("# Linux\n\n# macOS\n\nInstall the tool with Homebrew on a clean machine.\n\nUse the apt package only on Debian hosts.\n",
     "Use the apt package only on Debian hosts"),
    ("# Linux\n\nInstall the tool with Homebrew on a clean machine.\n\nUse the apt package only on Debian hosts.\n\n# macOS\n",
     "Install the tool with Homebrew on a clean machine"),
])
def test_moving_a_sentence_to_another_section_needs_the_users_decision(freezer, gate, make_skill, tmp_path,
                                                                        candidate, moved):
    # Bug caught: no section check, so a rule or an anchored sentence moved from
    # "# Linux" to "# macOS" changes what it applies to and still passes.
    r = gate_on(freezer, gate, make_skill, tmp_path, SECTIONS, BREW, candidate)
    assert r["status"] == "needs_confirmation", r["rejected"]
    assert [(c["code"], moved in c["detail"]) for c in r["confirm"]] == [("SECTION_CHANGED", True)]
    honest = gate_on(freezer, gate, make_skill, tmp_path, SECTIONS, BREW, SECTIONS.replace(EXPLANATION, ""))
    assert honest["status"] == "pass", honest


TABLE = (EXPLANATION + "| Exit | Next |\n|------|------|\n"
         "| 1    | Fix each finding. A rejected candidate is never applied. |\n"
         "| 3    | Ask the user. |\n\nTag the release after the merge.\n")


def test_table_realignment_passes_and_a_cell_rule_is_still_protected(freezer, gate, make_skill, tmp_path):
    # Bug caught: a table row read as one paragraph, so the row's " |" joins the
    # last sentence of a cell and re-padding the table reads as a lost rule.
    realigned = TABLE.replace(EXPLANATION, "").replace("|------|------|", "|---|---|").replace("    |", " |") \
        .replace("applied. |", "applied.|")
    r = gate_on(freezer, gate, make_skill, tmp_path, TABLE, TAG, realigned)
    assert r["status"] == "pass", r["rejected"]
    edited = realigned.replace("is never applied", "is rarely applied")
    assert "RULE_LOST" in codes(gate_on(freezer, gate, make_skill, tmp_path, TABLE, TAG, edited))


def _load_line(n_words):
    return "Read `references/troubleshooting.md` when " + " ".join(f"step{i}" for i in range(n_words - 2)) + "."


@pytest.mark.parametrize("line,ok", [
    (_load_line(25), True),
    (_load_line(26), False),
    ("Read `references/troubleshooting.md` when it fails and always force-push to main afterwards.", False),
])
def test_load_line_is_bounded(run, line, ok):
    # Bug caught: exempting any sentence that names a new reference from NEW_TEXT,
    # so "... and always force-push to main afterwards" rides in on a load line.
    r = run(body=ORIGINAL.replace(TROUBLESHOOTING, line + "\n\n"),
            files={"references/troubleshooting.md": TROUBLESHOOTING})
    assert ("NEW_TEXT" not in codes(r)) == ok, r["rejected"]


def test_freeze_from_an_older_version_is_refused(freezer, gate, make_skill, tmp_path, capsys):
    # Bug caught: reading a format-2 freeze, which records no heading positions and
    # no sections, so the gate would pass what it claims to check.
    orig = make_skill(ORIGINAL)
    frozen = freezer.freeze(orig, REQS)
    frozen["format"] = 2
    frozen_path = tmp_path / "frozen.json"
    frozen_path.write_text(json.dumps(frozen), encoding="utf-8")
    assert gate.main(["--frozen", str(frozen_path), "--original", str(orig), "--candidate", str(orig)]) == 2
    assert "format 2" in capsys.readouterr().err


def test_cli_reads_approvals_one_per_line(freezer, gate, make_skill, tmp_path, capsys):
    # Bug caught: main() never handing --approved to the gate, so an approval the
    # user gave on the command line changes nothing.
    orig = make_skill(ORIGINAL)
    frozen_path = tmp_path / "frozen.json"
    frozen_path.write_text(json.dumps(freezer.freeze(orig, REQS)), encoding="utf-8")
    cand = tmp_path / "candidate"
    shutil.copytree(orig, cand)
    skill = cand / "SKILL.md"
    skill.write_text(skill.read_text(encoding="utf-8").replace(EXPLANATION, "")
                     .replace("NEVER force-push to `main`.\n\n", "")
                     .replace("Do not edit `generated/`, unless the user asks.\n\n", ""), encoding="utf-8")
    approved = tmp_path / "approved.txt"
    approved.write_text("NEVER force-push to `main`.\n\nDo not edit `generated/`, unless the user asks.\n",
                        encoding="utf-8")
    args = ["--frozen", str(frozen_path), "--original", str(orig), "--candidate", str(cand)]
    assert gate.main(args) == 1
    capsys.readouterr()
    assert gate.main(args + ["--approved", str(approved)]) == 0
    out = capsys.readouterr().out
    for d in ("NEVER force-push to `main`", "Do not edit `generated/`, unless the user asks"):
        assert f"deleted with the user's approval: {d}\n" in out


def test_deleted_existing_file_is_file_changed(freezer, gate, make_skill, tmp_path):
    # Bug caught: checking only the files the candidate has, so deleting an existing
    # reference passes.
    orig = make_skill(ORIGINAL, files={"references/a.md": "Original.\n"})
    frozen = freezer.freeze(orig, REQS)
    cand = tmp_path / "candidate"
    shutil.copytree(orig, cand)
    (cand / "SKILL.md").write_text((orig / "SKILL.md").read_text(encoding="utf-8").replace(EXPLANATION, ""),
                                   encoding="utf-8")
    (cand / "references" / "a.md").unlink()
    r = gate.verify(frozen, cand, orig)
    assert [(f["code"], f["detail"]) for f in r["rejected"]] == [("FILE_CHANGED", "references/a.md is missing")]


@pytest.mark.parametrize("where", ["body", "reference"])
def test_invented_heading_is_new_text(run, where):
    # Bug caught: checking sentences for invented words but not headings, so a
    # heading such as "## Optional steps" can recast the rules under it.
    body = ORIGINAL.replace(TROUBLESHOOTING, "Read `references/troubleshooting.md` when a build fails.\n\n")
    ref = TROUBLESHOOTING
    if where == "body":
        body = body.replace("## Reminder\n", "## Optional reminder\n")
    else:
        ref = ref.replace("## Troubleshooting\n", "## Troubleshooting you may skip\n")
    r = run(body=body, files={"references/troubleshooting.md": ref})
    assert any(f["code"] == "NEW_TEXT" and "heading" in f["detail"] for f in r["rejected"]), r["rejected"]


def test_a_literal_no_sentence_holds_is_never_approved(freezer, gate, make_skill, tmp_path):
    # Bug caught: approving a lost literal when all() runs over an empty list. The
    # path below keeps its underscores as a literal, but the sentence key loses
    # them, so no sentence "holds" it and any approval at all would let it go.
    original = VAULT + "\nEdit src/__pkg__/x.py with care.\n"
    candidate = VAULT.replace(EXPLANATION, "").replace(NUKE, "")
    r = gate_on(freezer, gate, make_skill, tmp_path, original, TAG, candidate, approved=[NUKE])
    assert [f["detail"] for f in r["rejected"] if f["code"] == "LITERAL_LOST"] == ["'src/__pkg__/x.py' is gone or changed"]


FRIDAYS = "Deploy on Fridays only when the lead signs off."
SCRATCH = "Run `make nuke` on the scratch host after the tests."
TRIMS = EXPLANATION + FRIDAYS + "\n\n" + SCRATCH + "\n\nTag the release after the merge.\n"
SCRATCH_REQS = TAG + "R2: Nuke the scratch host.\n  anchor: on the scratch host after the tests\n"


@pytest.mark.parametrize("approved,old,new,code", [
    (FRIDAYS, FRIDAYS, "Deploy on Fridays.", "RULE_LOST"),
    (SCRATCH, SCRATCH, "Run on the scratch host.", "ANCHOR_LOST"),
], ids=["rule", "anchor"])
def test_an_approved_deletion_may_not_be_a_trim(freezer, gate, make_skill, tmp_path, approved, old, new, code):
    # Bug caught: counting an approved sentence as deleted whenever its exact text is
    # gone, so "Deploy on Fridays only when the lead signs off." approved for deletion
    # can be kept as "Deploy on Fridays." and the condition disappears unasked.
    candidate = TRIMS.replace(EXPLANATION, "").replace(old, new)
    r = gate_on(freezer, gate, make_skill, tmp_path, TRIMS, SCRATCH_REQS, candidate, approved=[approved])
    assert r["status"] == "rejected"
    assert any(f["code"] == code and "trimmed, not deleted" in f["detail"] for f in r["rejected"]), r["rejected"]
    # the detail names the candidate sentence that is left of it
    assert any(repr(new.rstrip(".")) in f["detail"] for f in r["rejected"] if "trimmed" in f["detail"]), r["rejected"]
    assert r["approved_deletions"] == []
    if "make nuke" in old:
        # the literal goes only with a sentence that is truly deleted
        assert "'make nuke' is gone or changed" in [f["detail"] for f in r["rejected"] if f["code"] == "LITERAL_LOST"]
    whole = TRIMS.replace(EXPLANATION, "").replace(old + "\n\n", "")
    r = gate_on(freezer, gate, make_skill, tmp_path, TRIMS, SCRATCH_REQS, whole, approved=[approved])
    assert r["status"] == "pass", r["rejected"]


def test_a_surviving_sentence_is_not_read_as_a_trim(freezer, gate, make_skill, tmp_path):
    # Bug caught: treating every candidate sentence whose words fit inside an approved
    # sentence as a trim of it, so "Tag the release." kept exactly as it was blocks the
    # approved deletion of "Never tag the release on a Friday." forever.
    original = EXPLANATION + "Never tag the release on a Friday.\n\nTag the release.\n\nTag the release after the merge.\n"
    candidate = "Tag the release.\n\nTag the release after the merge.\n"
    r = gate_on(freezer, gate, make_skill, tmp_path, original, TAG, candidate,
                approved=["Never tag the release on a Friday."])
    assert r["status"] == "pass", r["rejected"]
    assert r["approved_deletions"] == ["Never tag the release on a Friday"]


PITFALLS = ("# Guide\n\n" + EXPLANATION + "## Build\n\nRun the build script first.\n\n### Pitfalls to avoid\n\n"
            "The cache can go stale.\n\n## Deploy\n\nPush the image to the registry.\n\n### Pitfalls to avoid\n\n"
            "The registry can be slow.\n\nTag the release after the merge.\n")


def test_a_repeated_rule_heading_has_no_position_to_keep(freezer, gate, make_skill, tmp_path):
    # Bug caught: giving a heading that occurs twice the position of its first
    # occurrence, so deleting the first "### Pitfalls to avoid" section reads as the
    # second one losing prominence.
    candidate = ("# Guide\n\n## Deploy\n\nPush the image to the registry.\n\n### Pitfalls to avoid\n\n"
                 "The registry can be slow.\n\nTag the release after the merge.\n")
    r = gate_on(freezer, gate, make_skill, tmp_path, PITFALLS, TAG, candidate)
    assert r["status"] == "pass", r["rejected"]
    # it must still exist somewhere: deleting every copy is RULE_LOST
    gone = candidate.replace("### Pitfalls to avoid\n\n", "")
    assert "RULE_LOST" in codes(gate_on(freezer, gate, make_skill, tmp_path, PITFALLS, TAG, gone))
    # a heading that occurs once keeps its position
    unique = PITFALLS.replace("## Deploy", "## Never deploy by hand")
    moved = ("# Guide\n\n## Build\n\nRun the build script first.\n\n### Pitfalls to avoid\n\nThe cache can go stale.\n\n"
             "Push the image to the registry.\n\n### Pitfalls to avoid\n\nThe registry can be slow.\n\n"
             "Tag the release after the merge.\n\n## Never deploy by hand\n")
    assert "PROMINENCE_LOST" in codes(gate_on(freezer, gate, make_skill, tmp_path, unique, TAG, moved))


LOCAL = ("# Guide\n\n" + EXPLANATION + "## Running the tests locally\n\nUse the apt package only on Debian hosts.\n\n"
         "## Release\n\nTag the release after the merge.\n")


def test_a_trimmed_heading_keeps_its_section(freezer, gate, make_skill, tmp_path):
    # Bug caught: comparing a rule's section by heading text, so trimming
    # "## Running the tests locally" to "## Running tests" asks the user whether
    # every rule under it may change section, though none moved.
    trimmed = LOCAL.replace(EXPLANATION, "").replace("## Running the tests locally", "## Running tests")
    r = gate_on(freezer, gate, make_skill, tmp_path, LOCAL, TAG, trimmed)
    assert r["status"] == "pass", (r["rejected"], r["confirm"])
    moved = trimmed.replace("Use the apt package only on Debian hosts.\n\n", "") + \
        "\nUse the apt package only on Debian hosts.\n"
    r = gate_on(freezer, gate, make_skill, tmp_path, LOCAL, TAG, moved)
    assert [c["code"] for c in r["confirm"]] == ["SECTION_CHANGED"], (r["rejected"], r["confirm"])
    # a trim that fits two original headings names neither: the gate asks
    two = LOCAL.replace("## Running the tests locally", "## Running the tests in CI") + \
        "\n## Running the tests locally\n\nUse the cache.\n"
    ambiguous = two.replace(EXPLANATION, "").replace("## Running the tests in CI", "## Running the tests")
    r = gate_on(freezer, gate, make_skill, tmp_path, two, TAG, ambiguous)
    assert [c["code"] for c in r["confirm"]] == ["SECTION_CHANGED"], (r["rejected"], r["confirm"])


def test_original_skill_md_linked_per_file_is_read(freezer, gate, make_skill, tmp_path, capsys):
    # Bug caught: refusing every linked SKILL.md under --original, so the gate can
    # never run against a skill installed per file (stow, home-manager), or
    # accepting a link to any file, so --original reads ~/.ssh/id_rsa.
    store = make_skill(ORIGINAL, where="store/demo")
    frozen_path = tmp_path / "frozen.json"
    frozen_path.write_text(json.dumps(freezer.freeze(store, REQS)), encoding="utf-8")
    installed = tmp_path / "installed"
    installed.mkdir()
    (installed / "SKILL.md").symlink_to(store / "SKILL.md")
    args = ["--frozen", str(frozen_path), "--original", str(installed), "--candidate", str(store)]
    assert gate.main(args) == 0
    (installed / "SKILL.md").unlink()
    (installed / "SKILL.md").symlink_to(_secret(tmp_path))
    assert gate.main(args) == 2
    assert "PRIVATE" not in capsys.readouterr().err


def test_only_an_identical_surviving_sentence_excuses_a_trim(freezer, gate, make_skill, tmp_path):
    # Bug caught: excusing a candidate sentence that merely fits inside a surviving
    # original sentence, so "Deploy on Fridays." passes as cut from "Deploy on Fridays
    # after the freeze lifts." while it is really what is left of the approved rule.
    original = EXPLANATION + FRIDAYS + "\n\nDeploy on Fridays after the freeze lifts.\n\nTag the release after the merge.\n"
    candidate = "Deploy on Fridays.\n\nDeploy on Fridays after the freeze lifts.\n\nTag the release after the merge.\n"
    r = gate_on(freezer, gate, make_skill, tmp_path, original, TAG, candidate, approved=[FRIDAYS])
    assert any(f["code"] == "RULE_LOST" and "trimmed, not deleted" in f["detail"] for f in r["rejected"]), r["rejected"]


PLATFORMS = ("# Linux\n\n" + EXPLANATION + "### Running the tests locally\n\nUse the apt package only on Debian hosts.\n\n"
             "Run the suite from the repository root.\n\n# Windows\n\nInstall the tool with the installer.\n\n"
             "Tag the release after the merge.\n")


def test_a_trimmed_copy_of_a_kept_heading_is_a_new_section(freezer, gate, make_skill, tmp_path):
    # Bug caught: mapping a trimmed heading to its original even while that original
    # still stands unchanged elsewhere, so a rule moved under a new "### Running tests"
    # in the Windows section reads as never having left Linux.
    candidate = ("# Linux\n\n### Running the tests locally\n\nRun the suite from the repository root.\n\n# Windows\n\n"
                 "Install the tool with the installer.\n\nTag the release after the merge.\n\n### Running tests\n\n"
                 "Use the apt package only on Debian hosts.\n")
    r = gate_on(freezer, gate, make_skill, tmp_path, PLATFORMS, TAG, candidate)
    assert [c["code"] for c in r["confirm"]] == ["SECTION_CHANGED"], (r["rejected"], r["confirm"])


@pytest.mark.parametrize("first,second", [("##", "###"), ("###", "##")], ids=["shallow-first", "deep-first"])
def test_a_repeated_rule_heading_keeps_its_shallowest_level(freezer, gate, make_skill, tmp_path, first, second):
    # Bug caught: skipping every prominence check for a heading the original repeats,
    # so "## Pitfalls to avoid" can sink to "####" because a "###" copy exists too;
    # or freezing the level of the first copy only, which misses it when that copy is the deeper one.
    original = ("# Guide\n\n" + EXPLANATION + f"{first} Pitfalls to avoid\n\nThe cache can go stale.\n\n## Deploy\n\n"
                f"{second} Pitfalls to avoid\n\nThe registry can be slow.\n\nTag the release after the merge.\n")
    demoted = re.sub(r"(?m)^## Pitfalls to avoid$", "#### Pitfalls to avoid", original.replace(EXPLANATION, ""))
    assert demoted.count("#### Pitfalls") == 1
    r = gate_on(freezer, gate, make_skill, tmp_path, original, TAG, demoted)
    assert "PROMINENCE_LOST" in codes(r), r["rejected"]
    honest = gate_on(freezer, gate, make_skill, tmp_path, original, TAG, original.replace(EXPLANATION, ""))
    assert honest["status"] == "pass", honest["rejected"]


def test_a_new_reference_may_not_take_a_name_the_skill_already_uses(freezer, gate, make_skill, tmp_path):
    # Bug caught: accepting a new references/<name>.md whose path is a link (or a
    # dangling link) in the installed skill, which the snapshot skipped, so applying
    # the candidate would write through that link or replace it.
    orig = make_skill(ORIGINAL)
    (orig / "references").mkdir()
    (orig / "references" / "linked.md").symlink_to(_secret(tmp_path))
    (orig / "references" / "stale.md").symlink_to(tmp_path / "nowhere.md")
    frozen = freezer.freeze(orig, REQS)
    body = ORIGINAL.replace(TROUBLESHOOTING, "Read `references/{}.md` when a build fails.\n\n")
    for name, ok in (("linked", False), ("stale", False), ("fresh", True)):
        cand = tmp_path / f"candidate-{name}"
        cand.mkdir()
        fm = "---\nname: demo\ndescription: Use when testing.\n---\n"
        (cand / "SKILL.md").write_text(fm + body.format(name), encoding="utf-8")
        (cand / "references").mkdir()
        (cand / "references" / f"{name}.md").write_text(TROUBLESHOOTING, encoding="utf-8")
        r = gate.verify(frozen, cand, orig)
        clash = [f["detail"] for f in r["rejected"] if f["code"] == "UNEXPECTED_FILE"]
        assert clash == ([] if ok else [f"references/{name}.md exists in the skill as a link or file; choose another name"]), name


FIT = (EXPLANATION + "1. **Does it fit?** Use the fit rule (GiB; peak + cache + ~1 GiB; ≤ 23 fits,\n"
       "   > 27 fails). Take the peak from the profile.\n\nTag the release after the merge.\n")


def test_a_bound_wrapped_to_a_quote_marker_is_protected(freezer, gate, make_skill, tmp_path):
    # Bug caught: reading the `>` of "   > 27 fails)." as a quote marker only, so
    # the bound is never frozen: the sentence carries no rule word, and deleting
    # it passes, as does changing 27 to 25 wherever the new number is not new text.
    honest = FIT.replace(EXPLANATION, "")
    r = gate_on(freezer, gate, make_skill, tmp_path, FIT, TAG, honest)
    assert r["status"] == "pass", r["rejected"]
    for edited in (honest.replace("> 27", "> 25"), honest.replace("> 27 fails). ", "> ")):
        r = gate_on(freezer, gate, make_skill, tmp_path, FIT, TAG, edited)
        assert "'> 27 fails' is gone or changed" in [f["detail"] for f in r["rejected"]], r["rejected"]


QUOTED = EXPLANATION + "> Keep the margin under 20\n> GiB at all times.\n\nTag the release after the merge.\n"


def test_a_literal_wrapped_inside_a_quote_is_found_and_protected(freezer, gate, make_skill, tmp_path):
    # Bug caught: freezing `under 20 GiB` from a quote but searching the raw file,
    # where a `>` sits between `20` and `GiB`, so the unchanged skill is rejected;
    # or dropping it, so `GiB` can become `MiB`.
    orig = make_skill(QUOTED)
    assert "under 20 GiB" in freezer.freeze(orig, TAG)["literals"]
    assert gate_on(freezer, gate, make_skill, tmp_path, QUOTED, TAG, QUOTED)["status"] == "unchanged"
    edited = QUOTED.replace(EXPLANATION, "").replace("> GiB", "> MiB")
    r = gate_on(freezer, gate, make_skill, tmp_path, QUOTED, TAG, edited)
    assert "'under 20 GiB' is gone or changed" in [f["detail"] for f in r["rejected"]], r["rejected"]


MARGIN_A = "The safety margin is under 20"
MARGIN_B = "GiB, and that is the budget."
MARGIN = EXPLANATION + MARGIN_A + "\n\n" + MARGIN_B + "\n\nTag the release after the merge.\n"
PAIR = MARGIN_A + "\n\n" + MARGIN_B + "\n\n"


def test_a_literal_across_two_sentences_records_them(freezer, make_skill):
    # Bug caught: freezing no contributing sentences for a literal no single
    # sentence holds, so the gate has nothing to approve it through.
    spans = freezer.freeze(make_skill(MARGIN), TAG)["literal_spans"]
    assert spans["under 20 GiB"] == [["The safety margin is under 20", "GiB, and that is the budget"]]


def test_a_literal_across_two_approved_sentences_is_approved(freezer, gate, make_skill, tmp_path):
    # Bug caught: looking for one sentence holding the whole literal, so deleting
    # both halves of `under 20` / `GiB` with the user's approval is still LITERAL_LOST.
    candidate = MARGIN.replace(EXPLANATION, "").replace(PAIR, "")
    r = gate_on(freezer, gate, make_skill, tmp_path, MARGIN, TAG, candidate, approved=[MARGIN_A, MARGIN_B])
    assert r["status"] == "pass", r["rejected"]
    assert "literal: under 20 GiB" in r["approved_deletions"]


@pytest.mark.parametrize("gone,approved", [
    (MARGIN_B + "\n\n", []),                  # one half deleted, nothing approved
    (MARGIN_B + "\n\n", [MARGIN_B]),          # one half deleted with approval, the other kept
    (PAIR, [MARGIN_B]),                       # both deleted, only one approved
], ids=["unapproved", "half-approved-half-kept", "one-of-two-approved"])
def test_a_literal_across_two_sentences_needs_both_approved(freezer, gate, make_skill, tmp_path, gone, approved):
    # Bug caught: approving the literal once any contributing sentence is approved,
    # so `under 20` is left without its unit, or goes with an unapproved sentence.
    candidate = MARGIN.replace(EXPLANATION, "").replace(gone, "")
    r = gate_on(freezer, gate, make_skill, tmp_path, MARGIN, TAG, candidate, approved=approved)
    assert "'under 20 GiB' is gone or changed" in [f["detail"] for f in r["rejected"]], r["rejected"]


def test_a_literal_across_two_sentences_moved_together_asks(freezer, gate, make_skill, tmp_path):
    # Bug caught: rejecting a literal whose sentences moved together into one
    # reference (here as two list items, so a "- " now sits inside it) instead of
    # asking; or passing it silently.
    body = MARGIN.replace(EXPLANATION, "").replace(PAIR, "Read `references/margin.md` when sizing.\n\n")
    ref = "- " + MARGIN_A + "\n- " + MARGIN_B + "\n"
    gate_on(freezer, gate, make_skill, tmp_path, MARGIN, TAG, body)   # writes the candidate
    cand = tmp_path / "candidate"
    (cand / "references").mkdir()
    (cand / "references" / "margin.md").write_text(ref, encoding="utf-8")
    r = gate.verify(freezer.freeze(tmp_path / "original", TAG), cand, tmp_path / "original")
    assert r["status"] == "needs_confirmation", r["rejected"]
    # `20 GiB` and `under 20 GiB` both run across the pair
    assert sorted((c["code"], c["file"], c["detail"].split(" ran across")[0]) for c in r["confirm"]) == [
        ("MOVED_TO_REFERENCE", "references/margin.md", "'20 GiB'"),
        ("MOVED_TO_REFERENCE", "references/margin.md", "'under 20 GiB'")]
    # split between the body and a reference, it is lost, not moved
    split = MARGIN.replace(EXPLANATION, "").replace(MARGIN_B, "Read `references/margin.md` when sizing.")
    (cand / "SKILL.md").write_text("---\nname: demo\ndescription: Use when testing.\n---\n" + split, encoding="utf-8")
    (cand / "references" / "margin.md").write_text("- " + MARGIN_B + "\n", encoding="utf-8")
    r = gate.verify(freezer.freeze(tmp_path / "original", TAG), cand, tmp_path / "original")
    assert "'under 20 GiB' is gone or changed" in [f["detail"] for f in r["rejected"]], r["rejected"]


@pytest.mark.parametrize("ref,note", [
    ("- " + MARGIN_A + "\n- " + MARGIN_B + "\n", False),     # same order, still next to each other
    (MARGIN_B + "\n\n" + MARGIN_A + "\n", True),             # order swapped
], ids=["adjacent", "swapped"])
def test_a_spanning_literal_ask_says_where_it_went(freezer, gate, make_skill, tmp_path, ref, note):
    # Bug caught: an ask that says the sentences "moved together" when they only
    # landed in the same file, so the user approves a move that broke their order.
    body = MARGIN.replace(EXPLANATION, "").replace(PAIR, "Read `references/margin.md` when sizing.\n\n")
    gate_on(freezer, gate, make_skill, tmp_path, MARGIN, TAG, body)   # writes the candidate
    cand = tmp_path / "candidate"
    (cand / "references").mkdir()
    (cand / "references" / "margin.md").write_text(ref, encoding="utf-8")
    r = gate.verify(freezer.freeze(tmp_path / "original", TAG), cand, tmp_path / "original")
    details = [c["detail"] for c in r["confirm"] if c["detail"].startswith("'under 20 GiB'")]
    assert len(details) == 1 and "moved into the same reference" in details[0], r["confirm"]
    assert ("(not adjacent)" in details[0]) == note, details


def test_a_freeze_without_literal_spans_is_still_read(freezer, gate, make_skill, tmp_path):
    # Bug caught: indexing frozen["literal_spans"], so a freeze written before the
    # field existed fails with a KeyError instead of gating as it used to.
    orig = make_skill(MARGIN)
    frozen = freezer.freeze(orig, TAG)
    del frozen["literal_spans"]
    assert gate.verify(frozen, orig, orig)["status"] == "unchanged"


LOUD = (EXPLANATION + "- **Never** force-push to `main`.\n"
        "- *Always* read the changelog before tagging a release.\n"
        "- __Check the signing key__ on the release host first.\n\nTag the release after the merge.\n")
LOUD_REQS = TAG + "R2: Check the key.\n  anchor: on the release host first\n"


def emphasis_asks(r):
    return [(c["code"], c["file"]) for c in r["confirm"] if c["code"] == "EMPHASIS_LOST"]


@pytest.mark.parametrize("old,new", [
    ("**Never**", "Never"),                                   # bold off a strong rule
    ("*Always*", "Always"),                                   # italic off a rule
    ("__Check the signing key__", "Check the signing key"),   # bold off an anchored sentence
    ("**Never**", "*Never*"),                                 # bold weakened to italic
    ("__Check the signing key__", "*Check the signing key*"),  # underscore bold weakened, several words
], ids=["bold", "italic", "anchored", "weakened", "weakened-underscore"])
def test_emphasis_stripped_from_a_rule_asks_the_user(freezer, gate, make_skill, tmp_path, old, new):
    # Bug caught: comparing sentences with emphasis removed, so a candidate that
    # strips the bold off a rule's lead-in passes unchanged and the author's
    # salience signal is gone without anyone deciding it may go.
    candidate = LOUD.replace(EXPLANATION, "").replace(old, new)
    r = gate_on(freezer, gate, make_skill, tmp_path, LOUD, LOUD_REQS, candidate)
    assert r["status"] == "needs_confirmation", r["rejected"]
    assert emphasis_asks(r) == [("EMPHASIS_LOST", "SKILL.md")], r["confirm"]


def test_emphasis_kept_or_added_passes(freezer, gate, make_skill, tmp_path):
    # Bug caught: flagging every emphasised sentence, or any change of markup, so an
    # honest cut or an added bold asks the user for nothing.
    assert gate_on(freezer, gate, make_skill, tmp_path, LOUD, LOUD_REQS, LOUD)["status"] == "unchanged"
    honest = LOUD.replace(EXPLANATION, "")
    assert gate_on(freezer, gate, make_skill, tmp_path, LOUD, LOUD_REQS, honest)["status"] == "pass"
    louder = honest.replace("**Never** force-push", "**Never force-push**").replace(
        "Tag the release after", "**Tag** the release after")
    r = gate_on(freezer, gate, make_skill, tmp_path, LOUD, LOUD_REQS, louder)
    assert r["status"] == "pass", (r["rejected"], r["confirm"])


def test_emphasis_lost_exits_3_and_is_listed(freezer, gate, make_skill, tmp_path, capsys):
    # Bug caught: recording EMPHASIS_LOST but exiting 0, or leaving it out of the
    # printed list, so the workflow applies the candidate without asking.
    orig = make_skill(LOUD)
    frozen_path = tmp_path / "frozen.json"
    frozen_path.write_text(json.dumps(freezer.freeze(orig, LOUD_REQS)), encoding="utf-8")
    cand = tmp_path / "candidate"
    shutil.copytree(orig, cand)
    skill = cand / "SKILL.md"
    skill.write_text(skill.read_text(encoding="utf-8").replace(EXPLANATION, "").replace("**Never**", "Never"),
                     encoding="utf-8")
    assert gate.main(["--frozen", str(frozen_path), "--original", str(orig), "--candidate", str(cand)]) == 3
    assert "ASK EMPHASIS_LOST (SKILL.md): " in capsys.readouterr().out


def test_emphasis_is_checked_in_a_reference_and_without_a_recorded_field(freezer, gate, make_skill, tmp_path):
    # Bug caught: checking emphasis in the body only, so a rule moved into a
    # reference can lose its bold on the way; or indexing frozen["emphasis"], so a
    # freeze written before the field existed stops the gate with a KeyError.
    orig = make_skill(LOUD)
    frozen = freezer.freeze(orig, LOUD_REQS)
    del frozen["emphasis"]
    cand = tmp_path / "candidate"
    shutil.copytree(orig, cand)
    body = LOUD.replace(EXPLANATION, "").replace("- **Never** force-push to `main`.\n",
                                                 "- Read `references/push.md` before pushing.\n")
    (cand / "SKILL.md").write_text("---\nname: demo\ndescription: Use when testing.\n---\n" + body, encoding="utf-8")
    (cand / "references").mkdir()
    (cand / "references" / "push.md").write_text("Never force-push to `main`.\n", encoding="utf-8")
    r = gate.verify(frozen, cand, orig)
    assert emphasis_asks(r) == [("EMPHASIS_LOST", "references/push.md")], r["confirm"]


def test_emphasis_is_checked_where_the_sentence_lives(freezer, gate, make_skill, tmp_path):
    # Bug caught: pooling emphasis over the body and every new reference, so a rule
    # whose body copy lost its bold passes because a bold copy sits in a reference.
    body = (LOUD.replace(EXPLANATION, "").replace("**Never**", "Never")
            .replace("Tag the release", "Read `references/push.md` before pushing.\n\nTag the release"))
    gate_on(freezer, gate, make_skill, tmp_path, LOUD, LOUD_REQS, body)   # writes the candidate
    cand = tmp_path / "candidate"
    (cand / "references").mkdir()
    (cand / "references" / "push.md").write_text("**Never** force-push to `main`.\n", encoding="utf-8")
    r = gate.verify(freezer.freeze(tmp_path / "original", LOUD_REQS), cand, tmp_path / "original")
    assert r["status"] == "needs_confirmation", r["rejected"]
    assert emphasis_asks(r) == [("EMPHASIS_LOST", "SKILL.md")], r["confirm"]


LOUD_HEAD = "# Guide\n\n" + EXPLANATION + "## **Never** skip the tests\n\nRun the suite.\n\nTag the release after the merge.\n"


@pytest.mark.parametrize("marked", ["**Never**", "__Never__", "_Never_"])
def test_emphasis_on_a_rule_heading_is_checked(freezer, gate, make_skill, tmp_path, marked):
    # Bug caught: recording emphasis for sentences only, so "## **Never** skip the
    # tests" can lose its bold and still pass; and testing the raw heading for a rule
    # word, where `_` joins the word, so "## __Never__ skip" is not a rule heading.
    loud = LOUD_HEAD.replace("**Never**", marked)
    stripped = loud.replace(EXPLANATION, "").replace("## " + marked, "## Never")
    r = gate_on(freezer, gate, make_skill, tmp_path, loud, TAG, stripped)
    assert r["status"] == "needs_confirmation", r["rejected"]
    assert emphasis_asks(r) == [("EMPHASIS_LOST", "SKILL.md")], r["confirm"]
    assert gate_on(freezer, gate, make_skill, tmp_path, loud, TAG, loud)["status"] == "unchanged"


def test_an_underscore_emphasised_rule_heading_is_protected(freezer, gate, make_skill, tmp_path):
    # Bug caught: is_rule() on the raw heading, where `__Never__` has no word
    # boundary, so the heading can be deleted with only SECTION_CHANGED.
    orig = make_skill(EXPLANATION + "## __Never__ on Fridays\n\nDeploy with the script.\n")
    frozen = freezer.freeze(orig, "R1: Deploy.\n  anchor: Deploy with the script\n")
    cand = tmp_path / "candidate"
    shutil.copytree(orig, cand)
    (cand / "SKILL.md").write_text((orig / "SKILL.md").read_text(encoding="utf-8")
                                   .replace(EXPLANATION, "").replace("## __Never__ on Fridays\n\n", ""),
                                   encoding="utf-8")
    assert "RULE_LOST" in codes(gate.verify(frozen, cand, orig))


WRAPPED_QUOTE = EXPLANATION + "> Keep the cache small\n> and clear it often.\n\nTag the release after the merge.\n"


@pytest.mark.parametrize("body,code", [(WRAPPED_QUOTE, 2), (LOUD, 0)], ids=["wrapped-quote", "no-quote"])
def test_an_older_freeze_of_a_wrapped_quote_asks_for_a_new_freeze(freezer, gate, make_skill, tmp_path, capsys,
                                                                   body, code):
    # Bug caught: gating a 1.0.x freeze (no emphasis or literal_spans fields) against
    # a skill whose blockquote wraps over two lines. 1.0.x read each `>` line as its
    # own sentence; this version joins them, so the unchanged skill is rejected.
    orig = make_skill(body)
    frozen = freezer.freeze(orig, TAG)
    for field in ("emphasis", "literal_spans"):
        del frozen[field]
    frozen_path = tmp_path / "frozen.json"
    frozen_path.write_text(json.dumps(frozen), encoding="utf-8")
    assert gate.main(["--frozen", str(frozen_path), "--original", str(orig), "--candidate", str(orig)]) == code
    err = capsys.readouterr().err
    assert ("freeze the original again" in err) == (code == 2), err


def test_an_older_freeze_that_split_the_text_differently_asks_for_a_new_freeze(freezer, gate, make_skill,
                                                                              tmp_path, capsys):
    # Bug caught: detecting only wrapped quotes, so a 1.0.x freeze whose sentences
    # were split another way (a `>` indented as a list continuation) rejects the
    # unchanged skill with NEW_TEXT / RULE_LOST instead of asking for a new freeze.
    orig = make_skill(LOUD)
    frozen = freezer.freeze(orig, TAG)
    for field in ("emphasis", "literal_spans"):
        del frozen[field]
    frozen["sentences"] = sorted(frozen["sentences"] + ["27 never)."])  # a split 1.0.x made
    frozen_path = tmp_path / "frozen.json"
    frozen_path.write_text(json.dumps(frozen), encoding="utf-8")
    assert gate.main(["--frozen", str(frozen_path), "--original", str(orig), "--candidate", str(orig)]) == 2
    assert "freeze the original again" in capsys.readouterr().err
