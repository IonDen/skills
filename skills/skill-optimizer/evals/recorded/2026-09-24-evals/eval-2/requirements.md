R1: Never commit directly to main.
  anchor: NEVER commit directly to `main`.
R2: Do not push a tag without the maintainer's explicit approval, unless the user asked for a dry run.
  anchor: Do not push a tag without the maintainer's explicit approval, unless the user has asked for a dry run.
R3: Run pytest before opening a pull request.
  anchor: You MUST run `pytest -q --maxfail=1` before opening a pull request.
R4: Keep the wired memory limit under 20 GiB on a 32 GB machine.
  anchor: Keep the wired memory limit under 20 GiB on a 32 GB machine.
R5: Create the release branch from a fresh origin/main.
  anchor: Create a branch named `release/vX.Y.Z` from a fresh `origin/main`.
R6: Add a dated changelog entry for the new version.
  anchor: Add a dated entry for the new version to `CHANGELOG.md`.
R7: Run the test suite as a release step; it takes about 40 seconds.
  anchor: Run the test suite with `pytest -q --maxfail=1`.
R8: Open a pull request and wait for the review before merging.
  anchor: Open a pull request and wait for the review.
R9: After the merge, tag the merge commit and push the tag.
  anchor: After the merge, tag the merge commit as `vX.Y.Z` and push the tag.
R10: Build the distribution with the given command.
  anchor: python3 -m build
R11: Use a flat bullet list changelog format by default, unless the repository already uses another format.
  anchor: a flat bullet list is the default here, and you should use one of the others only if the repository already does.
R12: On a 403 Forbidden publish failure, configure the PyPI trusted publisher for the repository.
  anchor: If the publish workflow fails with `403 Forbidden`, the PyPI trusted publisher is not configured for this repository.
R13: On a missing build module error, install the build package and retry.
  anchor: If the build fails with `No module named build`, install it with `python3 -m pip install build` and build again.
R14: If the tag already exists on the remote, do not delete it; ask the maintainer.
  anchor: If the tag already exists on the remote, do not delete it.
R15: If the changelog CI check fails, the heading must match the required format.
  anchor: The heading must be `## vX.Y.Z (YYYY-MM-DD)`.
R16: When the tag already exists on the remote, ask the maintainer instead of deleting it.
  anchor: Ask the maintainer.
