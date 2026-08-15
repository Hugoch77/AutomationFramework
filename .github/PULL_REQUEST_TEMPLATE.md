## Qué cambia

<!-- Una o dos frases. Qué hace este PR y por qué. -->

## Fase del plan

<!-- p.ej. Fase 1 — Núcleo del framework. Enlaza el DoD de docs/PLAN.md que cubre. -->

## Checklist

- [ ] `uv run ruff check .` y `uv run ruff format --check .` en verde
- [ ] `uv run mypy src` sin errores
- [ ] `uv run pytest` en verde
- [ ] Los cambios en `core/` **no** introducen imports de `engines/` ni de librerías de automatización
- [ ] `PROGRESS.md` actualizado si cambia el estado de la fase o se toma una decisión nueva
- [ ] Documentación actualizada si cambia el contrato público

## Cómo se probó

<!-- Comandos ejecutados y resultado. Si hay suite e2e, indica en qué entorno corrió. -->
