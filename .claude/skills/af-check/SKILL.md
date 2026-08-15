---
name: af-check
description: Gate de calidad local de AutomationFramework — ejecuta ruff, formato, mypy, tests unitarios, arquitectura y cobertura, y reporta el resultado real. Úsala antes de commitear, antes de abrir un PR y antes de dar por cerrada una fase.
---

# Gate de calidad

Ejecuta la secuencia completa y **reporta lo que realmente pasó**. Si algo falla, incluye la
salida del error. Nunca declares verde algo que no ejecutaste.

## Secuencia

```bash
uv run ruff check . --fix          # lint (autocorrige lo seguro)
uv run ruff format .               # formato
uv run mypy src                    # tipos, modo strict
uv run pytest tests/unit tests/arch --cov=automation_framework --cov-report=term-missing
```

Si la fase actual ya tiene suite e2e web:

```bash
uv run pytest -m web
```

La suite `desktop` **no** entra en el gate automático: requiere sesión de Windows interactiva
y desbloqueada. Ejecútala sólo si el usuario lo pide, con `uv run pytest -m desktop`.

## Reglas de interpretación

- **Fallo de lint o formato** → arréglalo y vuelve a ejecutar. No lo reportes como "aviso menor".
- **Fallo de mypy** → arregla el tipo. `# type: ignore` sólo con comentario justificando por qué,
  y nunca en `core/`.
- **Test fallido** → diagnostica antes de tocar nada. Si el test está bien y el código mal, arregla
  el código. Si el test estaba mal, dilo explícitamente en vez de ajustarlo en silencio para que pase.
- **Test de arquitectura fallido** (`tests/arch/`) → es un fallo de diseño, no un detalle.
  Detente y replantea; no lo silencies con un skip.
- **Cobertura de `core/` por debajo del 85%** → señala qué líneas faltan. No es bloqueante fuera
  de la Fase 1, pero sí es información que hay que dar.

## Salida esperada

Un resumen corto por paso, con veredicto:

```
ruff check     ✅  0 problemas
ruff format    ✅  0 archivos reformateados
mypy           ✅  0 errores en N archivos
pytest         ✅  N pasados, M omitidos
cobertura      ⚠️  core/ 78% (faltan waits.py:41-58)
```

Si el gate está en verde, dilo en una línea y sigue. Si no, lista sólo lo que falla.
