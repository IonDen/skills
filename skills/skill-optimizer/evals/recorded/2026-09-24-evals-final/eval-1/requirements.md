R1: Never commit directly to main. Repeated as the closing reminder at the end of the skill.
  anchor: NEVER commit directly to `main`.

R2: Do not push a tag without the maintainer's explicit approval, unless the user asked for a dry run.
  anchor: Do not push a tag without the maintainer's explicit approval

R3: Must run pytest -q --maxfail=1 before opening a pull request.
  anchor: You MUST run `pytest -q --maxfail=1` before opening a pull request.

R4: Keep the wired memory limit under 20 GiB on a 32 GB machine.
  anchor: Keep the wired memory limit under 20 GiB on a 32 GB machine.

R5: Step 1: create a branch named release/vX.Y.Z from a fresh origin/main.
  anchor: Create a branch named `release/vX.Y.Z` from a fresh `origin/main`.

R6: Step 2: add a dated entry for the new version to CHANGELOG.md.
  anchor: Add a dated entry for the new version to `CHANGELOG.md`.

R7: Step 3: run the test suite with pytest -q --maxfail=1; it takes about 40 seconds.
  anchor: Run the test suite with `pytest -q --maxfail=1`.
  anchor: It takes about 40 seconds.

R8: Step 4: open a pull request and wait for the review.
  anchor: Open a pull request and wait for the review.

R9: Step 5: after the merge, tag the merge commit as vX.Y.Z and push the tag.
  anchor: After the merge, tag the merge commit as `vX.Y.Z` and push the tag.

R10: Build the distribution with python3 -m build.
  anchor: Build the distribution with:

R11: The changelog format default is a flat bullet list; use another format only if the repository already does.
  anchor: a flat bullet list is the default here, and you should use one of the others only if the repository already does

R12: Troubleshooting: a 403 Forbidden publish failure means the PyPI trusted publisher is not configured; open the publishing page and add the repository, workflow file and pypi environment.
  anchor: the PyPI trusted publisher is not configured for this repository
  anchor: Open https://pypi.org/manage/account/publishing/ and add the repository

R13: Troubleshooting: if the build fails with "No module named build", install build and build again.
  anchor: install it with `python3 -m pip install build` and build again

R14: Troubleshooting: if the tag already exists on the remote, do not delete it; ask the maintainer.
  anchor: If the tag already exists on the remote, do not delete it.
  anchor: Ask the maintainer.

R15: Troubleshooting: if the changelog check fails in CI, the heading does not match the tag; the heading must be `## vX.Y.Z (YYYY-MM-DD)`.
  anchor: the entry heading does not match the tag
  anchor: The heading must be `## vX.Y.Z (YYYY-MM-DD)`.
