# Plan de Proyecto — AutomationFramework

> Roadmap por fases (estilo agile). Documento **estable**: cambia sólo cuando cambia el alcance
> o las decisiones de arquitectura. El estado del día a día vive en [`PROGRESS.md`](../PROGRESS.md).

---

## 1. Visión

Construir un **framework de automatización genérico en Python** que sirva como base reutilizable
para distintos tipos de aplicaciones bajo prueba (SUT), sin reescribir el núcleo cada vez.

El framework NO es una suite de pruebas. Es la **infraestructura** sobre la que se escriben suites.
Las pruebas de Microsoft Store y de una web pública son *casos de validación* del framework, no su
propósito final.

### Principio rector

> El código de un test no debe saber **cómo** se automatiza la aplicación, sólo **qué** hace.

Un test habla con Page Objects. Los Page Objects hablan con un `Engine` abstracto. Sólo la capa
`engines/` sabe que existe Playwright o pywinauto. Cambiar de tecnología de automatización debe
costar un módulo nuevo, no una migración.

---

## 2. Decisiones de arquitectura (ADR resumidos)

| # | Decisión | Elegido | Razón |
|---|----------|---------|-------|
| 1 | Lenguaje / runtime | Python 3.13 | Ya instalado; ecosistema de testing maduro |
| 2 | Gestor de paquetes | **uv** | Ya instalado, 10-100x más rápido que pip, lockfile reproducible |
| 3 | Engine web | **Playwright** | Auto-waiting, tracing, multi-browser, headless nativo |
| 4 | Engine desktop | **pywinauto (backend UIA)** | Python puro, sin servidores externos; UIA soporta UWP/WinUI (Microsoft Store) |
| 5 | Estilo de tests | **pytest + Page Object Model** | Menos capas que BDD; se puede añadir pytest-bdd después sin reescribir |
| 6 | Ejecución CI web | GitHub Actions, runner hospedado (ubuntu) | Gratis, headless, rápido |
| 7 | Ejecución CI desktop | GitHub Actions, **self-hosted runner en el PC del usuario** | Los runners hospedados no tienen sesión interactiva ni Microsoft Store |
| 8 | Layout de código | `src/` layout | Evita imports accidentales desde el working dir; obliga a instalar el paquete |
| 9 | Repositorio | GitHub privado `Hugoch77/AutomationFramework` | Control de versiones + CI/CD |

### Restricción conocida y aceptada

Las pruebas de escritorio **requieren una sesión de Windows interactiva y desbloqueada**.
Un runner self-hosted corriendo como servicio en sesión 0 no puede automatizar la UI.
El runner debe ejecutarse en modo interactivo con el usuario logueado. Esto se documenta y
configura en la Fase 6.

---

## 3. Modelo de capas

```
┌─────────────────────────────────────────────────────────┐
│  tests/e2e/web/        tests/e2e/desktop/               │  ← Escenarios de negocio
├─────────────────────────────────────────────────────────┤
│  pages/ (Page Objects · Screen Objects · Components)    │  ← Vocabulario del dominio
├─────────────────────────────────────────────────────────┤
│  core/  Engine · Element · Locator · Waits · Config     │  ← Contratos abstractos (sin deps de UI)
├─────────────────────────────────────────────────────────┤
│  engines/web (Playwright)   engines/desktop (pywinauto) │  ← Implementaciones concretas
└─────────────────────────────────────────────────────────┘
```

**Regla de dependencias:** las flechas apuntan sólo hacia abajo, y `core/` **no importa nada**
de `engines/`. La factory resuelve la implementación en tiempo de ejecución vía registry.

---

## 4. Fases

Cada fase es un incremento entregable y verificable. No se avanza a la siguiente sin cumplir
el **Definition of Done (DoD)**. Cada fase = una rama + un PR.

---

### FASE 0 — Bootstrap del proyecto
**Objetivo:** que exista un repositorio instalable, con calidad automatizada y CI verde, sin lógica todavía.

