"""Keeping a copy of what was logged during a test.

The framework already tags every line with the test that produced it (``bound_context`` in
:mod:`automation_framework.core.log`). What was missing is a *copy*: structlog prints to
stdout, so the lines end up in the CI console — interleaved with everything else and gone the
moment the job is cleaned up — and cannot be attached to the failing test in a report.

pytest's own ``caplog`` is no help here: it hooks the stdlib ``logging`` module, and this
framework renders through ``PrintLoggerFactory``. So the copy is taken where the lines are
written, by wrapping the logger structlog uses.
"""

from __future__ import annotations

import re
import sys
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from io import TextIOBase

_ANSI = re.compile(r"\x1b\[[0-9;]*m")
"""Secuencias de color de la consola.

El renderer las emite para que la salida se lea bien en un terminal, pero en un fichero
adjunto al informe son ruido que se cuela entre cada palabra. Se quitan sólo de la copia: lo
que se imprime conserva su color."""


class LogCapture:
    """Accumulates rendered log lines, one test at a time.

    Not thread-safe by design: pytest runs one test at a time per process, and xdist gives
    each worker its own. Adding a lock would buy nothing and suggest a concurrency that does
    not exist.
    """

    def __init__(self) -> None:
        self._lines: list[str] = []
        self._active = False

    @property
    def active(self) -> bool:
        """Whether lines are being kept right now."""
        return self._active

    def start(self) -> None:
        """Begin a fresh capture, dropping anything held from a previous test."""
        self._lines.clear()
        self._active = True

    def stop(self) -> None:
        """Stop keeping lines. What was already captured stays readable."""
        self._active = False

    def add(self, line: str) -> None:
        """Record one rendered line, stripped of colour, if a capture is running."""
        if self._active:
            self._lines.append(_ANSI.sub("", line))

    def text(self) -> str:
        """Everything captured so far, ready to be written to a file."""
        return "\n".join(self._lines)

    def __len__(self) -> int:
        return len(self._lines)


class TeeLogger:
    """A structlog logger that prints *and* keeps a copy.

    structlog calls whichever method matches the level, so they are all the same function —
    the level is already rendered into the line by the processor chain.
    """

    def __init__(self, capture: LogCapture, stream: TextIOBase | Any = None) -> None:
        self._capture = capture
        self._stream = stream if stream is not None else sys.stdout

    def msg(self, message: str) -> None:
        """Render one line to the stream and keep a copy for the report."""
        print(message, file=self._stream)
        self._capture.add(message)

    # structlog escoge el método por nivel; todos hacen lo mismo porque el nivel ya viene
    # renderizado dentro de la línea.
    log = debug = info = warn = warning = msg
    error = critical = exception = fatal = msg


def capturing_logger_factory(capture: LogCapture) -> Any:
    """Build the ``logger_factory`` that :func:`configure_logging` expects.

    Returns a callable because structlog builds one logger per call site and passes it the
    logger's name, which is of no interest here.
    """

    def factory(*args: Any, **kwargs: Any) -> TeeLogger:
        return TeeLogger(capture)

    return factory
