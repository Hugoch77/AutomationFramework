"""A Markdown summary of a run, for the CI job summary.

Reads the JUnit XML that pytest already writes, so it needs neither Allure nor a live pytest
session. That is deliberate: the summary must be produced even when the run failed badly, and
the JUnit file is the one artefact that exists in every case.

Lives in the framework rather than as a shell snippet inside the workflow because logic that
formats failure reports deserves tests, and a `yq`/`grep` pipeline in YAML gets none.

Usage::

    python -m automation_framework.reporting.summary reports/junit-web.xml >> "$GITHUB_STEP_SUMMARY"
"""

from __future__ import annotations

import sys
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from xml.etree import ElementTree

MAX_FAILURES_SHOWN = 10
"""A job summary is a glance, not a log. Beyond this it stops being readable."""


@dataclass(frozen=True, slots=True)
class Failure:
    """One failing test, as JUnit describes it."""

    classname: str
    name: str
    message: str

    @property
    def label(self) -> str:
        """How the test is addressed, close enough to paste after `pytest`."""
        return f"{self.classname}::{self.name}" if self.classname else self.name


@dataclass(frozen=True, slots=True)
class Summary:
    """Counts and failures for one test run."""

    total: int = 0
    failed: int = 0
    errors: int = 0
    skipped: int = 0
    duration: float = 0.0
    failures: tuple[Failure, ...] = ()

    @property
    def passed(self) -> int:
        return self.total - self.failed - self.errors - self.skipped

    @property
    def ok(self) -> bool:
        return self.failed == 0 and self.errors == 0


def parse(path: Path) -> Summary:
    """Read a JUnit XML file into a :class:`Summary`.

    Raises:
        FileNotFoundError: There is no such file.
        ElementTree.ParseError: The file is not valid XML.
    """
    root = ElementTree.parse(path).getroot()
    # pytest envuelve los suites en <testsuites>; una sola suite puede venir sin envoltorio.
    suites = root.findall("testsuite") if root.tag == "testsuites" else [root]

    total = failed = errors = skipped = 0
    duration = 0.0
    failures: list[Failure] = []

    for suite in suites:
        total += int(suite.get("tests", 0))
        failed += int(suite.get("failures", 0))
        errors += int(suite.get("errors", 0))
        skipped += int(suite.get("skipped", 0))
        duration += float(suite.get("time", 0.0))
        failures.extend(_failures_in(suite))

    return Summary(total, failed, errors, skipped, duration, tuple(failures))


def _failures_in(suite: ElementTree.Element) -> list[Failure]:
    collected: list[Failure] = []
    for case in suite.iter("testcase"):
        for tag in ("failure", "error"):
            node = case.find(tag)
            if node is None:
                continue
            message = (node.get("message") or "").strip().splitlines()
            collected.append(
                Failure(
                    classname=case.get("classname", ""),
                    name=case.get("name", ""),
                    # Sólo la primera línea: el mensaje entero trae el assert desplegado, que
                    # en una tabla de resumen ocupa media pantalla y no aporta.
                    message=message[0] if message else "sin mensaje",
                )
            )
            break
    return collected


def render(summary: Summary, *, title: str = "Resultados") -> str:
    """Turn a summary into the Markdown that GitHub renders in the job summary."""
    icon = "✅" if summary.ok else "❌"
    lines = [
        f"## {icon} {title}",
        "",
        "| Total | Pasados | Fallidos | Errores | Omitidos | Duración |",
        "|---:|---:|---:|---:|---:|---:|",
        f"| {summary.total} | {summary.passed} | {summary.failed} | "
        f"{summary.errors} | {summary.skipped} | {summary.duration:.1f}s |",
    ]

    if summary.failures:
        shown = summary.failures[:MAX_FAILURES_SHOWN]
        lines += ["", "### Tests fallidos", ""]
        lines += [f"- `{failure.label}` — {failure.message}" for failure in shown]
        if len(summary.failures) > len(shown):
            lines.append(f"- …y {len(summary.failures) - len(shown)} más.")
        lines += [
            "",
            "> La evidencia de cada fallo (captura, árbol de elementos, registro y traza) "
            "está en el informe publicado como artifact de esta ejecución.",
        ]

    return "\n".join(lines)


def _force_utf8(stream: Any) -> None:
    """Make ``stream`` accept the summary's accents and icons.

    A Windows console defaults to cp1252, which cannot encode the status icons: printing the
    summary there dies with `UnicodeEncodeError`. GitHub's runners are UTF-8, so this only
    shows up on a developer machine — which is exactly where a tool that explodes instead of
    reporting is least welcome.
    """
    reconfigure = getattr(stream, "reconfigure", None)
    if reconfigure is None:  # pragma: no cover - un stream sin reconfigure ya es UTF-8 o falso
        return
    with suppress(Exception):
        reconfigure(encoding="utf-8", errors="replace")


def main(argv: list[str] | None = None) -> int:
    """Print the summary for the given JUnit file. Never fails the build.

    A summary that cannot be produced is a cosmetic problem; exiting non-zero would turn it
    into a red build and hide whatever the tests were actually saying. That promise is why the
    final `except` is deliberately broad: the alternative is a report generator that takes the
    build down with it.
    """
    _force_utf8(sys.stdout)

    args = sys.argv[1:] if argv is None else argv
    if not args:
        print("Uso: python -m automation_framework.reporting.summary <junit.xml> [título]")
        return 0

    path = Path(args[0])
    title = args[1] if len(args) > 1 else "Resultados"
    try:
        print(render(parse(path), title=title))
    except (OSError, ElementTree.ParseError) as error:
        print(f"> No se pudo generar el resumen desde `{path}`: {error}")
    except Exception as error:
        print(f"> No se pudo generar el resumen desde `{path}`: {error!r}")
    return 0


if __name__ == "__main__":  # pragma: no cover - punto de entrada
    raise SystemExit(main())
