---
name: release-checklist
description: Use when preparing a release of the Python package in this repository, from the version bump and changelog to the tag and the PyPI upload.
---

# Release checklist

## Why this skill exists

This skill exists to make sure that every release follows the same steps in
the same order, so that nothing important is forgotten.

## Rules

NEVER commit directly to `main`.

Do not push a tag without the maintainer's explicit approval, unless the user
has asked for a dry run.

You MUST run `pytest -q --maxfail=1` before opening a pull request.

Keep the wired memory limit under 20 GiB on a 32 GB machine.

## Steps

1. Create a branch named `release/vX.Y.Z` from a fresh `origin/main`.
2. Add a dated entry for the new version to `CHANGELOG.md`.
3. Run the test suite with `pytest -q --maxfail=1`. It takes about 40 seconds.
4. Open a pull request and wait for the review.
5. After the merge, tag the merge commit as `vX.Y.Z` and push the tag.

Build the distribution with:

```bash
python3 -m build
```

Here is an example of a good changelog entry:

```markdown
## v1.4.0 (2026-03-02)

- Added JSON output to the check command.
- Fixed a crash when the config file is empty.
```

## Changelog format

Any of these works, but a flat bullet list is the default here, and you
should use one of the others only if the repository already does.

## Troubleshooting

Read `references/troubleshooting.md` if the publish workflow, the build, a
tag push or the CI changelog check fails.

## Reminder

NEVER commit directly to `main`.
