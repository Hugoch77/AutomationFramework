"""Tests for the web engine that do not need a browser.

Construction, validation and the guards inherited from `Engine` are all checkable without
launching Chromium — and should be, so that a configuration mistake fails in milliseconds.
"""

import pytest

from automation_framework.core.capabilities import Feature
from automation_framework.core.exceptions import ConfigurationError, EngineNotStartedError
from automation_framework.core.locator import Locator, Strategy
from automation_framework.engines.web import PlaywrightEngine

pytestmark = pytest.mark.unit


class _FailingResource:
    """A Playwright handle whose `close()` fails with something Playwright never raises."""

    def close(self) -> None:
        raise OSError("el proceso del driver ya no está")


class _RecordingResource:
    def __init__(self) -> None:
        self.closed = False

    def close(self) -> None:
        self.closed = True


class TestConstruction:
    @pytest.mark.parametrize("browser", ["chromium", "firefox", "webkit"])
    def test_accepts_every_supported_browser(self, browser):
        assert PlaywrightEngine(browser=browser) is not None

    def test_rejects_an_unknown_browser_immediately(self):
        """Fails at construction, not thirty seconds later inside Playwright."""
        with pytest.raises(ConfigurationError, match="Navegador desconocido"):
            PlaywrightEngine(browser="internet-explorer")

    def test_the_error_lists_the_alternatives(self):
        with pytest.raises(ConfigurationError, match="chromium, firefox, webkit"):
            PlaywrightEngine(browser="netscape")

    def test_defaults_to_headless(self):
        """CI has no display, so the safe default is the one that works there."""
        assert PlaywrightEngine()._headless is True

    def test_tracing_is_off_by_default(self):
        assert PlaywrightEngine()._record_trace is False


class TestCapabilities:
    def test_declares_the_web_features(self):
        engine = PlaywrightEngine()

        assert engine.has_feature(Feature.SCREENSHOT)
        assert engine.has_feature(Feature.TRACING)

    def test_does_not_claim_desktop_only_features(self):
        assert PlaywrightEngine().has_feature(Feature.ATTACH_TO_RUNNING) is False

    def test_supports_web_strategies_only(self):
        engine = PlaywrightEngine()

        assert engine.supports(Strategy.CSS) is True
        assert engine.supports(Strategy.AUTOMATION_ID) is False


class TestGuardsBeforeStart:
    def test_page_is_refused(self):
        with pytest.raises(EngineNotStartedError) as excinfo:
            _ = PlaywrightEngine().page

        assert excinfo.value.operation == "page"

    def test_goto_is_refused(self):
        with pytest.raises(EngineNotStartedError) as excinfo:
            PlaywrightEngine().goto("https://ejemplo.test")

        assert excinfo.value.operation == "goto"

    def test_find_is_refused(self):
        with pytest.raises(EngineNotStartedError):
            PlaywrightEngine().find(Locator.css("h1"))


class TestTeardownRobustness:
    def test_stopping_a_never_started_engine_is_harmless(self):
        """Teardown runs from `finally`; raising there would mask the real failure."""
        PlaywrightEngine().stop()

    def test_save_trace_returns_none_when_tracing_was_off(self, tmp_path):
        """So a failure hook can call it unconditionally, without knowing the config."""
        assert PlaywrightEngine().save_trace(tmp_path / "traza.zip") is None

    def test_closing_survives_a_non_playwright_error(self):
        """Closing touches the filesystem and a pipe: an OSError is as likely as a
        PlaywrightError, and neither may become the exception the test reports."""
        engine = PlaywrightEngine()
        engine._page = _FailingResource()
        engine._browser = _FailingResource()

        engine._stop()

        assert engine._page is None
        assert engine._browser is None

    def test_every_resource_is_closed_even_if_an_earlier_one_fails(self):
        """One broken handle must not strand the rest — that is how processes leak."""
        engine = PlaywrightEngine()
        engine._page = _FailingResource()
        engine._browser = browser = _RecordingResource()

        engine._stop()

        assert browser.closed is True
