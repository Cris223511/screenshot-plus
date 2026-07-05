"""guardado de capturas a disco con el formato y la carpeta del usuario.

el nombre de archivo se arma con la fecha y la hora para que nunca haya
colisiones y las capturas queden ordenadas cronológicamente en la carpeta.
"""

import os
from datetime import datetime

from PySide6.QtGui import QImage

from src.config.settings import settings


def suggested_filename() -> str:
    """nombre tipo captura_2026-07-05_14-30-12, legible y único."""
    marca = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    extension = "jpg" if settings.get("image_format") == "jpeg" else "png"
    return f"captura_{marca}.{extension}"


def suggested_path() -> str:
    """ruta completa propuesta en el diálogo de guardar: última carpeta usada más nombre nuevo."""
    return os.path.join(settings.save_dir(), suggested_filename())


def save_image(imagen: QImage, ruta: str) -> bool:
    """escritura de la imagen en disco respetando el formato elegido.

    para jpeg se aplica la calidad configurada en opciones; png va sin
    pérdida siempre. si el guardado sale bien, la carpeta usada pasa a ser
    la que se abra la próxima vez.
    """
    if imagen.isNull() or not ruta:
        return False
    extension = os.path.splitext(ruta)[1].lower()
    try:
        if extension in (".jpg", ".jpeg"):
            # jpeg no admite transparencia, así que cualquier zona alfa se
            # aplana sobre blanco antes de escribir
            ok = imagen.convertToFormat(QImage.Format_RGB32).save(ruta, "JPEG", settings.get("jpeg_quality", 90))
        else:
            ok = imagen.save(ruta, "PNG")
    except OSError:
        return False
    if ok:
        settings.remember_save_dir(os.path.dirname(ruta))
    return ok
