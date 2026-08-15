"""Tests for the engine contract.

The guard rails live in the base class so that no engine author has to remember them.
These tests pin that down: lifecycle handling, strategy validation and feature gating must
work identically for every engine, present and future.
"""

from pathlib import Path

import pytest

from automation_framework.core.capabilities import Capabilities, Feature
from automation_framework.core.engine import Engine
from automation_framework.core.exceptions import (
    EngineError,
    EngineNotStartedError,
    UnsupportedOperationError,
    UnsupportedStrategyError,
)
from automation_framework.core.locator import Locator, Strategy
from automation_framework.testing import FakeEngine

pytestmark = pytest.mark.unit

BUTTON = Locator.test_id("submit")
ROW = Locator.css("table tr")


class NarrowEngine(FakeEngine):
    """An engine that only understands desktop strategies and cannot take screenshots."""

    @property
    def capabilities(self) -> Capabilities:
        return Capabilities.of(
            "narrow",
            strategies={Strategy.AUTOMATION_ID, Strategy.NAME},
            features={Feature.ATTACH_TO_RUNNING},
        )


@pytest.fixture
def engine():
    with FakeEngine(timeout=0.05, poll_interval=0.001) as engine:
        yield engine


class TestLifecycle:
    def test_starts_stopped(self):
        assert FakeEngine().is_started is False

    def test_start_marks_it_started_and_returns_self(self):
        engine = FakeEngine()

        assert engine.start() is engine
        assert engine.is_started is True
        assert engine.start_count == 1

    def test_stop_releases_and_flips_the_flag(self):
        engine = FakeEngine().start()

        engine.stop()

        assert engine.is_started is False
        assert engine.stop_count == 1

    def test_starting_twice_is_reported(self):
        """Almost always a fixture-scope bug, so it must not pass silently."""
        engine = FakeEngine().start()

        with pytest.raises(EngineError, match="scope de la fixture"):
            engine.start()

    def test_stopping_twice_is_harmless(self):
        engine = FakeEngine().start()
        engine.stop()

        engine.stop()

        assert engine.stop_count == 1

    def test_stopping_a_never_started_engine_is_harmless(self):
        engine = FakeEngine()

        engine.stop()

        assert engine.stop_count == 0

    def test_can_be_restarted(self):
        engine = FakeEngine()
        engine.start()
        engine.stop()

        engine.start()

        assert engine.is_started is True
        assert engine.start_count == 2

    def test_repr_shows_the_state(self):
        engine = FakeEngine()

        assert "parado" in repr(engine)
        assert "arrancado" in repr(engine.start())


class BrokenStartEngine(FakeEngine):
    """An engine whose launch blows up halfway, after acquiring something."""

    def _start(self) -> None:
        super()._start()
        raise RuntimeError("el navegador no arrancó")


class UncleanableEngine(BrokenStartEngine):
    """Worse: its own teardown is broken too."""

    def _stop(self) -> None:
        raise OSError("tampoco se pudo limpiar")


class TestStartFailure:
    """A half-started engine has to clean up after itself.

    Launching is several steps for every technology (driver, then app, then a window). If the
    second one fails, the first one's resources are already live and the caller never receives
    an engine to call `stop()` on, so nobody will ever close them.
    """

    def test_the_failure_reaches_the_caller(self):
        with pytest.raises(RuntimeError, match="el navegador no arrancó"):
            BrokenStartEngine().start()

    def test_teardown_runs_on_a_failed_start(self):
        engine = BrokenStartEngine()

        with pytest.raises(RuntimeError):
            engine.start()

        assert engine.stop_count == 1

    def test_the_engine_is_left_stopped(self):
        engine = BrokenStartEngine()

        with pytest.raises(RuntimeError):
            engine.start()

        assert engine.is_started is False

    def test_it_can_be_started_again_afterwards(self):
        """A retry must not hit the "already started" guard."""
        engine = BrokenStartEngine()

        with pytest.raises(RuntimeError):
            engine.start()

        with pytest.raises(RuntimeError):
            engine.start()

    def test_a_broken_teardown_does_not_hide_the_real_failure(self):
        """The start error explains what happened; the cleanup error is noise."""
        with pytest.raises(RuntimeError, match="el navegador no arrancó"):
            UncleanableEngine().start()


