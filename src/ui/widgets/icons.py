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


def _pixmap_logo(archivo: str, lado: int, radio: float | None = None) -> QPixmap:
    """el logo escalado a un cuadrado de `lado` píxeles.

    se dibuja al doble de resolución para que se vea nítido en pantallas con
    escalado. con un radio se recorta en esquinas redondeadas, y sin él se
    respeta la forma original del archivo, que es lo que necesita el logo
    circular: ya viene recortado y con su fondo transparente.
    """
    original = QPixmap(paths.resource_path(os.path.join("assets", "logo", archivo)))
    tam = lado * 2
    salida = QPixmap(tam, tam)
    salida.fill(Qt.transparent)
    pintor = QPainter(salida)
    pintor.setRenderHint(QPainter.Antialiasing)
    pintor.setRenderHint(QPainter.SmoothPixmapTransform)
    if radio is None:
        escalado = original.scaled(tam, tam, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        pintor.drawPixmap((tam - escalado.width()) // 2, (tam - escalado.height()) // 2, escalado)
    else:
        escalado = original.scaled(tam, tam, Qt.KeepAspectRatioByExpanding,
                                   Qt.SmoothTransformation)
        from PySide6.QtGui import QPainterPath
        mascara = QPainterPath()
        mascara.addRoundedRect(QRectF(0, 0, tam, tam), tam * radio, tam * radio)
        pintor.setClipPath(mascara)
        pintor.drawPixmap(0, 0, escalado)
    pintor.end()
    salida.setDevicePixelRatio(2.0)
    return salida


def rounded_logo(lado: int) -> QPixmap:
    """el logo circular, que es el que se ve en toda la aplicación.

    lo usan el acerca de, el manual y la ventana de versiones, además de los
    íconos de ventana y de la bandeja, para que la identidad sea la misma en
    todos lados.
    """
    return _pixmap_logo("logo-circle.png", lado)


def toolbar_logo(lado: int) -> QPixmap:
    """el logo completo, reservado a la barra del panel principal.

    ahí hay sitio para la versión cuadrada, que se recorta con esquinas
    redondeadas para acompañar al botón vecino sin puntas duras.
    """
    return _pixmap_logo("logo.png", lado, radio=0.28)


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