- [x] Estructura de directorios (`src/` layout)
- [x] `pyproject.toml` con uv, dependencias y extras `web` / `desktop`
- [x] Tooling de calidad: ruff (lint + format), mypy (strict), pytest + coverage
- [x] `.gitignore`, `.pre-commit-config.yaml`, PR template
- [x] `CLAUDE.md`, `PROGRESS.md`, `docs/PLAN.md`, `docs/ARCHITECTURE.md`, `README.md`
- [x] Skills de Claude Code en `.claude/skills/`
- [x] Repo privado en GitHub + primer commit + push
- [x] Workflow `ci.yml` mínimo (lint + mypy + unit tests)

**DoD:** `uv run pytest` pasa en local · `uv run ruff check` y `uv run mypy src` sin errores ·
el badge de CI está verde en GitHub.

---

### FASE 1 — Núcleo del framework (`core/`)
**Objetivo:** definir los contratos que hacen que el framework sea multi-engine. Es la fase más
importante del proyecto: todo lo demás se apoya aquí.

- [ ] `Locator` — descriptor unificado de elementos (`strategy` + `value` + hints por engine)
- [ ] `Element` (ABC/Protocol) — `click`, `fill`, `text`, `is_visible`, `wait_for`, `attribute`
- [ ] `Engine` (ABC/Protocol) — `start`, `stop`, `find`, `find_all`, `screenshot`, `capabilities`
- [ ] `EngineRegistry` + factory — resolución por nombre (`"web"`, `"desktop"`) sin acoplar core
- [ ] `Settings` con pydantic-settings — config por env vars + `.env` + defaults por engine
- [ ] Excepciones tipadas (`ElementNotFoundError`, `EngineNotReadyError`, `TimeoutError`…)
- [ ] Sistema de esperas explícitas (`wait_until`, políticas de reintento, timeouts por capa)
- [ ] Logging estructurado con structlog, correlacionado por `test_id`
- [ ] `FakeEngine` en memoria para poder testear el core sin navegador ni app

**DoD:** cobertura de `core/` ≥ 85% · **cero imports de playwright/pywinauto dentro de `core/`**
(verificado por un test de arquitectura) · toda la API pública tipada y documentada.

---

### FASE 2 — Engine Web (Playwright)
**Objetivo:** primera implementación concreta del contrato. Valida que las abstracciones de la Fase 1
son correctas — si algo no encaja, se corrige el core aquí, no se parchea el engine.

- [ ] `PlaywrightEngine` implementando `Engine`
- [ ] `WebElement` implementando `Element`
- [ ] Ciclo de vida browser → context → page, con limpieza garantizada
- [ ] Traducción `Locator` → selector de Playwright (role, text, css, xpath, test-id)
- [ ] Soporte headless/headed, multi-browser (chromium/firefox/webkit), viewport, timeouts
- [ ] Captura automática en fallo: screenshot + trace de Playwright
- [ ] Fixtures de pytest (`engine`, `page`, scopes correctos)

**DoD:** una suite smoke contra una web pública real pasa en local **y** en CI headless ·
en un test fallido intencionalmente se genera screenshot + trace.

---

### FASE 3 — Page Object Model y utilidades de test
**Objetivo:** dar a quien escribe tests un vocabulario cómodo y una primera suite web real.

- [ ] `BasePage` / `BaseScreen` — construcción sobre `Engine`, verificación de "página cargada"
- [ ] `Component` — bloques reutilizables (tablas, modales, navbars)
- [ ] Assertions propias con mensajes de fallo accionables (`expect_visible`, `expect_text`…)
- [ ] Gestión de datos de prueba: factories, fixtures parametrizadas, ficheros JSON/YAML
- [ ] Markers y convenciones: `@pytest.mark.web`, `@pytest.mark.desktop`, `@pytest.mark.smoke`
- [ ] Suite web real (8–12 tests) sobre el sitio de práctica elegido

**DoD:** la suite web pasa **3 ejecuciones consecutivas sin flaky** · escribir un test nuevo
no requiere tocar `core/` ni `engines/`.

---

### FASE 4 — Reporting y observabilidad
**Objetivo:** que un fallo se diagnostique sin reproducir manualmente.

- [ ] Reporte HTML/Allure generado en cada ejecución
- [ ] Adjuntos automáticos en fallo: screenshot, trace, logs del test, DOM/árbol UIA
- [ ] Logs correlacionados (cada línea sabe a qué test pertenece)
- [ ] Publicación del reporte como artifact de GitHub Actions
- [ ] Resumen de resultados en el PR (job summary)

