# Release checklist

Version [0.1.0 is published on PyPI](https://pypi.org/project/mpl-pointpicker/0.1.0/).
The first upload used the existing local maintainer credential and the exact
wheel/source assets from GitHub release `v0.1.0`. No token was stored in this
repository or GitHub Actions. Base and notebook-extra installations were checked
in a fresh environment using the public PyPI index.

## Future releases

1. Run CI and perform interactive desktop and Jupyter checks, including calibration and tagging.
2. Update the version in `pyproject.toml` and `src/mpl_pointpicker/__init__.py` together.
3. Build with `python -m build` and validate with `python -m twine check dist/*`.
4. Tag the checked commit and attach the generated wheel and sdist to the GitHub release.
5. Publish that new version, then verify installation from PyPI in a fresh environment.

Never move an existing release tag or replace an already published version.

## GitHub Trusted Publishing setup

The manual `.github/workflows/publish.yml` has passed its build-only run and the
GitHub environment `pypi` exists. Linking that workflow to the existing PyPI
project remains tracked in [issue #3](https://github.com/joanjcaceres/mpl-pointpicker/issues/3).
Keep `PYPI_PUBLISH_ENABLED` unset until the link is confirmed.

In the PyPI project's publishing settings, add a GitHub Trusted Publisher with
owner `joanjcaceres`, repository `mpl-pointpicker`, workflow `publish.yml` and
environment `pypi`. Follow [the PyPI instructions](https://docs.pypi.org/trusted-publishers/adding-a-publisher/).

After confirming that publisher, set the repository variable
`PYPI_PUBLISH_ENABLED=true`. Manually run `publish.yml` on a **new release tag**
with `publish=true`. The workflow reruns tests, builds distributions and uploads
using OIDC, without a long-lived PyPI token. A normal push, tag or GitHub release
does not publish to PyPI. Do not dispatch another upload of version 0.1.0.

## SCCircuits migration

The first publication unblocks normal index-based dependency installation in
[SCCircuits PR #84](https://github.com/joanjcaceres/sccircuits/pull/84). Remove the
provisional GitHub bootstrap, update its development lockfile and run its checks
against the PyPI release before merging.
