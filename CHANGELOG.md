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

- Documentación para realizar el refactor hacia mpv daemon

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
