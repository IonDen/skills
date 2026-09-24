"""skill-optimizer shared parsing. Each test names the one-line bug that would make it fail."""
from pathlib import Path

import pytest


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


@pytest.mark.parametrize("body", [
    "Pinned to https://github.com/openai/codex/blob/rust-v0.156.1/x.rs and rust-v0.156.1 in prose.",
    "Use python-3.12 or node-18.2 on the runner.",
    "Logs land in build-2026-09-24.txt.",
    "The tag is release-v1.4.0, not v1.3.0.",
    # A bound in one row's last cell followed by a word in the next row's first cell.
    "| Metric | Full | Tiny |\n|---|---|---|\n| LPIPS | ≤ 0.10 | ≤ 0.20 |\n"
    "| Pixel mismatch ratio | — | ≤ 0.15 (15% of pixels) |\n",
    # The same across two list items: the raw file has "- " between them.
    "- keep it under 20\n- GiB of headroom is not the point\n",
    # Two paragraphs: only whitespace between them, so a joined literal is findable.
    "Stay below 3\n\nRuns are fine.\n",
])
def test_every_literal_is_found_in_its_own_body(skillmd, body):
    # Bug caught: extraction and the survival check disagree on token boundaries,
    # so `v0.156.1` is frozen out of `rust-v0.156.1` but never found again, and an
    # unchanged skill is rejected with LITERAL_LOST.
    lits = skillmd.literals(body)
    assert lits
    for lit in lits:
        assert skillmd.contains_literal(body, lit), lit


REPO = Path(__file__).resolve().parent.parent
REAL_SKILLS = sorted(REPO.glob("skills/*/SKILL.md")) + sorted(REPO.glob("skills/*/evals/fixtures/*/SKILL.fixture.md"))


@pytest.mark.parametrize("path", REAL_SKILLS, ids=lambda p: str(p.relative_to(REPO)))
def test_every_literal_of_a_real_skill_is_found_in_it(skillmd, path):
    # Bug caught: a freeze that records a literal the gate cannot find in the same
    # file, so the unchanged skill fails with LITERAL_LOST. A general guard over the
    # shipped files (it caught 1.0.1's glued-version case when planted); the table
    # and list cases above are what cover 1.0.2's cross-unit case.
    _, body = skillmd.split_frontmatter(skillmd.read_text(path))
    assert [lit for lit in skillmd.literals(body) if not skillmd.contains_literal(body, lit)] == []


@pytest.mark.parametrize("body, edited", [
    ("The safety margin is under 20\n\nGiB, and that is the budget.\n",
     "The safety margin is under 20\n\nMiB, and that is the budget.\n"),
    ("### Cap is under 20\nGiB is the unit.\n", "### Cap is under 20\nMiB is the unit.\n"),
])
def test_a_unit_in_the_next_paragraph_stays_protected(skillmd, body, edited):
    # Bug caught: scanning each unit alone drops a unit word that starts the next
    # paragraph, so `under 20 GiB` is frozen as `under 20` and a changed unit passes.
    lits = skillmd.literals(body)
    assert all(skillmd.contains_literal(body, lit) for lit in lits)
    assert not all(skillmd.contains_literal(edited, lit) for lit in lits), lits


def test_a_prefixed_version_is_still_protected(skillmd):
    # Bug caught: fixing the boundary mismatch by dropping the literal, so
    # `rust-v0.156.1` could be edited to `rust-v0.155.0` without the gate noticing.
    lits = skillmd.literals("Codex source at rust-v0.156.1 says so.")
    assert "rust-v0.156.1" in lits
    assert not skillmd.contains_literal("Codex source at rust-v0.155.0 says so.", "rust-v0.156.1")


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


def _linked_skill(tmp_path):
    """A skill directory holding a file link and a directory link, both pointing inside it,
    and a link to a file outside it."""
    secret = tmp_path / "secret.txt"
    secret.write_text("PRIVATE KEY\n", encoding="utf-8")
    d = tmp_path / "skill"
    (d / "references").mkdir(parents=True)
    (d / "SKILL.md").write_text("Body.\n", encoding="utf-8")
    (d / "references" / "a.md").write_text("A.\n", encoding="utf-8")
    (d / "references" / "alias.md").symlink_to(d / "references" / "a.md")
    (d / "references" / "leak.md").symlink_to(secret)
    (d / "mirror").symlink_to(d / "references", target_is_directory=True)
    return d, secret


