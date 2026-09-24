"""skill-optimizer shared parsing. Each test names the one-line bug that would make it fail."""


def keys(skillmd, body):
    return [s["key"] for s in skillmd.sentences(body)]


def test_soft_wrapped_paragraph_is_one_unit(skillmd):
    # Bug caught: splitting sentences per physical line, so reflowing a paragraph
    # changes every key and the gate reads a reflow as an edit.
    wrapped = "Run the tests before\nyou open a pull request. Then wait.\n"
    one_line = "Run the tests before you open a pull request. Then wait.\n"
    assert keys(skillmd, wrapped) == keys(skillmd, one_line) == [
        "Run the tests before you open a pull request", "Then wait"]


def test_list_markers_are_not_sentences(skillmd):
    # Bug caught: leaving "1." on the item, so the sentence splitter makes "1" a sentence.
    assert keys(skillmd, "1. Run x.\n2. Run y.\n- Run z.\n") == ["Run x", "Run y", "Run z"]


def test_code_fence_lines_are_not_sentences(skillmd):
    # Bug caught: not tracking fences, so a heading-like line inside a code block
    # ("## v1.0") becomes a heading and code becomes prose.
    body = "Intro.\n\n```markdown\n## v1.0\nNEVER shown as prose.\n```\n\nAfter.\n"
    kinds = [(u["kind"], u["text"]) for u in skillmd.units(body)]
    assert ("code", "## v1.0") in kinds and ("code", "NEVER shown as prose.") in kinds
    assert keys(skillmd, body) == ["Intro", "After"]


def test_emphasis_and_final_punctuation_do_not_change_the_key(skillmd):
    # Bug caught: comparing raw text, so bolding a rule reads as editing it.
    assert skillmd.normalise("**NEVER** push to *main*.") == skillmd.normalise("NEVER push to main")


def test_inline_code_survives_emphasis_stripping(skillmd):
    # Bug caught: stripping ** and __ everywhere, so backticked `__init__.py` loses
    # its underscores and the gate ends up quoting text the user's SKILL.md never had.
    assert "__init__.py" in skillmd.normalise("Edit `__init__.py` carefully.")
    s = skillmd.sentences("Edit `__init__.py` carefully.\n")[0]
    assert "__init__.py" in s["key"] and "__init__.py" in s["text"]


def test_emphasis_does_not_change_sentence_boundaries(skillmd):
    # Bug caught: splitting sentences before removing emphasis, so "**Label.** Rest"
    # is one sentence but "Label. Rest" is two, and un-bolding a label reads as a lost rule.
    # Single-marker emphasis (*Label.* / _Label._) has the same boundary bug as bold.
    bold = "- **Kept exactly.** Never edit it.\n"
    italic = "- *Kept exactly.* Never edit it.\n"
    plain = "- Kept exactly. Never edit it.\n"
    assert [s["key"] for s in skillmd.sentences(bold)] == [s["key"] for s in skillmd.sentences(italic)] \
        == [s["key"] for s in skillmd.sentences(plain)] == ["Kept exactly", "Never edit it"]
    assert skillmd.order(bold) == skillmd.order(italic) == skillmd.order(plain)


def test_rule_words_match_in_any_case(skillmd):
    # Bug caught: a case-sensitive rule pattern, which misses either "NEVER"/"MUST"
    # or "is not"/"don't", so those rules can be flipped or dropped unnoticed.
    for s in ("NEVER push to main", "You MUST pin it", "ONLY on Fridays",
              "Tests are not optional", "Don't edit generated files",
              "Use it only if asked", "Run it unless told otherwise", "You should pin it",
              "No force pushes", "The exception is a hotfix release", "Merge without approval",
              "Avoid the cache", "Wait until CI is green", "Push even if it is late"):
        assert skillmd.is_rule(s), s
    assert not skillmd.is_rule("Read the docs before starting")
    assert not skillmd.is_rule("If the build fails, ask the maintainer")


def test_rule_words_inside_inline_code_do_not_count(skillmd):
    # Bug caught: an error message in backticks ("No module named build") turning an
    # ordinary sentence into a rule, which then cannot be moved without asking.
    assert not skillmd.is_rule("If the build fails with `No module named build`, install it")


