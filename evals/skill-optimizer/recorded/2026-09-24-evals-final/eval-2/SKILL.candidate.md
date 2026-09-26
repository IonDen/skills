---
name: release-checklist
description: Use when preparing a release of the Python package in this repository, from the version bump and changelog to the tag and the PyPI upload.
---

# Release checklist

## Why this skill exists

Releases are one of the most important moments in the life of a software
project. A release is the point where the work of many weeks reaches users, so
it is worth taking a little extra care. In the past, releases that were rushed
caused problems for users, and those problems took time to fix. This skill
exists to make sure that every release follows the same steps in the same
order, so that nothing important is forgotten. Following the checklist below
lets you release with confidence.

## What a release is

A release is a published version of the package. It has a version number, a
changelog entry, a git tag, and a build uploaded to PyPI. Semantic versioning
means the version number has three parts: major, minor and patch. The major
part changes when the public API breaks, the minor part when features are
added, and the patch part for fixes.

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

Here is another example of a good changelog entry:

```markdown
## v1.3.1 (2026-02-11)

- Fixed the version shown by the help screen.
```

## Changelog format

You can write the changelog entry in several ways. You could use Keep a
Changelog headings (Added, Changed, Fixed). You could use a flat bullet list.
You could write a short paragraph. Any of these works, but a flat bullet list
is the default here, and you should use one of the others only if the
repository already does.

## Troubleshooting

If the publish workflow fails with `403 Forbidden`, the PyPI trusted publisher
is not configured for this repository. Open
https://pypi.org/manage/account/publishing/ and add the repository, the
workflow file `.github/workflows/publish.yml` and the environment `pypi`.

If the build fails with `No module named build`, install it with
`python3 -m pip install build` and build again.

If the tag already exists on the remote, do not delete it. Ask the maintainer.

If the changelog check fails in CI, the entry heading does not match the tag.
The heading must be `## vX.Y.Z (YYYY-MM-DD)`.

## Reminder

NEVER commit directly to `main`.
