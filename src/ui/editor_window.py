"""editor de imágenes ya capturadas, en una ventana con scroll.

recibe la imagen en una ventana normal (la captura larga puede medir miles
de píxeles de alto y no cabe en el overlay de pantalla) y ofrece la misma
barra de herramientas y anotaciones que el editor de capturas, más zoom para
verla completa o acercarse, y una herramienta de recorte. ctrl+c copia,
ctrl+s guarda, ctrl+z deshace; el resultado sale por señales.

el lienzo se dibuja escalado por el zoom: la imagen y las anotaciones viven
siempre en coordenadas reales de la imagen, y solo al pintar y al leer el
ratón se aplica el factor. así el recorte y la exportación trabajan sobre los
píxeles reales, sin importar cuánto se haya acercado la vista.
"""

import os

from PySide6.QtCore import QPointF, QRect, QRectF, QSize, Qt, QTimer, Signal
from PySide6.QtGui import (QColor, QFont, QGuiApplication, QIcon, QImage,
                           QKeySequence, QPainter, QPainterPath, QPen)
from PySide6.QtWidgets import (QHBoxLayout, QLabel, QLineEdit, QScrollArea,
                               QVBoxLayout, QWidget)

from src import APP_NAME
from src.config import paths
from src.i18n.translator import t
from src.ui.overlays import annotation_tools as an
from src.ui.overlays.selection_overlay import _Toolbar
from src.ui.themes.theme_manager import theme
from src.ui.widgets.animated_button import AnimatedButton
from src.ui.widgets.icons import icon

_LADO_TIRADOR = 8.0


