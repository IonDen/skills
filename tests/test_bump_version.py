"""Each test names the one-line bug in bump_version.py that would make it fail."""


def test_inserts_1_1_0_right_after_name_when_absent(bump, tmp_path):
    # Bug caught: inserting at `start + 1` unconditionally puts version above `name`.
    p = tmp_path / "a.md"
    p.write_text("---\nname: a\ndescription: d\n---\nbody\n")
    assert bump.process(p, None, False).startswith("OK")
    assert p.read_text().splitlines()[:4] == ["---", "name: a", "version: 1.1.0", "description: d"]


def test_minor_bump_resets_patch(bump, tmp_path):
    # Bug caught: bump() returning f"{major}.{minor + 1}.{patch}" keeps a stale patch.
    p = tmp_path / "a.md"
    p.write_text("---\nname: a\nversion: 1.2.3\ndescription: d\n---\nbody\n")
    bump.process(p, None, False)
    assert "version: 1.3.0" in p.read_text()
    assert "1.2.3" not in p.read_text()


def test_set_forces_exact_version(bump, tmp_path):
    # Bug caught: ignoring `force` when a version line already exists.
    p = tmp_path / "a.md"
    p.write_text("---\nname: a\nversion: 1.2.3\n---\nbody\n")
    bump.process(p, "2.0.0", False)
    assert "version: 2.0.0" in p.read_text()


def test_dry_run_leaves_file_untouched(bump, tmp_path):
    # Bug caught: writing before the `if dry` check.
    p = tmp_path / "a.md"
    original = "---\nname: a\n---\nbody\n"
    p.write_text(original)
    assert bump.process(p, None, True).startswith("DRY")
    assert p.read_text() == original


def test_no_frontmatter_is_skipped(bump, tmp_path):
    # Bug caught: indexing fences[1] without the `len(fences) < 2` guard raises IndexError.
    p = tmp_path / "a.md"
    p.write_text("no frontmatter here\n")
    assert bump.process(p, None, False).startswith("SKIP")


# --- fixes from the review wave -------------------------------------------

def test_quoted_version_is_bumped_not_duplicated(bump, tmp_path):
    # Bug caught: VER_RE without optional quotes inserts a second `version:` above `version: "1.2.0"`.
    p = tmp_path / "a.md"
    p.write_text('---\nname: a\nversion: "1.2.0"\n---\nbody\n')
    bump.process(p, None, False)
    text = p.read_text()
    assert text.count("version:") == 1 and 'version: "1.3.0"' in text


def test_unparsable_version_line_is_skipped(bump, tmp_path):
    # Bug caught: an unmatched `version:` line falls into the insert branch and duplicates the key.
    p = tmp_path / "a.md"
    original = "---\nname: a\nversion: latest\n---\nbody\n"
    p.write_text(original)
    assert bump.process(p, None, False).startswith("SKIP")
    assert p.read_text() == original


def test_frontmatter_must_start_on_line_one(bump, tmp_path):
    # Bug caught: taking the first two `---` anywhere inserts a version after a horizontal rule.
    p = tmp_path / "a.md"
    original = "# Title\n\n---\n\ntext\n\n---\n"
    p.write_text(original)
    assert bump.process(p, None, False).startswith("SKIP")
    assert p.read_text() == original


def test_symlink_is_refused(bump, tmp_path):
    # Bug caught: writing through a symlink rewrites a file outside the pack.
    target = tmp_path / "outside.md"
    original = "---\nname: t\n---\nbody\n"
    target.write_text(original)
    link = tmp_path / "link.md"
    link.symlink_to(target)
    assert bump.process(link, None, False).startswith("SKIP")
    assert target.read_text() == original


def test_cli_continues_past_a_missing_file_and_exits_nonzero(bump, tmp_path):
    # Bug caught: an uncaught FileNotFoundError aborts the batch before later files are bumped.
    import subprocess, sys
    good = tmp_path / "good.md"
    good.write_text("---\nname: g\n---\nbody\n")
    r = subprocess.run([sys.executable, str(bump.__file__), str(tmp_path / "missing.md"), str(good)],
                       capture_output=True, text=True)
    assert r.returncode != 0
    assert "ERROR" in r.stdout and "version: 1.1.0" in good.read_text()


def test_crlf_line_endings_are_preserved(bump, tmp_path):
    # Bug caught: text-mode read/write flattens every CRLF in the file to LF.
    p = tmp_path / "a.md"
    p.write_bytes(b"---\r\nname: a\r\n---\r\nbody\r\n")
    bump.process(p, None, False)
    data = p.read_bytes()
    assert b"version: 1.1.0\r\n" in data and b"\nbody\r\n" in data and b"\n\n" not in data
