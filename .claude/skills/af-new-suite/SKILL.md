---
name: af-new-suite
description: Crear una suite de pruebas nueva en AutomationFramework (web o escritorio) con sus Page Objects / Screen Objects, locators, fixtures, markers y datos de prueba. Úsala cuando el usuario quiera automatizar una aplicación o un flujo nuevo.
---

# Nueva suite de pruebas

## 1. Averigua qué se va a probar

Antes de generar nada, ten claro:

- **Qué tipo de SUT**: web o escritorio (determina el engine).
- **Qué flujos de negocio** se cubren, en lenguaje de usuario, no de UI.
- **Precondiciones**: sesión, datos, estado inicial de la app.
- **Cómo se llega a un estado limpio** entre tests.

Si el usuario no lo ha dicho, pregunta lo mínimo imprescindible. No inventes flujos.

## 2. Estructura a generar

```
src/automation_framework/pages/<sut>/
├── __init__.py
├── locators.py         # Locators agrupados por pantalla, como constantes
├── <screen>_page.py    # Un Page/Screen Object por pantalla
└── components/         # Bloques reutilizables (tablas, modales, navbar)

tests/e2e/<web|desktop>/<sut>/
├── conftest.py         # fixtures propias de la suite
└── test_<flujo>.py
```

## 3. Reglas de los Page Objects

- Heredan de `BasePage` / `BaseScreen` y reciben el `Engine` por constructor.
- **Exponen acciones de negocio, no de UI**: `search("notepad")`, no `type_into_search_box()`.
- **Nunca contienen assertions.** Devuelven estado o el siguiente Page Object; el test afirma.
- Los locators viven en `locators.py`, no incrustados en los métodos.
- Nada de `playwright` ni `pywinauto` importado aquí. Sólo el contrato `Engine`/`Element`.

## 4. Reglas de los locators

| Contexto | Preferencia (de mejor a peor) |
|---|---|
| Web | `data-testid` → role + nombre accesible → texto → CSS → XPath |
| Escritorio | `auto_id` → `control_type` + `name` → `class_name` → índice |

En escritorio, **evita depender del texto visible**: cambia con el idioma del sistema y con cada
actualización de la app. Un locator por índice es el último recurso y hay que comentarlo.

## 5. Reglas de los tests

- Un marker de tipo obligatorio: `@pytest.mark.web` o `@pytest.mark.desktop`.
- Añade `@pytest.mark.smoke` sólo a los flujos verdaderamente críticos.
- Independientes entre sí y ejecutables en cualquier orden (van a correr en paralelo).
- Sin `time.sleep()`. Esperas explícitas basadas en condición.
- El nombre del test describe el comportamiento esperado, no los pasos.
- Datos de prueba en fixtures o ficheros, nunca hardcodeados dentro del test.

## 6. Verificación antes de entregar

1. `uv run pytest -m <web|desktop> -v` — que pasen.
2. **Ejecuta la suite 3 veces seguidas.** Si algún test falla alguna vez, es flaky: arréglalo ahora,
   no lo entregues. Un test flaky envenena la confianza en toda la suite.
3. Fuerza un fallo intencionado y comprueba que se genera la evidencia automática
   (screenshot, trace o árbol UIA). Si no se genera, es un bug del framework.
4. `/af-check`.
5. Actualiza `PROGRESS.md` con la suite añadida.
