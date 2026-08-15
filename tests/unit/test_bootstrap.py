"""Phase 0 sanity checks: the package is installed and importable."""

import pytest


@pytest.mark.unit
def test_package_is_importable():
    import automation_framework

    assert automation_framework.__version__


@pytest.mark.unit
def test_version_matches_project_metadata():
    from importlib.metadata import version

    import automation_framework

    assert version("automation-framework") == automation_framework.__version__
