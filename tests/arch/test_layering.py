"""Architecture rules, enforced by tests instead of by discipline.

The framework's whole value proposition is that ``core`` stays technology-agnostic.
That guarantee is worth nothing unless something checks it on every run.
"""

import ast
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[2] / "src" / "automation_framework"
CORE = SRC / "core"

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
