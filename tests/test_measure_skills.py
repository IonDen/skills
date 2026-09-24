"""skill-optimizer measure_skills.py. Each test names the one-line bug that would make it fail."""


def fm(description, when=None):
    extra = f"when_to_use: {when}\n" if when else ""
    return f"---\nname: demo\ndescription: {description}\n{extra}---\n"


def test_listing_is_description_plus_when_to_use(measure, make_skill):
    # Bug caught: counting the description alone, which understates what the listing costs.
    r = measure.measure(make_skill("Body.\n", frontmatter=fm("A" * 100, "B" * 50)))
    assert (r["listing_chars"], r["description_chars"]) == (150, 100)


def test_each_note_reads_its_own_field(measure, make_skill):
    # Bug caught: testing the spec limit against the listing, or the listing cap
    # against the description; the fixtures below differ only in which field is long.
    spec = measure.measure(make_skill("x\n", where="a", frontmatter=fm("x" * 1100, "y" * 10)))
    cap = measure.measure(make_skill("x\n", where="b", frontmatter=fm("x" * 1000, "y" * 600)))
    assert [n.split(":")[0] for n in spec["notes"]] == ["DESCRIPTION_OVER_SPEC_LIMIT"]
    assert [n.split(":")[0] for n in cap["notes"]] == ["LISTING_OVER_DEFAULT_CAP"]


def test_no_size_target_for_the_body(measure, make_skill):
    # Bug caught: a body-size target creeping back in. There is none by design:
    # the job is to cut what can go without loss, not to reach a number.
    r = measure.measure(make_skill("line\n" * 2000))
    assert r["notes"] == [] and r["body_lines"] == 2000


def test_body_excludes_frontmatter(measure, make_skill):
    # Bug caught: measuring the whole file, so frontmatter inflates the body.
    r = measure.measure(make_skill("one\ntwo\nthree\n"))
    assert (r["body_lines"], r["body_chars"]) == (3, 14)


def test_block_and_quoted_descriptions_parse_to_their_text(measure, make_skill):
    # Bug caught: counting YAML syntax (">-", quotes, backslashes) as description text.
    folded = measure.measure(make_skill("x\n", where="a",
                             frontmatter="---\nname: demo\ndescription: >-\n  one two\n  three\n---\n"))
    quoted = measure.measure(make_skill("x\n", where="b",
                             frontmatter='---\nname: demo\ndescription: "Say \\"hi\\" now"\n---\n'))
    assert folded["description_chars"] == len("one two three")
    assert quoted["description_chars"] == len('Say "hi" now')


def test_cli_reads_a_file_by_any_name_and_rejects_missing_paths(measure, tmp_path, capsys):
    # Bug caught: accepting only files named SKILL.md, or printing "nothing found"
    # and exiting 0 for a mistyped path.
    f = tmp_path / "fixture.md"
    f.write_text(fm("Use when x.") + "Body.\n", encoding="utf-8")
    assert measure.main([str(f), "--json"]) == 0
    assert measure.main([str(tmp_path / "missing")]) == 2
    assert "not found" in capsys.readouterr().err


def test_cli_reports_an_unreadable_file_without_a_traceback(measure, tmp_path, capsys):
    # Bug caught: a UnicodeDecodeError escaping main() as a traceback instead of exit 2.
    d = tmp_path / "bad"
    d.mkdir()
    (d / "SKILL.md").write_bytes(b"---\nname: bad\ndescription: x\n---\n\xff\xfe broken\n")
    assert measure.main([str(d)]) == 2
    assert "cannot read" in capsys.readouterr().err
