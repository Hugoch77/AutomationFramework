---
name: continuar
description: Retomar el trabajo en AutomationFramework al inicio de una sesión — lee PROGRESS.md, contrasta el estado documentado contra el repositorio real y propone el objetivo de la sesión. Invócala SÓLO cuando el usuario escriba /continuar; nunca de forma automática al arrancar.
---

# Retomar el proyecto

El usuario ha pedido explícitamente retomar el trabajo. Reconstruye el estado exacto del proyecto
antes de proponer nada.

> **No escribas ni modifiques código en esta skill.** Su único trabajo es orientar y proponer.
> El trabajo real empieza cuando el usuario confirme el objetivo.

## 1. Reconstruir el estado

1. Lee `PROGRESS.md` completo.
2. Lee **sólo la sección de la fase activa** en `docs/PLAN.md` (objetivo, checklist, DoD).
   No leas el documento entero.
3. En paralelo, inspecciona el repositorio real:
   - `git status --short`
   - `git log --oneline -10`
   - `git branch --show-current`
   - `gh pr list` (si hay PRs abiertos)

## 2. Contrastar documento contra realidad

Este es el paso que aporta valor. `PROGRESS.md` refleja lo que se sabía al cerrar la última sesión;
el repositorio refleja lo que hay ahora. **El usuario trabaja manualmente desde VS Code y hace sus
propios commits**, así que la divergencia es normal y esperable.

Busca activamente:

- Commits que la bitácora no menciona → el usuario avanzó por su cuenta.
- Cambios sin commitear → trabajo en curso que quizá no debas tocar.
- Archivos nuevos que el plan no contempla.
- Una rama distinta a la que dice `PROGRESS.md`.

**Si encuentras divergencias, dilo explícitamente y pregunta antes de asumir nada.**
Nunca sobrescribas trabajo manual del usuario ni des por hecho que un cambio es tuyo.

## 3. Presentar el resumen

Breve y accionable. No vuelques el contenido de los archivos: el usuario ya sabe qué hay, necesita
saber **dónde está y qué sigue**.

- **Dónde estamos** — fase activa y su estado, en una línea.
- **Novedades desde la última sesión** — sólo si el repo diverge de la bitácora. Si no hay, dilo
  en cuatro palabras y sigue.
- **Siguiente paso propuesto** — el primer pendiente del backlog, con una frase de por qué es ése.
- **Bloqueos o decisiones pendientes** — sólo si los hay.

Termina proponiendo un objetivo concreto para la sesión y **espera confirmación**.

## 4. Lo que NO debes hacer

- No arranques a implementar sin confirmación del objetivo.
- No hagas `git commit`, `git push`, `git merge` ni `gh pr create`. El usuario escribe la historia
  del repo. (Crear ramas y moverte entre ellas sí está permitido, pero no en modo apertura: aquí
  sólo se orienta.)
- No re-litigues decisiones ya registradas en la tabla **Decisiones tomadas** de `PROGRESS.md`,
  salvo que haya información nueva que las invalide.
- No propongas saltar a una fase posterior si la actual no cumple su DoD.