**DoD:** desde un run de CI fallido se puede descargar el reporte y ver la causa sin ejecutar nada local.

---

### FASE 5 — Engine Desktop (pywinauto) — la prueba de fuego
**Objetivo:** validar que el framework es *realmente* genérico añadiendo una tecnología con un
modelo muy distinto al web.

- [ ] `DesktopEngine` implementando el **mismo** contrato `Engine`
- [ ] `DesktopElement` implementando `Element`
- [ ] Traducción `Locator` → criterios UIA (`auto_id`, `name`, `control_type`, `class_name`)
- [ ] Lanzar app nueva vs. adjuntarse a una ya abierta (`start` / `connect`)
- [ ] Esperas UIA robustas (los timings de escritorio no se parecen a los de web)
- [ ] Captura de ventana + volcado del árbol de control en fallo
- [ ] Screen Objects + suite de Microsoft Store (abrir, buscar, ver ficha de app)

**DoD:** la suite desktop pasa localmente 3 veces seguidas · **no se modificó ni una línea de
`core/` para que el desktop encajara** (si hizo falta, se documenta como lección aprendida).

---

### FASE 6 — CI/CD completo
**Objetivo:** pipeline de verdad, con las dos suites.

- [ ] Self-hosted runner de GitHub Actions en el PC (sesión interactiva, label `windows-desktop`)
- [ ] Workflow `desktop.yml` disparado en PR y en `workflow_dispatch`
- [ ] Matrix de navegadores en el workflow web
- [ ] Branch protection en `main`: PR obligatorio + checks requeridos
- [ ] Caché de dependencias uv y de navegadores Playwright
- [ ] Versionado semántico y releases automáticas

**DoD:** un PR dispara web-CI (hospedado) + desktop-CI (self-hosted) · `main` no acepta push directo.

---

### FASE 7 — Endurecimiento y extensibilidad
**Objetivo:** cerrar el círculo demostrando que añadir un engine nuevo es barato.

- [ ] Ejecución en paralelo (pytest-xdist) con aislamiento correcto de engines
- [ ] Política de reintentos y detección/cuarentena de tests flaky
- [ ] Guía "cómo añadir un engine nuevo" + generador de scaffolding
- [ ] **Tercer engine de validación** (API/REST) — demuestra que el contrato no está sesgado a UI
- [ ] Documentación de usuario completa

**DoD:** el tercer engine se implementa siguiendo sólo la guía · la suite completa corre en paralelo
sin degradar estabilidad.

---

## 5. Flujo de trabajo por fase

```
1. Rama:      git switch -c fase-N-<slug>
2. Trabajo:   incrementos pequeños, cada uno con sus tests
3. Gate:      /af-check   (ruff + mypy + pytest + coverage)
4. Commit:    mensajes convencionales (feat/fix/docs/refactor/test/ci/chore)
5. PR:        gh pr create  → esperar CI verde
6. Merge:     squash a main
7. Cierre:    actualizar PROGRESS.md y marcar el DoD de la fase
```

## 6. Convenciones

- **Ramas:** `fase-N-<slug>`, `fix/<slug>`, `docs/<slug>`
- **Commits:** Conventional Commits (`feat(core): añade contrato Engine`)
- **Idioma:** documentación y commits en español; **código, nombres e identificadores en inglés**
- **Tests unitarios** (`tests/unit/`) prueban el framework; **e2e** (`tests/e2e/`) prueban el SUT
- Ningún `sleep()` fijo: siempre esperas explícitas basadas en condición

## 7. Riesgos abiertos

| Riesgo | Impacto | Mitigación |
|--------|---------|------------|
| pywinauto con Microsoft Store (UWP) puede exponer un árbol UIA pobre | Alto | Fase 5 empieza con un *spike* de inspección UIA antes de escribir Screen Objects |
| Microsoft Store cambia su UI sin aviso | Medio | Locators por `auto_id` antes que por texto; suite desktop marcada como no bloqueante al inicio |
| Self-hosted runner requiere sesión activa | Medio | Documentar arranque interactivo; fallback a ejecución manual |
| Abstracción demasiado rígida para el 3er engine | Medio | Fase 7 la valida a propósito con un engine no-UI |
