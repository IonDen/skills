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
