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

---

## Pendientes / Backlog inmediato

Lo primero de la lista es lo próximo que se hace.

- [ ] **Fase 1** — Definir `Locator`, `Element`, `Engine` y el `EngineRegistry` en `core/`
- [ ] **Fase 1** — `FakeEngine` en memoria para testear el core sin UI
- [ ] **Fase 1** — Test de arquitectura que prohíba imports de engines dentro de `core/`
- [ ] Elegir el sitio web público de práctica para la suite de la Fase 3
- [ ] Verificar que `pywinauto` instala correctamente en Python 3.13 (spike corto, antes de Fase 5)

---

## Puntos clave a recordar

Contexto que **no** se deduce leyendo el código:

- El objetivo real es **el framework**, no las pruebas. Microsoft Store y la web pública son
  casos de validación para demostrar que la abstracción funciona con dos tecnologías distintas.
- La Fase 5 (desktop) es la **prueba de fuego**: si para que encaje hay que modificar `core/`,
  significa que las abstracciones de la Fase 1 estaban sesgadas hacia web. Registrar la lección.
- El usuario revisa y hace cambios manuales desde **VS Code**. Antes de editar, comprobar
  si hay cambios sin commitear que no vengan de esta sesión.
- Las pruebas de escritorio necesitan **sesión de Windows interactiva y desbloqueada**. No pueden
  correr con la pantalla bloqueada ni como servicio en sesión 0.
- El `git config --global user.name` estaba como `Copilot`; se corrigió a la identidad del usuario
  en la Fase 0 a nivel de repositorio.

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
- Repo git inicializado, repo privado creado en GitHub y primer push.
- Workflow `ci.yml` (lint + mypy + unit tests) en verde.

**Bloqueos:** ninguno.

**Próximo paso:** abrir rama `fase-1-core` y empezar por `Locator` + `Element`.
