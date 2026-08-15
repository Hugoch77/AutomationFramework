# AutomationFramework

Framework de automatización **genérico y multi-engine** en Python. Un solo núcleo para automatizar
distintos tipos de aplicación: web hoy (Playwright), escritorio Windows después (pywinauto/UIA),
y lo que venga más adelante.

> **Estado:** núcleo (`core/`) completo y probado. Los engines concretos están en camino.

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

## Estructura

```
src/automation_framework/
├── core/          Contratos, config, esperas, logging, excepciones, registro
├── engines/       Implementaciones concretas (web, escritorio, ...)
├── pages/         Page Objects y Screen Objects
└── testing/       FakeEngine: implementación de referencia de los contratos

tests/
├── unit/          Prueban el FRAMEWORK (rápidos, sin UI)
├── arch/          Prueban las reglas de arquitectura
└── e2e/           Prueban una aplicación real
```

**Regla invariante:** `core/` define los contratos y **no importa nada** de `engines/` ni
ninguna librería de automatización. Es lo que permite que añadir una tecnología cueste un
módulo y no una migración. No depende de la disciplina: `tests/arch/test_layering.py` lo
verifica en cada ejecución.

Consecuencias prácticas al escribir código:

- Un test nunca importa `playwright` ni `pywinauto`. Si lo necesita, falta una primitiva
  en `Element`.
- `Element` se mantiene deliberadamente pobre (`click`, `fill`, `text`, `is_visible`,
  `wait_for`, `attribute`). Una interfaz pequeña es lo que abarata añadir un engine.
- Los métodos públicos de `Engine` y `Element` ya traen las guardas y la auto-espera; un
  engine sólo implementa las primitivas protegidas (`_click`, `_exists`, `_find`…).
- Cada engine declara sus `capabilities`, así que usar una estrategia no soportada falla
  de inmediato y con un mensaje claro.
- `playwright` y `pywinauto` son extras opcionales, nunca dependencias base.

## Licencia

MIT
