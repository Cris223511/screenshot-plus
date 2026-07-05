"""atajos de teclado globales de la aplicación.

acá viven los valores por defecto y la traducción al formato que entiende
pynput. el usuario puede cambiar cualquier atajo desde opciones; lo que
cambie se guarda en settings y pisa al valor por defecto.
"""

from src.config.settings import settings

DEFAULTS = {
    "capture_region": "alt+a",
    "capture_fullscreen": "alt+s",
    "capture_window": "alt+w",
    "capture_scroll": "alt+d",
    "zoom_mode": "alt+z",
    "toggle_panel": "alt+q",
}

# modificadores en el formato con corchetes angulares que usa pynput
_MODIFICADORES = {"alt": "<alt>", "ctrl": "<ctrl>", "shift": "<shift>", "win": "<cmd>"}


def get(accion: str) -> str:
    """atajo vigente para una acción, ya sea el personalizado o el de fábrica."""
    personalizados = settings.get("shortcuts", {})
    return personalizados.get(accion, DEFAULTS.get(accion, ""))


def set_shortcut(accion: str, combinacion: str):
    """el atajo se guarda normalizado en minúsculas y sin espacios."""
    personalizados = dict(settings.get("shortcuts", {}))
    personalizados[accion] = combinacion.lower().replace(" ", "")
    settings.set("shortcuts", personalizados)


def to_pynput(combinacion: str) -> str | None:
    """conversión de un atajo tipo "alt+a" al formato "<alt>+a" de pynput.

    las teclas de función y teclas especiales van entre corchetes angulares;
    una combinación vacía o irreconocible devuelve None y esa acción queda
    sin atajo en lugar de romper el registro de las demás.
    """
    if not combinacion:
        return None
    partes = []
    for pieza in combinacion.lower().split("+"):
        pieza = pieza.strip()
        if not pieza:
            return None
        if pieza in _MODIFICADORES:
            partes.append(_MODIFICADORES[pieza])
        elif len(pieza) == 1:
            partes.append(pieza)
        elif pieza.startswith("f") and pieza[1:].isdigit():
            partes.append(f"<{pieza}>")
        elif pieza in ("space", "tab", "esc", "enter", "home", "end", "insert", "delete",
                       "page_up", "page_down", "up", "down", "left", "right", "print_screen"):
            partes.append(f"<{pieza}>")
        else:
            return None
    return "+".join(partes)


def display(combinacion: str) -> str:
    """versión legible del atajo para mostrar en la interfaz, tipo "Alt + A"."""
    return " + ".join(p.strip().capitalize() for p in combinacion.split("+") if p.strip())
