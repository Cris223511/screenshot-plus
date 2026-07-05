"""los elementos que el usuario dibuja sobre una captura.

cada anotación (una flecha, un texto, un pixelado) es un objeto que sabe
pintarse, decir si un punto del mouse le pertenece, moverse y entregar sus
tiradores de redimensión. el overlay solo mantiene la lista y delega en
cada elemento, de modo que sumar una forma nueva es una clase más en este
módulo y una entrada en el menú.

todas las coordenadas van en píxeles lógicos de pantalla; al exportar, el
overlay escala el pintor y estos mismos objetos quedan bien ubicados sobre
la imagen a resolución nativa.
"""

import math

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (QColor, QFont, QFontMetricsF, QImage, QPainter,
                           QPainterPath, QPainterPathStroker, QPen, QPolygonF)

# margen de tolerancia al hacer clic sobre un trazo; sin él, acertarle a
# una línea de dos píxeles sería un suplicio
_TOLERANCIA = 6.0

# estilos de trazo disponibles para formas y líneas
DASHES = {"solid": Qt.SolidLine, "dashed": Qt.DashLine, "dotted": Qt.DotLine}

# remates posibles en los extremos de una línea o flecha
CAPS = ("none", "arrow", "arrow_filled", "dot", "square", "diamond")


def _trazo_ancho(camino: QPainterPath, ancho: float) -> QPainterPath:
    """versión engordada de un camino, para detectar clics cómodamente."""
    stroker = QPainterPathStroker()
    stroker.setWidth(max(ancho + _TOLERANCIA * 2, _TOLERANCIA * 2))
    return stroker.createStroke(camino)


class Item:
    """base común de todas las anotaciones."""

    def __init__(self, color: QColor, width: float):
        self.color = QColor(color)
        self.width = width
        self.dash = "solid"

    def paint(self, p: QPainter):
        raise NotImplementedError

    def path(self) -> QPainterPath:
        raise NotImplementedError

    def contains(self, punto: QPointF) -> bool:
        return _trazo_ancho(self.path(), self.width).contains(punto)

    def move_by(self, dx: float, dy: float):
        raise NotImplementedError

    def handles(self) -> list[QPointF]:
        """puntos de agarre para redimensionar; una lista vacía significa
        que el elemento solo se mueve, como un trazo de pincel."""
        return []

    def set_handle(self, indice: int, pos: QPointF):
        pass

    def bounding(self) -> QRectF:
        return self.path().boundingRect().adjusted(-_TOLERANCIA, -_TOLERANCIA, _TOLERANCIA, _TOLERANCIA)

    def _pen(self) -> QPen:
        return QPen(self.color, self.width, DASHES.get(self.dash, Qt.SolidLine), Qt.RoundCap, Qt.RoundJoin)


class ShapeItem(Item):
    """base de las formas definidas por un rectángulo: los tiradores son
    las cuatro esquinas y los cuatro puntos medios."""

    def __init__(self, rect: QRectF, color: QColor, width: float):
        super().__init__(color, width)
        self.rect = QRectF(rect)

    def move_by(self, dx, dy):
        self.rect.translate(dx, dy)

    def handles(self):
        r = self.rect
        return [r.topLeft(), QPointF(r.center().x(), r.top()), r.topRight(),
                QPointF(r.right(), r.center().y()), r.bottomRight(),
                QPointF(r.center().x(), r.bottom()), r.bottomLeft(),
                QPointF(r.left(), r.center().y())]

    def set_handle(self, indice, pos):
        # cada tirador ajusta el borde o la esquina que le corresponde; el
        # rectángulo se normaliza después por si el arrastre lo dio vuelta
        r = self.rect
        if indice == 0:
            r.setTopLeft(pos)
        elif indice == 1:
            r.setTop(pos.y())
        elif indice == 2:
            r.setTopRight(pos)
        elif indice == 3:
            r.setRight(pos.x())
        elif indice == 4:
            r.setBottomRight(pos)
        elif indice == 5:
            r.setBottom(pos.y())
        elif indice == 6:
            r.setBottomLeft(pos)
        elif indice == 7:
            r.setLeft(pos.x())
        self.rect = r.normalized()

    def paint(self, p):
        p.setPen(self._pen())
        p.setBrush(Qt.NoBrush)
        p.drawPath(self.path())

    def _poligono(self, puntos: list[QPointF]) -> QPainterPath:
        camino = QPainterPath()
        camino.addPolygon(QPolygonF(puntos + [puntos[0]]))
        return camino


class RectItem(ShapeItem):
    def path(self):
        camino = QPainterPath()
        camino.addRect(self.rect)
        return camino


