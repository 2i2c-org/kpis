import nox
from shlex import split

nox.options.default_venv_backend = "uv"
nox.options.reuse_existing_virtualenvs = True


@nox.session
def lab(session):
    """Launch JupyterLab for interactive exploration."""
    session.install("-r", "requirements.txt")
    session.run(*split("jupyter lab"))


@nox.session
def docs(session):
    """Generate static HTML of the documentation."""
    session.install("-r", "requirements.txt")
    env = {}
    if "github" in session.posargs:
        env["GITHUB_ACTION"] = "true"
    session.run(*split("python book/scripts/download_upstream_data.py"))
    session.run(*split("sphinx-build -b dirhtml book book/_build/dirhtml"), env=env)


@nox.session
def data(session):
    """Download data that we need for the book."""
    session.install("-r", "requirements.txt")
    data_dir = "book/data"
    # Download MAU data from data-private releases
    session.run(
        "gh", "release", "download", "maus-latest",
        "--repo", "2i2c-org/data-private",
        "--pattern", "maus-*.csv",
        "--dir", data_dir,
        "--clobber",
        external=True,
    )
    # Download HubSpot data from data-private releases
    session.run(
        "gh", "release", "download", "hubspot-latest",
        "--repo", "2i2c-org/data-private",
        "--pattern", "hubspot-deals.csv",
        "--dir", data_dir,
        "--clobber",
        external=True,
    )
    session.run(*split("python book/scripts/cloud/validate.py"))
    session.run(*split("python book/scripts/download_upstream_data.py"))


@nox.session(name="docs-live")
def docs_live(session):
    """Build the documentation with sphinx-autobuild for live preview"""
    session.install("-r", "requirements.txt")
    session.install("sphinx-autobuild")
    session.run(*split("python book/scripts/download_upstream_data.py"))
    session.run(
        *split(
            "sphinx-autobuild -b dirhtml book book/_build/dirhtml --ignore *.csv --ignore *.toml"
        )
    )
