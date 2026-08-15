---
name: af-phase
description: Ejecutar una fase completa del roadmap de AutomationFramework de principio a fin — rama, incrementos con tests, verificación del Definition of Done, PR y cierre en PROGRESS.md. Úsala cuando el usuario diga "empecemos la fase N", "sigamos con la fase actual" o "cierra la fase".
---

# Ejecutar una fase del plan

## 1. Preparación

1. Lee `PROGRESS.md` para confirmar cuál es la fase activa y si la anterior está realmente cerrada.
2. Lee **sólo la sección de esa fase** en `docs/PLAN.md`: objetivo, checklist y DoD.
3. **Si la fase anterior no cumple su DoD, no arranques.** Dilo y propone cerrarla primero.
4. Crea la rama: `git switch -c fase-N-<slug>`.

## 2. Planificación del incremento

Desglosa la checklist de la fase en tareas ordenadas por dependencia. Regla de orden:

> Primero lo que otros módulos van a importar. Después lo que los importa.

Presenta el desglose al usuario y confirma antes de empezar a escribir código.

## 3. Ejecución

Trabaja en **incrementos pequeños y verificables**. Cada incremento:

1. Código de producción con anotaciones de tipo completas.
2. Sus tests en el mismo paso — no al final, no "después".
3. `uv run pytest tests/unit tests/arch` en verde antes de pasar al siguiente.

Restricciones que aplican siempre:

- `core/` no importa `engines/` ni ninguna librería de automatización. Hay un test que lo verifica.
- Nada de `time.sleep()` fijo. Esperas explícitas basadas en condición.
- Si una abstracción del core no encaja con lo que estás implementando, **arregla el core** —
  no metas un caso especial en el engine. Y regístralo en `PROGRESS.md` como lección aprendida.
- Código, nombres y docstrings en inglés. Comentarios explicativos y documentación en español.

## 4. Verificación del DoD

Antes de dar la fase por terminada, recorre el DoD **punto por punto** y demuestra cada uno con
un comando y su salida real. No marques nada que no hayas ejecutado.

Ejecuta el gate completo: `/af-check`.

Si algún punto del DoD no se cumple, dilo abiertamente y propone: (a) completarlo,
o (b) moverlo explícitamente a otra fase con justificación. Nunca lo des por bueno en silencio.

## 5. Cierre

1. `gh pr create` con descripción que enlace el DoD cubierto.
2. Espera a que CI esté verde: `gh pr checks --watch`.
3. Tras el merge, ejecuta `/af-session` en modo cierre para actualizar `PROGRESS.md`
   y marcar el DoD en `docs/PLAN.md`.

## Cuando la fase se desvía

Si a mitad de la fase descubres que el plan estaba mal (una dependencia que no se vio, una
abstracción inviable): **para y dilo**. No amplíes el alcance en silencio ni recortes el DoD por
tu cuenta. Propone el cambio, deja que el usuario decida, y registra la decisión en `PROGRESS.md`.
