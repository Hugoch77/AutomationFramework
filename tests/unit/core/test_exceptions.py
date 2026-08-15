"""Tests for the exception hierarchy.

Error messages are part of the framework's usable surface: when a suite fails at 2am, the
message is the whole diagnosis. These tests pin down that they carry actionable context.
"""

import pytest

from automation_framework.core.exceptions import (
    AutomationError,
    ConfigurationError,
    ElementError,
    ElementNotFoundError,
    EngineAlreadyRegisteredError,
    EngineError,
    EngineNotRegisteredError,
    EngineNotStartedError,
    UnsupportedOperationError,
    UnsupportedStrategyError,
    WaitTimeoutError,
)
from automation_framework.core.locator import Locator, Strategy

pytestmark = pytest.mark.unit


class TestHierarchy:
    """A single base class lets callers catch the whole family."""

    @pytest.mark.parametrize(
        "exception",
        [
            ConfigurationError("x"),
            EngineError("x"),
            EngineNotRegisteredError("web"),
            EngineAlreadyRegisteredError("web"),
            EngineNotStartedError("web", "find"),
            ElementError("x"),
            ElementNotFoundError(Locator.css("a")),
            UnsupportedStrategyError("desktop", Strategy.CSS, []),
            UnsupportedOperationError("desktop", "trace"),
            WaitTimeoutError("algo", 1.0),
        ],
    )
    def test_everything_derives_from_automation_error(self, exception):
        assert isinstance(exception, AutomationError)

    @pytest.mark.parametrize(
        ("exception", "expected_base"),
        [
            (EngineNotRegisteredError("web"), EngineError),
            (EngineAlreadyRegisteredError("web"), EngineError),
            (EngineNotStartedError("web", "find"), EngineError),
            (ElementNotFoundError(Locator.css("a")), ElementError),
        ],
    )
    def test_subfamilies_are_catchable_on_their_own(self, exception, expected_base):
        assert isinstance(exception, expected_base)

    def test_wait_timeout_is_not_a_builtin_timeout_error(self):
        """A bare `except TimeoutError` in user code must not swallow framework waits."""
        assert not isinstance(WaitTimeoutError("algo", 1.0), TimeoutError)


class TestEngineNotRegisteredError:
    def test_lists_the_available_engines(self):
        error = EngineNotRegisteredError("mobile", ["web", "desktop"])

        assert "'mobile'" in str(error)
        assert "'web'" in str(error)
        assert "'desktop'" in str(error)

    def test_says_ninguno_when_the_registry_is_empty(self):
        assert "ninguno" in str(EngineNotRegisteredError("web"))

    def test_suggests_the_two_usual_causes(self):
        message = str(EngineNotRegisteredError("web"))

        assert "importar" in message
        assert "extra opcional" in message

    def test_keeps_the_data_queryable(self):
        error = EngineNotRegisteredError("mobile", ["web"])

        assert error.name == "mobile"
        assert error.available == ("web",)


class TestEngineNotStartedError:
    def test_names_the_engine_and_the_attempted_operation(self):
        error = EngineNotStartedError("web", "find")

        assert "'web'" in str(error)
        assert "'find'" in str(error)

    def test_explains_how_to_fix_it(self):
        assert "context manager" in str(EngineNotStartedError("web", "find"))


class TestElementNotFoundError:
    def test_includes_the_locator_description(self):
        locator = Locator.automation_id("SearchBox", description="caja de búsqueda")

        assert "caja de búsqueda" in str(ElementNotFoundError(locator))

    def test_reports_how_long_it_waited(self):
        error = ElementNotFoundError(Locator.css("a"), timeout=7.5)

        assert "7.5s" in str(error)

    def test_omits_the_wait_when_unknown(self):
        assert "esperar" not in str(ElementNotFoundError(Locator.css("a")))

    def test_keeps_the_locator_queryable(self):
        locator = Locator.css("a")

        assert ElementNotFoundError(locator).locator is locator


class TestUnsupportedStrategyError:
    def test_lists_the_supported_strategies_sorted(self):
        error = UnsupportedStrategyError(
            "desktop", Strategy.CSS, [Strategy.NAME, Strategy.AUTOMATION_ID]
        )

        message = str(error)
        assert "'css'" in message
        assert message.index("automation_id") < message.index("name")

    def test_says_ninguna_when_the_engine_supports_nothing(self):
        assert "ninguna" in str(UnsupportedStrategyError("fake", Strategy.CSS, []))


class TestUnsupportedOperationError:
    def test_appends_the_hint_when_given(self):
        error = UnsupportedOperationError("desktop", "trace", hint="Usa screenshot() en su lugar.")

        assert "Usa screenshot() en su lugar." in str(error)

    def test_works_without_a_hint(self):
        message = str(UnsupportedOperationError("desktop", "trace"))

        assert message.endswith("'trace'.")


class TestWaitTimeoutError:
    def test_reports_the_condition_and_the_budget(self):
        error = WaitTimeoutError("que el botón sea visible", 10.0)

        assert "que el botón sea visible" in str(error)
        assert "10s" in str(error)

    def test_formats_fractional_timeouts_without_noise(self):
        assert "0.5s" in str(WaitTimeoutError("algo", 0.5))
