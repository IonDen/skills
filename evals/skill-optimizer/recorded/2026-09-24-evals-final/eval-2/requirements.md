R1: Never commit directly to main.
  anchor: NEVER commit directly to `main`.
R2: Do not push a tag without the maintainer's explicit approval, unless the user has asked for a dry run.
  anchor: Do not push a tag without the maintainer's explicit approval, unless the user has asked for a dry run.
R3: Run pytest -q --maxfail=1 before opening a pull request.
  anchor: You MUST run `pytest -q --maxfail=1` before opening a pull request.
R4: Keep the wired memory limit under 20 GiB on a 32 GB machine.
  anchor: Keep the wired memory limit under 20 GiB on a 32 GB machine.
R5: Create a branch named release/vX.Y.Z from a fresh origin/main.
  anchor: Create a branch named `release/vX.Y.Z` from a fresh `origin/main`.
R6: Add a dated entry for the new version to CHANGELOG.md.
  anchor: Add a dated entry for the new version to `CHANGELOG.md`.
R7: Run the test suite with pytest -q --maxfail=1, which takes about 40 seconds.
  anchor: Run the test suite with `pytest -q --maxfail=1`.
  anchor: It takes about 40 seconds.
R8: Open a pull request and wait for the review.
  anchor: Open a pull request and wait for the review.
R9: After the merge, tag the merge commit as vX.Y.Z and push the tag.
  anchor: After the merge, tag the merge commit as `vX.Y.Z` and push the tag.
R10: Build the distribution with python3 -m build.
  anchor: Build the distribution with:
R11: A flat bullet list is the default changelog format; use one of the others only if the repository already does.
  anchor: a flat bullet list is the default here, and you should use one of the others only if the repository already does
R12: If the publish workflow fails with 403 Forbidden, the PyPI trusted publisher is not configured; open the publishing page and add the repository, the workflow file and the pypi environment.
  anchor: If the publish workflow fails with `403 Forbidden`, the PyPI trusted publisher is not configured for this repository.
  anchor: Open https://pypi.org/manage/account/publishing/ and add the repository, the workflow file `.github/workflows/publish.yml` and the environment `pypi`.
R13: If the build fails with No module named build, install it with python3 -m pip install build and build again.
  anchor: If the build fails with `No module named build`, install it with `python3 -m pip install build` and build again.
R14: If the tag already exists on the remote, do not delete it; ask the maintainer.
  anchor: If the tag already exists on the remote, do not delete it.
  anchor: Ask the maintainer.
R15: If the changelog check fails in CI, the entry heading does not match the tag; the heading must be ## vX.Y.Z (YYYY-MM-DD).
  anchor: If the changelog check fails in CI, the entry heading does not match the tag.
  anchor: The heading must be `## vX.Y.Z (YYYY-MM-DD)`.
