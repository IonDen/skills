#!/usr/bin/env python3
"""Copy a skill directory into a work directory as real files.

The skill the user named is followed wherever it is installed: a symlinked skill
directory is resolved to its real directory, and a SKILL.md that is itself a
link is copied as a file when the link resolves to a file named SKILL.md (a
per-file install such as stow or home-manager). No other link is copied or
read: a link inside a skill can point anywhere, ~/.ssh included. Each skipped
link is printed on its own line. Caches and VCS data are left out, and files are
copied without their modes, so a read-only install gives a writable snapshot.

Usage: snapshot.py SRC DEST
Exit 2 when DEST exists or lies inside SRC, when SRC has no SKILL.md (or its
SKILL.md is a link to anything but a SKILL.md), or when a directory or file in
SRC cannot be read; in that last case the partial DEST is removed.
"""
from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import skillmd  # noqa: E402


class SnapshotError(ValueError):
    pass


def snapshot(src, dest) -> list[str]:
    """Copy src into dest (which must not exist). Returns the links skipped, relative to src."""
    src, dest = Path(src).expanduser().resolve(), Path(dest).expanduser()
    if dest.exists() or dest.is_symlink():
        raise SnapshotError(f"{dest} exists; snapshot into a new directory")
    if dest.resolve() == src or dest.resolve().is_relative_to(src):
        raise SnapshotError(f"{dest} is inside the skill; snapshot into a directory outside it")
    skill = skillmd.skill_md(src / "SKILL.md")   # a link to anything but a SKILL.md raises here
    if not skill.is_file():
        raise SnapshotError(f"no SKILL.md in {src}")

    skipped = []
    dest.mkdir(parents=True)
    try:
        _copy(src, skill, dest, skipped)
    except OSError:
        shutil.rmtree(dest)   # no partial snapshot: a missing file would look like a cut
        raise
    return sorted(skipped)


def _raise(err: OSError) -> None:
    raise err


def _copy(src: Path, skill: Path, dest: Path, skipped: list) -> None:
    shutil.copyfile(skill, dest / "SKILL.md")
    # onerror: a directory that cannot be listed is an error, not an empty folder.
    for top, dirs, files in os.walk(src, followlinks=False, onerror=_raise):
        dirs[:] = [d for d in dirs if d not in skillmd.SKIP_PARTS]
        here = Path(top)
        for name in sorted(dirs + files):
            p = here / name
            rel = p.relative_to(src).as_posix()
            if name in skillmd.SKIP_PARTS or rel == "SKILL.md" or p.suffix == ".pyc":
                continue
            if p.is_symlink():
                skipped.append(rel)
            elif p.is_file():
                (dest / rel).parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(p, dest / rel, follow_symlinks=False)


def main(argv=None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 2:
        print(__doc__.strip(), file=sys.stderr)
        return 2
    try:
        skipped = snapshot(*args)
    except (SnapshotError, OSError) as exc:
        print(f"snapshot refused: {exc}", file=sys.stderr)
        return 2
    for rel in skipped:
        print(f"skipped link (not copied or read): {rel}")
    print(f"copied {args[0]} -> {args[1]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
