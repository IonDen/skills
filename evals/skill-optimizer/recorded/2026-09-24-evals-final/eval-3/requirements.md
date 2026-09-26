R1: Never commit directly to main.
  anchor: NEVER commit directly to `main`.

R2: Do not push a tag without the maintainer's explicit approval, unless a dry run was requested.
  anchor: Do not push a tag without the maintainer's explicit approval, unless the user has asked for a dry run.

R3: Run `pytest -q --maxfail=1` before opening a pull request (MUST).
  anchor: You MUST run `pytest -q --maxfail=1` before opening a pull request.

R4: Keep the wired memory limit under 20 GiB on a 32 GB machine.
  anchor: Keep the wired memory limit under 20 GiB on a 32 GB machine.

R5: Step 1 - create a branch named release/vX.Y.Z from a fresh origin/main.
  anchor: Create a branch named `release/vX.Y.Z` from a fresh `origin/main`.

R6: Step 2 - add a dated entry for the new version to CHANGELOG.md.
  anchor: Add a dated entry for the new version to `CHANGELOG.md`.

R7: Step 3 - run the test suite with `pytest -q --maxfail=1`; it takes about 40 seconds.
  anchor: Run the test suite with `pytest -q --maxfail=1`.
  anchor: It takes about 40 seconds.

R8: Step 4 - open a pull request and wait for the review.
  anchor: Open a pull request and wait for the review.

R9: Step 5 - after the merge, tag the merge commit as vX.Y.Z and push the tag.
  anchor: After the merge, tag the merge commit as `vX.Y.Z` and push the tag.

R10: The step order (1-5) is the instruction; steps run in this sequence.
  anchor: Create a branch named `release/vX.Y.Z` from a fresh `origin/main`.

R11: Build the distribution with `python3 -m build`.
  anchor: python3 -m build

R12: A good changelog entry example exists showing the heading format `## vX.Y.Z (YYYY-MM-DD)` with a flat bullet list.
  anchor: Here is an example of a good changelog entry:

R13: A flat bullet list is the default changelog format here; use one of the other forms (Keep a Changelog headings, a short paragraph) only if the repository already does.
  anchor: a flat bullet list is the default here, and you should use one of the others only if the repository already does.

R14: If the publish workflow fails with 403 Forbidden, the PyPI trusted publisher is not configured for the repository: open https://pypi.org/manage/account/publishing/ and add the repository, the workflow file `.github/workflows/publish.yml` and the environment `pypi`.
  anchor: If the publish workflow fails with `403 Forbidden`, the PyPI trusted publisher is not configured for this repository.

R15: If the build fails with "No module named build", install it with `python3 -m pip install build` and build again.
  anchor: If the build fails with `No module named build`, install it with `python3 -m pip install build` and build again.

R16: If the tag already exists on the remote, do not delete it - ask the maintainer.
  anchor: If the tag already exists on the remote, do not delete it.
  anchor: Ask the maintainer.

R17: If the changelog check fails in CI, the entry heading does not match the tag; the heading must be `## vX.Y.Z (YYYY-MM-DD)`.
  anchor: The heading must be `## vX.Y.Z (YYYY-MM-DD)`.

R18: Closing reminder - never commit directly to main (repeated at the end on purpose).
  anchor: NEVER commit directly to `main`.

R19: This skill exists so that nothing important about a release is forgotten (motivation sentence, carries the rule word "nothing").
  anchor: so that nothing important is forgotten
