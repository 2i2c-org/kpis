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
    session.run(*split("sphinx-build -b dirhtml book book/_build/dirhtml"), env=env)


def download_release(session, repo, tag, pattern, dest):
    """Download the assets matching `pattern` from a GitHub release, using the gh CLI."""
    cmd = f"gh release download {tag} --repo {repo} --pattern {pattern} --dir {dest} --clobber"
    session.run(*split(cmd), external=True)


@nox.session
def data(session):
    """Download data that we need for the book."""
    session.install("-r", "requirements.txt")
    data_dir = "book/data"
    # Monthly active users, published by 2i2c-org/data
    download_release(session, "2i2c-org/data", "cloud", "maus-*.csv", data_dir)
    session.run(*split("python book/scripts/cloud/validate.py"))
    # GitHub activity (2i2c-org plus the Jupyter orgs) and the team roster,
    # both published by 2i2c-org/data-private. Needs a token that can read it.
    download_release(
        session,
        "2i2c-org/data-private",
        "github-latest",
        "*.db",
        "book/_build/upstream-data",
    )
    download_release(
        session, "2i2c-org/data-private", "team-latest", "team.csv", data_dir
    )


@nox.session(name="docs-live")
def docs_live(session):
    """Build the documentation with sphinx-autobuild for live preview"""
    session.install("-r", "requirements.txt")
    session.install("sphinx-autobuild")
    session.run(
        *split(
            "sphinx-autobuild -b dirhtml book book/_build/dirhtml --ignore *.csv --ignore *.toml"
        )
    )
