#!/usr/bin/env python3
"""Bump (or set) the `version` field in an agent file's frontmatter.

Run this on each agent AFTER its optimisations are applied and approved.

Rules:
  - No `version` field present  -> insert `version: 1.1.0`
    (the unversioned baseline is treated as 1.0.0; optimisation is a minor bump).
  - `version: X.Y.Z` present    -> minor bump -> `X.(Y+1).0`.
  - `--set X.Y.Z`               -> force that exact version.

The field is inserted right after the `name:` line so it stays visible.
Idempotent only in the sense that each run bumps once; don't run twice per change.

Usage:
    python bump_version.py AGENT.md [AGENT.md ...] [--set X.Y.Z] [--dry-run]
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

VER_RE = re.compile(r"^version:\s*v?(\d+)\.(\d+)(?:\.(\d+))?\s*$")


def bump(major: int, minor: int) -> str:
    return f"{major}.{minor + 1}.0"


def process(path: Path, force: str | None, dry: bool) -> str:
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    # Locate frontmatter fences.
    fences = [i for i, l in enumerate(lines) if l.strip() == "---"]
    if len(fences) < 2:
        return f"SKIP {path.name}: no frontmatter"
    start, end = fences[0], fences[1]

    ver_idx = None
    for i in range(start + 1, end):
        if VER_RE.match(lines[i]):
            ver_idx = i
            break

    if force:
        new_ver = force
    elif ver_idx is not None:
        m = VER_RE.match(lines[ver_idx])
        new_ver = bump(int(m.group(1)), int(m.group(2)))
    else:
        new_ver = "1.1.0"

    old = "(none)"
    if ver_idx is not None:
        old = lines[ver_idx].strip().split(":", 1)[1].strip()
        new_lines = list(lines)
        new_lines[ver_idx] = f"version: {new_ver}\n"
    else:
        # Insert after the `name:` line (fallback: just after opening fence).
        insert_at = start + 1
        for i in range(start + 1, end):
            if re.match(r"^name:\s", lines[i]):
                insert_at = i + 1
                break
        new_lines = lines[:insert_at] + [f"version: {new_ver}\n"] + lines[insert_at:]

    if dry:
        return f"DRY  {path.name}: {old} -> {new_ver}"
    path.write_text("".join(new_lines), encoding="utf-8")
    return f"OK   {path.name}: {old} -> {new_ver}"


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("paths", nargs="+", help="agent .md files")
    ap.add_argument("--set", dest="force", help="force exact version X.Y.Z")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    if args.force and not re.fullmatch(r"\d+\.\d+\.\d+", args.force):
        sys.exit("--set must be X.Y.Z")
    for p in args.paths:
        print(process(Path(p).expanduser(), args.force, args.dry_run))


if __name__ == "__main__":
    main()