class RoundedRectItem(ShapeItem):
    def path(self):
        camino = QPainterPath()
        radio = min(12.0, self.rect.width() / 4, self.rect.height() / 4)
        camino.addRoundedRect(self.rect, radio, radio)
        return camino


class EllipseItem(ShapeItem):
    def path(self):
        camino = QPainterPath()
        camino.addEllipse(self.rect)
        return camino


class TriangleItem(ShapeItem):
    def path(self):
        r = self.rect
        return self._poligono([QPointF(r.center().x(), r.top()), r.bottomRight(), r.bottomLeft()])


class DiamondItem(ShapeItem):
    def path(self):
        r = self.rect
        return self._poligono([QPointF(r.center().x(), r.top()),
                               QPointF(r.right(), r.center().y()),
                               QPointF(r.center().x(), r.bottom()),
                               QPointF(r.left(), r.center().y())])


class PentagonItem(ShapeItem):
    def path(self):
        return self._poligono(self._regular(5))

    def _regular(self, lados: int) -> list[QPointF]:
        # vértices de un polígono regular inscrito en el rectángulo, con la
        # punta hacia arriba; sirve para pentágono, hexágono y compañía
        r = self.rect
        cx, cy = r.center().x(), r.center().y()
        puntos = []
        for i in range(lados):
            angulo = -math.pi / 2 + i * 2 * math.pi / lados
            puntos.append(QPointF(cx + math.cos(angulo) * r.width() / 2,
                                  cy + math.sin(angulo) * r.height() / 2))
        return puntos


class HexagonItem(PentagonItem):
    def path(self):
        return self._poligono(self._regular(6))


class StarItem(ShapeItem):
    def path(self):
        # estrella de cinco puntas alternando radio externo e interno
        r = self.rect
        cx, cy = r.center().x(), r.center().y()
        puntos = []
        for i in range(10):
            angulo = -math.pi / 2 + i * math.pi / 5
            factor = 1.0 if i % 2 == 0 else 0.42
            puntos.append(QPointF(cx + math.cos(angulo) * r.width() / 2 * factor,
                                  cy + math.sin(angulo) * r.height() / 2 * factor))
        return self._poligono(puntos)


