"""modelo de las anotaciones que se dibujan sobre una captura.

cada anotación (flecha, texto, forma, pixelado) es un objeto que sabe
pintarse, detectar si el mouse cae dentro, moverse y dar sus tiradores de
redimensión. los overlays solo mantienen la lista y delegan en cada
elemento, así que agregar una forma nueva es una clase más aquí. las
coordenadas van en píxeles lógicos y se escalan al exportar.
"""

import math

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (QColor, QFont, QFontMetricsF, QImage, QPainter,
                           QPainterPath, QPainterPathStroker, QPen, QPolygonF)

# margen de tolerancia al hacer clic sobre un trazo; sin él, acertarle a
# una línea de dos píxeles sería un suplicio
_TOLERANCIA = 6.0

# estilos de trazo disponibles para formas y líneas
DASHES = {"solid": Qt.SolidLine, "dashed": Qt.DashLine, "dotted": Qt.DotLine,
          "dashdot": Qt.DashDotLine, "dashdotdot": Qt.DashDotDotLine}

# remates posibles en los extremos de una línea o flecha
CAPS = ("none", "arrow", "arrow_filled", "dot", "square", "diamond")

# valores por defecto de las opciones de las herramientas de ocultar y borrar.
# a diferencia de la configuración del programa, estas no se guardan a disco:
# arrancan siempre igual y se reinician en cada sesión
PIXEL_MODO = "pixelate"      # pixelate o blur
PIXEL_CANTIDAD = 12          # intensidad del efecto
PIXEL_GROSOR = 30            # grosor del pincel de ocultar
BORRADOR_GROSOR = 30         # grosor del borrador


def _trazo_ancho(camino: QPainterPath, ancho: float) -> QPainterPath:
    """versión engordada de un camino, para detectar clics cómodamente."""
    stroker = QPainterPathStroker()
    stroker.setWidth(max(ancho + _TOLERANCIA * 2, _TOLERANCIA * 2))
    return stroker.createStroke(camino)


def paint_item(p: QPainter, item: "Item"):
    """pinta un elemento respetando su opacidad, sin ensuciar el pintor."""
    p.save()
    p.setOpacity(p.opacity() * item.opacity)
    item.paint(p)
    p.restore()


class Item:
    """base común de todas las anotaciones."""

    def __init__(self, color: QColor, width: float):
        self.color = QColor(color)
        self.width = width
        self.dash = "solid"
        self.opacity = 1.0

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
        # sin brush explícito, un trazo que se cruza consigo mismo rellenaría
        # sus lazos con lo que quedara puesto en el pintor; el pincel solo traza
        p.setPen(self._pen())
        p.setBrush(Qt.NoBrush)
        p.drawPath(self.path())