class _Canvas(QWidget):
    """el lienzo: la imagen (escalada por el zoom) con las anotaciones."""

    item_selected = Signal(str, object)
    zoom_changed = Signal(float)

    def __init__(self, imagen: QImage):
        super().__init__()
        self.imagen = imagen
        self.setMouseTracking(True)

        self.items: list[an.Item] = []
        self.rehechos: list[an.Item] = []
        self.activo: an.Item | None = None
        self._arrastre: dict | None = None

        # zoom: 1.0 es tamaño real. el mínimo lo fija la ventana al abrir, para
        # que no se pueda alejar más allá de "ver todo"; el máximo permite
        # acercarse a mirar el detalle
        self.zoom = 1.0
        self.zoom_min = 0.1
        self.zoom_max = 4.0
        self.setFixedSize(imagen.width(), imagen.height())

        # recorte: la zona que quedará al exportar. None significa la imagen
        # entera. en modo recorte se dibuja con velo y tiradores
        self.crop_mode = False
        self.crop_rect: QRectF | None = None
        self._crop_drag: dict | None = None

        # los mismos valores por defecto del editor de capturas
        self.tool = "select"
        self.forma = "rect"
        self.color = QColor("#e5484d")
        self.ancho = 3
        self.dash = "solid"
        self.cap_inicio = "none"
        self.cap_fin = "arrow_filled"
        self.opacidad = 1.0
        self.fuente = QFont("Segoe UI", 18)
        self.pixel_modo = an.PIXEL_MODO
        self.pixel_cantidad = an.PIXEL_CANTIDAD
        self.pixel_grosor = an.PIXEL_GROSOR
        self.borrador_grosor = an.BORRADOR_GROSOR
        self._cursor_pincel: QPointF | None = None

        self._editor: QLineEdit | None = None
        self._editor_pos = QPointF()

    # ------------------------------------------------------------------ #
    # zoom y recorte

    def _img_pos(self, p: QPointF) -> QPointF:
        """pasa un punto del widget (ya escalado) a coordenadas de la imagen."""
        z = self.zoom if self.zoom else 1.0
        return QPointF(p.x() / z, p.y() / z)

    def set_zoom(self, z: float):
        z = max(self.zoom_min, min(self.zoom_max, z))
        if abs(z - self.zoom) < 1e-4:
            return
        # un texto a medio escribir se confirma antes de reescalar, para no
        # tener que recolocar su cajita
        self.commit_texto()
        self.zoom = z
        self.setFixedSize(max(1, round(self.imagen.width() * z)),
                          max(1, round(self.imagen.height() * z)))
        self.update()
        self.zoom_changed.emit(z)

    def set_crop_mode(self, activo: bool):
        self.crop_mode = activo
        if activo and self.crop_rect is None:
            # por defecto el recorte abarca toda la imagen; el usuario lo
            # achica arrastrando sus tiradores
            self.crop_rect = QRectF(0, 0, self.imagen.width(), self.imagen.height())
        self.setCursor(Qt.CrossCursor if activo else Qt.ArrowCursor)
        self.update()

    def _crop_handles(self) -> list[QPointF]:
        r = self.crop_rect
        if r is None:
            return []
        cx, cy = r.center().x(), r.center().y()
        return [r.topLeft(), QPointF(cx, r.top()), r.topRight(),
                QPointF(r.right(), cy), r.bottomRight(),
                QPointF(cx, r.bottom()), r.bottomLeft(), QPointF(r.left(), cy)]

    def _press_crop(self, punto: QPointF):
        tol = (_LADO_TIRADOR + 5) / max(self.zoom, 0.01)
        for i, h in enumerate(self._crop_handles()):
            if (h - punto).manhattanLength() <= tol:
                self._crop_drag = {"modo": "tirador", "indice": i}
                return
        if self.crop_rect is not None and self.crop_rect.contains(punto):
            self._crop_drag = {"modo": "mover", "inicio": punto, "rect0": QRectF(self.crop_rect)}
            return
        self._crop_drag = {"modo": "crear", "origen": punto}
        self.crop_rect = QRectF(punto, punto)

    def _move_crop(self, punto: QPointF):
        if not self._crop_drag:
            return
        # el recorte no puede salirse de la imagen
        punto = QPointF(min(max(punto.x(), 0), self.imagen.width()),
                        min(max(punto.y(), 0), self.imagen.height()))
        modo = self._crop_drag["modo"]
        if modo == "crear":
            self.crop_rect = QRectF(self._crop_drag["origen"], punto).normalized()
        elif modo == "mover":
            delta = punto - self._crop_drag["inicio"]
            r = QRectF(self._crop_drag["rect0"])
            r.translate(delta.x(), delta.y())
            if r.left() < 0:
                r.moveLeft(0)
            if r.top() < 0:
                r.moveTop(0)
            if r.right() > self.imagen.width():
                r.moveRight(self.imagen.width())
            if r.bottom() > self.imagen.height():
                r.moveBottom(self.imagen.height())
            self.crop_rect = r
        else:
            r = QRectF(self.crop_rect)
            i = self._crop_drag["indice"]
            if i in (0, 6, 7):
                r.setLeft(punto.x())
            if i in (0, 1, 2):
                r.setTop(punto.y())
            if i in (2, 3, 4):
                r.setRight(punto.x())
            if i in (4, 5, 6):
                r.setBottom(punto.y())
            self.crop_rect = r.normalized()
        self.update()

    def _fin_crop(self):
        self._crop_drag = None
        # un recorte demasiado chico probablemente fue un clic sin querer;
        # se vuelve a la imagen completa para no dejar algo inservible
        if self.crop_rect is not None and (self.crop_rect.width() < 10 or self.crop_rect.height() < 10):
            self.crop_rect = QRectF(0, 0, self.imagen.width(), self.imagen.height())
        self.update()

    # ------------------------------------------------------------------ #
    # texto en línea

    def abrir_editor_texto(self, pos: QPointF, existente: an.TextItem | None = None):
        self.commit_texto()
        editor = QLineEdit(self)
        editor.setPlaceholderText(t("tool.text_placeholder"))
        fuente = self.fuente if existente is None else existente.font
        # la cajita se muestra a la escala del zoom para que calce con lo que
        # se verá; al confirmar se divide de vuelta para guardar el tamaño real
        vista = QFont(fuente)
        vista.setPointSizeF(max(1.0, fuente.pointSizeF() * self.zoom))
        editor.setFont(vista)
        color = self.color if existente is None else existente.color
        editor.setStyleSheet(
            f"background: transparent; border: none; color: {color.name()};"
            f" font-family: '{vista.family()}'; font-size: {vista.pointSizeF():.0f}pt;"
            f" font-weight: {'bold' if vista.bold() else 'normal'};"
            f" font-style: {'italic' if vista.italic() else 'normal'};")
        if existente is not None:
            editor.setText(existente.text)
            posicion = existente.pos
            self.items.remove(existente)
            if self.activo is existente:
                self.activo = None
        else:
            posicion = pos
        editor.move(int(posicion.x() * self.zoom) - 4, int(posicion.y() * self.zoom) - 6)
        editor.setMinimumWidth(180)
        editor.show()
        editor.setFocus()
        editor.returnPressed.connect(self.finalizar_texto)
        self._editor = editor
        self._editor_pos = QPointF(posicion)

    def commit_texto(self):
        """confirma el texto en edición; devuelve el elemento creado."""
        if self._editor is None:
            return None
        texto = self._editor.text().strip()
        fuente = QFont(self._editor.font())
        # se deshace la escala del zoom para guardar el tamaño real
        fuente.setPointSizeF(max(1.0, fuente.pointSizeF() / (self.zoom if self.zoom else 1.0)))
        self._editor.deleteLater()
        self._editor = None
        nuevo = None
        if texto:
            nuevo = an.TextItem(self._editor_pos, texto, fuente, self.color)
            self.items.append(nuevo)
            self.rehechos.clear()
        self.update()
        return nuevo

    def finalizar_texto(self):
        nuevo = self.commit_texto()
        if nuevo is not None:
            self.tool = "select"
            self.activo = nuevo
            self.item_selected.emit(self._tipo_de(nuevo), nuevo)

    # ------------------------------------------------------------------ #
    # mouse

    def mousePressEvent(self, e):
        if e.button() != Qt.LeftButton:
            return
        punto = self._img_pos(e.position())
        if self.crop_mode:
            self._press_crop(punto)
            self.update()
            return
        if self._editor is not None:
            self.finalizar_texto()
            return
        if self.tool == "select":
            self._press_seleccion(punto, bool(e.modifiers() & Qt.AltModifier))
        elif self.tool == "text":
            self.abrir_editor_texto(punto)
        elif self.tool == "eraser":
            self._arrastre = {"modo": "borrar"}
            self._borrar_en(punto)
        else:
            self._press_dibujo(punto)
        self.update()

    def _press_seleccion(self, punto: QPointF, alt: bool = False):
        if self.activo is not None:
            for i, tirador in enumerate(self.activo.handles()):
                if (tirador - punto).manhattanLength() <= _LADO_TIRADOR + 4:
                    self._arrastre = {"modo": "tirador", "indice": i}
                    if isinstance(self.activo, an.ShapeItem):
                        r = self.activo.rect
                        self._arrastre["centro"] = QPointF(r.center())
                        self._arrastre["aspecto"] = (r.width() / r.height()
                                                     if r.height() > 0 else 0)
                    elif isinstance(self.activo, an.TextItem):
                        self._arrastre["texto0"] = (QRectF(self.activo._rect()),
                                                    self.activo.font.pointSizeF())
                    return
        for item in reversed(self.items):
            if isinstance(item, an.PixelateItem):
                continue
            if item.contains(punto):
                if alt:
                    item = an.clonar(item)
                    self.items.append(item)
                    self.rehechos.clear()
                self.activo = item
                self.item_selected.emit(self._tipo_de(item), item)
                self._arrastre = {"modo": "mover", "inicio": punto,
                                  "antes_mov": an.snapshot(item)}
                return
        self.activo = None
        self.item_selected.emit("select", None)

    def _borrar_en(self, punto: QPointF):
        radio = max(2.0, self.borrador_grosor / 2)
        circulo = QPainterPath()
        circulo.addEllipse(punto, radio, radio)
        borrado = False
        for item in reversed(list(self.items)):
            trazo = an._trazo_ancho(item.path(), max(1.0, item.width))
            if trazo.intersects(circulo) or item.contains(punto):
                self.items.remove(item)
                if item is self.activo:
                    self.activo = None
                borrado = True
        if borrado:
            self.update()

    @staticmethod
    def _tipo_de(item: an.Item) -> str:
        if isinstance(item, an.PixelateItem):
            return "pixelate"
        if isinstance(item, an.TextItem):
            return "text"
        if isinstance(item, an.LineItem):
            return "arrow" if item.cap_start != "none" or item.cap_end != "none" else "line"
        if isinstance(item, an.BrushItem):
            return "brush"
        return "shape"

    def _press_dibujo(self, punto: QPointF):
        if self.tool == "shape":
            clase = an.SHAPES[self.forma][1]
            nuevo = clase(QRectF(punto, punto), self.color, self.ancho)
            nuevo.dash = self.dash
        elif self.tool == "line":
            nuevo = an.LineItem(punto, punto, self.color, self.ancho)
            nuevo.dash = self.dash
        elif self.tool == "arrow":
            nuevo = an.LineItem(punto, punto, self.color, self.ancho,
                                self.cap_inicio, self.cap_fin)
            nuevo.dash = self.dash
        elif self.tool == "brush":
            nuevo = an.BrushItem(punto, self.color, self.ancho)
        elif self.tool == "pixelate":
            nuevo = an.PixelateItem(punto, self.imagen, 1.0, self.pixel_modo,
                                    self.pixel_cantidad, self.pixel_grosor)
        else:
            return
        nuevo.opacity = self.opacidad
        self.items.append(nuevo)
        self.rehechos.clear()
        self._arrastre = {"modo": "crear", "item": nuevo, "origen": punto}

    def mouseMoveEvent(self, e):
        punto = self._img_pos(e.position())
        if self.crop_mode:
            if self._crop_drag:
                self._move_crop(punto)
            return
        if self.tool in ("pixelate", "eraser"):
            self._cursor_pincel = punto
            self.update()
        if not self._arrastre:
            self._cursor_hover(punto)
            return
        if self._arrastre.get("modo") == "borrar":
            self._borrar_en(punto)
            return
        mods = e.modifiers()
        shift = bool(mods & Qt.ShiftModifier)
        alt = bool(mods & Qt.AltModifier)
        modo = self._arrastre["modo"]
        if modo == "crear":
            item = self._arrastre["item"]
            origen = self._arrastre.get("origen")
            if isinstance(item, (an.BrushItem, an.PixelateItem)):
                if shift:
                    item.points = [QPointF(item.points[0]), QPointF(punto)]
                else:
                    item.add_point(punto)
            elif isinstance(item, an.ShapeItem):
                if alt and origen is not None:
                    espejo = QPointF(2 * origen.x() - punto.x(), 2 * origen.y() - punto.y())
                    rect = QRectF(espejo, punto).normalized()
                    if shift:
                        lado = max(rect.width(), rect.height())
                        rect = QRectF(origen.x() - lado / 2, origen.y() - lado / 2, lado, lado)
                    item.rect = rect
                else:
                    item.rect = (an.cuadrar_rect(origen, punto) if shift
                                 else QRectF(origen, punto).normalized())
            elif isinstance(item, an.LineItem):
                destino = an.snap_45(origen, punto) if shift and origen else punto
                item.p2 = destino
                if origen is not None:
                    item.p1 = (QPointF(2 * origen.x() - destino.x(),
                                       2 * origen.y() - destino.y())
                               if alt else QPointF(origen))
        elif modo == "mover":
            delta = punto - self._arrastre["inicio"]
            if shift:
                delta = an.restringir_eje(delta)
            an.restore(self.activo, self._arrastre["antes_mov"])
            self.activo.move_by(delta.x(), delta.y())
        elif modo == "tirador":
            indice = self._arrastre["indice"]
            if isinstance(self.activo, an.TextItem) and "texto0" in self._arrastre:
                rect0, tam0 = self._arrastre["texto0"]
                an.escalar_texto(self.activo, indice, punto, rect0, tam0)
            elif isinstance(self.activo, an.LineItem) and shift:
                fijo = self.activo.p2 if indice == 0 else self.activo.p1
                self.activo.set_handle(indice, an.snap_45(fijo, punto))
            else:
                self.activo.set_handle(indice, punto)
            if isinstance(self.activo, an.ShapeItem):
                if shift and self._arrastre.get("aspecto"):
                    self.activo.rect = an.ajustar_aspecto(
                        self.activo.rect, self._arrastre["aspecto"], indice)
                if alt and self._arrastre.get("centro") is not None:
                    self.activo.rect.moveCenter(self._arrastre["centro"])
        self.update()

    def _cursor_hover(self, punto: QPointF):
        if self.tool != "select":
            self.setCursor(Qt.IBeamCursor if self.tool == "text" else Qt.CrossCursor)
            return
        if self.activo is not None:
            for i, tirador in enumerate(self.activo.handles()):
                if (tirador - punto).manhattanLength() <= _LADO_TIRADOR + 4:
                    self.setCursor(an.cursor_tirador(self.activo, i))
                    return
        for item in reversed(self.items):
            if item.contains(punto):
                self.setCursor(Qt.OpenHandCursor)
                return
        self.setCursor(Qt.ArrowCursor)

    def mouseReleaseEvent(self, e):
        if e.button() != Qt.LeftButton:
            return
        if self.crop_mode:
            self._fin_crop()
            return
        if self._arrastre and self._arrastre["modo"] == "crear":
            item = self._arrastre["item"]
            if isinstance(item, an.PixelateItem):
                item.editando = False
            if item.bounding().width() < 8 and item.bounding().height() < 8:
                if item in self.items:
                    self.items.remove(item)
            elif self.tool not in ("brush", "pixelate"):
                self.tool = "select"
                self.activo = item
                self.item_selected.emit(self._tipo_de(item), item)
        self._arrastre = None
        self.update()

    def mouseDoubleClickEvent(self, e):
        if self.crop_mode:
            return
        punto = self._img_pos(e.position())
        for item in reversed(self.items):
            if isinstance(item, an.TextItem) and item.contains(punto):
                self.abrir_editor_texto(punto, existente=item)
                return

    # ------------------------------------------------------------------ #

    def exportar(self) -> QImage:
        self.commit_texto()
        salida = self.imagen.copy()
        pintor = QPainter(salida)
        pintor.setRenderHint(QPainter.Antialiasing)
        pintor.setRenderHint(QPainter.TextAntialiasing)
        for item in self.items:
            an.paint_item(pintor, item)
        pintor.end()
        # si hay un recorte más chico que la imagen, se aplica al resultado
        if self.crop_rect is not None:
            r = self.crop_rect.intersected(QRectF(0, 0, salida.width(), salida.height()))
            recorte = QRect(round(r.x()), round(r.y()), round(r.width()), round(r.height()))
            if (recorte.width() >= 1 and recorte.height() >= 1
                    and (recorte.width() < salida.width() or recorte.height() < salida.height())):
                salida = salida.copy(recorte)
        return salida

    def paintEvent(self, _):
        z = self.zoom
        pintor = QPainter(self)
        pintor.setRenderHint(QPainter.Antialiasing)
        # la imagen y las anotaciones se pintan en coordenadas reales, con el
        # lienzo escalado por el zoom
        pintor.save()
        pintor.scale(z, z)
        pintor.drawImage(0, 0, self.imagen)
        for item in self.items:
            an.paint_item(pintor, item)
        if (self.tool in ("pixelate", "eraser") and self._cursor_pincel is not None
                and not self.crop_mode):
            grosor = self.pixel_grosor if self.tool == "pixelate" else self.borrador_grosor
            an.pintar_circulo_pincel(pintor, self._cursor_pincel, grosor)
        pintor.restore()

        # los tiradores de selección se dibujan a tamaño constante en pantalla,
        # ya fuera de la escala, para que no se achiquen al alejar el zoom
        if self.activo is not None and not self.crop_mode:
            tiradores = self.activo.handles()
            pintor.setPen(QPen(QColor(theme.accent()), 1.2))
            pintor.setBrush(QColor("#ffffff"))
            mitad = _LADO_TIRADOR / 2
            for tir in tiradores:
                pintor.drawRect(QRectF(tir.x() * z - mitad, tir.y() * z - mitad,
                                       _LADO_TIRADOR, _LADO_TIRADOR))
            if not tiradores:
                pluma = QPen(QColor(theme.accent()), 1)
                pluma.setStyle(Qt.DashLine)
                pintor.setPen(pluma)
                pintor.setBrush(Qt.NoBrush)
                b = self.activo.bounding()
                pintor.drawRect(QRectF(b.x() * z, b.y() * z, b.width() * z, b.height() * z))

        if self.crop_mode and self.crop_rect is not None:
            self._pintar_recorte(pintor, z)
        pintor.end()

    def _pintar_recorte(self, pintor: QPainter, z: float):
        r = self.crop_rect
        rz = QRectF(r.x() * z, r.y() * z, r.width() * z, r.height() * z)
        velo = QColor(0, 0, 0, 110)
        w, h = self.width(), self.height()
        pintor.fillRect(QRectF(0, 0, w, rz.top()), velo)
        pintor.fillRect(QRectF(0, rz.bottom(), w, h - rz.bottom()), velo)
        pintor.fillRect(QRectF(0, rz.top(), rz.left(), rz.height()), velo)
        pintor.fillRect(QRectF(rz.right(), rz.top(), w - rz.right(), rz.height()), velo)
        pintor.setPen(QPen(QColor(theme.accent()), 1.6))
        pintor.setBrush(Qt.NoBrush)
        pintor.drawRect(rz)
        pintor.setBrush(QColor("#ffffff"))
        pintor.setPen(QPen(QColor(theme.accent()), 1.2))
        mitad = _LADO_TIRADOR / 2
        for hnd in self._crop_handles():
            pintor.drawRect(QRectF(hnd.x() * z - mitad, hnd.y() * z - mitad,
                                   _LADO_TIRADOR, _LADO_TIRADOR))

    def leaveEvent(self, e):
        if self._cursor_pincel is not None:
            self._cursor_pincel = None
            self.update()
        super().leaveEvent(e)


