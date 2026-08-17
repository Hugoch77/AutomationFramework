"""Collecting the evidence a failed test leaves behind.

Deliberately ignorant of any report format. This module knows how to ask an engine for what it
can produce and how to write it to disk; publishing it into Allure — or tomorrow into something
else — is an adapter's job. Same reasoning as the engine registry: the framework should not be
married to one vendor.

Every capture is attempted independently and never raises. Evidence is collected from a
teardown, where an exception would replace the real failure with a confusing one about
screenshots, and the reader would lose the actual cause.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from automation_framework.core.capabilities import Feature
from automation_framework.core.log import get_logger

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

    from automation_framework.core.engine import Engine

log = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class Evidence:
    """One artefact collected from a failing test.

    Args:
        name: Human-readable label, used as the attachment name in the report.
        path: Where the artefact was written.
        mime_type: How a report should render it. An image wants to be shown inline, a trace
            wants to be a download link, and getting this wrong turns a screenshot into an
            unreadable wall of bytes.
    """

    name: str
    path: Path
    mime_type: str


SCREENSHOT_NAME = "captura.png"
TREE_NAME = "arbol.html"
TRACE_NAME = "traza.zip"
LOG_NAME = "registro.log"


def collect_evidence(
    engine: Engine,
    destination: Path,
    *,
    logs: str | None = None,
) -> list[Evidence]:
    """Gather everything ``engine`` can produce into ``destination``.

    Args:
        engine: The engine driving the application, still alive. Order matters at the call
            site: once the browser is closed there is nothing left to photograph.
        destination: Folder for this test's artefacts. Created if missing.
        logs: The test's own log output, if it was captured.

    Returns:
        One :class:`Evidence` per artefact that could actually be produced, in the order a
        reader wants them: the picture first, then the tree, then the replayable trace.
    """
    try:
        destination.mkdir(parents=True, exist_ok=True)
    except OSError as error:
        # Sin carpeta no hay nada que recoger, pero esta función corre desde un teardown y
        # prometió no lanzar: un disco lleno o un permiso denegado no puede sustituir el
        # fallo real del test por otro sobre directorios.
        log.warning(
            "no se pudo crear la carpeta de evidencia", ruta=str(destination), error=str(error)
        )
        return []

    collected: list[Evidence] = []

    if _screenshot(engine, destination / SCREENSHOT_NAME):
        collected.append(
            Evidence("Captura de pantalla", destination / SCREENSHOT_NAME, "image/png")
        )

    if _tree(engine, destination / TREE_NAME):
        collected.append(Evidence("Árbol de elementos", destination / TREE_NAME, "text/html"))

    if logs and _write(destination / LOG_NAME, logs):
        collected.append(Evidence("Registro del test", destination / LOG_NAME, "text/plain"))

    if _trace(engine, destination / TRACE_NAME):
        collected.append(Evidence("Traza", destination / TRACE_NAME, "application/zip"))

    return collected


def _screenshot(engine: Engine, path: Path) -> bool:
    if not engine.has_feature(Feature.SCREENSHOT):
        return False
    try:
        engine.screenshot(path)
    except Exception as error:
        log.warning("no se pudo capturar la pantalla", error=str(error))
        return False
    return True


def _tree(engine: Engine, path: Path) -> bool:
    if not engine.has_feature(Feature.ELEMENT_TREE_DUMP):
        return False
    try:
        return _write(path, engine.dump_tree())
    except Exception as error:
        log.warning("no se pudo volcar el árbol de elementos", error=str(error))
        return False


def _trace(engine: Engine, path: Path) -> bool:
    """Ask for a trace, which only the engines that record one can provide.

    Looked up by attribute rather than declared in the contract: saving a trace is not an
    operation every technology has, and `save_trace` returning `None` when tracing was off is
    already part of the web engine's contract.
    """
    save_trace = getattr(engine, "save_trace", None)
    if save_trace is None:
        return False
    try:
        return save_trace(path) is not None
    except Exception as error:
        log.warning("no se pudo guardar la traza", error=str(error))
        return False


def _write(path: Path, content: str) -> bool:
    try:
        path.write_text(content, encoding="utf-8")
    except OSError as error:
        log.warning("no se pudo escribir la evidencia", ruta=str(path), error=str(error))
        return False
    return True


def describe(collected: Sequence[Evidence]) -> str:
    """One line naming what was collected, for the log that a CI reader scans first."""
    if not collected:
        return "sin evidencia"
    return ", ".join(item.path.name for item in collected)