class LineItem(Item):
    """línea con remates configurables en cada extremo.

    una flecha clásica es esta misma clase con remate de flecha al final;
    poner un punto al inicio o flechas en ambos lados es solo cambiar los
    remates, sin clases nuevas.
    """

    def __init__(self, p1: QPointF, p2: QPointF, color: QColor, width: float,
                 cap_start: str = "none", cap_end: str = "none"):
        super().__init__(color, width)
        self.p1 = QPointF(p1)
        self.p2 = QPointF(p2)
        self.cap_start = cap_start
        self.cap_end = cap_end

    def path(self):
        camino = QPainterPath(self.p1)
        camino.lineTo(self.p2)
        return camino

    def move_by(self, dx, dy):
        self.p1 += QPointF(dx, dy)
        self.p2 += QPointF(dx, dy)

    def handles(self):
        return [self.p1, self.p2]

    def set_handle(self, indice, pos):
        if indice == 0:
            self.p1 = QPointF(pos)
        else:
            self.p2 = QPointF(pos)

    def paint(self, p):
        p.setPen(self._pen())
        p.drawLine(self.p1, self.p2)
        self._pintar_remate(p, self.p2, self.p1, self.cap_end)
        self._pintar_remate(p, self.p1, self.p2, self.cap_start)

    def _pintar_remate(self, p: QPainter, punta: QPointF, origen: QPointF, remate: str):
        if remate == "none":
            return
        # el remate se dibuja con trazo continuo aunque la línea sea
        # punteada, para que la punta se vea firme
        p.setPen(QPen(self.color, self.width, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        lado = max(8.0, self.width * 2.6)
        if remate in ("arrow", "arrow_filled"):
            angulo = math.atan2(punta.y() - origen.y(), punta.x() - origen.x())
            largo = max(11.0, self.width * 3.6)
            abertura = math.radians(26)
            a = QPointF(punta.x() - largo * math.cos(angulo - abertura),
                        punta.y() - largo * math.sin(angulo - abertura))
            b = QPointF(punta.x() - largo * math.cos(angulo + abertura),
                        punta.y() - largo * math.sin(angulo + abertura))
            if remate == "arrow_filled":
                p.setBrush(self.color)
                p.drawPolygon(QPolygonF([punta, a, b]))
                p.setBrush(Qt.NoBrush)
            else:
                p.drawLine(punta, a)
                p.drawLine(punta, b)
        elif remate == "dot":
            p.setBrush(self.color)
            p.drawEllipse(punta, lado / 2, lado / 2)
            p.setBrush(Qt.NoBrush)
        elif remate == "square":
            p.setBrush(self.color)
            p.drawRect(QRectF(punta.x() - lado / 2, punta.y() - lado / 2, lado, lado))
            p.setBrush(Qt.NoBrush)
        elif remate == "diamond":
            p.setBrush(self.color)
            p.drawPolygon(QPolygonF([QPointF(punta.x(), punta.y() - lado / 1.6),
                                     QPointF(punta.x() + lado / 1.6, punta.y()),
                                     QPointF(punta.x(), punta.y() + lado / 1.6),
                                     QPointF(punta.x() - lado / 1.6, punta.y())]))
            p.setBrush(Qt.NoBrush)


class BrushItem(Item):
    """trazo libre; guarda los puntos por los que pasó el mouse."""

    def __init__(self, inicio: QPointF, color: QColor, width: float):
        super().__init__(color, width)
        self.points = [QPointF(inicio)]

    def add_point(self, punto: QPointF):
        self.points.append(QPointF(punto))

    def path(self):
        camino = QPainterPath(self.points[0])
        for punto in self.points[1:]:
            camino.lineTo(punto)
        return camino

    def move_by(self, dx, dy):
        self.points = [p + QPointF(dx, dy) for p in self.points]

    def paint(self, p):
        p.setPen(self._pen())
        p.drawPath(self.path())


class TextItem(Item):
    """texto con su tipografía, tamaño, estilo y color."""

    def __init__(self, pos: QPointF, texto: str, fuente: QFont, color: QColor):
        super().__init__(color, 1)
        self.pos = QPointF(pos)
        self.text = texto
        self.font = QFont(fuente)

    def _rect(self) -> QRectF:
        medidas = QFontMetricsF(self.font)
        r = medidas.boundingRect(QRectF(0, 0, 10000, 10000), Qt.AlignLeft, self.text)
        return QRectF(self.pos, r.size())

    def path(self):
        camino = QPainterPath()
        camino.addRect(self._rect())
        return camino

    def contains(self, punto):
        # el rectángulo completo del texto responde al clic, no solo el
        # contorno; con letras finas sería imposible atinarle al trazo
        return self._rect().adjusted(-4, -4, 4, 4).contains(punto)

    def move_by(self, dx, dy):
        self.pos += QPointF(dx, dy)

    def paint(self, p):
        p.setFont(self.font)
        p.setPen(QPen(self.color))
        p.drawText(self._rect(), Qt.AlignLeft | Qt.TextDontClip, self.text)


class PixelateItem(ShapeItem):
    """mosaico que oculta una zona, pensado para tapar datos sensibles.

    el efecto se logra encogiendo la zona de la imagen original y volviendo
    a agrandarla sin suavizado; el tamaño del bloque sale del grosor elegido
    en la barra. la imagen fuente llega en resolución física, por eso el
    resultado no se degrada al exportar.
    """

    def __init__(self, rect: QRectF, fuente: QImage, dpr: float, block: int = 12):
        super().__init__(rect, QColor("#000000"), block)
        self._fuente = fuente
        self._dpr = dpr

    def contains(self, punto):
        return self.rect.contains(punto)

    def paint(self, p):
        r = self.rect.normalized()
        if r.width() < 2 or r.height() < 2:
            return
        fisico = QRectF(r.x() * self._dpr, r.y() * self._dpr,
                        r.width() * self._dpr, r.height() * self._dpr).toRect()
        recorte = self._fuente.copy(fisico)
        if recorte.isNull():
            return
        bloque = max(4, int(self.width))
        chica = recorte.scaled(max(1, recorte.width() // bloque), max(1, recorte.height() // bloque),
                               Qt.IgnoreAspectRatio, Qt.FastTransformation)
        pixelada = chica.scaled(recorte.size(), Qt.IgnoreAspectRatio, Qt.FastTransformation)
        p.drawImage(r, pixelada)


# catálogo de formas que ofrece el menú del editor: clave, ícono y clase
SHAPES = {
    "rect": ("shape-rect", RectItem),
    "rounded": ("shape-rounded", RoundedRectItem),
    "ellipse": ("shape-ellipse", EllipseItem),
    "triangle": ("shape-triangle", TriangleItem),
    "diamond": ("shape-diamond", DiamondItem),
    "pentagon": ("shape-pentagon", PentagonItem),
    "hexagon": ("shape-hexagon", HexagonItem),
    "star": ("shape-star", StarItem),
}
