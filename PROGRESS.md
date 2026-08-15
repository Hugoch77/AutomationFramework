# PROGRESS — Estado vivo del proyecto

> **Este es el primer archivo que se lee al empezar una sesión y el último que se actualiza al cerrarla.**
> Roadmap estable: [`docs/PLAN.md`](docs/PLAN.md) · Arquitectura: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)

---

## Estado actual

| Campo | Valor |
|---|---|
| **Fase activa** | Fase 1 — Núcleo del framework (`core/`) |
| **Estado de la fase** | ✅ Completada (DoD verificado) |
| **Siguiente fase** | Fase 2 — Engine Web (Playwright) |
| **Rama actual** | `main` (pendiente crear `fase-1-core`) |
| **Repositorio** | https://github.com/Hugoch77/AutomationFramework (privado) |
| **CI** | ✅ Verde (`ci.yml`: lint + mypy + unit/arch) |
| **Última actualización** | 2026-08-14 |
| **Última sesión** | Sesión 1 |

---

## Progreso por fase

| Fase | Nombre | Estado | PR |
|---|---|---|---|
| 0 | Bootstrap del proyecto | ✅ Completada | — (commit directo) |
| 1 | Núcleo del framework (`core/`) | ✅ Completada | pendiente |
| 2 | Engine Web (Playwright) | ⬜ Pendiente | — |
| 3 | Page Object Model y utilidades | ⬜ Pendiente | — |
| 4 | Reporting y observabilidad | ⬜ Pendiente | — |
| 5 | Engine Desktop (pywinauto) | ⬜ Pendiente | — |
| 6 | CI/CD completo | ⬜ Pendiente | — |
| 7 | Endurecimiento y extensibilidad | ⬜ Pendiente | — |

Leyenda: ⬜ Pendiente · 🟡 En curso · ✅ Completada · ⛔ Bloqueada

---

## Decisiones tomadas

Decisiones cerradas que **no** deben re-litigarse sin una razón nueva.

| Fecha | Decisión | Motivo |
|---|---|---|
| 2026-08-14 | Engine desktop = **pywinauto (backend UIA)** | Python puro, sin servidores externos; soporta UWP/WinUI |
| 2026-08-14 | Estilo de tests = **pytest + Page Object Model** (sin BDD por ahora) | Menos capas; BDD se puede añadir después sin reescribir |
| 2026-08-14 | CI desktop vía **self-hosted runner** en el PC del usuario | Los runners hospedados no tienen sesión interactiva ni Microsoft Store |
| 2026-08-14 | Repositorio **privado** `Hugoch77/AutomationFramework` | Proyecto personal |
| 2026-08-14 | Gestor de paquetes = **uv** | Ya instalado, lockfile reproducible, mucho más rápido que pip |
| 2026-08-14 | Layout **`src/`** | Evita imports accidentales desde el working dir |
| 2026-08-14 | Docs y commits en **español**; código e identificadores en **inglés** | Preferencia del usuario + convención estándar de código |
| 2026-08-14 | `.gitattributes` con `* text=auto eol=lf` | Sin esto, Git convierte a CRLF en Windows y el hook `mixed-line-ending` lo revierte a LF en cada commit → ruido infinito en los diffs |
| 2026-08-14 | `ruff format` excluye `*.md` | Ruff 0.16 formatea bloques de código dentro de Markdown y rompe la alineación deliberada de los ejemplos de la documentación |
| 2026-08-14 | Identidad de git configurada **a nivel de repo**, no global | La global estaba como `Copilot`; se corrigió sólo aquí para no alterar otros proyectos del usuario |
| 2026-08-14 | **Claude no escribe la historia del repo**: nada de `commit`, `push`, `merge`, `rebase`, `tag` ni PRs. Sí puede crear ramas y moverse entre ellas | El usuario revisa cada cambio en VS Code y controla el historial. Crear ramas no toca la historia, así que no necesita su intervención |
| 2026-08-14 | **Claude no lee el proyecto al arrancar una sesión.** Sólo con `/continuar` | Evita gastar contexto y tiempo en un ritual de orientación que el usuario no siempre necesita |
| 2026-08-14 | Skill `af-session` dividida en `/continuar` (apertura) y `/bitacora` (cierre) | Ahora tienen disparadores distintos: la apertura la pide el usuario explícitamente, el cierre no |
| 2026-08-14 | Nombre `/continuar` en vez de `/continue` | `claude --continue` existe como flag de la CLI; el nombre en español elimina el riesgo de colisión |
| 2026-08-14 | **Núcleo síncrono**, no async | Playwright tiene API síncrona oficial y pywinauto es síncrono puro; async obligaría a envolver cada llamada de escritorio en un executor de hilos, justo en el engine más frágil |
| 2026-08-14 | **Elementos lazy**: `find()` no toca la app | Es el modelo nativo de Playwright (`Locator`) y de pywinauto (`WindowSpecification`); permite declarar locators como constantes de módulo y habilita la auto-espera |
| 2026-08-14 | Contratos como **ABC**, no `Protocol` | Un método olvidado falla al instanciar en vez de sólo en mypy, y la clase base alberga la lógica de espera compartida (que es la parte fácil de equivocar) |
| 2026-08-14 | Patrón **template method**: público concreto + primitivas `_protegidas` | Un engine sólo implementa consultas de un intento; las guardas y la política de espera se escriben una vez y se heredan |
| 2026-08-14 | Mensajes de error en **español** | Los lee el usuario en un stack trace, y el resto de la documentación ya está en español. El código y los identificadores siguen en inglés |
| 2026-08-14 | Módulo `log.py`, no `logging.py` | Un módulo que ensombrece un nombre de la stdlib es fuente recurrente de bugs de import |
| 2026-08-14 | `bound_context()` en vez de `test_context()` | pytest recolecta cualquier función `test*` como caso de prueba; el helper importado se reportaba como test roto |
| 2026-08-14 | Hook de mypy en pre-commit como `repo: local` con `language: system` | El hook oficial crea un venv aislado y obliga a duplicar cada dependencia en `additional_dependencies`; se desincronizó de `pyproject.toml` a la primera (faltaba structlog) y rompió el commit. Con playwright y pywinauto por llegar —y pywinauto siendo solo-Windows— no compensa. Ruff sí sigue aislado: no necesita las dependencias del proyecto |

