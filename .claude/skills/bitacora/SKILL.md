---
name: bitacora
description: Cerrar una sesión de trabajo en AutomationFramework actualizando PROGRESS.md — estado de fases, decisiones nuevas con su motivo, pendientes, puntos clave y entrada de bitácora. Úsala antes de terminar una sesión o cuando el usuario pida registrar el avance.
---

# Registrar el avance en la bitácora

Actualiza `PROGRESS.md` para que la próxima sesión —que arranca **en frío**— pueda retomar el
trabajo sin reconstruir nada de memoria.

## 1. Recoger lo que pasó

1. `git status --short` y `git log --oneline` desde el inicio de la sesión.
2. Verifica el estado real del gate de calidad (`/af-check`). **Si no está en verde, dilo.**
   No cierres una sesión declarando un estado que no comprobaste.

## 2. Actualizar `PROGRESS.md`

- **Estado actual** — fase, estado de la fase, rama, fecha, número de sesión, estado de CI.
- **Progreso por fase** — marca lo que cambió de estado.
- **Decisiones tomadas** — añade las nuevas **con su motivo**. Esta tabla es lo que evita
  re-discutir lo mismo dentro de tres sesiones. Una decisión sin el porqué no sirve.
- **Pendientes** — quita lo hecho, añade lo descubierto, reordena. Lo primero de la lista es
  literalmente lo próximo que se hará.
- **Puntos clave** — sólo contexto que **no** se deduce leyendo el código o el historial de git.
  Si está en el repo, no lo dupliques aquí.
- **Bitácora** — entrada nueva al final: Objetivo / Hecho / Verificado / Bloqueos / Próximo paso.

Si la bitácora supera ~10 entradas, mueve las más antiguas a `docs/sessions/`.
Si se completó una fase, marca también su DoD en `docs/PLAN.md`.

## 3. Reglas de escritura

- **Escribe para alguien sin ningún contexto previo.**
- Fechas **absolutas** (`2026-08-14`), nunca "ayer" ni "la semana pasada".
- En **Verificado**, incluye sólo lo que ejecutaste de verdad, con su resultado. Si algo no se
  probó, dilo. Un DoD marcado sin comprobar es peor que uno sin marcar.
- Un bloqueo sin próximo paso concreto no es información. Dale acción o no lo pongas.
- No dupliques lo que ya está en el código, en `docs/PLAN.md` o en el historial de git.

## 4. Cierre

Deja los cambios **en el working tree, sin commitear**. Avisa al usuario de qué archivos tocaste
para que él los revise y decida el commit.

> El usuario escribe la historia del repo. No ejecutes `git commit`, `git push`, `git merge`
> ni `gh pr create` salvo que te lo pida de forma explícita en ese momento. Crear ramas y
> moverte entre ellas sí está permitido.
