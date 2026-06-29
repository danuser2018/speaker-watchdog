# Refactor: Sustitución de cola FIFO por reproducción mediante mpv daemon + IPC

> [!WARNING]
> **PROPUESTA RECHAZADA / DEPRECADA**
> Esta propuesta de refactorización fue descartada tras comprobarse en entornos reales que el aislamiento de recursos y las políticas del sistema cortaban de manera automática los sockets Unix persistentes, dejando procesos huérfanos e inutilizables de `mpv`.
>
> De acuerdo con el [ADR-008: Modelo de Reproducción de Audio Física en speaker-watchdog](file:///home/danuser2018/workspace/home-assistant/docs/adr/adr-008.md), se mantiene de manera definitiva la arquitectura de procesos efímeros de `mpv` independientes lanzados por demanda con control mediante señales `SIGTERM`/`SIGKILL` de Python.

## Objetivo

Modificar `speaker-watchdog` para abandonar el modelo actual de reproducción secuencial basado en procesos `mpv` efímeros y una cola FIFO interna.

A partir de esta versión, el servicio utilizará una única instancia persistente de `mpv` ejecutándose en modo daemon con interfaz IPC mediante Unix Socket.

Cada nuevo archivo `.wav` detectado provocará una orden de reproducción mediante:

```json
{
  "command": ["loadfile", "<path>", "replace"]
}
```

El modo `replace` garantiza que cualquier sonido actualmente en reproducción será interrumpido inmediatamente y sustituido por el nuevo.

## Motivación

La arquitectura actual implementa una cola FIFO para evitar solapamientos sonoros.

Sin embargo, el caso de uso real del proyecto ha evolucionado:

* Los sonidos representan estados transitorios del sistema.
* El sonido más reciente siempre es más relevante que cualquier sonido anterior.
* No existe necesidad de reproducir todos los sonidos generados.
* No existe necesidad de mantener una cola de reproducción.

La política deseada es:

> El último sonido recibido reemplaza siempre al anterior.

Esto simplifica significativamente la arquitectura y elimina la necesidad de gestionar procesos de reproducción independientes.

---

## Nueva Arquitectura

### Arquitectura actual

```text
Watcher
   ↓
Queue FIFO
   ↓
Worker Thread
   ↓
mpv (proceso temporal)
   ↓
Eliminar archivo
```

### Nueva arquitectura

```text
Watcher
   ↓
Player
   ↓
mpv daemon (persistente)
   ↓ IPC socket
loadfile(..., replace)
   ↓
Eliminar archivo
```

---

## Cambios funcionales

### Eliminación de la cola FIFO

Eliminar:

* `queue.Queue`
* hilo consumidor dedicado
* lógica Productor/Consumidor
* espera bloqueante sobre la cola

Ya no es necesaria.

### Reproducción inmediata

Cada evento válido generado por `watchdog` deberá:

1. Esperar a que el archivo esté completamente escrito (comportamiento actual).
2. Enviar orden IPC a mpv.
3. Eliminar el archivo.
4. Continuar monitorizando.

---

## Gestión de mpv daemon

### Socket IPC

Definir una ruta fija:

```text
/tmp/speaker-watchdog.sock
```

### Arranque

Durante la inicialización del servicio:

1. Comprobar si existe el socket.
2. Verificar que responde.
3. Si no existe o no responde:

   * eliminar socket huérfano si existe
   * arrancar una nueva instancia de mpv

Comando recomendado:

```bash
mpv \
  --idle=yes \
  --no-video \
  --quiet \
  --input-ipc-server=/tmp/speaker-watchdog.sock
```

### Comportamiento esperado

* mpv permanece vivo aunque no reproduzca nada.
* el servicio no crea procesos mpv por cada audio.
* el socket IPC permanece disponible durante toda la vida del servicio.

---

## Protocolo IPC

Para reproducir un archivo:

```json
{
  "command": [
    "loadfile",
    "/ruta/audio.wav",
    "replace"
  ]
}
```

### Semántica

Si mpv está reproduciendo:

```text
audio_A.wav
```

y llega:

```text
audio_B.wav
```

el resultado será:

```text
audio_A.wav
(interrumpido)
↓
audio_B.wav
```

No existe cola.

No existe espera.

No existe reproducción secuencial.

---

## Eliminación de archivos

La eliminación debe producirse inmediatamente después de que la orden IPC haya sido aceptada por mpv.

No es necesario esperar a que finalice la reproducción.

Flujo:

```text
Detectar archivo
    ↓
Enviar loadfile(..., replace)
    ↓
Eliminar archivo
```

Esto es seguro porque mpv abre el fichero antes de comenzar la reproducción.

En Linux, eliminar el archivo no afecta al descriptor ya abierto.

---

## Tratamiento de errores

### Socket inexistente

Si el socket no existe:

1. Registrar warning.
2. Intentar recrear mpv daemon.
3. Reintentar la operación.

### Socket corrupto o colgado

Si la conexión IPC falla:

1. Registrar error.
2. Reiniciar mpv daemon.
3. Reintentar una vez.

### Archivo inválido

Mantener comportamiento actual:

* registrar error
* eliminar archivo
* continuar ejecución

---

## Impacto sobre la estructura del proyecto

### watcher.py

Cambios mínimos.

Sigue detectando archivos `.wav`.

### player.py

Refactor completo.

Responsabilidades:

* gestión del daemon mpv
* conexión IPC
* envío de comandos JSON
* recuperación automática ante fallos

### main.py

Sin cambios relevantes.

---

## Compatibilidad

La interfaz pública del sistema no cambia.

Los productores de audio continúan funcionando exactamente igual:

```text
Generar WAV
    ↓
Depositar WAV en WATCHDOG_DIR
```

No se requiere ninguna modificación en:

* InteractionManager
* TheaterManager
* otros productores de audio

El cambio es completamente transparente para los consumidores del servicio.

---

## Resultado esperado

Tras la implementación:

* no existe cola FIFO
* no existen procesos mpv efímeros
* existe una única instancia mpv persistente
* el sonido más reciente siempre reemplaza al anterior
* la interfaz basada en carpeta permanece intacta
* no se requieren cambios en otros componentes del ecosistema Nova

```
```
