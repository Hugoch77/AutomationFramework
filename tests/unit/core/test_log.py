"""Tests for structured logging.

What matters here is not the rendering but the context: with tests running in parallel, a log
line that cannot be attributed to a test is noise.

Output is asserted through an injected logger factory rather than through
``structlog.testing.capture_logs``, because that helper replaces the processor chain —
``merge_contextvars`` included — and would therefore prove nothing about the pipeline
actually shipped.
"""

import json

import pytest
import structlog

from automation_framework.core.exceptions import ConfigurationError
from automation_framework.core.log import (
    bind_context,
    bound_context,
    clear_context,
    configure_logging,
    current_context,
    get_logger,
    unbind_context,
)

pytestmark = pytest.mark.unit


class Capture:
    """Collects the JSON lines the real processor chain produces."""

    def __init__(self) -> None:
        self.factory = structlog.testing.CapturingLoggerFactory()

    @property
    def entries(self) -> list[dict]:
        return [json.loads(call.args[0]) for call in self.factory.logger.calls]

    @property
    def events(self) -> list[str]:
        return [entry["event"] for entry in self.entries]


@pytest.fixture
def capture():
    capture = Capture()
    configure_logging(level="DEBUG", json_output=True, logger_factory=capture.factory)
    return capture


@pytest.fixture(autouse=True)
def _clean_logging():
    clear_context()
    yield
    clear_context()
    structlog.reset_defaults()


class TestConfiguration:
    @pytest.mark.parametrize("level", ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])
    def test_accepts_every_standard_level(self, level):
        configure_logging(level=level)

    def test_is_case_insensitive(self):
        configure_logging(level="debug")

    def test_rejects_an_unknown_level(self):
        with pytest.raises(ConfigurationError, match="Nivel de log desconocido"):
            configure_logging(level="CHATTY")

    def test_does_not_chain_the_raw_keyerror(self):
        with pytest.raises(ConfigurationError) as excinfo:
            configure_logging(level="CHATTY")

        assert excinfo.value.__cause__ is None

    def test_filters_below_the_configured_level(self):
        capture = Capture()
        configure_logging(level="WARNING", json_output=True, logger_factory=capture.factory)

        get_logger("test").debug("no debería salir")
        get_logger("test").warning("sí debería salir")

        assert capture.events == ["sí debería salir"]

    def test_reconfiguring_takes_effect_on_existing_loggers(self):
        """Loggers are not cached, so changing the level mid-session actually works."""
        logger = get_logger("test")
        capture = Capture()
        configure_logging(level="ERROR", json_output=True, logger_factory=capture.factory)

        logger.info("silenciado")

        assert capture.events == []

    def test_human_readable_output_is_the_default(self):
        capture = Capture()
        configure_logging(level="DEBUG", logger_factory=capture.factory)

        get_logger("test").info("evento", termino="notepad")

        rendered = capture.factory.logger.calls[0].args[0]
        assert "evento" in rendered
        assert not rendered.lstrip().startswith("{")


class TestLogger:
    def test_emits_the_event_and_its_fields(self, capture):
        get_logger("test").info("buscando", termino="notepad")

        assert capture.entries[0]["event"] == "buscando"
        assert capture.entries[0]["termino"] == "notepad"

    def test_records_the_level(self, capture):
        get_logger("test").warning("cuidado")

        assert capture.entries[0]["level"] == "warning"

    def test_stamps_every_line_with_a_timestamp(self, capture):
        get_logger("test").info("evento")

        assert capture.entries[0]["timestamp"].endswith("Z")

    def test_works_without_a_name(self, capture):
        get_logger().info("sin nombre")

        assert capture.events == ["sin nombre"]

    def test_renders_an_exception(self, capture):
        try:
            raise RuntimeError("algo explotó")
        except RuntimeError:
            get_logger("test").exception("fallo")

        assert "algo explotó" in capture.entries[0]["exception"]


class TestContext:
    def test_bound_values_reach_every_later_line(self, capture):
        bind_context(test_id="test_busqueda")

        get_logger("test").info("una")
        get_logger("test").info("otra")

        assert all(entry["test_id"] == "test_busqueda" for entry in capture.entries)

    def test_unbind_removes_a_single_key(self, capture):
        bind_context(test_id="test_busqueda", intento=1)
        unbind_context("intento")

        get_logger("test").info("evento")

        assert capture.entries[0]["test_id"] == "test_busqueda"
        assert "intento" not in capture.entries[0]

    def test_clear_removes_everything(self, capture):
        bind_context(test_id="test_busqueda")
        clear_context()

        get_logger("test").info("evento")

        assert "test_id" not in capture.entries[0]

    def test_current_context_reports_what_is_bound(self):
        bind_context(test_id="test_busqueda", engine="fake")

        assert current_context() == {"test_id": "test_busqueda", "engine": "fake"}

    def test_current_context_is_a_copy(self):
        bind_context(test_id="test_busqueda")

        current_context()["test_id"] = "modificado"

        assert current_context()["test_id"] == "test_busqueda"


class TestBoundContext:
    def test_binds_for_the_duration_of_the_block(self, capture):
        with bound_context(test_id="test_busqueda"):
            get_logger("test").info("dentro")

        assert capture.entries[0]["test_id"] == "test_busqueda"

    def test_carries_several_fields(self, capture):
        with bound_context(test_id="test_x", engine="fake"):
            get_logger("test").info("dentro")

        assert capture.entries[0]["engine"] == "fake"

    def test_restores_the_previous_context_on_exit(self):
        """Teardown logs must not inherit the context of the test that just ended."""
        with bound_context(test_id="test_busqueda"):
            pass

        assert current_context() == {}

    def test_restores_even_when_the_block_raises(self):
        with pytest.raises(RuntimeError), bound_context(test_id="test_busqueda"):
            raise RuntimeError("el test explotó")

        assert current_context() == {}

    def test_nesting_restores_the_outer_value(self, capture):
        with bound_context(test_id="externo"):
            with bound_context(test_id="interno"):
                get_logger("test").info("dentro")
            get_logger("test").info("fuera")

        assert [entry["test_id"] for entry in capture.entries] == ["interno", "externo"]

    def test_does_not_disturb_unrelated_keys(self):
        bind_context(engine="fake")

        with bound_context(test_id="test_x"):
            pass

        assert current_context() == {"engine": "fake"}
