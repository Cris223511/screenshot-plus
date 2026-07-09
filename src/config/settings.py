"""preferencias del usuario, persistidas en un json dentro de %APPDATA%.

el objeto es un singleton sencillo: cualquier módulo importa `settings` y lee
o escribe la misma instancia. cada cambio se guarda a disco de inmediato, así
un cierre inesperado no pierde nada.
"""

import json
import os

from src.config import paths

# valores con los que arranca la app la primera vez; el idioma por defecto
# es español y el tema claro, tal como está definido el producto
_DEFAULTS = {
    "language": "es",
    "theme": "light",
    "save_dir": "",              # vacío significa usar la carpeta imágenes por defecto
    "last_save_dir": "",         # la última carpeta donde el usuario guardó, se recuerda entre sesiones
    "image_format": "png",       # png o jpeg
    "jpeg_quality": 90,
    "autostart": False,
    "start_in_tray": False,      # arrancar directo a la bandeja, sin mostrar el panel
    "hide_main_on_capture": True,
    "show_notifications": True,
    "shortcuts": {},             # solo los atajos que el usuario cambió; el resto sale de shortcuts.py
    "laser_color": "#ff3b30",    # el puntero del modo presentación, a gusto de cada quien
    "laser_size": 14,
    "laser_trail": True,         # la estela que se desvanece detrás del láser
    "board_keys": {},            # letras personalizadas de las herramientas del panel
    "recent_colors": [],         # los últimos colores elegidos en el selector
    "confirm_discard_board": True,   # preguntar antes de perder lo dibujado en la pizarra
    "open_folder_after_save": False, # abrir el explorador señalando la captura guardada
    "board_master_key": ".",         # la tecla que enciende los atajos globales del panel
}


class Settings:
    def __init__(self):
        self._data = dict(_DEFAULTS)
        self._load()

    def _load(self):
        """lectura del json de preferencias, tolerante a archivos dañados.

        si el archivo no existe o está corrupto, la app arranca con los
        valores por defecto en lugar de fallar; el usuario no pierde la app
        por un json roto.
        """
        try:
            with open(paths.settings_file(), "r", encoding="utf-8") as f:
                guardado = json.load(f)
            for clave in _DEFAULTS:
                if clave in guardado:
                    self._data[clave] = guardado[clave]
        except (OSError, json.JSONDecodeError):
            pass

    def _save(self):
        try:
            with open(paths.settings_file(), "w", encoding="utf-8") as f:
                json.dump(self._data, f, ensure_ascii=False, indent=2)
        except OSError:
            # un disco lleno o sin permisos no debe tumbar la app; la
            # preferencia queda en memoria durante la sesión
            pass

    def get(self, clave, por_defecto=None):
        return self._data.get(clave, por_defecto)

    def set(self, clave, valor):
        self._data[clave] = valor
        self._save()

    def save_dir(self) -> str:
        """carpeta efectiva donde guardar capturas.

        la prioridad es: la última carpeta que el usuario usó, luego la que
        configuró en opciones, y al final la carpeta imágenes por defecto.
        si una carpeta recordada ya no existe (usb desconectado, carpeta
        borrada), se ignora y se sigue con la siguiente.
        """
        for candidata in (self._data["last_save_dir"], self._data["save_dir"]):
            if candidata and os.path.isdir(candidata):
                return candidata
        return paths.default_captures_dir()

    def remember_save_dir(self, carpeta: str):
        """después de cada guardado, la carpeta elegida pasa a ser la próxima en abrirse."""
        self.set("last_save_dir", carpeta)


# instancia compartida por toda la aplicación
settings = Settings()