class TestContextManager:
    def test_starts_on_enter_and_stops_on_exit(self):
        engine = FakeEngine()

        with engine as entered:
            assert entered is engine
            assert engine.is_started is True

        assert engine.is_started is False
        assert engine.stop_count == 1

    def test_stops_even_when_the_body_raises(self):
        """Teardown must survive a failing test, or the next one inherits a dirty session."""
        engine = FakeEngine()

        with pytest.raises(RuntimeError), engine:
            raise RuntimeError("el test explotó")

        assert engine.is_started is False
        assert engine.stop_count == 1


class TestStartedGuard:
    """Using a stopped engine gives a readable error, not an AttributeError deep inside."""

    @pytest.mark.parametrize(
        ("operation", "call"),
        [
            ("find", lambda e: e.find(BUTTON)),
            ("find_all", lambda e: e.find_all(BUTTON)),
            ("screenshot", lambda e: e.screenshot(Path("shot.png"))),
        ],
    )
    def test_operations_require_a_started_engine(self, operation, call):
        engine = FakeEngine()

        with pytest.raises(EngineNotStartedError) as excinfo:
            call(engine)

        assert excinfo.value.operation == operation

    def test_the_guard_returns_after_stopping(self, engine):
        engine.stop()

        with pytest.raises(EngineNotStartedError):
            engine.find(BUTTON)


class TestStrategyValidation:
    def test_supports_reflects_the_declared_capabilities(self):
        engine = NarrowEngine()

        assert engine.supports(Strategy.AUTOMATION_ID) is True
        assert engine.supports(Strategy.CSS) is False

    def test_an_unsupported_locator_fails_at_lookup_time(self):
        """Failing here beats a mysterious "element not found" ten seconds later."""
        with NarrowEngine() as engine, pytest.raises(UnsupportedStrategyError) as excinfo:
            engine.find(ROW)

        assert excinfo.value.strategy is Strategy.CSS
        assert excinfo.value.engine_name == "narrow"

    def test_find_all_validates_too(self):
        with NarrowEngine() as engine, pytest.raises(UnsupportedStrategyError):
            engine.find_all(ROW)

    def test_the_error_lists_what_is_supported(self):
        with NarrowEngine() as engine, pytest.raises(UnsupportedStrategyError) as excinfo:
            engine.find(ROW)

        assert "automation_id" in str(excinfo.value)

    def test_a_supported_locator_goes_through(self):
        with NarrowEngine() as engine:
            assert engine.find(Locator.automation_id("SearchBox")) is not None


class TestFeatureGating:
    def test_has_feature_reflects_the_declaration(self, engine):
        assert engine.has_feature(Feature.SCREENSHOT) is True
        assert engine.has_feature(Feature.TRACING) is False

    def test_screenshot_works_when_declared(self, engine, tmp_path):
        destination = engine.screenshot(tmp_path / "shots" / "captura.png")

        assert destination.exists()

    def test_screenshot_is_refused_when_not_declared(self, tmp_path):
        with NarrowEngine() as engine, pytest.raises(UnsupportedOperationError) as excinfo:
            engine.screenshot(tmp_path / "captura.png")

        assert excinfo.value.operation == "screenshot"


class TestFind:
    def test_find_returns_a_handle_without_resolving(self, engine):
        assert engine.find(Locator.test_id("nope")) is not None

    def test_find_all_is_empty_when_nothing_matches(self, engine):
        assert engine.find_all(BUTTON) == []

    def test_find_all_returns_one_handle_per_match(self, engine):
        engine.add(BUTTON, text="uno")
        engine.add(BUTTON, text="dos")

        elements = engine.find_all(BUTTON)

        assert [element.text() for element in elements] == ["uno", "dos"]

    def test_elements_inherit_the_engine_timeouts(self, engine):
        element = engine.find(BUTTON)

        assert element._timeout == engine.timeout
        assert element._poll_interval == engine.poll_interval


class TestDescription:
    def test_name_comes_from_the_capabilities(self, engine):
        assert engine.name == "fake"

    def test_the_abstract_contract_cannot_be_instantiated(self):
        with pytest.raises(TypeError):
            Engine()  # type: ignore[abstract]

    def test_an_incomplete_engine_fails_loudly_at_construction(self):
        """The payoff of ABC over Protocol: a forgotten method is a runtime error, now."""

        class Incomplete(Engine):
            @property
            def capabilities(self):
                return Capabilities.of("incomplete", strategies=set())

        with pytest.raises(TypeError, match="abstract"):
            Incomplete()  # type: ignore[abstract]