class EditorWindow(QWidget):
    copied = Signal(QImage)
    save_requested = Signal(QImage)
    closed = Signal()

    def __init__(self, imagen: QImage):
        super().__init__(None)
        self.setWindowTitle(f'{t("editor.title")} · {APP_NAME}')
        self.setWindowIcon(QIcon(paths.resource_path(os.path.join("assets", "logo", "logo.jpg"))))
        self.setAttribute(Qt.WA_DeleteOnClose, True)
        self._ajuste_hecho = False

        columna = QVBoxLayout(self)
        columna.setContentsMargins(10, 10, 10, 10)
        columna.setSpacing(8)

        self._canvas = _Canvas(imagen)

        # la barra de herramientas va pegada a la izquierda, a su tamaño; los
        # controles de zoom y recorte quedan a la derecha, y entre ambos un
        # espaciador se come el ancho sobrante en pantalla completa
        self._barra = _Toolbar(self)
        self._conectar_barra()

        fila_superior = QHBoxLayout()
        fila_superior.setContentsMargins(0, 0, 0, 0)
        fila_superior.setSpacing(8)
        fila_superior.addWidget(self._barra, 0, Qt.AlignTop)
        fila_superior.addStretch()
        fila_superior.addLayout(self._controles_zoom())
        columna.addLayout(fila_superior)

        self._area = QScrollArea()
        self._area.setWidget(self._canvas)
        self._area.setAlignment(Qt.AlignCenter)
        columna.addWidget(self._area)

        # la ventana abre a un tamaño cómodo; el zoom se encarga de que la
        # imagen entre completa dentro de ese espacio
        pantalla = QGuiApplication.primaryScreen().availableGeometry()
        ancho = min(1040, int(pantalla.width() * 0.9))
        alto = min(760, int(pantalla.height() * 0.9))
        self.resize(max(ancho, self._barra.sizeHint().width() + 220), max(alto, 460))

    def _controles_zoom(self) -> QHBoxLayout:
        fila = QHBoxLayout()
        fila.setSpacing(4)

        def boton(nombre_icono: str, tooltip: str, marcable: bool = False) -> AnimatedButton:
            b = AnimatedButton()
            b.setIcon(icon(nombre_icono, theme.icon_color()))
            b.setIconSize(QSize(20, 20))
            b.setToolTip(tooltip)
            b.setCheckable(marcable)
            b.setCursor(Qt.PointingHandCursor)
            return b

        self._btn_recorte = boton("crop", t("tool.crop"), True)
        self._btn_recorte.toggled.connect(self._alternar_recorte)
        fila.addWidget(self._btn_recorte)

        alejar = boton("zoom-out", t("tool.zoom_out"))
        alejar.clicked.connect(lambda: self._canvas.set_zoom(self._canvas.zoom / 1.25))
        fila.addWidget(alejar)

        self._lbl_zoom = QLabel("100%")
        self._lbl_zoom.setObjectName("secundario")
        self._lbl_zoom.setAlignment(Qt.AlignCenter)
        self._lbl_zoom.setMinimumWidth(44)
        fila.addWidget(self._lbl_zoom)

        acercar = boton("zoom-in", t("tool.zoom_in"))
        acercar.clicked.connect(lambda: self._canvas.set_zoom(self._canvas.zoom * 1.25))
        fila.addWidget(acercar)

        self._canvas.zoom_changed.connect(
            lambda z: self._lbl_zoom.setText(f"{round(z * 100)}%"))
        fila.setAlignment(Qt.AlignTop)
        return fila

    def showEvent(self, e):
        super().showEvent(e)
        # al mostrarse por primera vez, la imagen se ajusta para verse completa
        if not self._ajuste_hecho:
            self._ajuste_hecho = True
            QTimer.singleShot(0, self._ajustar_a_ventana)

    def _ajustar_a_ventana(self):
        vp = self._area.viewport().size()
        iw, ih = self._canvas.imagen.width(), self._canvas.imagen.height()
        if iw <= 0 or ih <= 0:
            return
        margen = 8
        ajuste = min((vp.width() - margen) / iw, (vp.height() - margen) / ih)
        # al abrir no se agranda más allá del tamaño real; y ese ajuste pasa a
        # ser el zoom mínimo, o sea el "todo visible": no se puede alejar más
        ajuste = min(ajuste, 1.0)
        self._canvas.zoom_min = max(0.05, ajuste)
        # se fuerza el reescalado aunque coincida con el zoom actual
        self._canvas.zoom = 0.0
        self._canvas.set_zoom(ajuste)

    def _alternar_recorte(self, activo: bool):
        self._canvas.set_crop_mode(activo)

    def _desactivar_recorte(self):
        if self._btn_recorte.isChecked():
            self._btn_recorte.setChecked(False)

    def _conectar_barra(self):
        b, c = self._barra, self._canvas
        b.tool_changed.connect(self._cambiar_tool)
        b.shape_changed.connect(lambda f: setattr(c, "forma", f))
        b.color_changed.connect(self._aplicar("color", "color"))
        b.width_changed.connect(self._aplicar("ancho", "width"))
        b.dash_changed.connect(self._aplicar("dash", "dash"))
        b.cap_start_changed.connect(self._aplicar("cap_inicio", "cap_start"))
        b.cap_end_changed.connect(self._aplicar("cap_fin", "cap_end"))
        b.opacity_changed.connect(self._aplicar("opacidad", "opacity"))
        b.font_changed.connect(self._aplicar_fuente)
        b.font_size_changed.connect(self._aplicar_tamano)
        b.bold_toggled.connect(lambda v: self._aplicar_estilo_fuente("setBold", v))
        b.italic_toggled.connect(lambda v: self._aplicar_estilo_fuente("setItalic", v))
        b.pixel_mode_changed.connect(lambda m: self._aplicar_pixel("mode", m))
        b.pixel_amount_changed.connect(lambda v: self._aplicar_pixel("amount", v))
        b.pixel_size_changed.connect(lambda v: self._aplicar_pixel("size", v))
        b.eraser_size_changed.connect(self._aplicar_borrador)
        b.undo_clicked.connect(self._deshacer)
        b.redo_clicked.connect(self._rehacer)
        b.clear_clicked.connect(self._limpiar)
        b.copy_clicked.connect(self._copiar)
        b.save_clicked.connect(self._guardar)
        b.cancel_clicked.connect(self.close)
        c.item_selected.connect(self._al_seleccionar)

    def _al_seleccionar(self, tipo: str, item):
        if item is not None and self._canvas.tool == "select":
            self._barra.activate("select")
        self._barra.configure(tipo, item)

    def _cambiar_tool(self, nombre: str):
        # elegir una herramienta de dibujo apaga el recorte, para que el clic
        # vuelva a dibujar y no siga ajustando el recuadro
        self._desactivar_recorte()
        self._canvas.commit_texto()
        self._canvas.tool = nombre
        if nombre != "select":
            self._canvas.activo = None
        if nombre not in ("pixelate", "eraser"):
            self._canvas._cursor_pincel = None
        self._canvas.setCursor({"select": Qt.ArrowCursor,
                                "text": Qt.IBeamCursor}.get(nombre, Qt.CrossCursor))
        self._canvas.update()

    def _aplicar(self, atributo_defecto: str, atributo_item: str):
        def manejar(valor):
            c = self._canvas
            setattr(c, atributo_defecto, valor if not isinstance(valor, QColor) else QColor(valor))
            if c.activo is not None:
                if atributo_item == "color" and isinstance(c.activo, an.PixelateItem):
                    return
                if atributo_item in ("cap_start", "cap_end") and not isinstance(c.activo, an.LineItem):
                    return
                setattr(c.activo, atributo_item,
                        QColor(valor) if isinstance(valor, QColor) else valor)
                c.update()
        return manejar

    def _aplicar_pixel(self, campo: str, valor):
        c = self._canvas
        if campo == "mode":
            c.pixel_modo = valor
        elif campo == "amount":
            c.pixel_cantidad = int(valor)
        elif campo == "size":
            c.pixel_grosor = int(valor)
        if isinstance(c.activo, an.PixelateItem):
            if campo == "mode":
                c.activo.mode = valor
            elif campo == "amount":
                c.activo.amount = int(valor)
            elif campo == "size":
                c.activo.width = int(valor)
            c.update()

    def _aplicar_borrador(self, valor: int):
        self._canvas.borrador_grosor = int(valor)
        self._canvas.update()

    def _aplicar_fuente(self, familia: str):
        c = self._canvas
        c.fuente.setFamily(familia)
        if isinstance(c.activo, an.TextItem):
            c.activo.font.setFamily(familia)
            c.update()

    def _aplicar_tamano(self, puntos: int):
        c = self._canvas
        c.fuente.setPointSize(puntos)
        if isinstance(c.activo, an.TextItem):
            c.activo.font.setPointSize(puntos)
            c.update()

    def _aplicar_estilo_fuente(self, metodo: str, valor: bool):
        c = self._canvas
        getattr(c.fuente, metodo)(valor)
        if isinstance(c.activo, an.TextItem):
            getattr(c.activo.font, metodo)(valor)
            c.update()

    def _deshacer(self):
        c = self._canvas
        c.commit_texto()
        if c.items:
            quitado = c.items.pop()
            c.rehechos.append(quitado)
            if quitado is c.activo:
                c.activo = None
            c.update()

    def _rehacer(self):
        c = self._canvas
        if c.rehechos:
            c.items.append(c.rehechos.pop())
            c.update()

    def _limpiar(self):
        c = self._canvas
        c.commit_texto()
        c.items.clear()
        c.activo = None
        c.update()

    def _pegar_imagen(self):
        c = self._canvas
        imagen = QGuiApplication.clipboard().image()
        if imagen.isNull():
            return
        factor = min(1.0, c.imagen.width() * 0.6 / max(1, imagen.width()),
                     c.imagen.height() * 0.6 / max(1, imagen.height()))
        ancho, alto = imagen.width() * factor, imagen.height() * factor
        nuevo = an.ImageItem(QRectF((c.imagen.width() - ancho) / 2, (c.imagen.height() - alto) / 2,
                                    ancho, alto), imagen)
        nuevo.opacity = c.opacidad
        c.items.append(nuevo)
        c.rehechos.clear()
        c.activo = nuevo
        self._barra.activate("select")
        c.update()

    def _copiar(self):
        self.copied.emit(self._canvas.exportar())
        self.close()

    def _guardar(self):
        imagen = self._canvas.exportar()
        self.save_requested.emit(imagen)

    def keyPressEvent(self, e):
        if e.matches(QKeySequence.Copy):
            self._copiar()
        elif e.matches(QKeySequence.Save):
            self._guardar()
        elif e.matches(QKeySequence.Undo):
            self._deshacer()
        elif e.matches(QKeySequence.Redo):
            self._rehacer()
        elif e.matches(QKeySequence.Paste):
            self._pegar_imagen()
        elif e.key() == Qt.Key_Delete and self._canvas.activo is not None:
            self._canvas.items.remove(self._canvas.activo)
            self._canvas.activo = None
            self._canvas.update()
        elif e.key() == Qt.Key_Escape:
            if self._canvas._editor is not None:
                self._canvas.finalizar_texto()
            elif self._btn_recorte.isChecked():
                # esc sale del modo recorte antes que del editor
                self._btn_recorte.setChecked(False)
            else:
                self.close()
        else:
            super().keyPressEvent(e)

    def closeEvent(self, e):
        self.closed.emit()
        super().closeEvent(e)
