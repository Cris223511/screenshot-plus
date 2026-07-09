"""carga de los íconos svg pintados con el color del tema activo.

los svg de assets/icons usan currentColor como color de trazo; acá se lee el
archivo, se reemplaza ese marcador por el color que pida la interfaz y se
rasteriza al vuelo. cada combinación de ícono, color y tamaño se cachea
porque los overlays piden los mismos íconos muchas veces.
"""

import os

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QIcon, QImage, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

from src.config import paths

_cache: dict[tuple, QIcon] = {}


def rounded_logo(lado: int) -> QPixmap:
    """el logo recortado en un cuadrado de esquinas redondeadas.

    lo usan el panel principal, el acerca de y el manual, para que la
    imagen se integre igual en todos lados, sin marcos duros.
    """
    original = QPixmap(paths.resource_path(os.path.join("assets", "logo", "logo.jpg")))
    escalado = original.scaled(lado * 2, lado * 2, Qt.KeepAspectRatioByExpanding,
                               Qt.SmoothTransformation)
    salida = QPixmap(lado * 2, lado * 2)
    salida.fill(Qt.transparent)
    pintor = QPainter(salida)
    pintor.setRenderHint(QPainter.Antialiasing)
    from PySide6.QtGui import QPainterPath
    mascara = QPainterPath()
    mascara.addRoundedRect(QRectF(0, 0, lado * 2, lado * 2), lado * 0.55, lado * 0.55)
    pintor.setClipPath(mascara)
    pintor.drawPixmap(0, 0, escalado)
    pintor.end()
    salida.setDevicePixelRatio(2.0)
    return salida


def icon(nombre: str, color: str, tamano: int = 20) -> QIcon:
    """ícono listo para usar en botones y menús.

    el rasterizado se hace al doble de resolución y se marca el factor de
    escala, así los íconos se ven nítidos en pantallas con escalado alto.
    """
    llave = (nombre, color, tamano)
    if llave in _cache:
        return _cache[llave]

    ruta = paths.resource_path(os.path.join("assets", "icons", f"{nombre}.svg"))
    try:
        with open(ruta, "r", encoding="utf-8") as f:
            contenido = f.read().replace("currentColor", color)
    except OSError:
        _cache[llave] = QIcon()
        return _cache[llave]

    lado = tamano * 2
    imagen = QImage(lado, lado, QImage.Format_ARGB32)
    imagen.fill(Qt.transparent)
    pintor = QPainter(imagen)
    pintor.setRenderHint(QPainter.Antialiasing)
    QSvgRenderer(contenido.encode("utf-8")).render(pintor, QRectF(0, 0, lado, lado))
    pintor.end()

    pixmap = QPixmap.fromImage(imagen)
    pixmap.setDevicePixelRatio(2.0)
    _cache[llave] = QIcon(pixmap)
    return _cache[llave]
