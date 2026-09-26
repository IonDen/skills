"""Seeded sabotage and honest edits, on the eval fixture and on real skills.

A gate that has never caught a planted defect has no evidence of working, and a
gate that has never passed an honest cut is useless. Each mutation below must be
rejected by name on every skill it applies to; each honest edit must pass."""
import re
import shutil
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
FIXTURE = ROOT / "evals" / "skill-optimizer" / "fixtures" / "release-checklist" / "SKILL.fixture.md"
SKILLS = {
    "fixture": FIXTURE,
    "subagent-optimizer": ROOT / "skills" / "subagent-optimizer" / "SKILL.md",
    "skill-optimizer": ROOT / "skills" / "skill-optimizer" / "SKILL.md",
}


def span(body, text):
    """Locate a sentence in the raw body, across line wraps, list markers and emphasis."""
    words = ["[*_]*" + "[*_]*".join(re.escape(c) for c in w) + "[*_]*" for w in text.split()]
    return re.search(r"\s+".join(words), body)


def rules(skillmd, body, strong=False):
    sents = skillmd.sentences(body)
    counts = {}
    for s in sents:
        counts[s["key"]] = counts.get(s["key"], 0) + 1
    tail = {s["key"] for s in sents[-3:]}
    return [s for s in sents if skillmd.is_rule(s["key"]) and counts[s["key"]] == 1
            and s["key"] not in tail and (skillmd.is_strong(s["key"]) or not strong)
            and span(body, s["text"])]


def cut(body, m, replacement=""):
    return body[:m.start()] + replacement + body[m.end():]


def m_delete_strong_rule(sk, body):
    r = rules(sk, body, strong=True)
    return r and cut(body, span(body, r[0]["text"]))


def m_delete_weak_rule(sk, body):
    r = [s for s in rules(sk, body) if not sk.is_strong(s["key"])]
    return r and cut(body, span(body, r[0]["text"]))


def m_flip_negation(sk, body):
    for s in rules(sk, body):
        m = span(body, s["text"])
        new = re.sub(r"\b(?:not|n't)\b ?", "", m.group(0), count=1, flags=re.I)
        if new != m.group(0):
            return cut(body, m, new)


def m_weaken(sk, body):
    for s in rules(sk, body, strong=True):
        m = span(body, s["text"])
        new = re.sub(r"\b(?:NEVER|never|MUST|must|ALWAYS|always)\b", "rarely", m.group(0), count=1)
        if new != m.group(0):
            return cut(body, m, new)


def m_drop_exception(sk, body):
    for s in rules(sk, body):
        m = span(body, s["text"])
        new = re.sub(r",?\s+(?:unless|except)\b[^.]*", "", m.group(0), count=1, flags=re.I)
        if new != m.group(0):
            return cut(body, m, new)


def m_drop_literal(sk, body):
    for lit in sk.literals(body):
        hits = [m for m in re.finditer(re.escape("`" + lit + "`"), body)]
        if len(hits) == 1 and sum(1 for other in sk.literals(body) if lit in other) == 1:
            return cut(body, hits[0], "it")


def m_change_threshold(sk, body):
    m = sk.THRESHOLD_RE.search(body)
    if m:
        number = re.search(r"\d+", m.group(0))
        return cut(body, m, m.group(0).replace(number.group(0), str(int(number.group(0)) + 1), 1))


def m_demote_strong_rule(sk, body):
    r = rules(sk, body, strong=True)
    if r:
        m = span(body, r[0]["text"])
        return cut(body, m).rstrip("\n") + "\n\n" + m.group(0) + "\n"


def m_invent_sentence(sk, body):
    first = next(u for u in sk.units(body) if u["kind"] == "text")
    m = span(body, first["text"])
    return cut(body, m, m.group(0) + " You may skip the tests when in a hurry.")


def m_edit_example(sk, body):
    m = re.search(r"```(?:markdown|md|text|yaml|json)\n(.+?)\n```", body, re.S)
    if m:
        return body[:m.start(1)] + m.group(1) + " (edited)" + body[m.end(1):]