---

## Pendientes / Backlog inmediato

Lo primero de la lista es lo próximo que se hace.

- [ ] **Fase 2** — `PlaywrightEngine` + `WebElement`: implementar sólo las primitivas
      (`_exists`, `_is_visible`, `_text`, `_attribute`, `_click`, `_fill`, `_start`, `_stop`,
      `_find`, `_find_all`, `_screenshot`). Toda la política de espera ya está heredada
- [ ] **Fase 2** — Traducir `Strategy` → selectores de Playwright y declarar `Capabilities`
- [ ] **Fase 2** — Fixtures de pytest (`engine`, `page`) con los scopes correctos
- [ ] Elegir el sitio web público de práctica para la suite de la Fase 3 (candidatos:
      `saucedemo.com`, `the-internet.herokuapp.com`, `practicesoftwaretesting.com`)
- [ ] Decidir en Fase 4 entre Allure y pytest-html para el reporting
- [ ] Revisar en la Fase 5 si `Element` necesita una primitiva más para escritorio. Si hace
      falta añadirla, es señal de que el contrato estaba sesgado hacia web — registrarlo

---

## Puntos clave a recordar

Contexto que **no** se deduce leyendo el código:

- ⚠️ **Regla dura: Claude no escribe la historia del repo.** Prohibido: `git commit`, `git push`,
  `git merge`, `git rebase`, `git tag`, `gh pr create/merge`. Permitido: `git switch`,
  `git switch -c`, `git branch` y toda la lectura. Deja los cambios en el working tree y resume
  qué tocó; el usuario revisa en VS Code y commitea él mismo. Una autorización puntual no se
  extiende a los commits siguientes.
- ⚠️ **Regla dura: al iniciar sesión, Claude no lee el proyecto por iniciativa propia.** La revisión
  de estado sólo ocurre con `/continuar`.

- El objetivo real es **el framework**, no las pruebas. Microsoft Store y la web pública son
  casos de validación para demostrar que la abstracción funciona con dos tecnologías distintas.
- La Fase 5 (desktop) es la **prueba de fuego**: si para que encaje hay que modificar `core/`,
  significa que las abstracciones de la Fase 1 estaban sesgadas hacia web. Registrar la lección.
