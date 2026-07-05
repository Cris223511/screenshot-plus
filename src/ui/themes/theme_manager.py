"""aplicación del tema visual a toda la app.

cada tema es una hoja de estilos qss (el css de qt) más un par de colores
que los íconos y widgets pintados a mano necesitan conocer. al cambiar de
tema se recarga la hoja completa y se avisa por señal para que las ventanas
que dibujan íconos los pidan de nuevo con el color correcto.
"""

import os

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QApplication

from src.config import paths
from src.config.settings import settings

# colores que el código necesita fuera del qss: el trazo de los íconos, el
# acento azul tomado del logo y el fondo del panel, que se pinta a mano
_COLORES = {
    "light": {"icon": "#3d4451", "icon_active": "#2f7df6", "accent": "#2f7df6",
              "panel_bg": "#ffffff", "panel_border": "#dfe3ea"},
    "dark": {"icon": "#c9ccd4", "icon_active": "#5c9bff", "accent": "#5c9bff",
             "panel_bg": "#1b202b", "panel_border": "#2a3140"},
}


class ThemeManager(QObject):
    theme_changed = Signal(str)

    def __init__(self):
        super().__init__()
        self._tema = settings.get("theme", "light")
        if self._tema not in _COLORES:
            self._tema = "light"

    @property
    def theme(self) -> str:
        return self._tema

    def icon_color(self) -> str:
        return _COLORES[self._tema]["icon"]

    def icon_active_color(self) -> str:
        return _COLORES[self._tema]["icon_active"]

    def accent(self) -> str:
        return _COLORES[self._tema]["accent"]

    def panel_bg(self) -> str:
        return _COLORES[self._tema]["panel_bg"]

    def panel_border(self) -> str:
        return _COLORES[self._tema]["panel_border"]

    def apply(self):
        """carga del qss del tema activo sobre la aplicación entera."""
        ruta = paths.resource_path(os.path.join("src", "ui", "themes", f"{self._tema}.qss"))
        try:
            with open(ruta, "r", encoding="utf-8") as f:
                QApplication.instance().setStyleSheet(f.read())
        except OSError:
            # sin hoja de estilos la app funciona igual, solo que con el
            # aspecto por defecto de qt
            pass

    def set_theme(self, tema: str):
        if tema not in _COLORES or tema == self._tema:
            return
        self._tema = tema
        settings.set("theme", tema)
        self.apply()
        self.theme_changed.emit(tema)


theme = ThemeManager()