MUTATIONS = {
    "delete a strong rule": (m_delete_strong_rule, "RULE_LOST"),
    "delete a weak rule": (m_delete_weak_rule, "RULE_LOST"),
    "flip a negation": (m_flip_negation, "RULE_LOST"),
    "weaken a strong rule": (m_weaken, "RULE_LOST"),
    "drop an exception": (m_drop_exception, "RULE_LOST"),
    "drop a command or flag": (m_drop_literal, "LITERAL_LOST"),
    "change a threshold": (m_change_threshold, "LITERAL_LOST"),
    "demote a strong rule": (m_demote_strong_rule, "PROMINENCE_LOST"),
    "invent a sentence": (m_invent_sentence, "NEW_TEXT"),
    "edit a kept example": (m_edit_example, "CODE_EDITED"),
}


@pytest.fixture
def setup(freezer, gate, skillmd, tmp_path):
    def _setup(skill):
        src = SKILLS[skill]
        orig = tmp_path / "original"
        if src.name == "SKILL.md":
            shutil.copytree(src.parent, orig, ignore=shutil.ignore_patterns("__pycache__"))
        else:
            orig.mkdir()
            shutil.copy(src, orig / "SKILL.md")
        fm, body = skillmd.split_frontmatter(skillmd.read_text(orig / "SKILL.md"))
        keys = [s["key"] for s in skillmd.sentences(body)]
        fit = [k for k in keys if not skillmd.is_rule(k) and len(k.split()) >= 4 and keys.count(k) == 1]
        anchor = next((k for k in fit if "`" in k), fit[0])   # prefer a real instruction
        frozen = freezer.freeze(orig, f"R1: The skill keeps its first instruction.\n  anchor: {anchor}\n")
        cand = tmp_path / "candidate"
        shutil.copytree(orig, cand)

        def check(new_body, new_fm=None, files=None, approved=None):
            (cand / "SKILL.md").write_text((new_fm or fm) + new_body, encoding="utf-8")
            for rel, t in (files or {}).items():
                (cand / rel).parent.mkdir(parents=True, exist_ok=True)
                (cand / rel).write_text(t, encoding="utf-8")
            return gate.verify(frozen, cand, orig, approved)
        return body, fm, check, anchor
    return _setup


@pytest.mark.parametrize("name", sorted(MUTATIONS))
def test_the_fixture_supports_every_mutation(skillmd, name):
    # Bug caught: a mutation that silently finds nothing to mutate, so its test proves nothing.
    _, body = skillmd.split_frontmatter(skillmd.read_text(FIXTURE))
    mutated = MUTATIONS[name][0](skillmd, body)
    assert mutated and mutated != body


@pytest.mark.parametrize("skill", sorted(SKILLS))
@pytest.mark.parametrize("name", sorted(MUTATIONS))
def test_each_mutation_is_rejected_by_name(setup, skillmd, skill, name):
    # Bug caught: a gate that passes a planted defect in a real skill.
    body, _, check, _ = setup(skill)
    mutate, code = MUTATIONS[name]
    mutated = mutate(skillmd, body)
    if not mutated:
        pytest.skip(f"{skill} has nothing for '{name}' to mutate")
    r = check(mutated)
    assert r["status"] == "rejected" and code in {f["code"] for f in r["rejected"]}, r["rejected"]


@pytest.mark.parametrize("skill", sorted(SKILLS))
def test_frontmatter_edit_is_rejected(setup, skill):
    # Bug caught: a gate that reads only the body of a real skill.
    body, fm, check, _ = setup(skill)
    r = check(body, new_fm=fm.replace("description:", "description: Tweaked.", 1))
    assert "FRONTMATTER_CHANGED" in {f["code"] for f in r["rejected"]}


@pytest.mark.parametrize("skill", sorted(SKILLS))
def test_moving_a_strong_rule_asks_the_user(setup, skillmd, skill):
    # Bug caught: a rule leaving the body without the user's say.
    body, _, check, _ = setup(skill)
    rule = rules(skillmd, body, strong=True)[0]
    m = span(body, rule["text"])
    r = check(cut(body, m, "See `references/moved.md`."), files={"references/moved.md": m.group(0) + "\n"})
    assert r["status"] == "needs_confirmation", r["rejected"]


