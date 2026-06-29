# Registro de cambios

Todos los cambios notables de este proyecto se documentan en este fichero.

El formato está basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/)
y este proyecto adhiere a [Versionado Semántico](https://semver.org/lang/es/).

## Guía de uso

Cada versión se documenta bajo su número de versión y fecha de publicación.
Los cambios se agrupan en las siguientes categorías:

- **Añadido** — nuevas funcionalidades.
- **Cambiado** — cambios en funcionalidades existentes.
- **Obsoleto** — funcionalidades que serán eliminadas en versiones futuras.
- **Eliminado** — funcionalidades eliminadas en esta versión.
- **Corregido** — corrección de errores.
- **Seguridad** — correcciones de vulnerabilidades.

---

## Sin publicar

### Añadido

- Carpeta `.agent/skills` añadida con información relevante para la IA.

### Cambiado

- **Descarte de la arquitectura de daemon IPC**: Se ha formalizado el descarte del modelo de daemon persistente de `mpv` con sockets Unix (documentado en `docs/refactor_mpv_daemon.md`) debido a inestabilidad y desconexiones automáticas de sockets bajo entornos de aislamiento de recursos del host. Se consolida de forma definitiva el modelo de procesos efímeros e independientes de la v1.1.0 (ver ADR-008).

## [1.1.0] - 2026-06-22

### Añadido

- Documentación del diseño de reproductor mpv (`docs/refactor_mpv_daemon.md`).
- Suite de tests para `MpvPlayer` en `tests/test_player.py`: 14 casos de prueba que cubren reproducción exitosa, archivo inexistente, fallo de mpv, borrado garantizado tras `process.wait()`, comportamiento de SIGTERM/SIGKILL y ciclo de vida del servicio.

### Cambiado

- `src/player.py`: refactor completo. Se sustituye `AudioPlayerWorker` (hilo consumidor con `queue.Queue` y `subprocess.run` bloqueante) por `MpvPlayer` (arquitectura proceso-por-reproducción con semántica *last sound wins*). Cuando llega un nuevo archivo, el proceso `mpv` en curso recibe SIGTERM (SIGKILL de respaldo a los 2 s) y se lanza uno nuevo. El archivo se borra en un hilo daemon (`MpvWaiter`) que espera `process.wait()`, evitando la condición de carrera donde el `unlink` ocurría antes de que `mpv` abriese el fichero.
- `src/watcher.py`: `AudioFolderHandler` recibe ahora un `player` (`MpvPlayer`) en lugar de `audio_queue` (`queue.Queue`). Llama a `player.play(filepath)` directamente tras estabilizar el archivo.
- `src/main.py`: eliminada la creación de `queue.Queue` y la gestión del hilo consumidor. `MpvPlayer` se inicializa y se pasa directamente al `AudioFolderHandler`.
- `tests/test_watcher.py`: actualizado para usar un mock de `MpvPlayer` como colaborador del handler en lugar de `queue.Queue`.
- `README.md`: descripción, diagrama de arquitectura y buenas prácticas actualizados para reflejar la nueva arquitectura.

### Eliminado

- Clase `AudioPlayerWorker` y toda la lógica asociada: `queue.Queue`, hilo consumidor (`threading.Thread`), patrón Productor-Consumidor y `subprocess.run` síncrono por cada archivo de audio.

## [1.0.0] - 2026-05-31

### Añadido

- Fichero CONTRIBUTING.md con el flujo de trabajo Trunk Based Development, convenciones de commits, guía de Pull Requests y buenas prácticas para desarrollo asistido con IA.
- Fichero CHANGELOG.md con el formato Keep a Changelog v1.1.0 en castellano.
- Fichero README.md con la descripción completa del proyecto, arquitectura de la cola secuencial de reproducción, guía de instalación de servicio de usuario de systemd y buenas prácticas.
- Fichero `requirements.txt` con dependencias `watchdog>=4.0.0` y `python-dotenv>=1.0.1`.
- Fichero `.env.example` con plantilla de configuración de variables de entorno (`WATCHDOG_DIR`, `LOG_LEVEL`, `MPV_PATH`).
- Módulo `src/config.py`: carga y validación de variables de entorno; crea el directorio vigilado si no existe.
- Módulo `src/watcher.py`: manejador reactivo de eventos de sistema de archivos (`AudioFolderHandler`) con filtrado por extensión `.wav` y comprobación de estabilidad de archivo antes de encolar.
- Módulo `src/player.py`: hilo consumidor thread-safe (`AudioPlayerWorker`) con cola FIFO secuencial, reproducción mediante subproceso `mpv` y eliminación garantizada del archivo tras reproducción, exitosa o fallida.
- Módulo `src/main.py`: punto de entrada del servicio con configuración de logging hacia `journald`, orquestación de hilos y apagado ordenado (graceful shutdown) ante señales `SIGINT`/`SIGTERM`.
- Suite de pruebas unitarias en `tests/`: `test_player.py` y `test_watcher.py` con 9 casos de prueba, cobertura de escenarios exitosos, errores de `mpv` y timeouts de estabilización.
- Pipeline de CI en `.github/workflows/ci.yml`: ejecuta los tests unitarios automáticamente en cada Pull Request dirigida a `main` mediante GitHub Actions (Python 3.11, `unittest discover`).

--

<!-- Plantilla para nuevas versiones:

## [X.Y.Z] - AAAA-MM-DD

### Añadido
-

### Cambiado
-

### Obsoleto
-

### Eliminado
-

### Corregido
-

### Seguridad
-

-->

[Sin publicar]: https://github.com/danuser2018/speaker-watchdog/compare/HEAD...HEAD
