## Qué cambia

<!-- Una o dos frases. Qué hace este PR y por qué. -->

## Alcance

<!-- Qué entra y, si ayuda a revisar, qué queda deliberadamente fuera. -->

## Checklist

- [ ] `uv run ruff check .` y `uv run ruff format --check .` en verde
- [ ] `uv run mypy src` sin errores
- [ ] `uv run pytest` en verde
- [ ] Los cambios en `core/` **no** introducen imports de `engines/` ni de librerías de automatización
- [ ] `README.md` actualizado si cambia el contrato público o la estructura

## Cómo se probó

<!-- Comandos ejecutados y resultado. Si hay suite e2e, indica en qué entorno corrió. -->
