"""Tests for engine discovery and registration."""

import pytest

from automation_framework.core.registry import create_engine, is_registered
from automation_framework.engines import KNOWN_ENGINES, load_available
from automation_framework.engines.web import PlaywrightEngine

pytestmark = pytest.mark.unit


class TestLoading:
    def test_reports_one_result_per_known_engine(self):
        assert set(load_available()) == set(KNOWN_ENGINES)

    def test_the_web_engine_loads_when_playwright_is_installed(self):
        assert load_available()["web"] is None

    def test_loading_twice_is_harmless(self):
        """Registration is idempotent, so reimporting must not raise about a taken name."""
        load_available()
        load_available()

        assert is_registered("web")


class TestRegistration:
    def test_importing_the_package_registers_the_engine(self):
        assert is_registered("web")

    def test_the_registry_builds_a_playwright_engine(self):
        engine = create_engine("web")

        assert isinstance(engine, PlaywrightEngine)

    def test_it_comes_back_stopped(self):
        """Creating an engine must not launch a browser; that is what start() is for."""
        assert create_engine("web").is_started is False
