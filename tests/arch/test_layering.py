"""Architecture rules, enforced by tests instead of by discipline.

The framework's whole value proposition is that ``core`` stays technology-agnostic.
That guarantee is worth nothing unless something checks it on every run.
"""

import ast
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[2] / "src" / "automation_framework"
CORE = SRC / "core"
PAGES = SRC / "pages"
REPORTING = SRC / "reporting"

# El adaptador es el único sitio donde puede aparecer un reporter concreto.
ALLURE_ADAPTER = "allure_adapter.py"

# Anything that would tie the abstract contracts to one automation technology.
FORBIDDEN_IN_CORE = ("playwright", "pywinauto", "selenium", "appium")


def _imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            modules.add(node.module)
    return modules


@pytest.mark.arch
@pytest.mark.skipif(not CORE.exists(), reason="core/ aún no existe (se crea en la Fase 1)")
def test_core_does_not_depend_on_any_automation_library():
    offenders: list[str] = []
    for module_file in CORE.rglob("*.py"):
        for imported in _imported_modules(module_file):
            root = imported.split(".")[0]
            if root in FORBIDDEN_IN_CORE:
                offenders.append(f"{module_file.relative_to(SRC)} importa {imported!r}")

    assert not offenders, (
        "core/ debe permanecer agnóstico a la tecnología de automatización.\n"
        + "\n".join(offenders)
    )


@pytest.mark.arch
@pytest.mark.skipif(not PAGES.exists(), reason="pages/ aún no existe (se crea en la Fase 3)")
def test_pages_do_not_depend_on_any_automation_library():
    """Page objects are the reason the framework can serve two technologies.

    The moment one of them imports Playwright, the layer stops being reusable by the desktop
    suites of Fase 5 — and that only shows up much later, as a rewrite.
    """
    offenders: list[str] = []
    for module_file in PAGES.rglob("*.py"):
        for imported in _imported_modules(module_file):
            root = imported.split(".")[0]
            if root in FORBIDDEN_IN_CORE:
                offenders.append(f"{module_file.relative_to(SRC)} importa {imported!r}")

    assert not offenders, (
        "pages/ debe hablar con el contrato Engine, nunca con una librería concreta.\n"
        + "\n".join(offenders)
    )


@pytest.mark.arch
@pytest.mark.skipif(not PAGES.exists(), reason="pages/ aún no existe (se crea en la Fase 3)")
def test_pages_do_not_import_engines():
    offenders: list[str] = []
    for module_file in PAGES.rglob("*.py"):
        for imported in _imported_modules(module_file):
            if "automation_framework.engines" in imported:
                offenders.append(f"{module_file.relative_to(SRC)} importa {imported!r}")

    assert not offenders, (
        "pages/ se construye sobre core/; el engine concreto llega inyectado.\n"
        + "\n".join(offenders)
    )


@pytest.mark.arch
@pytest.mark.skipif(
    not REPORTING.exists(), reason="reporting/ aún no existe (se crea en la Fase 4)"
)
def test_only_the_adapter_knows_which_reporter_is_used():
    """Cambiar de reporter debe costar un fichero, no una búsqueda por todo el paquete.

    En cuanto la recolección de evidencia importa `allure`, el formato del informe deja de ser
    un detalle intercambiable y pasa a estar cosido al framework.
    """
    offenders: list[str] = []
    for module_file in REPORTING.rglob("*.py"):
        if module_file.name == ALLURE_ADAPTER:
            continue
        for imported in _imported_modules(module_file):
            if imported.split(".")[0] in ("allure", "allure_commons"):
                offenders.append(f"{module_file.relative_to(SRC)} importa {imported!r}")

    assert not offenders, (
        f"Sólo {ALLURE_ADAPTER} puede conocer el reporter concreto.\n" + "\n".join(offenders)
    )


@pytest.mark.arch
@pytest.mark.skipif(
    not REPORTING.exists(), reason="reporting/ aún no existe (se crea en la Fase 4)"
)
def test_reporting_does_not_depend_on_any_automation_library():
    """La evidencia se pide al contrato `Engine`, no a Playwright.

    Es lo que hará que la Fase 5 recoja árboles UIA sin tocar este paquete.
    """
    offenders: list[str] = []
    for module_file in REPORTING.rglob("*.py"):
        for imported in _imported_modules(module_file):
            if imported.split(".")[0] in FORBIDDEN_IN_CORE:
                offenders.append(f"{module_file.relative_to(SRC)} importa {imported!r}")

    assert not offenders, (
        "reporting/ debe hablar con el contrato Engine, nunca con una librería concreta.\n"
        + "\n".join(offenders)
    )


@pytest.mark.arch
@pytest.mark.skipif(not CORE.exists(), reason="core/ aún no existe (se crea en la Fase 1)")
def test_core_does_not_import_engines():
    offenders: list[str] = []
    for module_file in CORE.rglob("*.py"):
        for imported in _imported_modules(module_file):
            if "automation_framework.engines" in imported:
                offenders.append(f"{module_file.relative_to(SRC)} importa {imported!r}")

    assert not offenders, (
        "core/ define contratos; las implementaciones se registran en runtime vía el registry.\n"
        + "\n".join(offenders)
    )
