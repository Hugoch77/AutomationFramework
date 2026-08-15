# AutomationFramework

Framework de automatización **genérico y multi-engine** en Python. Un solo núcleo para automatizar
distintos tipos de aplicación: web hoy (Playwright), escritorio Windows después (pywinauto/UIA),
y lo que venga más adelante.

> **Estado:** Fase 0 (bootstrap) completada. Ver [`PROGRESS.md`](PROGRESS.md).

## La idea

Automatizar una web y automatizar una app de escritorio usan APIs incompatibles. Si los tests
hablan directamente con esas APIs, acabas manteniendo dos frameworks. Aquí los tests hablan con
un contrato abstracto (`Engine`, `Element`, `Locator`) y cada tecnología lo implementa por debajo.

```
tests/e2e  →  pages  →  core  ←  engines/web · engines/desktop
```

Añadir soporte para una tecnología nueva cuesta **un módulo**, no una migración.

## Requisitos

- Python 3.13+
- [uv](https://docs.astral.sh/uv/)
- Windows (sólo para la suite de escritorio)

## Puesta en marcha

```bash
uv sync --all-extras
uv run playwright install chromium
uv run pytest
```

## Ejecutar pruebas

```bash
uv run pytest                  # todo excepto escritorio
uv run pytest tests/unit       # pruebas del framework (rápidas, sin UI)
uv run pytest -m web           # suite web end-to-end
uv run pytest -m desktop       # suite de escritorio (requiere sesión Windows desbloqueada)
```

La suite de escritorio queda excluida por defecto porque necesita una sesión de Windows
interactiva; hay que pedirla explícitamente.

## Documentación

| Documento | Contenido |
|---|---|
| [`PROGRESS.md`](PROGRESS.md) | Estado actual, pendientes, bitácora de sesiones |
| [`docs/PLAN.md`](docs/PLAN.md) | Roadmap por fases con Definition of Done |
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | Por qué el código está organizado así |
| [`CLAUDE.md`](CLAUDE.md) | Guía para Claude Code |

## Licencia

MIT