class TextItem(Item):
    """texto con estilo completo: tipografía, tamaño, negrita, cursiva,
    subrayado, tachado, espaciado de letras, rotación, fondo con o sin
    esquinas redondeadas, sombra y contorno."""

    def __init__(self, pos: QPointF, texto: str, fuente: QFont, color: QColor):
        super().__init__(color, 1)
        self.pos = QPointF(pos)
        self.text = texto
        self.font = QFont(fuente)
        self.rotation = 0.0            # grados, alrededor del centro
        self.bg = "none"               # none | solid | rounded
        self.bg_color = QColor("#ffffff")
        self.shadow = False
        self.outline = False

    def _rect(self) -> QRectF:
        medidas = QFontMetricsF(self.font)
        r = medidas.boundingRect(QRectF(0, 0, 10000, 10000), Qt.AlignLeft, self.text)
        return QRectF(self.pos, r.size())

    def _al_plano(self, punto: QPointF) -> QPointF:
        """lleva un punto de pantalla al sistema del texto sin rotar."""
        if not self.rotation:
            return QPointF(punto)
        centro = self._rect().center()
        angulo = math.radians(-self.rotation)
        dx, dy = punto.x() - centro.x(), punto.y() - centro.y()
        return QPointF(centro.x() + dx * math.cos(angulo) - dy * math.sin(angulo),
                       centro.y() + dx * math.sin(angulo) + dy * math.cos(angulo))

    def path(self):
        camino = QPainterPath()
        camino.addRect(self._rect())
        return camino

    def contains(self, punto):
        # el rectángulo completo del texto responde al clic, no solo el
        # contorno; la rotación se compensa girando el punto al revés
        return self._rect().adjusted(-4, -4, 4, 4).contains(self._al_plano(punto))

    def move_by(self, dx, dy):
        self.pos += QPointF(dx, dy)

    def handles(self):
        r = self._rect()
        return [r.topLeft(), r.topRight(), r.bottomRight(), r.bottomLeft()]

    def set_handle(self, indice, pos):
        """estirar una esquina agranda o achica la letra.

        el ancla es la esquina opuesta; el alto del rectángulo resultante
        define el nuevo tamaño en puntos, con un piso para no perder el
        texto de vista.
        """
        r = self._rect()
        anclas = [r.bottomRight(), r.bottomLeft(), r.topLeft(), r.topRight()]
        nuevo = QRectF(anclas[indice], pos).normalized()
        if nuevo.height() < 10:
            return
        self.pos = nuevo.topLeft()
        self.font.setPointSizeF(max(6.0, nuevo.height() * 0.62))

    def paint(self, p):
        r = self._rect()
        p.save()
        if self.rotation:
            centro = r.center()
            p.translate(centro)
            p.rotate(self.rotation)
            p.translate(-centro)
        if self.bg != "none":
            caja = r.adjusted(-7, -4, 7, 4)
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(self.bg_color))
            radio = 8 if self.bg == "rounded" else 0
            p.drawRoundedRect(caja, radio, radio)
        if self.shadow:
            # la sombra es el mismo texto corrido en diagonal, translúcido
            p.setFont(self.font)
            p.setPen(QColor(0, 0, 0, 130))
            p.drawText(r.translated(2, 2), Qt.AlignLeft | Qt.TextDontClip, self.text)
        if self.outline:
            # el contorno se dibuja trazando la silueta de las letras con
            # un tono que contraste contra el propio color del texto
            medidas = QFontMetricsF(self.font)
            camino = QPainterPath()
            camino.addText(r.left(), r.top() + medidas.ascent(), self.font, self.text)
            contraste = QColor("#ffffff") if self.color.lightness() < 128 else QColor("#111111")
            p.setPen(QPen(contraste, max(2.0, self.font.pointSizeF() / 8)))
            p.setBrush(Qt.NoBrush)
            p.drawPath(camino)
            p.fillPath(camino, self.color)
        else:
            p.setFont(self.font)
            p.setPen(QPen(self.color))
            p.drawText(r, Qt.AlignLeft | Qt.TextDontClip, self.text)
        p.restore()


