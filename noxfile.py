import nox
from shlex import split
import os

nox.options.default_venv_backend = "uv"
nox.options.reuse_existing_virtualenvs = True


@nox.session
def lab(session):
    session.install("-r", "requirements.txt")
    session.run(*split("jupyter lab"))


@nox.session
def docs(session):
    session.install("-r", "requirements.txt")
    env = {}
    if "github" in session.posargs:
        # Simulate being in a GitHub Action
        env["GITHUB_ACTION"] = "true"

    session.run(*split("sphinx-build -b dirhtml book book/_build/dirhtml"), env=env)


@nox.session(name="docs-live")
def docs_live(session):
    """Build the documentation with sphinx-autobuild for live preview"""
    session.install("-r", "requirements.txt")
    session.install("sphinx-autobuild")
    session.run(
        *split(
            "sphinx-autobuild -b dirhtml book book/_build/dirhtml --ignore */book/data/*"
        )
    )
