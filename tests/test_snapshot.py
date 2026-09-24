"""skill-optimizer snapshot.py. Each test names the one-line bug that would make it fail."""
from pathlib import Path

SKILL = "---\nname: demo\ndescription: Use when testing.\n---\nBody.\n"


def _skill(tmp_path, name="skill"):
    d = tmp_path / name
    (d / "references").mkdir(parents=True)
    (d / "SKILL.md").write_text(SKILL, encoding="utf-8")
    (d / "references" / "a.md").write_text("A.\n", encoding="utf-8")
    return d


def _files(root: Path):
    """Relative path -> 'link' or the file's text, for everything under root."""
    return {p.relative_to(root).as_posix(): "link" if p.is_symlink() else p.read_text(encoding="utf-8")
            for p in sorted(root.rglob("*")) if p.is_symlink() or p.is_file()}


def test_a_linked_skill_directory_is_copied_as_real_files(snapshot, tmp_path, capsys):
    # Bug caught: copying the link itself (or refusing it), so a skill installed as
    # a symlinked directory snapshots to a link, or not at all.
    real = _skill(tmp_path, "real")
    (tmp_path / "installed").symlink_to(real, target_is_directory=True)
    dest = tmp_path / "work" / "original"
    assert snapshot.main([str(tmp_path / "installed"), str(dest)]) == 0
    assert not dest.is_symlink()
    assert _files(dest) == {"SKILL.md": SKILL, "references/a.md": "A.\n"}
    capsys.readouterr()


def test_a_skill_md_linked_per_file_is_copied_only_when_its_target_is_a_skill_md(snapshot, tmp_path, capsys):
    # Bug caught: treating every linked SKILL.md alike, so a stow or home-manager
    # install (SKILL.md -> .../demo/SKILL.md) cannot be snapshotted, or a SKILL.md
    # pointing at any other file (~/.ssh/id_rsa) is copied into the work directory.
    store = _skill(tmp_path, "store")
    skill = tmp_path / "skill"
    (skill / "references").mkdir(parents=True)
    (skill / "SKILL.md").symlink_to(store / "SKILL.md")
    (skill / "references" / "a.md").write_text("A.\n", encoding="utf-8")
    dest = tmp_path / "copy"
    assert snapshot.main([str(skill), str(dest)]) == 0
    assert not (dest / "SKILL.md").is_symlink()
    assert _files(dest) == {"SKILL.md": SKILL, "references/a.md": "A.\n"}
    secret = tmp_path / "secret.md"
    secret.write_text("PRIVATE KEY\n", encoding="utf-8")
    (skill / "SKILL.md").unlink()
    (skill / "SKILL.md").symlink_to(secret)
    assert snapshot.main([str(skill), str(tmp_path / "copy2")]) == 2
    assert not (tmp_path / "copy2").exists()
    assert "PRIVATE" not in capsys.readouterr().out


def test_an_inner_link_is_skipped_and_its_target_never_read(snapshot, tmp_path, capsys):
    # Bug caught: copytree's default, which follows links, so a link inside a skill
    # to a file outside it (~/.ssh/id_rsa) or to a directory is read and copied.
    skill = _skill(tmp_path)
    secret = tmp_path / "secret.md"
    secret.write_text("PRIVATE KEY\n", encoding="utf-8")
    secret.chmod(0)   # reading it would raise, so a pass proves it was never read
    (skill / "references" / "leak.md").symlink_to(secret)
    (skill / "mirror").symlink_to(skill / "references", target_is_directory=True)
    dest = tmp_path / "copy"
    try:
        assert snapshot.main([str(skill), str(dest)]) == 0
    finally:
        secret.chmod(0o600)
    assert _files(dest) == {"SKILL.md": SKILL, "references/a.md": "A.\n"}
    out = capsys.readouterr().out
    assert [ln for ln in out.splitlines() if ln.startswith("skipped link")] == [
        "skipped link (not copied or read): mirror", "skipped link (not copied or read): references/leak.md"]


def test_a_dangling_link_is_skipped(snapshot, tmp_path, capsys):
    # Bug caught: copying with the links resolved, which stops on a link whose
    # target is gone, so one stale link blocks the whole snapshot.
    skill = _skill(tmp_path)
    (skill / "references" / "gone.md").symlink_to(tmp_path / "nowhere.md")
    dest = tmp_path / "copy"
    assert snapshot.main([str(skill), str(dest)]) == 0
    assert _files(dest) == {"SKILL.md": SKILL, "references/a.md": "A.\n"}
    assert "skipped link (not copied or read): references/gone.md" in capsys.readouterr().out.splitlines()


def test_an_existing_destination_or_a_missing_skill_md_is_refused(snapshot, tmp_path, capsys):
    # Bug caught: copying into a directory that already exists, which mixes an old
    # snapshot (or a candidate) into the new one, or snapshotting a folder with no
    # skill without saying so plainly.
    skill = _skill(tmp_path)
    dest = tmp_path / "copy"
    dest.mkdir()
    (dest / "old.md").write_text("old\n", encoding="utf-8")
    assert snapshot.main([str(skill), str(dest)]) == 2
    assert _files(dest) == {"old.md": "old\n"}
    (skill / "SKILL.md").unlink()
    assert snapshot.main([str(skill), str(tmp_path / "copy2")]) == 2
    assert not (tmp_path / "copy2").exists()
    err = capsys.readouterr().err
    assert "exists" in err and "no SKILL.md in" in err


def test_a_destination_inside_the_skill_is_refused(snapshot, tmp_path, capsys):
    # Bug caught: snapshotting into a folder inside the skill, which copies the
    # snapshot into itself as it walks, and leaves work files in the user's skill.
    skill = _skill(tmp_path)
    before = _files(skill)
    assert snapshot.main([str(skill), str(skill / "work" / "original")]) == 2
    assert snapshot.main([str(skill), str(skill)]) == 2
    assert _files(skill) == before
    assert "inside" in capsys.readouterr().err


def _unreadable(path, run):
    path.chmod(0)
    try:
        return run()
    finally:
        path.chmod(0o700)


def test_an_unreadable_directory_or_file_fails_and_leaves_no_partial_copy(snapshot, tmp_path, capsys):
    # Bug caught: os.walk's default of skipping a directory it cannot list (or a
    # copy error mid-way) leaving a snapshot that silently lacks part of the skill.
    skill = _skill(tmp_path)
    (skill / "scripts").mkdir()
    (skill / "scripts" / "run.py").write_text("print(1)\n", encoding="utf-8")
    dest = tmp_path / "work" / "original"
    assert _unreadable(skill / "scripts", lambda: snapshot.main([str(skill), str(dest)])) == 2
    assert not dest.exists()
    assert _unreadable(skill / "references" / "a.md", lambda: snapshot.main([str(skill), str(dest)])) == 2
    assert not dest.exists()
    assert snapshot.main([str(skill), str(dest)]) == 0
    capsys.readouterr()
