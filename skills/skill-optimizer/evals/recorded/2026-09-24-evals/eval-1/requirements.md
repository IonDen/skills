R1: Never commit directly to main (also the closing reminder).
  anchor: NEVER commit directly to `main`.
R2: Never push a tag without the maintainer's explicit approval, except for a dry run the user asked for.
  anchor: Do not push a tag without the maintainer's explicit approval
R3: Run pytest before opening a pull request.
  anchor: You MUST run `pytest -q --maxfail=1` before opening a pull request.
R4: Keep the wired memory limit under 20 GiB on a 32 GB machine.
  anchor: Keep the wired memory limit under 20 GiB on a 32 GB machine.
R5: Step 1: create the release branch from a fresh origin/main.
  anchor: Create a branch named `release/vX.Y.Z` from a fresh `origin/main`.
R6: Step 2: add a dated CHANGELOG.md entry for the new version.
  anchor: Add a dated entry for the new version to `CHANGELOG.md`.
R7: Step 3: run the test suite.
  anchor: Run the test suite with `pytest -q --maxfail=1`.
R8: Step 3 gotcha: the test suite takes about 40 seconds.
  anchor: It takes about 40 seconds.
R9: Step 4: open a pull request and wait for the review.
  anchor: Open a pull request and wait for the review.
R10: Step 5: after the merge, tag the merge commit and push the tag.
  anchor: tag the merge commit as `vX.Y.Z` and push the tag
R11: Build the distribution with python3 -m build.
  anchor: Build the distribution with
R12: Show at least one worked example of a good changelog entry.
  anchor: Here is an example of a good changelog entry
R13: Changelog default format is a flat bullet list; use another format only if the repository already does.
  anchor: a flat bullet list is the default here, and you should use one of the others only if the repository already does
R14: Troubleshooting: 403 Forbidden means the PyPI trusted publisher is not configured for this repository.
  anchor: the PyPI trusted publisher is not configured for this repository
R15: Troubleshooting: fix a 403 by registering the repo, workflow file and environment on the PyPI publishing page.
  anchor: add the repository, the workflow file `.github/workflows/publish.yml` and the environment `pypi`
R16: Troubleshooting: fix "No module named build" by installing the build tool and building again.
  anchor: install it with `python3 -m pip install build` and build again
R17: Troubleshooting: never delete an existing remote tag.
  anchor: do not delete it
R18: Troubleshooting: ask the maintainer instead of deleting an existing tag.
  anchor: Ask the maintainer
R19: Troubleshooting: a changelog CI failure means the entry heading does not match the tag.
  anchor: the entry heading does not match the tag
R20: Troubleshooting: the required changelog heading format.
  anchor: The heading must be `## vX.Y.Z (YYYY-MM-DD)`.
R21: Motivation sentence (kept pending the user's decision): the skill exists so release steps are not forgotten.
  anchor: so that nothing important is forgotten
