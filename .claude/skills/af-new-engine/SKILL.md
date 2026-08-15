---
name: af-new-engine
description: Añadir un engine de automatización nuevo a AutomationFramework (otra tecnología de UI, móvil, API...) respetando los contratos abstractos de core. Úsala cuando haya que soportar un tipo de aplicación que el framework todavía no cubre.
---

# Añadir un engine nuevo

Un engine traduce los contratos abstractos de `core/` a una tecnología concreta. Si añadir uno
resulta caro, el problema está en las abstracciones, no en el engine.

## 1. Spike primero, código después

**No empieces implementando.** Haz un script desechable en el scratchpad que, usando la librería
en crudo, consiga: lanzar la app, localizar un elemento, interactuar con él y cerrarla.

Ese spike responde lo que necesitas saber:

- ¿Cómo identifica elementos esta tecnología? → define el mapeo de `Strategy`.
- ¿Auto-espera o hay que hacer polling? → define la estrategia de esperas.
- ¿Cómo se lanza y se cierra la app? ¿Se puede adjuntar a una instancia existente?
- ¿Qué se puede capturar en un fallo (screenshot, árbol de elementos, logs)?
- ¿Es síncrona o asíncrona? ¿Thread-safe para ejecución paralela?

## 2. Estructura

```
src/automation_framework/engines/<nombre>/
├── __init__.py       # registra el engine en el EngineRegistry
├── engine.py         # implementa el contrato Engine
├── element.py        # implementa el contrato Element
├── locators.py       # traduce core.Locator -> selector nativo
└── config.py         # opciones específicas del engine
```

## 3. Implementación

1. **`Element` primero.** Implementa `click`, `fill`, `text`, `is_visible`, `wait_for`, `attribute`.
   Si alguna primitiva no tiene sentido en esta tecnología, lanza `UnsupportedOperationError`
   con un mensaje que explique la alternativa — nunca la implementes con un `pass` silencioso.
2. **Traducción de locators.** Mapea cada `Strategy` soportada. Declara las soportadas en
   `capabilities` y **falla rápido y claro** ante una estrategia que no soportas.
3. **`Engine` después.** Ciclo de vida (`start`/`stop`) con limpieza garantizada aunque el test
   explote. Debe funcionar como context manager.
4. **Registro.** Añádelo al `EngineRegistry` con un nombre corto. `core/` no debe importarlo:
   el registro ocurre en el `__init__` del engine.
5. **Dependencia opcional.** Añádela como extra en `pyproject.toml`, nunca como dependencia base.
   Si el extra no está instalado, el error debe decir qué instalar.

## 4. Reglas innegociables

- **`core/` no se toca para acomodar un engine.** Si crees que hace falta, para y planteálo:
  o la abstracción estaba sesgada (arréglala para *todos* los engines), o el engine lo está
  resolviendo mal. Cualquiera de los dos casos se registra en `PROGRESS.md`.
- Todo lo específico de la tecnología queda **dentro** de la carpeta del engine. Si algo se filtra
  a `pages/` o a `tests/`, es un fallo de diseño.
- Los tests del engine van en `tests/unit/engines/<nombre>/` y deben poder correr sin la app real
  siempre que sea posible (mock del cliente nativo).

## 5. Verificación

1. Un test end-to-end mínimo real contra la tecnología nueva.
2. `uv run pytest tests/arch` — las reglas de capas siguen en verde.
3. **La prueba definitiva:** coge un test escrito para otro engine y comprueba que su forma es
   idéntica. Si el test del engine nuevo se ve distinto, la abstracción tiene fugas.
4. Documenta el engine en `docs/ARCHITECTURE.md` y actualiza `PROGRESS.md`.
