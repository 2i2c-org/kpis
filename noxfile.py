import nox
from shlex import split

nox.options.reuse_existing_virtualenvs = True

@nox.session
def lab(session):
    session.install('-r', 'requirements.txt')
    session.run(*split('jupyter lab'))

@nox.session
def docs(session):
    session.install('-r', 'requirements.txt')
    
    if "live" in session.posargs:
      session.install("sphinx-autobuild")
      session.run(*split("sphinx-autobuild book book/_build/html"))
    else:
      session.run(*split("sphinx-build book book/_build/html"))
