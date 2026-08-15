"""Tests for the Strategy → Playwright translation.

No browser here on purpose. The mapping is a lookup table, and a lookup table deserves tests
that run in milliseconds rather than a 30-second browser suite. The end-to-end tests then
confirm the translated locators actually resolve.
"""

import pytest

from automation_framework.core.exceptions import UnsupportedStrategyError
from automation_framework.core.locator import Locator, Strategy
from automation_framework.engines.web.locators import (
    ENGINE_NAME,
    WEB_CAPABILITIES,
    to_playwright,
)

pytestmark = pytest.mark.unit


class SpyPage:
    """Records which Playwright API was called, and with what."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple, dict]] = []

    def _record(self, name):
        def call(*args, **kwargs):
            self.calls.append((name, args, kwargs))
            return f"<{name}>"

        return call

    def __getattr__(self, name):
        return self._record(name)

    @property
    def last(self):
        return self.calls[-1]


@pytest.fixture
def page():
    return SpyPage()


class TestCapabilities:
    def test_declares_the_web_strategies(self):
        for strategy in (
            Strategy.TEST_ID,
            Strategy.ROLE,
            Strategy.TEXT,
            Strategy.LABEL,
            Strategy.PLACEHOLDER,
            Strategy.CSS,
            Strategy.XPATH,
        ):
            assert WEB_CAPABILITIES.supports(strategy)

    @pytest.mark.parametrize(
        "strategy", [Strategy.AUTOMATION_ID, Strategy.CONTROL_TYPE, Strategy.CLASS_NAME]
    )
    def test_does_not_claim_the_desktop_strategies(self, strategy):
        assert not WEB_CAPABILITIES.supports(strategy)

    def test_does_not_claim_name(self):
        """An accessible name is only addressable paired with a role, so claiming NAME would
        mean guessing — and a locator that silently matches the wrong element is worse than
        one that refuses to exist."""
        assert not WEB_CAPABILITIES.supports(Strategy.NAME)

    def test_is_named_web(self):
        assert WEB_CAPABILITIES.name == ENGINE_NAME == "web"


class TestTranslation:
    def test_test_id(self, page):
        to_playwright(page, Locator.test_id("caja"))

        assert page.last == ("get_by_test_id", ("caja",), {})

    def test_css(self, page):
        to_playwright(page, Locator.css("button.primario"))

        assert page.last == ("locator", ("button.primario",), {})

    def test_xpath_carries_an_explicit_prefix(self, page):
        """Without it we would rely on Playwright's heuristic, which only recognises XPath
        starting with `//` or `..`."""
        to_playwright(page, Locator.xpath("(//button)[1]"))

        assert page.last == ("locator", ("xpath=(//button)[1]",), {})

    def test_text_defaults_to_a_loose_match(self, page):
        to_playwright(page, Locator.text("Buscar"))

        assert page.last == ("get_by_text", ("Buscar",), {"exact": False})

    def test_text_honours_the_exact_option(self, page):
        to_playwright(page, Locator(Strategy.TEXT, "Buscar", options={"exact": True}))

        assert page.last[2] == {"exact": True}

    def test_label(self, page):
        to_playwright(page, Locator(Strategy.LABEL, "Correo"))

        assert page.last == ("get_by_label", ("Correo",), {"exact": False})

    def test_placeholder(self, page):
        to_playwright(page, Locator(Strategy.PLACEHOLDER, "Buscar algo"))

        assert page.last == ("get_by_placeholder", ("Buscar algo",), {})

    def test_role_without_options(self, page):
        to_playwright(page, Locator.role("button"))

        assert page.last == ("get_by_role", ("button",), {})

    def test_role_forwards_the_accessible_name(self, page):
        to_playwright(page, Locator.role("button", name="Buscar"))

        assert page.last == ("get_by_role", ("button",), {"name": "Buscar"})

    def test_role_forwards_exact(self, page):
        to_playwright(page, Locator(Strategy.ROLE, "button", options={"exact": True}))

        assert page.last[2] == {"exact": True}

    def test_role_ignores_options_it_does_not_know(self, page):
        """Passing unknown keys straight through would blow up inside Playwright with a
        message that says nothing about our locator."""
        to_playwright(page, Locator(Strategy.ROLE, "button", options={"inventado": 1}))

        assert page.last[2] == {}


class TestUnsupported:
    @pytest.mark.parametrize(
        "locator",
        [
            Locator.automation_id("SearchBox"),
            Locator.control_type("Button"),
            Locator.class_name("TextBox"),
            Locator.name("Buscar"),
        ],
    )
    def test_a_desktop_locator_is_refused(self, page, locator):
        with pytest.raises(UnsupportedStrategyError):
            to_playwright(page, locator)

    def test_the_error_names_the_engine_and_lists_the_alternatives(self, page):
        with pytest.raises(UnsupportedStrategyError) as excinfo:
            to_playwright(page, Locator.automation_id("SearchBox"))

        assert excinfo.value.engine_name == "web"
        assert "test_id" in str(excinfo.value)

    def test_nothing_is_asked_of_the_page(self, page):
        """It must fail before touching the browser, not after a failed lookup."""
        with pytest.raises(UnsupportedStrategyError):
            to_playwright(page, Locator.automation_id("SearchBox"))

        assert page.calls == []
