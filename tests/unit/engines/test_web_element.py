"""Tests for the translation of Playwright errors, without launching a browser.

The point of the web element is not only to drive Playwright but to **contain** it. If a
`playwright.sync_api.Error` reached a test, suites would start catching engine-specific types
and the abstraction the framework is built on would be gone. A stub locator is enough to pin
that down, and it does it in milliseconds.
"""

import re

import pytest
from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from automation_framework.core.exceptions import ElementError, ElementNotFoundError
from automation_framework.core.locator import Locator
from automation_framework.engines.web.element import WebElement

pytestmark = pytest.mark.unit

BUTTON = Locator.css("button.enviar")

# Un error de Playwright real trae el mensaje y, debajo, un "call log" larguísimo.
CONTEXT_LOST = "Execution context was destroyed, most likely because of a navigation"
WITH_CALL_LOG = f"{CONTEXT_LOST}\nCall log:\n  - waiting for locator('button')\n  - retrying"


class ExplodingLocator:
    """Stands in for a Playwright locator that fails on every call."""

    def __init__(self, error: Exception) -> None:
        self._error = error

    def _raise(self, *args: object, **kwargs: object) -> None:
        raise self._error

    count = inner_text = get_attribute = input_value = click = fill = is_visible = _raise


def element_raising(error: Exception) -> WebElement:
    """A web element whose underlying locator raises ``error`` for anything it is asked."""
    web_element = WebElement(page=None, locator=BUTTON, timeout=0.05, poll_interval=0.001)  # type: ignore[arg-type]
    web_element._resolved = ExplodingLocator(error)  # type: ignore[assignment]
    return web_element


class TestNonTimeoutErrorsAreTranslated:
    """A destroyed context, a detached node or a closed page are not "not found"."""

    @pytest.mark.parametrize(
        ("operation", "call"),
        [
            ("_text", lambda el: el._text()),
            ("_attribute", lambda el: el._attribute("href")),
            ("_click", lambda el: el._click()),
            ("_fill", lambda el: el._fill("hola")),
        ],
    )
    def test_playwright_errors_never_escape(self, operation, call):
        element = element_raising(PlaywrightError(CONTEXT_LOST))

        with pytest.raises(ElementError):
            call(element)

    def test_the_message_names_the_locator(self):
        element = element_raising(PlaywrightError(CONTEXT_LOST))

        with pytest.raises(ElementError, match=re.escape("button.enviar")):
            element._text()

    def test_the_message_keeps_the_cause(self):
        element = element_raising(PlaywrightError(CONTEXT_LOST))

        with pytest.raises(ElementError, match="Execution context was destroyed"):
            element._text()

    def test_the_call_log_is_dropped(self):
        """Playwright's retry history buries the actual cause under fifty lines."""
        element = element_raising(PlaywrightError(WITH_CALL_LOG))

        with pytest.raises(ElementError) as excinfo:
            element._text()

        assert "Call log" not in str(excinfo.value)

    def test_the_original_error_is_chained(self):
        """`raise ... from` keeps the Playwright traceback available for debugging."""
        element = element_raising(PlaywrightError(CONTEXT_LOST))

        with pytest.raises(ElementError) as excinfo:
            element._click()

        assert isinstance(excinfo.value.__cause__, PlaywrightError)


class TestTimeoutsStayNotFound:
    """A timeout has its own meaning and must not be flattened into a generic failure."""

    @pytest.mark.parametrize(
        ("operation", "call"),
        [
            ("_text", lambda el: el._text()),
            ("_attribute", lambda el: el._attribute("href")),
            ("_click", lambda el: el._click()),
            ("_fill", lambda el: el._fill("hola")),
        ],
    )
    def test_a_timeout_is_reported_as_not_found(self, operation, call):
        element = element_raising(PlaywrightTimeoutError("Timeout 1000ms exceeded"))

        with pytest.raises(ElementNotFoundError):
            call(element)


class TestQueriesThatSwallowErrors:
    """`_exists` and `_is_visible` answer a question; failing to answer means "no"."""

    def test_exists_is_false_when_the_query_blows_up(self):
        assert element_raising(PlaywrightError(CONTEXT_LOST))._exists() is False

    def test_is_visible_is_false_when_the_query_blows_up(self):
        assert element_raising(PlaywrightError(CONTEXT_LOST))._is_visible() is False


class TestValueKeepsItsOwnMessage:
    def test_a_non_editable_element_gets_an_actionable_hint(self):
        """The generic wrapper would lose the "did you mean text()?" nudge."""
        element = element_raising(PlaywrightError("Node is not an <input>, <textarea> or <select>"))

        with pytest.raises(ElementError, match="text\\(\\) o attribute\\(\\)"):
            element._value()

    def test_a_timeout_is_still_not_found(self):
        element = element_raising(PlaywrightTimeoutError("Timeout 1000ms exceeded"))

        with pytest.raises(ElementNotFoundError):
            element._value()
