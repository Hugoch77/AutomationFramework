"""Fixtures, command-line options and failure capture.

The `engine` fixture is function-scoped on purpose. A session-scoped browser would be faster,
but state leaks between tests — cookies, local storage, a modal left open — and the resulting
failures depend on execution order, which is the worst kind of flakiness to debug. Starting a
browser costs a fraction of a second; an order-dependent bug costs an afternoon.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

import pytest

from automation_framework.core.config import load_settings
from automation_framework.core.exceptions import ConfigurationError
from automation_framework.core.log import bound_context, configure_logging, get_logger
from automation_framework.core.registry import create_engine
from automation_framework.engines import load_available

if TYPE_CHECKING:
    from collections.abc import Generator, Iterator, Mapping
    from pathlib import Path

    from automation_framework.core.config import Settings
    from automation_framework.core.engine import Engine

log = get_logger(__name__)

_REPORTS = pytest.StashKey[dict[str, pytest.TestReport]]()
_UNSAFE_IN_FILENAMES = re.compile(r"[^A-Za-z0-9._-]+")


# ------------------------------------------------------------------------ opciones ---


def pytest_addoption(parser: pytest.Parser) -> None:
    group = parser.getgroup("automation-framework")
    group.addoption(
        "--headed",
        action="store_true",
        default=False,
        help="Ejecuta con la interfaz visible. Útil para depurar; en CI nunca.",
    )
    group.addoption(
        "--browser-name",
        action="store",
        default=None,
        help="Navegador para el engine web: chromium, firefox o webkit.",
    )
    # No se llama --trace: pytest ya usa ese nombre para lanzar el depurador al empezar
    # cada test, y registrar una opción duplicada aborta la sesión entera.
    group.addoption(
        "--record-trace",
        action="store_true",
        default=False,
        help="Graba una traza del engine y la adjunta si el test falla.",
    )
    group.addoption(
        "--app-url",
        action="store",
        default=None,
        help="URL raíz de la aplicación bajo prueba, para navegación relativa.",
    )


# ------------------------------------------------------------------------ fixtures ---


@pytest.fixture(scope="session")
def settings(request: pytest.FixtureRequest) -> Settings:
    """Configuration for the run, with command-line options taking precedence.

    The CLI wins over the environment because it is the more specific intent: someone typing
    `--headed` is debugging right now and should not have to unset a variable first.
    """
    overrides: dict[str, Any] = {}
    if request.config.getoption("--headed"):
        overrides["headless"] = False
    if browser := request.config.getoption("--browser-name"):
        overrides["browser"] = browser
    if request.config.getoption("--record-trace"):
        overrides["trace"] = True
    if url := request.config.getoption("--app-url"):
        overrides["base_url"] = url

    resolved = load_settings(**overrides)
    configure_logging(level=resolved.log_level, json_output=resolved.log_json)
    return resolved


def apply_overrides(settings: Settings, overrides: Mapping[str, Any]) -> Settings:
    """Merge ``@pytest.mark.af_config(...)`` values onto ``settings``, revalidating.

    Not `model_copy(update=...)`: pydantic v2 applies that update **without validating it**,
    so `af_config(headles=False)` attaches a brand-new attribute, leaves the real `headless`
    untouched and the test runs looking configured when it is not. Same failure mode as
    `AF_HEADLES` in the environment, and the same answer as `core.config` gives it — reject
    the unknown name loudly rather than ignore it.

    Rebuilding through `load_settings` also revalidates the *values*, so `af_config(browser=1)`
    or a negative timeout fail here instead of somewhere inside the engine.

    Raises:
        ConfigurationError: An override names no setting, or its value is invalid.
    """
    if not overrides:
        return settings

    known = set(type(settings).model_fields)
    if unknown := sorted(set(overrides) - known):
        raise ConfigurationError(
            f"Ajustes desconocidos en @pytest.mark.af_config: {', '.join(unknown)}. "
            f"Válidos: {', '.join(sorted(known))}."
        )
    return load_settings(**{**settings.model_dump(), **overrides})


@pytest.fixture(scope="session")
def artifacts_dir(settings: Settings) -> Path:
    """Directory for screenshots, traces and reports."""
    settings.artifacts_dir.mkdir(parents=True, exist_ok=True)
    return settings.artifacts_dir


@pytest.fixture
def engine(
    request: pytest.FixtureRequest, settings: Settings, artifacts_dir: Path
) -> Iterator[Engine]:
    """A started engine, torn down after the test, capturing evidence if it failed.

    A test can override any setting with ``@pytest.mark.af_config(...)``, which is how a
    suite against an app that publishes its hooks as ``data-test`` gets a correctly
    configured engine without giving up the shared failure capture.
    """
    load_available()

    marker = request.node.get_closest_marker("af_config")
    resolved = apply_overrides(settings, marker.kwargs) if marker else settings

    instance = create_engine(
        resolved.engine,
        browser=resolved.browser,
        headless=resolved.headless,
        base_url=resolved.base_url,
        viewport=resolved.viewport.as_tuple(),
        record_trace=resolved.trace,
        test_id_attribute=resolved.test_id_attribute,
        timeout=resolved.timeouts.default,
        poll_interval=resolved.timeouts.poll_interval,
    )

    with bound_context(test_id=request.node.name, engine=resolved.engine):
        instance.start()
        try:
            yield instance
        finally:
            # La captura va ANTES de parar: una vez cerrado el navegador ya no hay nada
            # que fotografiar, y la evidencia del fallo es justo lo que hace falta.
            if resolved.capture_on_failure and _test_failed(request):
                _capture_evidence(instance, request, artifacts_dir)
            instance.stop()


# ------------------------------------------------------------------------- captura ---


@pytest.hookimpl(wrapper=True, tryfirst=True)
def pytest_runtest_makereport(
    item: pytest.Item, call: pytest.CallInfo[None]
) -> Generator[None, pytest.TestReport, pytest.TestReport]:
    """Stash each phase's report so fixtures can tell whether the test passed.

    Fixtures have no other way to know: teardown runs the same whether the test passed or
    blew up, and capturing evidence for every green test would be pure noise.
    """
    report = yield
    item.stash.setdefault(_REPORTS, {})[report.when] = report
    return report


def _test_failed(request: pytest.FixtureRequest) -> bool:
    reports = request.node.stash.get(_REPORTS, {})
    return any(report.failed for report in reports.values())


def _slugify(node_id: str) -> str:
    """Turn a node id into something a filesystem accepts on every platform."""
    return _UNSAFE_IN_FILENAMES.sub("_", node_id).strip("_")[:120]


def _capture_evidence(engine: Engine, request: pytest.FixtureRequest, destination: Path) -> None:
    """Save whatever the engine can produce, never raising.

    An exception here would replace the real failure with a confusing one from teardown, so
    each capture is attempted independently and problems are logged instead.
    """
    folder = destination / _slugify(request.node.nodeid)

    try:
        engine.screenshot(folder / "captura.png")
    except Exception as error:
        log.warning("no se pudo capturar la pantalla", error=str(error))

    save_trace = getattr(engine, "save_trace", None)
    if save_trace is None:
        return
    try:
        if trace := save_trace(folder / "traza.zip"):
            log.info("traza guardada", ruta=str(trace))
    except Exception as error:
        log.warning("no se pudo guardar la traza", error=str(error))
