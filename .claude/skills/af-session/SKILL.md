---
name: af-session
description: Abrir o cerrar una sesión de trabajo en AutomationFramework. Al abrir, reconstruye el estado exacto del proyecto desde PROGRESS.md y propone el objetivo de la sesión; al cerrar, actualiza PROGRESS.md con lo hecho, decisiones nuevas, bloqueos y próximo paso. Úsala al principio de cada sesión y antes de terminar.
---

# Sesión de trabajo

Esta skill tiene dos modos. Deduce cuál por el argumento (`start` / `end`) o por el contexto:
si aún no se ha hecho nada en la conversación, es apertura; si ya se hizo trabajo, es cierre.

---

## Modo APERTURA

**No escribas código todavía.** Primero reconstruye el estado.

1. Lee `PROGRESS.md` completo.
2. Lee la sección de la **fase activa** en `docs/PLAN.md` (sólo esa fase, no todo el documento).
3. Ejecuta en paralelo:
   - `git status --short` y `git log --oneline -10`
   - `git branch --show-current`
4. **Compara realidad contra documento.** Si hay cambios sin commitear o commits que `PROGRESS.md`
   no refleja, probablemente el usuario trabajó manualmente desde VS Code. Dilo explícitamente
   y pregunta antes de asumir nada.
5. Si hay PRs abiertos: `gh pr list`.

Después presenta un resumen **breve** (no vuelques los archivos):

- **Dónde estamos:** fase activa y su estado.
- **Desde la última sesión:** cambios en el repo que no están en la bitácora, si los hay.
- **Siguiente paso propuesto:** el primer pendiente del backlog, con una frase de justificación.
- **Bloqueos o decisiones pendientes**, si existen.

Termina proponiendo un objetivo concreto para la sesión y espera confirmación del usuario.

---

## Modo CIERRE

1. Ejecuta `git status --short` y `git log --oneline` desde el inicio de la sesión.
2. Verifica que el gate de calidad pasó (`/af-check`). Si no, dilo — no cierres fingiendo verde.
3. Actualiza `PROGRESS.md`:
   - Tabla **Estado actual**: fase, estado, rama, fecha, número de sesión.
   - Tabla **Progreso por fase**: marca lo que cambió de estado.
   - **Decisiones tomadas**: añade cualquier decisión nueva *con su motivo*. Esto es lo que evita
     re-litigar lo mismo en sesiones futuras.
   - **Pendientes**: quita lo hecho, añade lo descubierto. Lo primero de la lista es lo próximo.
   - **Puntos clave**: sólo contexto que no se deduce leyendo el código.
   - **Bitácora**: entrada nueva al final con Objetivo / Hecho / Bloqueos / Próximo paso.
4. Si la bitácora supera ~10 entradas, mueve las más antiguas a `docs/sessions/`.
5. Si se completó una fase, marca su DoD en `docs/PLAN.md`.
6. Ofrece commitear los cambios de documentación.

### Reglas de escritura de PROGRESS.md

- **Escribe para alguien sin ningún contexto previo.** La próxima sesión arranca en frío.
- Fechas siempre absolutas (`2026-08-14`), nunca "ayer" ni "la semana pasada".
- Registra el **porqué** de las decisiones, no sólo el qué.
- No dupliques lo que ya está en el código o en el historial de git.
- Un bloqueo sin dueño ni próximo paso no es información: dilo con acción concreta.
