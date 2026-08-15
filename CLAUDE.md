# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Idioma

El usuario trabaja en **español**: responde, documenta y escribe mensajes de commit en español.
El **código, los identificadores, los nombres de archivo y los docstrings van en inglés**.

## Lo primero de cada sesión

Lee [`PROGRESS.md`](PROGRESS.md) **antes de tocar nada**. Contiene la fase activa, las decisiones
ya cerradas, los pendientes y la bitácora de sesiones. Al terminar la sesión, actualízalo.
La skill `/af-session` automatiza ambos extremos.

Jerarquía de documentos:
- `PROGRESS.md` — estado vivo (cambia cada sesión)
- `docs/PLAN.md` — roadmap por fases y DoD (estable)
- `docs/ARCHITECTURE.md` — por qué el código está organizado así (estable)

## Comandos

```bash
# Entorno
uv sync --all-extras                    # instalar todo (core + web + desktop)
uv sync --extra web                     # sólo web (lo que usa el CI en Linux)
uv run playwright install chromium      # navegadores (tras instalar el extra web)

# Calidad — el gate completo está en la skill /af-check
uv run ruff check . --fix
uv run ruff format .
uv run mypy src

# Tests
uv run pytest                           # todo lo que no esté marcado como desktop
uv run pytest tests/unit                # sólo tests del framework (rápidos, sin UI)
uv run pytest -m web                    # suite web e2e
uv run pytest -m desktop                # suite desktop (requiere sesión Windows interactiva)
uv run pytest tests/unit/test_x.py::test_y   # un único test
uv run pytest -k "search and not slow"  # por expresión
uv run pytest --cov=automation_framework --cov-report=term-missing
uv run pytest -n auto                   # en paralelo (xdist)

# Ejecución web en modo visible para depurar
uv run pytest -m web --headed --browser chromium
```

Los markers `desktop` están **deselccionados por defecto** en `pyproject.toml` (`addopts`), porque
requieren Windows con sesión interactiva. Hay que pedirlos explícitamente con `-m desktop`.

## Arquitectura — lo que hay que entender antes de escribir código

El framework existe para automatizar **tipos de aplicación distintos** (web hoy, escritorio después,
API más adelante) con el mismo núcleo. Toda la estructura se deriva de una sola regla:

> **`core/` define contratos abstractos y NO importa nada de `engines/`.**

Flujo de dependencias, siempre hacia abajo:

```
tests/e2e/**  →  pages/**  →  core/**  ←  engines/web · engines/desktop
```

- **`core/`** — `Locator`, `Element`, `Engine`, `EngineRegistry`, `Settings`, esperas, excepciones.
  Cero dependencias de Playwright o pywinauto. Se testea con un `FakeEngine` en memoria.
- **`engines/`** — implementaciones concretas del contrato. `web/` traduce `Locator` a selectores
  de Playwright; `desktop/` lo traduce a criterios UIA (`auto_id`, `name`, `control_type`).
- **`pages/`** — Page Objects / Screen Objects. Hablan con el `Engine` abstracto, nunca con la
  librería de automatización directamente.
- **`tests/e2e/`** — escenarios de negocio. Sólo conocen Page Objects y assertions.

Consecuencias prácticas:
- Un test **no debe** importar `playwright` ni `pywinauto`. Si lo necesita, falta una primitiva en `Element`.
- `Element` se mantiene deliberadamente **pobre** (`click`, `fill`, `text`, `is_visible`, `wait_for`,
  `attribute`). Una interfaz pequeña es lo que hace barato añadir un engine nuevo.
- Cada engine declara sus `capabilities` (qué estrategias de `Locator` soporta). Usar `Strategy.CSS`
  en desktop debe fallar de forma explícita y temprana.
- `playwright` y `pywinauto` son **extras opcionales** de `pyproject.toml`, no dependencias base.

## Flujo de trabajo

Se trabaja por fases (ver `docs/PLAN.md`). Una fase = una rama = un PR.

```bash
git switch -c fase-N-<slug>
# ... incrementos pequeños, cada uno con sus tests ...
# gate de calidad → /af-check
gh pr create        # esperar CI verde
# merge squash a main, luego actualizar PROGRESS.md
```

- **No avances de fase sin cumplir su DoD** (definido en `docs/PLAN.md`).
- Commits en formato Conventional Commits: `feat(core): añade contrato Engine`.
- El usuario también edita manualmente desde VS Code: comprueba `git status` antes de editar,
  puede haber cambios que no vengan de esta sesión.

## Convenciones de testing

- `tests/unit/` prueba **el framework** (rápido, sin UI, con `FakeEngine`).
  `tests/e2e/` prueba **el SUT**. `tests/arch/` prueba las reglas de arquitectura.
- **Nunca `time.sleep()` fijo.** Siempre esperas explícitas basadas en condición. En desktop la
  tentación es fuerte porque UIA no auto-espera: se resuelve con `wait_until`, no con sleeps.
- Locators de escritorio: preferir `auto_id` sobre texto visible — el texto de Microsoft Store
  cambia con el idioma y con las actualizaciones.
- Un test que falla debe dejar evidencia automática (screenshot, trace, árbol UIA). Si no la deja,
  eso es un bug del framework, no del test.

## CI/CD

- `ci.yml` — runner hospedado (ubuntu): lint + mypy + `tests/unit` + suite web headless.
- `desktop.yml` — **self-hosted runner** en el PC del usuario (label `windows-desktop`), porque
  los runners hospedados no tienen sesión interactiva ni Microsoft Store instalada. Requiere que
  la sesión de Windows esté iniciada y **desbloqueada**.

## Skills disponibles

| Skill | Para qué |
|---|---|
| `/af-session` | Abrir o cerrar sesión: lee/actualiza `PROGRESS.md` |
| `/af-phase` | Ejecutar una fase del plan de principio a fin, verificando su DoD |
| `/af-check` | Gate de calidad local antes de commit/PR |
| `/af-new-suite` | Scaffolding de una suite de pruebas nueva (web o desktop) |
| `/af-new-engine` | Añadir un engine nuevo respetando los contratos del core |
