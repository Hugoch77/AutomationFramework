# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Idioma

El usuario trabaja en **español**: responde, documenta y escribe mensajes de commit en español.
El **código, los identificadores, los nombres de archivo y los docstrings van en inglés**.

## Reglas de operación — leer antes que nada

### 1. El usuario escribe la historia del repo. Tú no.

La frontera es **quién escribe commits**, no "git en general".

**Prohibido** — escribe historia o publica: `git commit`, `git push`, `git merge`, `git rebase`,
`git tag`, `gh pr create`, `gh pr merge`. Aunque el trabajo esté terminado, aunque el gate esté
verde, aunque sea el paso obvio. El usuario revisa en VS Code y commitea él mismo.

**Permitido** — no toca la historia: `git switch`, `git switch -c`, `git branch`, y toda
la lectura (`status`, `log`, `diff`, `show`). Crea la rama de la fase tú mismo, sin preguntar.

- Deja siempre los cambios **en el working tree** y resume qué archivos tocaste y por qué.
- Si te sirve, **ofrece el mensaje de commit como texto** para que él lo copie. No lo ejecutes.
- Al cambiar de rama, **dilo**: los cambios sin commitear se llevan consigo y eso sorprende
  si no se ve venir.
- Única excepción a lo prohibido: que el usuario lo pida explícitamente **en ese momento**.
  Una autorización puntual no se extiende a los commits siguientes.

### 2. No arranques la sesión leyendo el proyecto.

**No hagas ritual de orientación al empezar una sesión.** No leas `PROGRESS.md`, ni recorras el
repositorio, ni resumas el estado por iniciativa propia. Responde a lo que el usuario pida.

La revisión de estado se hace **sólo** cuando el usuario escribe **`/continuar`**, que invoca la
skill del mismo nombre. Si la tarea concreta que te piden necesita un dato de `PROGRESS.md`,
consúltalo puntualmente — eso no es el ritual, es hacer el trabajo.

---

## Documentación del proyecto

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

| Paso | Quién |
|---|---|
| Crear la rama `fase-N-<slug>` | Claude, al arrancar la fase |
| Implementar en incrementos pequeños, cada uno con sus tests | Claude |
| Gate de calidad → `/af-check` | Claude |
| Revisar los cambios en VS Code | Usuario |
| `git commit`, `git push`, PR y merge | **Usuario, siempre** |
| Actualizar `PROGRESS.md` → `/bitacora` | Claude |

- **No avances de fase sin cumplir su DoD** (definido en `docs/PLAN.md`).
- Mensajes de commit sugeridos en formato Conventional Commits: `feat(core): añade contrato Engine`.
- El usuario también edita manualmente desde VS Code: comprueba `git status` antes de editar,
  puede haber cambios que no vengan de esta sesión y que no debes pisar.

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

| Skill | Para qué | Quién la dispara |
|---|---|---|
| `/continuar` | Retomar el proyecto: lee `PROGRESS.md`, contrasta contra el repo real y propone objetivo | **Sólo el usuario**, nunca automático |
| `/bitacora` | Cerrar sesión: actualiza `PROGRESS.md` con lo hecho, decisiones y próximo paso | Usuario o Claude al terminar |
| `/af-phase` | Ejecutar una fase del plan de principio a fin, verificando su DoD | Usuario |
| `/af-check` | Gate de calidad local antes de entregar cambios | Claude, libremente |
| `/af-new-suite` | Scaffolding de una suite de pruebas nueva (web o desktop) | Usuario |
| `/af-new-engine` | Añadir un engine nuevo respetando los contratos del core | Usuario |
