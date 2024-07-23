import nox
from shlex import split
import os

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

    if "live" in session.posargs:
        # Run a live server
        session.install("sphinx-autobuild")
        session.run(
            *split(
                "sphinx-autobuild -b dirhtml book book/_build/dirhtml --port 0 --ignore book/data"
            ), env=env
        )
    else:
        session.run(*split("sphinx-build -b dirhtml book book/_build/dirhtml"), env=env)
