"""arranque automático junto con windows.

se usan dos vías a la vez para que sea fiable con un ejecutable portable y sin
firma: una entrada en la clave Run del registro del usuario y un acceso directo
en la carpeta de inicio de windows. además se retira del propio ejecutable la
marca de "descargado de internet", que es la que dispara el aviso de SmartScreen
y puede impedir que el arranque automático corra sin que nadie acepte el aviso.

la ruta que se registra depende de cómo corre la app: el .exe empaquetado se
apunta a sí mismo, y en desarrollo se registra el intérprete de python con el
main.py.
"""

import os
import sys
import winreg

_CLAVE = r"Software\Microsoft\Windows\CurrentVersion\Run"
_NOMBRE = "ScreenshotPlus"


# la bandera avisa que la app arrancó sola con windows; con ella se queda en
# la bandeja sin mostrar el panel, sin importar la configuración de inicio
ARG_BANDEJA = "--tray"


def _es_frozen() -> bool:
    return getattr(sys, "frozen", False)


def _comando() -> str:
    if _es_frozen():
        return f'"{sys.executable}" {ARG_BANDEJA}'
    principal = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "main.py"))
    return f'"{sys.executable}" "{principal}" {ARG_BANDEJA}'


def _ruta_acceso() -> str:
    inicio = os.path.join(os.environ.get("APPDATA", ""), "Microsoft", "Windows",
                          "Start Menu", "Programs", "Startup")
    return os.path.join(inicio, f"{_NOMBRE}.lnk")


def _crear_acceso_directo():
    """acceso directo en la carpeta de inicio, apuntando al exe con la bandera
    de bandeja. solo tiene sentido con el ejecutable empaquetado."""
    if not _es_frozen():
        return
    try:
        import pythoncom
        from win32com.client import Dispatch
        try:
            pythoncom.CoInitialize()
        except Exception:
            pass
        shell = Dispatch("WScript.Shell")
        acceso = shell.CreateShortCut(_ruta_acceso())
        acceso.TargetPath = sys.executable
        acceso.Arguments = ARG_BANDEJA
        acceso.WorkingDirectory = os.path.dirname(sys.executable)
        acceso.WindowStyle = 7  # arranca minimizado
        acceso.save()
    except Exception:
        # si no se puede crear el acceso, la entrada del registro sigue
        pass


def _borrar_acceso_directo():
    try:
        ruta = _ruta_acceso()
        if os.path.exists(ruta):
            os.remove(ruta)
    except OSError:
        pass


def clear_web_mark():
    """quita la marca de "descargado de internet" del propio ejecutable.

    esa marca es un flujo alterno Zone.Identifier pegado al archivo; mientras
    está, SmartScreen puede frenar el arranque automático. borrarla del propio
    exe deja que se inicie con windows sin trabas. es inofensivo si no existe.
    """
    if not _es_frozen():
        return
    try:
        os.remove(sys.executable + ":Zone.Identifier")
    except OSError:
        pass


def enable():
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _CLAVE, 0, winreg.KEY_SET_VALUE) as clave:
            winreg.SetValueEx(clave, _NOMBRE, 0, winreg.REG_SZ, _comando())
    except OSError:
        pass
    _crear_acceso_directo()
    clear_web_mark()


def disable():
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _CLAVE, 0, winreg.KEY_SET_VALUE) as clave:
            winreg.DeleteValue(clave, _NOMBRE)
    except OSError:
        # la entrada puede no existir, y eso ya es el estado deseado
        pass
    _borrar_acceso_directo()


def is_enabled() -> bool:
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _CLAVE, 0, winreg.KEY_READ) as clave:
            winreg.QueryValueEx(clave, _NOMBRE)
        return True
    except OSError:
        return os.path.exists(_ruta_acceso())


def sync(activado: bool):
    """deja el arranque alineado con lo que el usuario marcó en opciones."""
    if activado:
        enable()
    else:
        disable()
