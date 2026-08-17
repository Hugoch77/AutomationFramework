"""Cleaning up the generated Allure report.

Allure's generated report embeds Google Analytics and calls it from the browser of whoever
opens it. This is an internal artefact of a private repository: it should not phone home, and
the person reading a failure at least deserves not to be measured while doing it.

The Allure CLI offers no supported switch for this — `ALLURE_NO_ANALYTICS` and
`-Dallure.analytics.enable=false` were both tried against 2.32 and neither had any effect — so
the tag is removed after the fact. Doing it here, rather than with a `sed` buried in the
workflow, is what makes it testable and what makes a future Allure version that changes the
markup fail *loudly* instead of silently leaving the tracker in.

Usage::

    python -m automation_framework.reporting.postprocess informe/index.html
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

TRACKERS = ("googletagmanager.com", "google-analytics.com")
"""Hosts the report must not contact."""

_SCRIPT_WITH_SRC = re.compile(
    r"<script[^>]*\bsrc=[\"'][^\"']*(?:googletagmanager|google-analytics)[^\"']*[\"'][^>]*>\s*</script>",
    re.IGNORECASE,
)
_DATALAYER_BLOCK = re.compile(
    r"<script>\s*window\.dataLayer\s*=.*?</script>",
    re.IGNORECASE | re.DOTALL,
)


def strip_analytics(html: str) -> str:
    """Remove the analytics tags from a generated report."""
    without_src = _SCRIPT_WITH_SRC.sub("", html)
    return _DATALAYER_BLOCK.sub("", without_src)


def has_trackers(html: str) -> bool:
    """Whether the report would still contact a tracker."""
    return any(tracker in html for tracker in TRACKERS)


def clean_file(path: Path) -> bool:
    """Strip analytics from the report at ``path``. ``True`` if it is clean afterwards."""
    html = path.read_text(encoding="utf-8", errors="surrogateescape")
    cleaned = strip_analytics(html)
    if cleaned != html:
        path.write_text(cleaned, encoding="utf-8", errors="surrogateescape")
    return not has_trackers(cleaned)


def main(argv: list[str] | None = None) -> int:
    """Clean the report named on the command line.

    Returns 0 even when the report could not be cleaned: an artefact that still carries a
    tracker is worth a loud warning, not a failed build that hides the test results it holds.
    """
    args = sys.argv[1:] if argv is None else argv
    if not args:
        print("Uso: python -m automation_framework.reporting.postprocess <informe.html>")
        return 0

    path = Path(args[0])
    try:
        limpio = clean_file(path)
    except OSError as error:
        print(f"AVISO: no se pudo limpiar {path}: {error}")
        return 0

    if limpio:
        print(f"Telemetría eliminada de {path}.")
    else:
        # Que se vea: si Allure cambia el marcado, esto avisa en vez de dejar el rastreador
        # dentro sin que nadie se entere.
        print(f"AVISO: {path} todavía contiene un rastreador. Revisa si Allure cambió el HTML.")
    return 0


if __name__ == "__main__":  # pragma: no cover - punto de entrada
    raise SystemExit(main())