- El usuario revisa y hace cambios manuales desde **VS Code**. Antes de editar, comprobar
  si hay cambios sin commitear que no vengan de esta sesión.
- Las pruebas de escritorio necesitan **sesión de Windows interactiva y desbloqueada**. No pueden
  correr con la pantalla bloqueada ni como servicio en sesión 0.
- El `git config --global user.name` estaba como `Copilot`; se corrigió a la identidad del usuario
  **sólo a nivel de este repositorio** (la global sigue igual, para no afectar otros proyectos).
- ✅ **Riesgo descartado:** `pywinauto 0.6.9` instala y resuelve correctamente en Python 3.13.14
  (verificado en la Sesión 1). El riesgo pendiente de la Fase 5 es la *calidad del árbol UIA*
  que exponga Microsoft Store, no la compatibilidad de la librería.
- El CI emite dos anotaciones benignas que **no** son fallos: `upload-artifact@v5` aún apunta a
  Node 20 (limitación upstream) y una carrera de caché entre los dos jobs paralelos de uv.
  No tocar salvo que se vuelvan bloqueantes.
- La suite `desktop` está excluida por defecto vía `addopts = ["-m", "not desktop"]` en
  `pyproject.toml`. Hay que pedirla con `-m desktop`.
- ⚠️ **Trampa de coverage ya pisada (no repetir):** el patrón `\.\.\.` en `exclude_lines`
  excluía **funciones enteras**. Coverage lo casa contra cada línea de una sentencia, así que
  una firma como `ignored_exceptions: tuple[type[Exception], ...]` marcaba todo el `def` como
  excluido. `waits.py` reportaba 8 statements en vez de 28 y la cobertura salía inflada. Ahora
  el patrón está anclado (`^\s*\.\.\.$`). Si un módulo reporta sospechosamente pocos statements,
  mirar aquí primero.
- Para escribir un engine nuevo sólo hay que implementar las **primitivas protegidas** de
  `Element` y `Engine` (`_click`, `_exists`, `_find`…). Los métodos públicos ya traen las
  guardas y la auto-espera. No sobrescribir los públicos.
- `FakeEngine` (`automation_framework.testing`) es la implementación de referencia de los
  contratos. `appear_after=N` simula un elemento que tarda en aparecer, y así las esperas se
  prueban sin que pase tiempo real.
- `waits.wait_until` acepta `clock` y `sleep` inyectables: por eso los 239 tests corren en ~1s.

---

## Bitácora de sesiones

Entrada nueva al final. Mantener las últimas ~10; archivar el resto en `docs/sessions/`.

### Sesión 1 — 2026-08-14
**Objetivo:** definir el proyecto y completar la Fase 0.

**Hecho:**
- Definidas las 4 decisiones de arquitectura clave (desktop engine, estilo de tests, CI, repo).
- Creados `docs/PLAN.md` (roadmap de 8 fases con DoD) y `docs/ARCHITECTURE.md`.
- Creados `CLAUDE.md`, `PROGRESS.md`, `README.md`.
- Scaffolding de Fase 0: `pyproject.toml` (uv), estructura `src/` layout, ruff, mypy, pytest,
  pre-commit, `.gitignore`, PR template.
- Creadas 5 skills de Claude Code en `.claude/skills/`.
- Repo git inicializado, repo privado creado en GitHub y primer push (2 commits).
- Workflow `ci.yml` (lint + mypy + unit/arch) en verde en el primer intento.

**Verificado con ejecución real:**
- `uv sync --all-extras` → OK. Playwright 1.62.0, **pywinauto 0.6.9 en Python 3.13.14**.
- `ruff check` → 0 problemas · `ruff format --check` → OK · `mypy src` → 0 errores.
- `pytest tests/unit tests/arch` → 2 pasados, 2 omitidos (los de arquitectura esperan a `core/`).
- `pre-commit run --all-files` → los 10 hooks en verde; hook instalado en `.git/hooks`.
- CI en GitHub Actions → ambos jobs verdes.

**Bloqueos:** ninguno.

**Próximo paso:** `git switch -c fase-1-core` y empezar por `Locator` + `Element` (en ese orden:
`Element` depende de `Locator`, y `Engine` depende de ambos).

---

