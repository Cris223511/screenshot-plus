"""rutas de la aplicación resueltas de forma segura para cualquier windows.

acá no existe ninguna ruta escrita a mano tipo c:\\users\\fulano, porque cada
equipo tiene su usuario, su disco y su idioma. todo se le pregunta al sistema:
la configuración vive en %APPDATA% y las capturas van a la carpeta imágenes
real del usuario, que windows conoce sin importar cómo se llame en su idioma.
"""

import ctypes
import ctypes.wintypes
import os
import sys

# identificador oficial de la carpeta imágenes en windows (known folder id),
# funciona igual en un sistema en español, inglés o japonés
_FOLDERID_PICTURES = "{33E28130-4E1E-4676-835A-98395C3BC3BB}"


def config_dir() -> str:
    """carpeta donde la app guarda su configuración y datos propios.

    %APPDATA% siempre existe en windows y es escribible sin permisos de
    administrador, por eso es el lugar correcto y no la carpeta del programa.
    """
    base = os.getenv("APPDATA") or os.path.expanduser("~")
    ruta = os.path.join(base, "ScreenshotPlus")
    os.makedirs(ruta, exist_ok=True)
    return ruta


def settings_file() -> str:
    """archivo json con las preferencias del usuario."""
    return os.path.join(config_dir(), "settings.json")


def _known_folder(folder_id: str) -> str | None:
    """consulta a windows la ruta real de una carpeta conocida.

    la api SHGetKnownFolderPath devuelve la ubicación aunque el usuario la
    haya movido de sitio, cosa que adivinar con expanduser no garantiza.
    """
    try:
        buf = ctypes.c_wchar_p()
        guid = ctypes.create_string_buffer(16)
        ctypes.oledll.ole32.CLSIDFromString(folder_id, guid)
        ctypes.windll.shell32.SHGetKnownFolderPath(guid, 0, None, ctypes.byref(buf))
        ruta = buf.value
        ctypes.windll.ole32.CoTaskMemFree(buf)
        return ruta
    except Exception:
        return None


def default_captures_dir() -> str:
    """carpeta por defecto donde se guardan las capturas.

    la primera opción es una subcarpeta propia dentro de imágenes; si por
    alguna razón el sistema no responde, se cae al perfil del usuario, que
    existe siempre. en ambos casos la carpeta se crea si no está.
    """
    imagenes = _known_folder(_FOLDERID_PICTURES) or os.path.join(os.path.expanduser("~"), "Pictures")
    ruta = os.path.join(imagenes, "Screenshot Plus")
    try:
        os.makedirs(ruta, exist_ok=True)
    except OSError:
        ruta = config_dir()
    return ruta


def resource_path(relativa: str) -> str:
    """ruta absoluta a un recurso empaquetado (logo, íconos, idiomas).

    cuando la app corre como .exe, pyinstaller descomprime los recursos en
    una carpeta temporal que expone en _MEIPASS; en desarrollo los recursos
    están junto al código, en la raíz del proyecto.
    """
    if hasattr(sys, "_MEIPASS"):
        base = sys._MEIPASS
    else:
        base = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    return os.path.join(base, relativa)
