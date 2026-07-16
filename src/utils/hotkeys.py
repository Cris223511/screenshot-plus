"""atajos de teclado globales, los que funcionan con la app en segundo plano.

pynput escucha el teclado en un hilo propio del sistema; desde ahí no se
puede tocar la interfaz, así que cada atajo emite una señal de qt, que llega
al hilo principal en forma de evento encolado. la interfaz reacciona segura
y el hilo del teclado nunca se bloquea.

la coincidencia es estricta: un atajo solo dispara si están pulsados
exactamente sus modificadores y su tecla, ni uno de más. así alt+a no salta
cuando en realidad se presionó ctrl+alt+a, ni cuando ya había otra tecla
apretada. se trabaja con el código de tecla virtual, que no cambia con el
idioma del teclado ni al tener alt sostenido.
"""

from pynput import keyboard
from PySide6.QtCore import QObject, Signal

from src.config import shortcuts

# cada tecla modificadora (izquierda, derecha o genérica) apunta a su nombre
_MOD_KEYS = {
    keyboard.Key.ctrl: "ctrl", keyboard.Key.ctrl_l: "ctrl", keyboard.Key.ctrl_r: "ctrl",
    keyboard.Key.alt: "alt", keyboard.Key.alt_l: "alt", keyboard.Key.alt_r: "alt",
    getattr(keyboard.Key, "alt_gr", keyboard.Key.alt): "alt",
    keyboard.Key.shift: "shift", keyboard.Key.shift_l: "shift", keyboard.Key.shift_r: "shift",
    keyboard.Key.cmd: "win", keyboard.Key.cmd_l: "win", keyboard.Key.cmd_r: "win",
}

# teclas especiales admitidas como tecla principal de un atajo
_ESPECIALES = {
    "space": keyboard.Key.space, "tab": keyboard.Key.tab, "esc": keyboard.Key.esc,
    "enter": keyboard.Key.enter, "home": keyboard.Key.home, "end": keyboard.Key.end,
    "insert": keyboard.Key.insert, "delete": keyboard.Key.delete,
    "page_up": keyboard.Key.page_up, "page_down": keyboard.Key.page_down,
    "up": keyboard.Key.up, "down": keyboard.Key.down, "left": keyboard.Key.left,
    "right": keyboard.Key.right, "print_screen": keyboard.Key.print_screen,
}

_NOMBRES_MOD = ("alt", "ctrl", "shift", "win")


def _parsear(combinacion: str):
    """convierte "alt+a" en (conjunto de modificadores, tecla principal).

    la tecla principal queda como ("vk", código) para las alfanuméricas o
    como ("key", Key) para las especiales. una combinación vacía o rara
    devuelve None y esa acción se queda sin atajo, sin romper las demás.
    """
    if not combinacion:
        return None
    mods = set()
    principal = None
    for pieza in combinacion.lower().split("+"):
        pieza = pieza.strip()
        if not pieza:
            return None
        if pieza in _NOMBRES_MOD:
            mods.add(pieza)
        elif len(pieza) == 1 and pieza.isalnum():
            # el vk de una letra o dígito es el ordinal de su mayúscula
            principal = ("vk", ord(pieza.upper()))
        elif pieza.startswith("f") and pieza[1:].isdigit():
            tecla = getattr(keyboard.Key, pieza, None)
            if tecla is None:
                return None
            principal = ("key", tecla)
        elif pieza in _ESPECIALES:
            principal = ("key", _ESPECIALES[pieza])
        else:
            return None
    if principal is None:
        return None
    return frozenset(mods), principal


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
        self._listener: keyboard.Listener | None = None
        self._atajos: list[tuple[frozenset, tuple, Signal]] = []
        self._mods_pulsados: set[str] = set()
        self._teclas_pulsadas: set = set()

    def start(self):
        """arma la lista de atajos vigentes leyendo la configuración actual.

        después de cambiar un atajo en opciones basta con llamar restart. la
        captura funciona en todo momento, incluso sobre juegos y navegadores
        a pantalla completa.
        """
        acciones = {
            "capture_region": self.capture_region,
            "capture_fullscreen": self.capture_fullscreen,
            "capture_window": self.capture_window,
            "capture_scroll": self.capture_scroll,
            "zoom_mode": self.zoom_mode,
            "toggle_panel": self.toggle_panel,
        }
        self._atajos = []
        for accion, senal in acciones.items():
            spec = _parsear(shortcuts.get(accion))
            if spec:
                self._atajos.append((spec[0], spec[1], senal))

        self._mods_pulsados = set()
        self._teclas_pulsadas = set()
        try:
            self._listener = keyboard.Listener(on_press=self._al_presionar,
                                               on_release=self._al_soltar)
            self._listener.daemon = True
            self._listener.start()
        except Exception:
            # si el registro global falla (otro programa acaparó el hook),
            # la app sigue usable desde el panel y la bandeja
            self._listener = None

    @staticmethod
    def _clave(tecla):
        """identificador estable de una tecla no modificadora."""
        vk = getattr(tecla, "vk", None)
        return ("vk", vk) if vk is not None else ("key", tecla)

    def _al_presionar(self, tecla):
        nombre_mod = _MOD_KEYS.get(tecla)
        if nombre_mod:
            self._mods_pulsados.add(nombre_mod)
            return

        # si ya había otra tecla no modificadora apretada, esta combinación no
        # cuenta; tampoco vuelve a dispararse por la repetición automática
        otra_pulsada = len(self._teclas_pulsadas) > 0
        self._teclas_pulsadas.add(self._clave(tecla))
        if otra_pulsada:
            return

        vk = getattr(tecla, "vk", None)
        for mods, principal, senal in self._atajos:
            if principal[0] == "vk":
                coincide = vk is not None and vk == principal[1]
            else:
                coincide = tecla == principal[1]
            if coincide and self._mods_pulsados == set(mods):
                senal.emit()
                return

    def _al_soltar(self, tecla):
        nombre_mod = _MOD_KEYS.get(tecla)
        if nombre_mod:
            self._mods_pulsados.discard(nombre_mod)
        else:
            self._teclas_pulsadas.discard(self._clave(tecla))

    def stop(self):
        if self._listener:
            self._listener.stop()
            self._listener = None
        self._mods_pulsados = set()
        self._teclas_pulsadas = set()

    def restart(self):
        """recarga de atajos tras un cambio en opciones."""
        self.stop()
        self.start()
