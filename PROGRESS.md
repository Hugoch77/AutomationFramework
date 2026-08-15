# PROGRESS — Estado vivo del proyecto

> **Este es el primer archivo que se lee al empezar una sesión y el último que se actualiza al cerrarla.**
> Roadmap estable: [`docs/PLAN.md`](docs/PLAN.md) · Arquitectura: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)

---

## Estado actual

| Campo | Valor |
|---|---|
| **Fase activa** | Fase 0 — Bootstrap |
| **Estado de la fase** | ✅ Completada |
| **Siguiente fase** | Fase 1 — Núcleo del framework (`core/`) |
| **Rama actual** | `main` |
| **Repositorio** | https://github.com/Hugoch77/AutomationFramework (privado) |
| **CI** | ✅ Verde (`ci.yml`: lint + mypy + unit/arch) |
| **Última actualización** | 2026-08-14 |
| **Última sesión** | Sesión 1 |

---

## Progreso por fase

| Fase | Nombre | Estado | PR |
|---|---|---|---|
| 0 | Bootstrap del proyecto | ✅ Completada | — (commit directo) |
| 1 | Núcleo del framework (`core/`) | ⬜ Pendiente | — |
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
| 2026-08-14 | **Claude nunca commitea ni hace push.** Deja los cambios en el working tree | El usuario revisa personalmente cada cambio en VS Code y controla el historial del repo |
| 2026-08-14 | **Claude no lee el proyecto al arrancar una sesión.** Sólo con `/continuar` | Evita gastar contexto y tiempo en un ritual de orientación que el usuario no siempre necesita |
| 2026-08-14 | Skill `af-session` dividida en `/continuar` (apertura) y `/bitacora` (cierre) | Ahora tienen disparadores distintos: la apertura la pide el usuario explícitamente, el cierre no |
| 2026-08-14 | Nombre `/continuar` en vez de `/continue` | `claude --continue` existe como flag de la CLI; el nombre en español elimina el riesgo de colisión |

---

## Pendientes / Backlog inmediato

Lo primero de la lista es lo próximo que se hace.

- [ ] **Fase 1** — Definir `Locator`, `Element`, `Engine` y el `EngineRegistry` en `core/`
- [ ] **Fase 1** — `FakeEngine` en memoria para testear el core sin UI
- [x] ~~Test de arquitectura que prohíba imports de engines dentro de `core/`~~ — ya escrito en
      `tests/arch/test_layering.py`; se auto-omite (skip) hasta que exista `core/`
- [ ] Elegir el sitio web público de práctica para la suite de la Fase 3 (candidatos:
      `saucedemo.com`, `the-internet.herokuapp.com`, `practicesoftwaretesting.com`)
- [ ] Decidir en Fase 4 entre Allure y pytest-html para el reporting

---

## Puntos clave a recordar

Contexto que **no** se deduce leyendo el código:

- ⚠️ **Regla dura: Claude no ejecuta `git commit`, `git push` ni `gh pr create`.** Deja los cambios
  en el working tree y resume qué tocó. El usuario revisa en VS Code y commitea él mismo. Una
  autorización puntual no se extiende a los commits siguientes.
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