def test_strong_rules(skillmd):
    # Bug caught: treating "should" as strong, which would pin every soft suggestion in place.
    assert skillmd.is_strong("NEVER force-push") and skillmd.is_strong("do not delete it")
    assert not skillmd.is_strong("You should pin it")


def test_literals_capture_bare_text_and_skip_prose(skillmd):
    # Bug caught: a literal pattern that only sees backticked text, or one so broad
    # that "and/or" and "Step 1" become literals and block honest edits.
    body = (
        "Pass --max-failures=1 and write to src/app/ or ~/.cache/tool.\n"
        "Pin mlx==0.32.0. Keep usage under 20 GiB. See https://example.com/docs.\n"
        "Step 1: pick one and/or the other.\n\n"
        "```bash\npython3 -m build\n```\n"
    )
    lits = set(skillmd.literals(body))
    for expected in ("--max-failures=1", "src/app/", "~/.cache/tool", "mlx==0.32.0",
                     "under 20 GiB", "https://example.com/docs", "python3 -m build"):
        assert expected in lits, expected
    more = set(skillmd.literals("Retry at most 3 times on Python 3.10 or Claude Code 2.1.252+, "
                                "keep bodies >~150 lines, changed 2026-05-17.\n"))
    for expected in ("at most 3 times", "3.10", "2.1.252+", ">~150 lines", "2026-05-17"):
        assert expected in more, expected
    assert "and/or" not in lits and "1" not in lits


def test_example_fences_are_not_literals(skillmd):
    # Bug caught: freezing example code, so a duplicate example can never be cut.
    body = "```markdown\n## v1.4.0\n- Added `--json` output.\n```\n"
    assert skillmd.literals(body) == []


def test_contains_literal_respects_token_boundaries(skillmd):
    # Bug caught: a plain substring test, so a lost literal "survives" inside a longer token.
    assert not skillmd.contains_literal("Keep it under 120 GiB", "under 20 GiB")
    assert not skillmd.contains_literal("run pytest -qq now", "pytest -q")
    assert not skillmd.contains_literal("maintain the branch", "main")
    assert not skillmd.contains_literal("fetch origin/main first", "main")
    assert not skillmd.contains_literal("tag `release/vX.Y.Z`", "vX.Y.Z")
    assert skillmd.contains_literal("Never push to `main`.", "main")
    assert skillmd.contains_literal("Keep it\nunder 20 GiB.", "under 20 GiB")


def test_frontmatter_split_handles_crlf_and_no_final_newline(skillmd):
    # Bug caught: a frontmatter pattern that needs "\n" after the closing fence,
    # so CRLF files and body-less files are read as all body.
    assert skillmd.split_frontmatter("---\r\nname: a\r\n---\r\nBody\r\n") == ("---\r\nname: a\r\n---\r\n", "Body\r\n")
    assert skillmd.split_frontmatter("---\nname: a\n---") == ("---\nname: a\n---", "")
    assert skillmd.split_frontmatter("No frontmatter.\n") == ("", "No frontmatter.\n")


def test_tokens_allow_clause_deletion_but_not_new_words(skillmd):
    # Bug caught: a subsequence test that ignores order or punctuation, so either
    # an honest clause cut is refused or a reworded sentence slips through.
    orig = skillmd.tokens("Run the tests, then open the pull request")
    assert skillmd.is_subsequence(skillmd.tokens("Run the tests"), orig)
    assert skillmd.is_subsequence(skillmd.tokens("then open the pull request"), orig)
    assert not skillmd.is_subsequence(skillmd.tokens("Open the pull request, then run the tests"), orig)
    assert not skillmd.is_subsequence(skillmd.tokens("Run the tests quickly"), orig)


def test_code_blocks_keep_their_lines_together(skillmd):
    # Bug caught: comparing code line by line, so editing one line of a kept block
    # still matches some original line and passes.
    body = "```yaml\na: 1\nb: 2\n```\n\nText.\n\n```bash\nmake\n```\n"
    assert skillmd.code_blocks(body) == [{"lang": "yaml", "text": "a: 1\nb: 2"}, {"lang": "bash", "text": "make"}]
