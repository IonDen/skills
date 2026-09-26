R1: Never commit directly to main, no exceptions.
  anchor: NEVER commit directly to `main`.

R2: Never push a tag without the maintainer's explicit approval, except for an approved dry run.
  anchor: Do not push a tag without the maintainer's explicit approval, unless the user has asked for a dry run.

R3: Running the test suite before opening a pull request is mandatory.
  anchor: You MUST run `pytest -q --maxfail=1` before opening a pull request.

R4: Keep wired memory usage under a fixed bound on this machine.
  anchor: Keep the wired memory limit under 20 GiB on a 32 GB machine.

R5: Step 1: branch from a fresh origin/main with the release naming convention.
  anchor: Create a branch named `release/vX.Y.Z` from a fresh `origin/main`.

R6: Step 2: record the release in the changelog with a date.
  anchor: Add a dated entry for the new version to `CHANGELOG.md`.

R7: Step 3: run the test suite; it takes about 40 seconds.
  anchor: Run the test suite with `pytest -q --maxfail=1`.
  anchor: It takes about 40 seconds.

R8: Step 4: open the pull request and wait for review.
  anchor: Open a pull request and wait for the review.

R9: Step 5: after merge, tag the merge commit and push the tag.
  anchor: After the merge, tag the merge commit as `vX.Y.Z` and push the tag.

R10: Build the distribution with the build module.
  anchor: Build the distribution with:

R11: The default changelog format is a flat bullet list; use another format only if the repository already uses one.
  anchor: a flat bullet list is the default here, and you should use one of the others only if the repository already does.

R12: A 403 on publish means the PyPI trusted publisher isn't configured; fix it on pypi.org, naming the repo, workflow file and environment.
  anchor: the PyPI trusted publisher is not configured for this repository.
  anchor: add the repository, the workflow file

R13: A missing build module must be installed before rebuilding.
  anchor: install it with `python3 -m pip install build` and build again

R14: Never delete an existing remote tag; ask the maintainer instead.
  anchor: do not delete it.
  anchor: Ask the maintainer.

R15: A CI changelog-check failure means the heading doesn't match the required tag format.
  anchor: the entry heading does not match the tag
  anchor: The heading must be `## vX.Y.Z (YYYY-MM-DD)`.

R16: The stated reason the skill exists is to keep every release following the same steps in the same order.
  anchor: This skill exists to make sure that every release follows the same steps in the same order, so that nothing important is forgotten.