@pytest.mark.parametrize("skill", sorted(SKILLS))
def test_identity_is_unchanged(setup, skill):
    # Bug caught: a false reject on a real skill that nobody touched.
    body, _, check, _ = setup(skill)
    assert check(body)["status"] == "unchanged"


@pytest.mark.parametrize("skill", sorted(SKILLS))
def test_cutting_unprotected_text_passes(setup, skillmd, skill):
    # Bug caught: a gate that rejects deleting a paragraph with no rule word,
    # literal or anchor in it, which is where every legitimate cut happens.
    # Passing here is not a verdict that the cut was wise: a plain instruction with
    # no rule word is protected only by its anchor in requirements.md, which is
    # why the workflow lists unprotected sentences before the freeze.
    body, _, check, anchor = setup(skill)
    literals = skillmd.literals(body)
    tail = {s["key"] for s in skillmd.sentences(body)[-3:]}
    for u in skillmd.units(body):
        if u["kind"] != "text" or skillmd.is_rule(u["text"]) or "`" in u["text"]:
            continue
        keys = {s["key"] for s in skillmd.sentences(u["text"])}
        if any(skillmd.contains_literal(u["text"], lit) for lit in literals) or keys & (tail | {anchor}):
            continue
        m = span(body, u["text"])
        if m:
            r = check(cut(body, m))
            assert r["status"] == "pass", (u["text"], r["rejected"])
            return
    pytest.fail(f"{skill} has no paragraph free of rules, literals and anchors to cut")


WHY = FIXTURE.read_text(encoding="utf-8").split("## Why this skill exists\n", 1)[1].split("## Rules\n", 1)[0]
SECOND_EXAMPLE = ("Here is another example of a good changelog entry:\n\n```markdown\n## v1.3.1 (2026-02-11)\n\n"
                  "- Fixed the version shown by the help screen.\n```\n\n")
MENU = ("You can write the changelog entry in several ways. You could use Keep a\nChangelog headings (Added, "
        "Changed, Fixed). You could use a flat bullet list.\nYou could write a short paragraph. ")
TROUBLESHOOTING = FIXTURE.read_text(encoding="utf-8").split("## Troubleshooting\n", 1)[1].split("## Reminder\n", 1)[0]

# A motivation sentence that happens to carry a rule word ("nothing") may only go
# with the user's approval of that exact sentence.
MOTIVATION_RULE = ("This skill exists to make sure that every release follows the same steps in the "
                   "same order, so that nothing important is forgotten.")
DROP_WHY = lambda b: b.replace("## Why this skill exists\n" + WHY, "")  # noqa: E731

HONEST_EDITS = {
    "drop the motivation and definition sections, with approval": (DROP_WHY, {}, [MOTIVATION_RULE], "pass"),
    "drop the motivation and definition sections, without approval": (DROP_WHY, {}, None, "rejected"),
    "drop the second example": (lambda b: b.replace(SECOND_EXAMPLE, ""), {}, None, "pass"),
    "collapse the option menu, keeping its rule": (lambda b: b.replace(MENU, ""), {}, None, "pass"),
    "move troubleshooting behind a load line": (
        lambda b: b.replace("## Troubleshooting\n" + TROUBLESHOOTING,
                            "Read `references/troubleshooting.md` when a release step fails.\n\n"),
        {"references/troubleshooting.md": "## Troubleshooting\n" + TROUBLESHOOTING}, None, "needs_confirmation"),
}


@pytest.mark.parametrize("name", sorted(HONEST_EDITS))
def test_honest_edits_on_the_fixture(setup, name):
    # Bug caught: a false reject on the cuts what-not-to-cut.md calls safe; a rule
    # sentence deleted without the user's approval; or a section with rule words
    # moved without asking.
    body, _, check, _ = setup("fixture")
    edit, files, approved, status = HONEST_EDITS[name]
    edited = edit(body)
    assert edited != body, "the edit did not change the fixture"
    r = check(edited, files=files, approved=approved)
    assert r["status"] == status, r["rejected"]
    if status == "rejected":
        assert [f["code"] for f in r["rejected"]] == ["RULE_LOST"]