def test_symlinks_are_not_package_files(skillmd, tmp_path):
    # Bug caught: keeping every path is_file() accepts, which follows links, so a
    # link to ~/.ssh/id_rsa inside a skill is hashed and read, and a linked
    # directory brings its files in under a second name.
    d, _ = _linked_skill(tmp_path)
    assert [p.relative_to(d).as_posix() for p in skillmd.package_files(d)] == ["SKILL.md", "references/a.md"]


def test_reading_a_symlink_is_refused(skillmd, tmp_path):
    # Bug caught: read_text() and sha256_file() dereferencing a link, so a
    # symlinked SKILL.md sends another file's bytes into the freeze and the gate.
    d, _ = _linked_skill(tmp_path)
    for fn in (skillmd.read_text, skillmd.sha256_file):
        with pytest.raises(OSError, match="symlink"):
            fn(d / "references" / "leak.md")
    assert skillmd.read_text(d / "references" / "a.md") == "A.\n"


def test_sentence_ends_before_a_closing_quote_or_bracket(skillmd):
    # Bug caught: a split that needs whitespace right after the stop, so a sentence
    # ending in a quote or bracket swallows the next one and a rule hides inside it.
    assert keys(skillmd, 'He said "run it." Then leave.\n') == ['He said "run it."', "Then leave"]
    assert keys(skillmd, "(Run it first.) Never skip it.\n") == ["(Run it first.)", "Never skip it"]


def test_table_cells_are_their_own_units(skillmd):
    # Bug caught: reading a table row as one paragraph, so a cell's last sentence
    # keeps the row's " |" and re-padding the table reads as an edited rule.
    body = ("| Exit | Next |\n|---|---|\n| 1 | Fix it. Never apply it. |\n| 2 | Use `a \\| b` here. |\n"
            "| 3 | Pick x \\| y. |\n")
    realigned = ("|Exit|Next|\n|:--|--:|\n|1|Fix it. Never apply it.|\n|2|Use `a \\| b` here.|\n"
                 "|3|Pick x \\| y.|\n")
    assert keys(skillmd, body) == keys(skillmd, realigned) == [
        "Exit", "Next", "1", "Fix it", "Never apply it", "2", "Use `a \\| b` here", "3", "Pick x \\| y"]
    assert skillmd.order(body) == skillmd.order(realigned)


def test_heading_marker_is_not_part_of_the_key(skillmd):
    # Bug caught: stripping list and quote markers but not "## ", so an approval
    # copied with its heading marker never matches the heading it names.
    assert skillmd.normalise("## Never on Fridays") == skillmd.normalise("Never on Fridays") == "Never on Fridays"
    assert skillmd.normalise("### Never on Fridays ###") == "Never on Fridays"


def test_a_pipe_inside_code_does_not_split_a_cell(skillmd):
    # Bug caught: splitting a table row on every unescaped "|", so a cell holding
    # `ps aux | grep mlx` breaks in two and the command is never frozen as a literal.
    body = "| Step | How |\n|---|---|\n| Filter | Run `ps aux | grep mlx` to list them. |\n"
    assert keys(skillmd, body) == ["Step", "How", "Filter", "Run `ps aux | grep mlx` to list them"]
    assert "ps aux | grep mlx" in skillmd.literals(body)


def test_a_double_backtick_code_span_keeps_its_pipe(skillmd):
    # Bug caught: reading ``a | b`` as two empty code spans around plain text, so
    # the pipe inside it splits the table cell and the command is cut in half.
    body = "| Step | How |\n|---|---|\n| Filter | Run ``ps aux | grep `mlx` `` to list them. |\n"
    assert keys(skillmd, body) == ["Step", "How", "Filter", "Run ``ps aux | grep `mlx` `` to list them"]


