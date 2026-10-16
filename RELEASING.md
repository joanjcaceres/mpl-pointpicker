# Release checklist

The first deliverable is the GitHub v0.1.0 release with a wheel and sdist.
Publishing to PyPI is a separate, pending action.

1. Run CI and perform interactive desktop and Jupyter checks, including calibration and tagging.
2. Keep the version in `pyproject.toml` and `src/mpl_pointpicker/__init__.py` consistent.
3. Build with `python -m build` and validate with `python -m twine check dist/*`.
4. Tag the checked commit and attach the generated wheel and sdist to the GitHub release.

## First PyPI publication

Configure a pending GitHub Trusted Publisher on PyPI for owner `joanjcaceres`,
repository `mpl-pointpicker`, workflow `publish.yml` and environment `pypi`.
Create the `pypi` GitHub environment. The name is not reserved until PyPI accepts
the first publication; recheck it at that point.

Set the repository variable `PYPI_PUBLISH_ENABLED=true`, then manually run
`publish.yml` on the release tag with `publish=true`. The workflow reruns tests,
builds distributions and uploads them using OIDC. No long-lived PyPI token is
required. A normal push, tag or GitHub release never publishes to PyPI.

After publication:

- Check `python -m pip install mpl-pointpicker==0.1.0` in a fresh environment.
- Check `python -m pip install "mpl-pointpicker[notebook]==0.1.0"` and `%matplotlib widget`.
- Update the README's primary installation commands to use PyPI.
- Replace the provisional GitHub installation in the SCCircuits draft PR's CI/development setup with index-based resolution, update its lockfile, and run all required checks.
- Merge the SCCircuits migration only after its ordinary `pip install .` resolves from PyPI.
