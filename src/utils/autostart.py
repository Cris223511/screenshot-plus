"""arranque automático junto con windows.

la forma estándar y sin permisos de administrador es una entrada en la clave
Run del registro del usuario actual. la ruta que se registra depende de cómo
corre la app: el .exe empaquetado se apunta a sí mismo, y en desarrollo se
registra el intérprete de python con el main.py.
"""

import os
import sys
import winreg

_CLAVE = r"Software\Microsoft\Windows\CurrentVersion\Run"
_NOMBRE = "ScreenshotPlus"


def _comando() -> str:
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}"'
    principal = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "main.py"))
    return f'"{sys.executable}" "{principal}"'


def enable():
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _CLAVE, 0, winreg.KEY_SET_VALUE) as clave:
            winreg.SetValueEx(clave, _NOMBRE, 0, winreg.REG_SZ, _comando())
    except OSError:
        pass


def disable():
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _CLAVE, 0, winreg.KEY_SET_VALUE) as clave:
            winreg.DeleteValue(clave, _NOMBRE)
    except OSError:
        # la entrada puede no existir, y eso ya es el estado deseado
        pass


def is_enabled() -> bool:
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _CLAVE, 0, winreg.KEY_READ) as clave:
            winreg.QueryValueEx(clave, _NOMBRE)
        return True
    except OSError:
        return False


def sync(activado: bool):
    """deja el registro alineado con lo que el usuario marcó en opciones."""
    if activado:
        enable()
    else:
        disable()
