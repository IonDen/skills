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
