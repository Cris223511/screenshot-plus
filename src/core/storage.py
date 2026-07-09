"""guardado de capturas a disco con el formato y la carpeta del usuario.

el nombre de archivo se arma con la fecha y la hora para que nunca haya
colisiones y las capturas queden ordenadas cronológicamente. la escritura
corre sobre pillow, que domina muchos más formatos que qt: desde png y
jpeg hasta webp, gif, avif, heic, ico o tga. los formatos modernos entran
gracias a sus plugins; si alguno faltara en el equipo, simplemente no se
ofrece en la lista.
"""

import os
from datetime import datetime

from PIL import Image
from PySide6.QtGui import QImage

from src.config.settings import settings

# los plugins de heif y avif se registran una vez; si no están
# instalados, esos formatos quedan fuera de la lista sin romper nada
_CON_HEIF = False
_CON_AVIF = False
try:
    import pillow_heif
    pillow_heif.register_heif_opener()
    _CON_HEIF = True
except ImportError:
    pass
try:
    import pillow_avif  # noqa: F401  (se registra solo al importarse)
    _CON_AVIF = True
except ImportError:
    pass

# cada formato: extensión de archivo, nombre para pillow y si comprime
# con pérdida (los que sí, respetan la calidad elegida en opciones)
_CATALOGO = {
    "png": ("png", "PNG", False),
    "jpg": ("jpg", "JPEG", True),
    "jpeg": ("jpeg", "JPEG", True),
    "jfif": ("jfif", "JPEG", True),
    "webp": ("webp", "WEBP", True),
    "gif": ("gif", "GIF", False),
    "avif": ("avif", "AVIF", True),
    "bmp": ("bmp", "BMP", False),
    "tiff": ("tiff", "TIFF", False),
    "tif": ("tif", "TIFF", False),
    "heic": ("heic", "HEIF", True),
    "heif": ("heif", "HEIF", True),
    "ico": ("ico", "ICO", False),
    "tga": ("tga", "TGA", False),
}

# sin transparencia: estos formatos aplanan el alfa sobre blanco
_SIN_ALFA = {"JPEG", "BMP"}


def available_formats() -> dict:
    """el catálogo filtrado a lo que este equipo puede escribir."""
    disponibles = {}
    for clave, (ext, pil, con_perdida) in _CATALOGO.items():
        if pil == "HEIF" and not _CON_HEIF:
            continue
        if pil == "AVIF" and not _CON_AVIF:
            continue
        disponibles[clave] = (ext, pil, con_perdida)
    return disponibles


def is_lossy(clave: str) -> bool:
    return _CATALOGO.get(clave, ("", "", False))[2]


def suggested_filename() -> str:
    """nombre tipo captura_2026-07-05_14-30-12, legible y único."""
    marca = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    extension = _CATALOGO.get(settings.get("image_format"), ("png",))[0]
    return f"captura_{marca}.{extension}"


def suggested_path() -> str:
    """ruta completa propuesta en el diálogo de guardar: última carpeta usada más nombre nuevo."""
    return os.path.join(settings.save_dir(), suggested_filename())


def _a_pillow(imagen: QImage) -> Image.Image:
    """conversión de la imagen de qt al formato de pillow, sin pérdida."""
    convertida = imagen.convertToFormat(QImage.Format_ARGB32)
    crudo = bytes(convertida.constBits())
    return Image.frombuffer("RGBA", (convertida.width(), convertida.height()),
                            crudo, "raw", "BGRA", convertida.bytesPerLine(), 1)


def save_image(imagen: QImage, ruta: str) -> bool:
    """escritura de la imagen respetando el formato de la extensión.

    la extensión del archivo decide el formato real; los que comprimen
    con pérdida usan la calidad configurada en opciones. si el guardado
    sale bien, la carpeta usada pasa a ser la que se abra la próxima vez.
    """
    if imagen.isNull() or not ruta:
        return False
    extension = os.path.splitext(ruta)[1].lower().lstrip(".")
    entrada = next((v for v in _CATALOGO.values() if v[0] == extension), None)
    if entrada is None:
        entrada = ("png", "PNG", False)
    _ext, formato_pil, con_perdida = entrada

    try:
        lienzo = _a_pillow(imagen)
        if formato_pil in _SIN_ALFA:
            fondo = Image.new("RGB", lienzo.size, (255, 255, 255))
            fondo.paste(lienzo, mask=lienzo.split()[3])
            lienzo = fondo
        opciones = {}
        if con_perdida:
            opciones["quality"] = settings.get("jpeg_quality", 90)
        if formato_pil == "ICO":
            # el ico guarda varias resoluciones para que windows elija
            lado = min(256, max(lienzo.size))
            opciones["sizes"] = [(s, s) for s in (16, 32, 48, 64, 128, 256) if s <= lado] or [(lado, lado)]
        lienzo.save(ruta, formato_pil, **opciones)
    except (OSError, ValueError):
        return False

    settings.remember_save_dir(os.path.dirname(ruta))
    return True