# The heavy-runs shape: a wrap inside a list item puts a bound's comparator at the
# start of a line. CommonMark reads "   > 27 never)." as a blockquote inside the
# item, so the split is right, but the `>` is still the bound's comparator.
FIT = ("1. **Does it fit?** Use the fit rule (GiB; peak + cache + ~1 GiB; ≤ 23 fits,\n"
       "   > 27 never). Take the peak from the profile.\n")


def test_a_quote_marker_that_is_a_bound_keeps_its_comparator(skillmd):
    # Bug caught: stripping the `>` of a blockquote that interrupts a list item or
    # paragraph as a marker only, so the `> 27` bound is never frozen and an edit
    # to `> 25` passes the gate.
    lits = skillmd.literals(FIT)
    assert any(lit.startswith("> 27") for lit in lits), lits
    assert all(skillmd.contains_literal(FIT, lit) for lit in lits)
    edited = FIT.replace("> 27", "> 25")
    assert not all(skillmd.contains_literal(edited, lit) for lit in lits)


def test_a_multi_line_blockquote_is_one_unit(skillmd):
    # Bug caught: starting a new unit at every `>` line, so a wrapped quote splits
    # per line and `under 20` loses its unit word `GiB`.
    body = "> under 20\n> GiB is the cap.\n"
    assert [(u["kind"], u["text"]) for u in skillmd.units(body)] == [("text", "under 20 GiB is the cap.")]
    lits = skillmd.literals(body)
    assert "under 20 GiB" in lits
    assert all(skillmd.contains_literal(body, lit) for lit in lits)
    assert not skillmd.contains_literal(body.replace("GiB", "MiB"), "under 20 GiB")


def test_an_empty_quote_line_ends_a_paragraph_inside_the_quote(skillmd):
    # Bug caught: joining every `>` line into one unit, so two quoted paragraphs
    # run together, or keeping the bare `>` as a sentence of its own.
    assert keys(skillmd, "> First part.\n>\n> Second part.\n") == ["First part", "Second part"]


def test_a_quote_marker_indented_past_the_paragraph_continues_it(skillmd):
    # Bug caught: splitting at every `>` line. CommonMark reads a `>` indented four
    # or more columns past the paragraph's text as paragraph text, not a quote.
    body = "- Keep it small,\n      > 27 is too many. Stop there.\n"
    assert keys(skillmd, body) == ["Keep it small, > 27 is too many", "Stop there"]


TRICKY = ["Edit `__init__.py` and **bold `x | y`** now.", "***Both*** at once, and a**b, and * not * this.",
          "An unpaired ** marker and _snake_case_ and __dunder__.", "**Stop. Now.** Then *go*.",
          "Use ``a `b` c`` with **care**."]


@pytest.mark.parametrize("path", REAL_SKILLS, ids=lambda p: str(p.relative_to(REPO)))
def test_emphasis_tracking_reads_the_same_text_as_the_keys(skillmd, path):
    # Bug caught: _marked() removing markers differently from _unemphasise(), so
    # emphasis is recorded under a key no sentence has and a stripped bold is never checked.
    _, body = skillmd.split_frontmatter(skillmd.read_text(path))
    texts = TRICKY + [u["text"] for u in skillmd.units(body) if u["kind"] == "text"]
    assert [skillmd._marked(t)[0] for t in texts] == [skillmd._unemphasise(t) for t in texts]


def test_emphasis_belongs_to_the_sentence_it_sits_in(skillmd):
    # Bug caught: giving a unit's emphasis to every sentence in it, or losing a bold
    # phrase that spans a sentence break, so the gate flags the wrong sentence or none.
    assert skillmd.emphasis("- **Kept exactly.** Never edit it.\n") == {"Kept exactly": [["Kept exactly", 2]]}
    assert skillmd.emphasis("**Stop. Now.** Then *go* home.\n") == {
        "Stop": [["Stop", 2]], "Now": [["Now", 2]], "Then go home": [["go", 1]]}
    assert skillmd.emphasis("Run `__init__.py` as is.\n") == {}
