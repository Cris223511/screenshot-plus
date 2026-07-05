"""copiado de capturas al portapapeles del sistema.

qt se encarga de registrar la imagen en los formatos que windows espera, de
modo que el pegado funciona igual en word, paint, un chat o el navegador.
"""

from PySide6.QtGui import QGuiApplication, QImage


def copy_image(imagen: QImage) -> bool:
    """la imagen queda disponible para pegar en cualquier aplicación."""
    if imagen.isNull():
        return False
    QGuiApplication.clipboard().setImage(imagen)
    return True