### Sesión 1 (continuación) — 2026-08-14
**Objetivo:** ajustar el flujo de trabajo según dos reglas nuevas del usuario.

**Hecho:**
- Skill `af-session` eliminada y dividida en dos con disparadores distintos:
  - `/continuar` — apertura de sesión, **sólo bajo petición explícita del usuario**.
  - `/bitacora` — cierre de sesión y registro del avance.
- Regla "Claude no commitea" propagada a `CLAUDE.md`, `/af-phase`, `/bitacora` y `/continuar`.
- `CLAUDE.md` reestructurado: las dos reglas de operación van ahora al principio del documento,
  antes de cualquier detalle técnico, y el flujo de trabajo indica quién hace cada paso.

**Estado del repo:** cambios **sin commitear** en el working tree, a la espera de que el usuario
los revise en VS Code. Archivos tocados: `CLAUDE.md`, `PROGRESS.md`,
`.claude/skills/{continuar,bitacora}/SKILL.md` (nuevos),
`.claude/skills/af-phase/SKILL.md` (modificado), `.claude/skills/af-session/` (eliminada).

**Bloqueos:** ninguno.

**Próximo paso:** sin cambios — Fase 1, empezando por `Locator` + `Element`.

---

### Sesión 1 (Fase 1) — 2026-08-14
**Objetivo:** construir el núcleo del framework (`core/`) y cumplir su DoD.

**Decisiones de arranque:** núcleo síncrono, elementos lazy, contratos como ABC
(ver la tabla de decisiones).

**Hecho** — 10 módulos en `core/` + el doble de pruebas:
- `exceptions.py` — jerarquía bajo `AutomationError`, con mensajes que llevan contexto
  accionable (qué locator, cuánto se esperó, qué estrategias sí soporta el engine).
- `locator.py` — `Strategy` (11 estrategias, web y UIA) y `Locator` congelado y hasheable,
  con atajos (`Locator.automation_id(...)`).
- `waits.py` — `wait_until` / `wait_while` con reloj y sleep inyectables.
- `capabilities.py` — `Capabilities` y `Feature`. **No estaba en el plan**; salió al escribir
  `Engine` y hacía falta para que un desajuste falle pronto y claro.
- `element.py` / `engine.py` — los contratos, con patrón template method.
- `registry.py` — registro por nombre; es la costura que mantiene `core/` libre de engines.
- `config.py` — `Settings` por capas (defaults → `.env` → entorno) bajo el prefijo `AF_`.
- `log.py` — structlog con contexto por test.
- `testing/fake.py` — `FakeEngine`, implementación de referencia de los contratos.

**Desviación del plan:** el `FakeEngine` estaba previsto para el incremento 6 y se adelantó al 3.
Los contratos son ABC y no se pueden probar sin una implementación concreta, así que se convirtió
en el vehículo de prueba. Salió mejor: validó las abstracciones mientras se escribían.

**Verificado con ejecución real:**
- `ruff check` → 0 problemas · `ruff format --check` → OK · `mypy --strict src` → 0 errores.
- `pytest tests/unit tests/arch` → **239 pasados en ~1s**.
- Cobertura → **100%** (526 statements, 48 branches), umbral del DoD: 85%.
- `pytest tests/arch -v` → los 2 tests de capas **ejecutan** (ya no se saltan) y pasan.

**Tres bugs reales encontrados por el propio gate:**
1. `EngineFactory = Callable[..., Engine]` reventaba en runtime: `from __future__ import annotations`
   no cubre las asignaciones de alias. Resuelto con la sintaxis perezosa de PEP 695 (`type X = ...`).
2. `structlog.testing.capture_logs` reemplaza la cadena de procesadores, así que `merge_contextvars`
   nunca corría y los tests de contexto no probaban nada. Resuelto añadiendo un `logger_factory`
   inyectable a `configure_logging` y capturando la salida JSON real.
3. `extra="forbid"` de pydantic-settings **no** detecta variables de entorno desconocidas.
   Implementada la comprobación a mano para que `AF_HEADLES` (typo) falle en vez de ignorarse.

**Bloqueos:** ninguno.

**Próximo paso:** Fase 2 — `PlaywrightEngine`. Empezar por la traducción `Strategy` → selector
y las `Capabilities`, luego las primitivas de `WebElement`.
