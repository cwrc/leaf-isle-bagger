#!/usr/bin/python3

import nox

_python_app_dir = "rootfs/var/www/leaf-isle-bagger"
_requirements_app = f"{_python_app_dir}/requirements/requirements.txt"
_requirements_tests = (
    "rootfs/var/www/leaf-isle-bagger/requirements/requirements_pytests.txt"
)


@nox.session
def format(session):
    session.install("-r", _requirements_tests)
    session.run("black", ".")


@nox.session
def lint(session):
    session.install("-r", _requirements_tests)
    session.install("-r", _requirements_app)
    session.run("flake8", "--max-line-length=120", "--exclude=venv,__pycache__,.nox")
    # session.run("pylint", f"{_python_app_dir}", "--extension-pkg-allow-list=")


@nox.session(python=["3.10", "3.11", "3.12"])
def test(session):
    session.install("-r", _requirements_tests)
    session.install("-r", _requirements_app)
    session.run("pytest", *session.posargs)
