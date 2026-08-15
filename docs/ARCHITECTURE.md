# Arquitectura

> Documento de referencia técnica. Explica **por qué** el código está organizado así.
> El roadmap está en [`PLAN.md`](PLAN.md); el estado actual en [`PROGRESS.md`](../PROGRESS.md).

---

## El problema que resuelve

Automatizar una web y automatizar una app de escritorio son tareas con APIs incompatibles:

| | Web (Playwright) | Desktop (pywinauto/UIA) |
|---|---|---|
| Unidad de trabajo | `Page` dentro de un `BrowserContext` | `WindowSpecification` dentro de una `Application` |
| Localización | CSS, XPath, role, text | `auto_id`, `name`, `control_type`, `class_name` |
| Esperas | Auto-waiting integrado | Manual, basado en polling |
| Ciclo de vida | Arranca/mata el navegador | Lanza el ejecutable **o** se adjunta a un proceso vivo |

Si los tests hablan directamente con estas APIs, el framework no es genérico: es dos frameworks.
La solución es un **contrato común** en `core/` que ambos mundos implementan.

---

## Capas

```
tests/e2e/**            →  Escenarios. Sólo conocen Page Objects y assertions.
       ↓
pages/**                →  Vocabulario del dominio. Conocen Locators y el contrato Engine.
       ↓
core/**                 →  Contratos abstractos. NO conoce Playwright ni pywinauto.
       ↑ (implementado por)
engines/web, engines/desktop
```

**Regla invariante:** `core/` no importa nada de `engines/`.
Se verifica con un test de arquitectura automatizado, no con disciplina.

---

## Piezas clave de `core/`

### `Locator`
Descriptor declarativo e independiente de tecnología. No es un selector: es una *intención*
que cada engine traduce a su propio lenguaje.

```python
Locator(strategy=Strategy.TEST_ID, value="search-box")
Locator(strategy=Strategy.NAME,    value="Buscar")
Locator(strategy=Strategy.CSS,     value="button.primary")   # sólo lo entiende web
```

Cada engine declara qué estrategias soporta (`capabilities`). Usar una estrategia no soportada
falla de forma explícita y temprana, no con un error críptico a mitad del test.

### `Element`
Interfaz mínima y deliberadamente pobre: `click`, `fill`, `text`, `is_visible`, `wait_for`,
`attribute`. Todo lo que se pueda expresar con esas primitivas **no** entra en la interfaz.
Una interfaz pequeña es lo que hace barato añadir un engine.

### `Engine`
Ciclo de vida y búsqueda: `start`, `stop`, `find`, `find_all`, `screenshot`, `capabilities`.
Es un context manager: la limpieza está garantizada aunque el test explote.

### `EngineRegistry`
Los engines se registran por nombre. La factory devuelve la implementación pedida por
configuración, así que el core nunca importa una implementación concreta.

```python
engine = create_engine("web")      # o "desktop", o el que exista mañana
```

### `Settings`
Configuración por capas: valores por defecto → `.env` → variables de entorno → CLI de pytest.
Las variables de entorno mandan, para que CI pueda cambiar comportamiento sin tocar código.

---

## Cómo encaja un test

```python
def test_busqueda(engine):                  # fixture: crea/destruye el engine
    home = HomePage(engine).open()          # Page Object
    resultados = home.search("notepad")     # vocabulario de negocio
    expect_visible(resultados.first_item)   # assertion con mensaje accionable
```

Este test es idéntico en forma para web y para desktop. Lo único que cambia es qué Page Object
se instancia y qué engine inyecta la fixture.

---

## Estructura de directorios

```
src/automation_framework/
├── core/          Contratos, config, esperas, logging, excepciones, registry
├── engines/
│   ├── web/       PlaywrightEngine, WebElement, traducción de Locators
│   └── desktop/   DesktopEngine (pywinauto UIA), DesktopElement
├── pages/         BasePage, Component, assertions
├── fixtures/      Plugin de pytest: fixtures, hooks, markers
├── reporting/     Screenshots, traces, adjuntos, integración con el reporter
└── utils/         Datos de prueba, ficheros, reintentos

tests/
├── unit/          Prueban el FRAMEWORK (rápidos, sin UI, usan FakeEngine)
├── arch/          Prueban las reglas de arquitectura (p.ej. core no importa engines)
└── e2e/
    ├── web/       Prueban un SUT web
    └── desktop/   Prueban Microsoft Store
```

## Dependencias opcionales

`playwright` y `pywinauto` son **extras**, no dependencias base:

```bash
uv sync --extra web        # sólo automatización web
uv sync --extra desktop    # sólo escritorio (Windows)
uv sync --all-extras       # todo
```

Así el CI en Linux instala sólo lo que puede usar, y el core sigue siendo instalable en cualquier
sistema operativo.
