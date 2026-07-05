"""atajos de teclado globales, los que funcionan con la app en segundo plano.

pynput escucha el teclado en un hilo propio del sistema; desde ahí no se
puede tocar la interfaz, así que cada atajo emite una señal de qt, que llega
al hilo principal en forma de evento encolado. la interfaz reacciona segura
y el hilo del teclado nunca se bloquea.
"""

from pynput import keyboard
from PySide6.QtCore import QObject, Signal

from src.config import shortcuts


class HotkeyManager(QObject):
    # una señal por acción; la app conecta cada una con lo que corresponda
    capture_region = Signal()
    capture_fullscreen = Signal()
    capture_window = Signal()
    capture_scroll = Signal()
    zoom_mode = Signal()
    toggle_panel = Signal()

    def __init__(self):
        super().__init__()
        self._listener: keyboard.GlobalHotKeys | None = None

    def start(self):
        """registro de todos los atajos vigentes.

        el mapa se arma leyendo la configuración en ese momento, por eso
        después de cambiar un atajo en opciones basta con llamar restart.
        un atajo mal formado simplemente se omite; los demás siguen vivos.
        """
        mapa = {}
        acciones = {
            "capture_region": self.capture_region,
            "capture_fullscreen": self.capture_fullscreen,
            "capture_window": self.capture_window,
            "capture_scroll": self.capture_scroll,
            "zoom_mode": self.zoom_mode,
            "toggle_panel": self.toggle_panel,
        }
        for accion, senal in acciones.items():
            combinacion = shortcuts.to_pynput(shortcuts.get(accion))
            if combinacion:
                # el argumento por defecto fija la señal de esta vuelta del
                # bucle; sin él todas las entradas dispararían la última
                mapa[combinacion] = lambda s=senal: s.emit()
        try:
            self._listener = keyboard.GlobalHotKeys(mapa)
            self._listener.daemon = True
            self._listener.start()
        except Exception:
            # si el registro global falla (otro programa acaparó el hook),
            # la app sigue usable desde el panel y la bandeja
            self._listener = None

    def stop(self):
        if self._listener:
            self._listener.stop()
            self._listener = None

    def restart(self):
        """recarga de atajos tras un cambio en opciones."""
        self.stop()
        self.start()
