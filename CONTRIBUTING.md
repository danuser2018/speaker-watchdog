# Contributing Guide

Bienvenido al proyecto. Este documento describe las normas y flujos de trabajo que todo colaborador debe seguir para mantener la calidad del código, la trazabilidad del historial de cambios y la eficiencia del desarrollo asistido con IA.

---

## Tabla de contenidos

1. [Modelo de ramificación](#modelo-de-ramificación)
2. [Ciclo de vida de una feature](#ciclo-de-vida-de-una-feature)
3. [Convenciones de commits](#convenciones-de-commits)
4. [Pull Requests](#pull-requests)
5. [Code Review](#code-review)
6. [Desarrollo asistido con IA](#desarrollo-asistido-con-ia)
7. [Estándares de código](#estándares-de-código)
8. [Testing](#testing)
9. [Gestión de secretos y seguridad](#gestión-de-secretos-y-seguridad)

---

## Modelo de ramificación

Este proyecto sigue **Trunk Based Development (TBD)**. La rama `main` es el tronco único y siempre debe estar en estado desplegable.

### Reglas fundamentales

- ✅ **Todas las features** se desarrollan en ramas de corta duración que parten de `main`.
- ✅ **Todo el código** regresa a `main` exclusivamente mediante una **Pull Request (PR)**.
- ❌ **Nunca** hagas commits directos sobre `main`.
- ❌ **Nunca** mergees código a `main` sin pasar por una PR aprobada.
- ❌ **Nunca** trabajes sobre `main` localmente.

### Nomenclatura de ramas

```
<tipo>/<descripcion-corta-en-kebab-case>

Ejemplos:
  feature/tts-voice-selection
  fix/audio-buffer-overflow
  chore/update-dependencies
  docs/api-reference
  refactor/streaming-pipeline
```

| Prefijo | Uso |
|---|---|
| `feature/` | Nueva funcionalidad |
| `fix/` | Corrección de un bug |
| `chore/` | Tareas de mantenimiento sin impacto en lógica |
| `docs/` | Cambios exclusivos en documentación |
| `refactor/` | Refactorización sin cambio de comportamiento |
| `test/` | Adición o mejora de tests |

---

## Ciclo de vida de una feature

```
main ──────────────────────────────────────────► main
       │                                    ▲
       └─► feature/mi-feature ─── PR ──────┘
```

### Pasos

1. **Sincronizar** con `main` antes de crear la rama:
   ```bash
   git checkout main
   git pull origin main
   ```

2. **Crear la rama** desde `main`:
   ```bash
   git checkout -b feature/nombre-de-la-feature
   ```

3. **Desarrollar** en commits pequeños y atómicos.

4. **Mantener la rama al día** con `main` mediante rebase (preferido sobre merge):
   ```bash
   git fetch origin
   git rebase origin/main
   ```

5. **Abrir una PR** cuando la feature esté lista para revisión.

6. **Resolver los comentarios** del code review antes de mergear.

7. **Mergear** únicamente con la aprobación de al menos un revisor.

8. **Eliminar la rama** remota tras el merge.

> **Importante:** las ramas de feature deben ser de corta duración (idealmente no más de 1-2 días de trabajo). Si una feature es grande, divídela en incrementos entregables más pequeños usando *feature flags* si es necesario.

---

## Convenciones de commits

Usamos el estándar **[Conventional Commits](https://www.conventionalcommits.org/)**.

### Formato

```
<tipo>(<ámbito>): <descripción en imperativo>

[cuerpo opcional]

[pie opcional: breaking changes, referencias a issues]
```

### Tipos permitidos

| Tipo | Descripción |
|---|---|
| `feat` | Nueva funcionalidad |
| `fix` | Corrección de bug |
| `docs` | Cambios en documentación |
| `style` | Formato, espaciado (sin cambio lógico) |
| `refactor` | Refactorización sin bug fix ni feature |
| `test` | Añadir o modificar tests |
| `chore` | Tareas de mantenimiento del proyecto |
| `perf` | Mejora de rendimiento |
| `ci` | Cambios en pipelines de CI/CD |

### Ejemplos

```
feat(tts): añadir soporte para voz en español neutro

fix(streaming): corregir desbordamiento de buffer en chunks > 32kb

docs(api): documentar endpoint de síntesis de voz

chore(deps): actualizar openai-sdk a v5.2.1
```

---

## Pull Requests

### Antes de abrir una PR

- [ ] El código compila y los tests pasan localmente.
- [ ] El linter no reporta errores (`npm run lint` o equivalente).
- [ ] La rama está actualizada con `main` (rebase).
- [ ] El archivo `CHANGELOG.md` ha sido actualizado bajo la sección `[Sin publicar]`.
- [ ] La descripción de la PR está completa.

### Plantilla de PR

Al abrir una PR, completa siempre los siguientes apartados:

```markdown
## ¿Qué hace este cambio?
<!-- Descripción clara y concisa del cambio -->

## ¿Por qué es necesario?
<!-- Contexto del problema que resuelve -->

## ¿Cómo se probó?
<!-- Pasos para verificar el comportamiento -->

## Checklist
- [ ] Tests añadidos / actualizados
- [ ] Documentación actualizada si aplica
- [ ] Registro de cambios (`CHANGELOG.md`) actualizado
- [ ] No introduce secretos o datos sensibles
- [ ] Breaking changes documentados (si aplica)

## Referencias
<!-- Issues relacionados, ADRs, documentación externa -->
```

### Tamaño de las PRs

- **Objetivo:** PRs pequeñas y enfocadas (< 400 líneas cambiadas como referencia).
- PRs grandes dificultan el review y aumentan el riesgo de conflictos.
- Si una PR supera ese umbral, considera dividirla.

---

## Code Review

### Para el revisor

- Prioriza la comprensión de la intención antes de buscar errores.
- Distingue entre **bloqueantes** (deben resolverse antes del merge) y **sugerencias** (mejoras opcionales). Usa prefijos como `[bloqueante]` o `[nit]`.
- Proporciona sugerencias concretas y constructivas, no solo señales de problemas.
- Aprueba cuando el código es correcto y seguro, aunque no sea exactamente como lo habrías escrito tú.

### Para el autor

- Responde a cada comentario, aunque sea para decir que lo has tenido en cuenta.
- Si no estás de acuerdo con un comentario, explica tu razonamiento con datos o contexto.
- No hagas cambios no relacionados en la misma PR.

---

## Desarrollo asistido con IA

El uso de herramientas de IA (como Antigravity, GitHub Copilot, etc.) está expresamente bienvenido. Sin embargo, su uso conlleva responsabilidades específicas.

### Principios generales

1. **El autor es siempre responsable del código**, independientemente de quién (o qué) lo haya generado. No mergees código que no entiendes.

2. **La IA como copiloto, no como piloto.** La IA sugiere; el desarrollador decide, revisa y valida.

3. **El contexto lo pone el humano.** Define claramente los requisitos, restricciones y criterios de aceptación antes de delegar trabajo a la IA.

### Flujo de trabajo recomendado con IA

```
Requisito claro → Prompt preciso → Revisión crítica → Tests → Commit
```

- **Define el alcance** antes de lanzar un prompt. Un requisito vago produce código vago.
- **Itera en pequeños pasos.** Pide cambios incrementales en lugar de generar grandes bloques de código de una vez.
- **Revisa siempre la salida** antes de aceptarla. Comprueba lógica, seguridad, rendimiento y legibilidad.
- **Haz preguntas explícitas** cuando el asistente proponga algo que no entiendas. No asumas que es correcto por defecto.

### Gestión de ramas con asistentes de IA

- **El asistente nunca cambiará de rama sin confirmación explícita del desarrollador.**
- Antes de cualquier operación de cambio de rama, merge o rebase, el asistente preguntará explícitamente y esperará respuesta.
- El estado del repositorio (rama activa, cambios en staging, etc.) debe ser verificado antes de ejecutar comandos git relevantes.

### Qué revisar específicamente en código generado por IA

| Área | Qué comprobar |
|---|---|
| **Seguridad** | Inyecciones, validaciones de entrada, exposición de secretos |
| **Lógica** | Condiciones de borde, manejo de errores, casos no contemplados |
| **Rendimiento** | Bucles innecesarios, llamadas bloqueantes, fugas de memoria |
| **Legibilidad** | Nombres de variables y funciones, comentarios útiles |
| **Tests** | ¿El código generado es testeable? ¿Se han generado tests útiles? |
| **Dependencias** | ¿Se han añadido paquetes innecesarios o desactualizados? |

### Trazabilidad del uso de IA

- Si un bloque de código fue generado sustancialmente por IA y contiene decisiones de diseño no triviales, añade un comentario breve explicando la intención. Esto ayuda a futuros revisores (humanos y IA) a entender el contexto.
- Documenta en la descripción de la PR si la feature fue desarrollada con asistencia de IA, especialmente si hay decisiones de arquitectura que requieran contexto adicional.

### Prompts como artefactos

- Para funcionalidades complejas, considera guardar el prompt principal usado en el desarrollo dentro del directorio `docs/prompts/` con nombre descriptivo. Esto facilita reproducir o iterar sobre decisiones de diseño en el futuro.

---

## Estándares de código

- **Idioma del código:** inglés (nombres de variables, funciones, clases, comentarios en código).
- **Idioma de la documentación:** español (README, CONTRIBUTING, ADRs, comentarios de PR).
- Sigue las convenciones de estilo definidas en la configuración del linter del proyecto.
- Prefiere **claridad sobre brevedad**: el código se lee muchas más veces de las que se escribe.
- Evita comentarios que expliquen *qué* hace el código (eso lo dice el código); comenta *por qué* cuando la razón no sea obvia.
- Mantén las funciones pequeñas y con una única responsabilidad.

---

## Testing

- Todo nuevo código debe estar acompañado de tests.
- Los tests deben ejecutarse en CI antes de que una PR pueda mergearse.
- Prioriza tests de **comportamiento** sobre tests de implementación.
- Para código generado por IA, verifica que los tests cubran casos de borde y no solo el happy path.

### Niveles de test esperados

| Nivel | Scope | Herramienta sugerida |
|---|---|---|
| Unitario | Funciones y módulos individuales | Jest / Vitest |
| Integración | Interacción entre módulos | Supertest / Jest |
| E2E | Flujos completos desde el usuario | Playwright / Cypress |

---

## Gestión de secretos y seguridad

- ❌ **Nunca** commits credenciales, API keys, tokens o datos sensibles en el repositorio.
- Usa variables de entorno (`.env`) y asegúrate de que el fichero `.env` esté en `.gitignore`.
- Usa un gestor de secretos o ficheros `.env.example` con valores de ejemplo para documentar las variables necesarias.
- Si accidentalmente has commiteado un secreto, **rota la credencial inmediatamente** y notifica al equipo.

---

*Este documento es vivo. Si encuentras algo que mejorar, abre una PR con el prefijo `docs(contributing):`.*
