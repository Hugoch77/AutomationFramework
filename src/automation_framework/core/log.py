"""Structured logging.

Named ``log`` rather than ``logging`` on purpose: a module that shadows a stdlib name is a
recurring source of confusing import bugs, and the two characters saved are not worth it.

Every line carries the context bound around it, so a log from a parallel run can still be
traced back to the test that produced it::

    with bound_context(test_id="test_busqueda"):
        get_logger(__name__).info("buscando", termino="notepad")
    # 2026-08-14T10:00:00Z [info] buscando  termino=notepad test_id=test_busqueda
"""

from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import TYPE_CHECKING, Any

import structlog

from automation_framework.core.exceptions import ConfigurationError

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator

    from structlog.typing import FilteringBoundLogger, Processor, WrappedLogger


def configure_logging(
    *,
    level: str = "INFO",
    json_output: bool = False,
    logger_factory: Callable[..., WrappedLogger] | None = None,
) -> None:
    """Set up structlog for the whole process.

    Args:
        level: Minimum level to emit.
        json_output: Emit JSON lines instead of the coloured human-readable format. Turn this
            on in CI, where logs are parsed rather than read.
        logger_factory: Where rendered lines end up. Defaults to stdout. Injectable so that
            the framework's own tests can assert on the real processor chain instead of a
            stubbed one — the same reasoning as the injectable clock in :mod:`.waits`.

    Raises:
        ConfigurationError: ``level`` is not a valid logging level.
    """
    try:
        level_number = logging.getLevelNamesMapping()[level.strip().upper()]
    except KeyError:
        raise ConfigurationError(f"Nivel de log desconocido: {level!r}.") from None

    shared: list[Processor] = [
        # Debe ir primero: es lo que inyecta el contexto del test en cada línea.
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]
    renderer: Processor = (
        structlog.processors.JSONRenderer()
        if json_output
        else structlog.dev.ConsoleRenderer(colors=True)
    )

    structlog.configure(
        processors=[*shared, renderer],
        wrapper_class=structlog.make_filtering_bound_logger(level_number),
        context_class=dict,
        logger_factory=logger_factory or structlog.PrintLoggerFactory(),
        # Sin caché: reconfigurar (en tests, o al cambiar de nivel a mitad de una sesión)
        # tiene que surtir efecto en los loggers ya obtenidos.
        cache_logger_on_first_use=False,
    )


def get_logger(name: str | None = None) -> FilteringBoundLogger:
    """Return a logger, optionally tagged with ``name``."""
    logger: FilteringBoundLogger = structlog.get_logger(name)
    return logger


def bind_context(**values: Any) -> None:
    """Attach ``values`` to every subsequent log line in this context.

    Backed by context variables, so it is safe under threads and under xdist workers.
    """
    structlog.contextvars.bind_contextvars(**values)


def unbind_context(*keys: str) -> None:
    """Remove ``keys`` from the bound context."""
    structlog.contextvars.unbind_contextvars(*keys)


def clear_context() -> None:
    """Drop everything bound in this context."""
    structlog.contextvars.clear_contextvars()


@contextmanager
def bound_context(**values: Any) -> Iterator[None]:
    """Bind ``values`` for the duration of the block, then restore what was there before.

    Restoring matters because fixtures nest: a teardown log must not inherit the context of
    the test that just finished.

    Deliberately not called ``test_context``: pytest collects anything named ``test*`` as a
    test case, and an imported helper would be reported as a broken one.
    """
    tokens = structlog.contextvars.bind_contextvars(**values)
    try:
        yield
    finally:
        structlog.contextvars.reset_contextvars(**tokens)


def current_context() -> dict[str, Any]:
    """Everything currently bound. Mostly useful for assertions."""
    return dict(structlog.contextvars.get_contextvars())
