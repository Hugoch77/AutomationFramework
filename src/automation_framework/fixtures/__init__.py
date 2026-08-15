"""Pytest integration.

The plugin is registered through the ``pytest11`` entry point in ``pyproject.toml``, so
installing the package is enough — suites never need a ``conftest.py`` just to wire it up.
"""

from automation_framework.fixtures.plugin import artifacts_dir, engine, settings

__all__ = ["artifacts_dir", "engine", "settings"]
