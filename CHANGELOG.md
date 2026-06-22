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

- `tests/test_player.py`: nueva suite completa para `MpvPlayer` (13 casos de prueba).

### Cambiado

- `src/player.py`: segunda refactorización. Se abandona la arquitectura basada en mpv daemon + IPC socket (causa raíz: AppArmor bloquea `bind()` de sockets Unix en mpv). Se introduce `MpvPlayer`: arquitectura proceso-por-reproducción con semántica *last sound wins* — cuando llega un nuevo archivo se termina el proceso mpv en curso (SIGTERM/SIGKILL) y se lanza uno nuevo. No requiere IPC, sockets ni FIFOs.
- `src/main.py`: actualizado para importar y usar `MpvPlayer` en lugar de `MpvDaemonPlayer`.
- `src/config.py`: eliminado el campo `mpv_socket_path` (ya no es necesario sin IPC).
- `.env.example`: eliminada la variable `MPV_SOCKET_PATH`.

### Eliminado

- Clase `MpvDaemonPlayer` y toda su infraestructura asociada: socket IPC, proceso daemon persistente, hilo `MpvStderrLogger`, lógica de reintento y reinicio del daemon.
- Variable de entorno `MPV_SOCKET_PATH`.

---

## [1.1.0] - 2026-06-21

### Añadido

- Documentación para realizar el refactor hacia mpv daemon (`docs/refactor_mpv_daemon.md`).
- Clase `MpvDaemonPlayer` en `src/player.py`: gestiona un proceso `mpv` persistente en modo idle con interfaz IPC mediante Unix socket (`/tmp/speaker-watchdog.sock`), recuperación automática ante fallos del daemon y lógica de reintento.
- Suite de tests para `MpvDaemonPlayer` en `tests/test_player.py`: 11 casos de prueba que cubren reproducción exitosa, archivo inexistente, reintento tras fallo de socket, borrado garantizado del archivo, comando IPC correcto, arranque y parada del daemon, y comportamiento de SIGTERM/SIGKILL.

### Cambiado

- `src/player.py`: refactor completo. Se sustituye `AudioPlayerWorker` (hilo consumidor con `queue.Queue` y procesos `mpv` efímeros) por `MpvDaemonPlayer` (instancia mpv persistente con control IPC). El nuevo comportamiento es: el último sonido recibido siempre reemplaza al anterior (`loadfile ... replace`), sin cola y sin espera.
- `src/watcher.py`: `AudioFolderHandler` recibe ahora un `player` (`MpvDaemonPlayer`) en lugar de `audio_queue` (`queue.Queue`). Llama a `player.play(filepath)` directamente tras estabilizar el archivo.
- `src/main.py`: eliminada la creación de `queue.Queue`. El `MpvDaemonPlayer` se inicializa y se pasa directamente al `AudioFolderHandler`.
- `tests/test_watcher.py`: actualizado para usar un mock de `MpvDaemonPlayer` como colaborador del handler en lugar de `queue.Queue`. Añadido test explícito para el caso de archivo no estabilizado.

### Corregido

- `src/player.py` (`_send_loadfile`): `FileNotFoundError` durante el intento de retry ya no dispara un nuevo `_restart_daemon()`, evitando un bucle infinito de reinicios del daemon.
- `src/player.py` (`_start_daemon`): la salida `stderr` de mpv ya no se suprime con `DEVNULL`; fluye a journald junto con los logs del servicio para facilitar el diagnóstico de fallos de arranque.
- `src/player.py` (`_start_daemon` y `_wait_for_socket`): se detecta muerte temprana del proceso mpv (antes de que el socket esté disponible) y se lanza `RuntimeError`, en lugar de continuar silenciosamente con el servicio en estado no funcional.

### Eliminado

- Clase `AudioPlayerWorker` y toda la lógica asociada: `queue.Queue`, hilo consumidor (`threading.Thread`), patrón Productor/Consumidor y espera bloqueante sobre la cola.

- Dependencia de `subprocess.run` síncrono por cada archivo de audio.

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
