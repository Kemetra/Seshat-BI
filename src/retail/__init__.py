"""Deprecated ``retail`` console entry point for the renamed :mod:`seshat` package.

This package exists ONLY so the legacy ``retail`` command and
``python -m retail.cli`` keep working (``retail.cli.main`` is
``seshat.cli.main``). It is not a module alias: ``retail.rules``,
``retail.validate`` and other ``retail.*`` submodules do not exist -- import the
``seshat.*`` equivalents instead.
"""