class PixelateItem(Item):
    """oculta a mano alzada: se pinta un trazo y bajo él la imagen queda
    pixelada o difuminada, según el modo elegido.

    el trazo se guarda como puntos con un grosor de pincel, igual que el
    lápiz, pero en vez de tinta deja el efecto. el efecto se logra
    encogiendo el recorte de la imagen y volviéndolo a agrandar: sin
    suavizado da el mosaico del pixelado, con suavizado el difuminado. la
    cantidad controla cuánto se encoge. mientras se pinta se muestra un
    contorno azul para que se vea dónde va cayendo el efecto.
    """

    def __init__(self, inicio: QPointF, fuente: QImage, dpr: float,
                 mode: str = "pixelate", amount: int = 12, brush: int = 30):
        super().__init__(QColor("#2f7df6"), brush)
        self.points = [QPointF(inicio)]
        self._fuente = fuente
        self._dpr = dpr
        self.mode = mode        # pixelate | blur
        self.amount = amount    # intensidad del efecto
        self.editando = True    # mientras se pinta, se marca el trazo en azul

    def add_point(self, punto: QPointF):
        self.points.append(QPointF(punto))

    def _trazo(self) -> QPainterPath:
        camino = QPainterPath(self.points[0])
        for punto in self.points[1:]:
            camino.lineTo(punto)
        if len(self.points) == 1:
            # un solo punto no dibuja stroke; un segmento mínimo lo salva
            camino.lineTo(self.points[0] + QPointF(0.1, 0.1))
        stroker = QPainterPathStroker()
        stroker.setWidth(max(2.0, self.width))
        stroker.setCapStyle(Qt.RoundCap)
        stroker.setJoinStyle(Qt.RoundJoin)
        return stroker.createStroke(camino)

    def path(self):
        return self._trazo()

    def contains(self, punto):
        return self._trazo().contains(punto)

    def bounding(self):
        return self._trazo().boundingRect().adjusted(-2, -2, 2, 2)

    def move_by(self, dx, dy):
        self.points = [p + QPointF(dx, dy) for p in self.points]

    def handles(self):
        return []   # trazo libre, solo se mueve

    def paint(self, p):
        forma = self._trazo()
        if self.editando:
            # mientras el usuario arrastra solo se marca la zona en azul; el
            # efecto se aplica al soltar, cuando el trazo ya está definido
            tinta = QColor(self.color)
            tinta.setAlpha(90)
            p.fillPath(forma, tinta)
            return
        r = forma.boundingRect()
        if r.width() < 2 or r.height() < 2:
            return
        # el bloque mide la intensidad, en píxeles físicos de la fuente
        paso = max(2, int(self.amount))
        # la zona del trazo se alinea a una rejilla global anclada en el (0,0)
        # de la imagen. así dos trazos de la misma intensidad producen los
        # mismos bloques donde se cruzan: pasar el pincel de nuevo no acumula
        # ni oscurece, se ve igual; y si cambia la intensidad, manda el trazo
        # de encima porque se pinta después
        ax = int(math.floor(r.left() * self._dpr / paso)) * paso
        ay = int(math.floor(r.top() * self._dpr / paso)) * paso
        aw = max(paso, int(math.ceil(r.right() * self._dpr / paso)) * paso - ax)
        ah = max(paso, int(math.ceil(r.bottom() * self._dpr / paso)) * paso - ay)
        recorte = self._fuente.copy(ax, ay, aw, ah)
        if recorte.isNull():
            return
        # sin suavizado da el mosaico del pixelado; con suavizado, el difuminado
        filtro = Qt.FastTransformation if self.mode == "pixelate" else Qt.SmoothTransformation
        chica = recorte.scaled(max(1, aw // paso), max(1, ah // paso),
                               Qt.IgnoreAspectRatio, filtro)
        efecto = chica.scaled(recorte.size(), Qt.IgnoreAspectRatio, filtro)
        destino = QRectF(ax / self._dpr, ay / self._dpr,
                         aw / self._dpr, ah / self._dpr)
        p.save()
        # se intersecta con el recorte que ya trae el pintor (la selección),
        # si no el efecto se saldría del contorno al reemplazarlo
        p.setClipPath(forma, Qt.IntersectClip)
        p.drawImage(destino, efecto)
        p.restore()


def snap_45(fijo: QPointF, movil: QPointF) -> QPointF:
    """con shift, el punto arrastrado se alinea al ángulo guiado más
    cercano, en saltos de 15 grados.

    además de los ejes rectos y las diagonales clásicas, entran los
    ángulos intermedios (15, 30, 60, 75...), así una línea casi oblicua
    también encuentra su riel. se mide desde el extremo fijo.
    """
    delta = movil - fijo
    distancia = math.hypot(delta.x(), delta.y())
    if distancia < 1:
        return QPointF(movil)
    paso = math.pi / 12
    angulo = round(math.atan2(delta.y(), delta.x()) / paso) * paso
    return QPointF(fijo.x() + math.cos(angulo) * distancia,
                   fijo.y() + math.sin(angulo) * distancia)


def cuadrar_rect(origen: QPointF, actual: QPointF) -> QRectF:
    """con shift, la forma en creación sale proporcionada (cuadrado,
    círculo perfecto), respetando hacia qué lado se arrastra."""
    dx = actual.x() - origen.x()
    dy = actual.y() - origen.y()
    lado = max(abs(dx), abs(dy))
    return QRectF(origen, QPointF(origen.x() + math.copysign(lado, dx or 1),
                                  origen.y() + math.copysign(lado, dy or 1))).normalized()


def ajustar_aspecto(rect: QRectF, aspecto: float, indice: int) -> QRectF:
    """con shift al estirar, el rectángulo conserva su proporción.

    el alto se recalcula desde el ancho; el borde que se mantiene quieto
    depende de qué tirador se arrastra, para que la forma no salte.
    """
    if aspecto <= 0:
        return rect
    r = QRectF(rect)
    nueva_altura = r.width() / aspecto
    if indice in (0, 1, 2):
        r.setTop(r.bottom() - nueva_altura)
    else:
        r.setBottom(r.top() + nueva_altura)
    return r


def clonar(item: "Item") -> "Item":
    """copia independiente de un elemento, para duplicar con alt+arrastre.

    se parte de una copia superficial de los atributos escalares y luego
    se duplican a mano los objetos mutables (rectángulos, puntos, fuente),
    para que el clon no comparta geometría con el original. la imagen y la
    fuente de un pixelado sí se comparten a propósito: son de solo lectura.
    """
    import copy as _copy
    nuevo = _copy.copy(item)
    nuevo.color = QColor(item.color)
    if isinstance(item, ShapeItem):
        nuevo.rect = QRectF(item.rect)
    if isinstance(item, LineItem):
        nuevo.p1 = QPointF(item.p1)
        nuevo.p2 = QPointF(item.p2)
    if isinstance(item, (BrushItem, PixelateItem)):
        nuevo.points = [QPointF(p) for p in item.points]
    if isinstance(item, TextItem):
        nuevo.pos = QPointF(item.pos)
        nuevo.font = QFont(item.font)
        nuevo.bg_color = QColor(item.bg_color)
    return nuevo


def cursor_tirador(item: "Item", indice: int):
    """el cursor de redimensión que corresponde a cada tirador.

    las formas tienen ocho tiradores (esquinas y puntos medios) y cada uno
    apunta en su dirección; el texto tiene cuatro esquinas; las líneas dos
    extremos que solo se mueven. así el usuario ve la flechita correcta.
    """
    if isinstance(item, LineItem):
        return Qt.SizeAllCursor
    diag_principal = Qt.SizeFDiagCursor   # ↖↘
    diag_secundaria = Qt.SizeBDiagCursor  # ↗↙
    horizontal = Qt.SizeHorCursor
    vertical = Qt.SizeVerCursor
    if isinstance(item, TextItem):
        return [diag_principal, diag_secundaria, diag_principal, diag_secundaria][indice]
    # formas: esquinas y medios en el orden de ShapeItem.handles
    return [diag_principal, vertical, diag_secundaria, horizontal,
            diag_principal, vertical, diag_secundaria, horizontal][indice % 8]


def pintar_circulo_pincel(p: QPainter, centro: QPointF, grosor: float):
    """dibuja el contorno del cursor bajo el mouse, del tamaño del trazo.

    un anillo blanco fino con una sombra gris muy tenue por debajo, para que
    se vea sobre cualquier fondo sin ensuciar con negro. el radio es la mitad
    del grosor, así el círculo abarca justo lo que la herramienta cubrirá.
    """
    radio = max(1.0, grosor / 2)
    p.save()
    p.setBrush(Qt.NoBrush)
    p.setPen(QPen(QColor(120, 120, 120, 70), 2.0))
    p.drawEllipse(centro, radio, radio)
    p.setPen(QPen(QColor(255, 255, 255, 230), 1.0))
    p.drawEllipse(centro, radio, radio)
    p.restore()


def restringir_eje(delta: QPointF) -> QPointF:
    """con shift al mover, el desplazamiento se pega al eje más cercano.

    horizontal, vertical o diagonal de 45 grados: el elemento viaja recto
    aunque la mano tiemble. la magnitud es la proyección sobre ese eje,
    que es lo que se siente natural al arrastrar.
    """
    if abs(delta.x()) < 1 and abs(delta.y()) < 1:
        return QPointF(delta)
    paso = math.pi / 4
    angulo = round(math.atan2(delta.y(), delta.x()) / paso) * paso
    ux, uy = math.cos(angulo), math.sin(angulo)
    proyeccion = delta.x() * ux + delta.y() * uy
    return QPointF(ux * proyeccion, uy * proyeccion)


def escalar_texto(item: "TextItem", indice: int, pos: QPointF,
                  rect0: QRectF, tam0: float):
    """estira un texto desde una esquina con el ancla quieta.

    el ancla es la esquina opuesta del rectángulo tal como estaba al
    empezar el arrastre; calcular contra ese estado inicial (y no contra
    el rectángulo vivo) evita que el texto se corra siguiendo al mouse.
    """
    if rect0.height() <= 0:
        return
    # con el texto rotado, el punto del mouse se gira al plano del texto
    # para que la matemática del ancla siga funcionando
    pos = item._al_plano(pos)
    anclas = [rect0.bottomRight(), rect0.bottomLeft(),
              rect0.topLeft(), rect0.topRight()]
    ancla = anclas[indice]
    nuevo = QRectF(ancla, pos).normalized()
    if nuevo.height() < 10:
        return
    item.font.setPointSizeF(max(6.0, tam0 * (nuevo.height() / rect0.height())))
    # con el tamaño nuevo, el texto se reubica para que la esquina ancla
    # no se mueva ni un píxel
    lados = item._rect().size()
    if indice == 0:
        item.pos = QPointF(ancla.x() - lados.width(), ancla.y() - lados.height())
    elif indice == 1:
        item.pos = QPointF(ancla.x(), ancla.y() - lados.height())
    elif indice == 2:
        item.pos = QPointF(ancla)
    else:
        item.pos = QPointF(ancla.x() - lados.width(), ancla.y())


def snapshot(item: Item):
    """la geometría de un elemento, para poder deshacer un movimiento."""
    if isinstance(item, (BrushItem, PixelateItem)):
        return ("points", [QPointF(p) for p in item.points])
    if isinstance(item, LineItem):
        return ("line", QPointF(item.p1), QPointF(item.p2))
    if isinstance(item, TextItem):
        return ("text", QPointF(item.pos), item.font.pointSizeF())
    if isinstance(item, ShapeItem):
        return ("rect", QRectF(item.rect))
    return None


def restore(item: Item, estado):
    if estado is None:
        return
    tipo = estado[0]
    if tipo == "points":
        item.points = [QPointF(p) for p in estado[1]]
    elif tipo == "line":
        item.p1, item.p2 = QPointF(estado[1]), QPointF(estado[2])
    elif tipo == "text":
        item.pos = QPointF(estado[1])
        item.font.setPointSizeF(estado[2])
    elif tipo == "rect":
        item.rect = QRectF(estado[1])


class ImageItem(ShapeItem):
    """una imagen pegada encima, movible y estirable como cualquier forma."""

    def __init__(self, rect: QRectF, imagen: QImage):
        super().__init__(rect, QColor("#000000"), 1)
        self.image = imagen

    def path(self):
        # el contorno rectangular es lo que permite pintar la selección de
        # la imagen y mostrar sus tiradores
        camino = QPainterPath()
        camino.addRect(self.rect)
        return camino

    def contains(self, punto):
        return self.rect.contains(punto)

    def paint(self, p):
        p.drawImage(self.rect, self.image)


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
