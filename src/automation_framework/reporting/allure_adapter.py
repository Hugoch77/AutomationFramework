"""Publishing evidence into an Allure report.

The only module in the framework that knows Allure exists. `evidence.py` collects artefacts
and writes them to disk; this turns them into attachments. Swapping reporter means rewriting
this file and nothing else.

`allure-pytest` is an optional dependency: the import is guarded so that a suite running
without it still collects evidence to disk. A missing reporter must degrade the report, never
break the run — teardown is the worst possible place to raise an ImportError.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from automation_framework.core.log import get_logger

if TYPE_CHECKING:
    from collections.abc import Sequence

    from automation_framework.reporting.evidence import Evidence

log = get_logger(__name__)

# Se guarda como `Any` a propósito: el módulo puede no estar instalado, y un alias tipado
# obligaría a que el resto del framework conociera los tipos de un reporter concreto.
_allure: Any = None
ALLURE_AVAILABLE = False

try:  # pragma: no cover - depende de si allure-pytest está instalado
    import allure as _allure_module
except ImportError:  # pragma: no cover - camino sin allure instalado
    pass
else:  # pragma: no cover
    _allure = _allure_module
    ALLURE_AVAILABLE = True


def is_available() -> bool:
    """Whether Allure can receive attachments in this run."""
    return ALLURE_AVAILABLE


def attach_evidence(collected: Sequence[Evidence]) -> int:
    """Attach every artefact in ``collected`` to the current Allure test.

    Returns how many were attached — zero when Allure is not installed, which is a normal
    state and not a failure.

    Never raises. It runs from teardown, where an exception about the *report* would replace
    the failure the report exists to explain.
    """
    if not ALLURE_AVAILABLE:
        return 0

    attached = 0
    for item in collected:
        try:
            _allure.attach.file(
                str(item.path),
                name=item.name,
                attachment_type=item.mime_type,
                extension=item.path.suffix.lstrip("."),
            )
        except Exception as error:
            log.warning(
                "no se pudo adjuntar la evidencia al informe",
                evidencia=item.name,
                error=str(error),
            )
        else:
            attached += 1
    return attached


def attach_text(name: str, content: str, *, mime_type: str = "text/plain") -> bool:
    """Attach a string directly, for what never becomes a file on disk."""
    if not ALLURE_AVAILABLE or not content:
        return False
    try:
        _allure.attach(content, name=name, attachment_type=mime_type)
    except Exception as error:
        log.warning("no se pudo adjuntar el texto al informe", nombre=name, error=str(error))
        return False
    return True


def describe_environment(values: dict[str, Any], destination: Any) -> bool:
    """Write Allure's ``environment.properties`` next to the results.

    It is what makes a downloaded report answer "which browser, headless or not, against which
    URL" without digging through the CI logs — the first three questions anyone asks about a
    failure they did not witness.
    """
    if not values:
        return False
    try:
        destination.mkdir(parents=True, exist_ok=True)
        lines = "\n".join(f"{key}={value}" for key, value in sorted(values.items()))
        (destination / "environment.properties").write_text(lines, encoding="utf-8")
    except OSError as error:
        log.warning("no se pudo escribir el entorno del informe", error=str(error))
        return False
    return True
