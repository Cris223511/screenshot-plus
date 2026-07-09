"""editor de imágenes ya capturadas, pensado para la captura larga.

la captura con desplazamiento termina en una imagen que puede medir miles
de píxeles de alto, imposible de editar en el overlay de pantalla. este
editor la recibe en una ventana normal con scroll: arriba la misma barra
de herramientas del editor de capturas (formas, líneas, flechas, pincel,
texto, pixelado, con todas sus propiedades) y abajo el lienzo. las
anotaciones funcionan igual: se dibujan, se seleccionan, se mueven, se
redimensionan y se les cambia color o estilo en vivo.

ctrl+c copia, ctrl+s guarda, ctrl+z deshace, supr borra el elemento
seleccionado. el resultado sale por señales y la app decide portapapeles,
diálogo de guardado y notificaciones, igual que con cualquier captura.
"""

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import (QColor, QFont, QGuiApplication, QIcon, QImage,
                           QKeySequence, QPainter, QPen)
from PySide6.QtWidgets import (QLineEdit, QScrollArea, QVBoxLayout, QWidget)

import os

from src import APP_NAME
from src.config import paths
from src.i18n.translator import t
from src.ui.overlays import annotation_tools as an
from src.ui.overlays.selection_overlay import _Toolbar
from src.ui.themes.theme_manager import theme

_LADO_TIRADOR = 8.0


class _Canvas(QWidget):
    """el lienzo: la imagen a tamaño real con las anotaciones encima."""

    item_selected = Signal(str, object)

    def __init__(self, imagen: QImage):
        super().__init__()
        self.imagen = imagen
        self.setFixedSize(imagen.width(), imagen.height())
        self.setMouseTracking(True)

        self.items: list[an.Item] = []
        self.rehechos: list[an.Item] = []
        self.activo: an.Item | None = None
        self._arrastre: dict | None = None

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

        self._editor: QLineEdit | None = None
        self._editor_pos = QPointF()

    # ------------------------------------------------------------------ #
    # texto en línea

    def abrir_editor_texto(self, pos: QPointF, existente: an.TextItem | None = None):
        self.commit_texto()
        editor = QLineEdit(self)
        editor.setPlaceholderText(t("tool.text_placeholder"))
        fuente = self.fuente if existente is None else existente.font
        editor.setFont(fuente)
        color = self.color if existente is None else existente.color
        # sin caja ni fondo, con la fuente dentro del estilo: la hoja de
        # estilos global fija 13px y pisaría el setFont
        editor.setStyleSheet(
            f"background: transparent; border: none; color: {color.name()};"
            f" font-family: '{fuente.family()}'; font-size: {fuente.pointSizeF():.0f}pt;"
            f" font-weight: {'bold' if fuente.bold() else 'normal'};"
            f" font-style: {'italic' if fuente.italic() else 'normal'};")
        if existente is not None:
            editor.setText(existente.text)
            posicion = existente.pos
            self.items.remove(existente)
            if self.activo is existente:
                self.activo = None
        else:
            posicion = pos
        editor.move(int(posicion.x()) - 4, int(posicion.y()) - 6)
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
        """esc, enter o un clic afuera confirman el texto y lo dejan
        seleccionado con la herramienta en selección."""
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
        punto = QPointF(e.position())
        if self._editor is not None:
            # el clic afuera confirma el texto y lo deja seleccionado
            self.finalizar_texto()
            return

        if self.tool == "select":
            self._press_seleccion(punto, bool(e.modifiers() & Qt.AltModifier))
        elif self.tool == "text":
            self.abrir_editor_texto(punto)
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
                        # el texto escala anclado a su estado inicial
                        self._arrastre["texto0"] = (QRectF(self.activo._rect()),
                                                    self.activo.font.pointSizeF())
                    return
        for item in reversed(self.items):
            if item.contains(punto):
                # el texto se selecciona como cualquier elemento; su
                # contenido se edita con doble clic
                if alt:
                    # se duplica el elemento y se arrastra la copia
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
            # sobre una imagen ya capturada la relación es uno a uno, por
            # eso el factor de pantalla va en 1
            nuevo = an.PixelateItem(QRectF(punto, punto), self.imagen, 1.0, self.ancho + 9)
        else:
            return
        nuevo.opacity = self.opacidad
        self.items.append(nuevo)
        # una figura nueva invalida lo que estaba pendiente de rehacer
        self.rehechos.clear()
        self._arrastre = {"modo": "crear", "item": nuevo, "origen": punto}

    def mouseMoveEvent(self, e):
        punto = QPointF(e.position())
        if not self._arrastre:
            self._cursor_hover(punto)
            return
        # los mismos modificadores de los otros editores: shift endereza
        # y proporciona, alt crece desde el centro
        # el evento trae los modificadores reales; la caché de la app
        # no se entera si shift ya venía presionado desde antes del clic
        mods = e.modifiers()
        shift = bool(mods & Qt.ShiftModifier)
        alt = bool(mods & Qt.AltModifier)
        modo = self._arrastre["modo"]
        if modo == "crear":
            item = self._arrastre["item"]
            origen = self._arrastre.get("origen")
            if isinstance(item, an.BrushItem):
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
            # desplazamiento absoluto desde el punto de agarre; con shift
            # se pega al eje recto más cercano
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
        objetivo = Qt.ArrowCursor
        if self.activo is not None:
            for tirador in self.activo.handles():
                if (tirador - punto).manhattanLength() <= _LADO_TIRADOR + 4:
                    objetivo = Qt.SizeAllCursor
                    break
        if objetivo == Qt.ArrowCursor:
            for item in reversed(self.items):
                if item.contains(punto):
                    objetivo = Qt.OpenHandCursor
                    break
        self.setCursor(objetivo)

    def mouseReleaseEvent(self, e):
        if e.button() != Qt.LeftButton:
            return
        if self._arrastre and self._arrastre["modo"] == "crear":
            item = self._arrastre["item"]
            if item.bounding().width() < 8 and item.bounding().height() < 8:
                if item in self.items:
                    self.items.remove(item)
            elif self.tool != "brush":
                # lo recién dibujado queda seleccionado y la herramienta
                # pasa a selección, lista para acomodar
                self.tool = "select"
                self.activo = item
                self.item_selected.emit(self._tipo_de(item), item)
        self._arrastre = None
        self.update()

    def mouseDoubleClickEvent(self, e):
        punto = QPointF(e.position())
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
        return salida

    def paintEvent(self, _):
        pintor = QPainter(self)
        pintor.setRenderHint(QPainter.Antialiasing)
        pintor.drawImage(0, 0, self.imagen)
        for item in self.items:
            an.paint_item(pintor, item)
        if self.activo is not None:
            tiradores = self.activo.handles()
            pintor.setPen(QPen(QColor(theme.accent()), 1.2))
            pintor.setBrush(QColor("#ffffff"))
            mitad = _LADO_TIRADOR / 2
            for tirador in tiradores:
                pintor.drawRect(QRectF(tirador.x() - mitad, tirador.y() - mitad,
                                       _LADO_TIRADOR, _LADO_TIRADOR))
            if not tiradores:
                pluma = QPen(QColor(theme.accent()), 1)
                pluma.setStyle(Qt.DashLine)
                pintor.setPen(pluma)
                pintor.setBrush(Qt.NoBrush)
                pintor.drawRect(self.activo.bounding())
        pintor.end()


class EditorWindow(QWidget):
    copied = Signal(QImage)
    save_requested = Signal(QImage)
    closed = Signal()

    def __init__(self, imagen: QImage):
        super().__init__(None)
        self.setWindowTitle(f'{t("editor.title")} · {APP_NAME}')
        self.setWindowIcon(QIcon(paths.resource_path(os.path.join("assets", "logo", "logo.jpg"))))
        self.setAttribute(Qt.WA_DeleteOnClose, True)

        columna = QVBoxLayout(self)
        columna.setContentsMargins(10, 10, 10, 10)
        columna.setSpacing(8)

        self._canvas = _Canvas(imagen)

        # la misma barra del editor de capturas, conectada al lienzo
        self._barra = _Toolbar(self)
        self._conectar_barra()
        columna.addWidget(self._barra)

        area = QScrollArea()
        area.setWidget(self._canvas)
        area.setAlignment(Qt.AlignHCenter | Qt.AlignTop)
        columna.addWidget(area)

        # la ventana abre a un tamaño cómodo: lo que mida la imagen, con
        # tope en el 85 por ciento de la pantalla
        pantalla = QGuiApplication.primaryScreen().availableGeometry()
        ancho = min(imagen.width() + 60, int(pantalla.width() * 0.85))
        alto = min(imagen.height() + 120, int(pantalla.height() * 0.85))
        self.resize(max(ancho, self._barra.sizeHint().width() + 40), max(alto, 420))

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
        b.undo_clicked.connect(self._deshacer)
        b.redo_clicked.connect(self._rehacer)
        b.clear_clicked.connect(self._limpiar)
        b.copy_clicked.connect(self._copiar)
        b.save_clicked.connect(self._guardar)
        b.cancel_clicked.connect(self.close)
        c.item_selected.connect(self._al_seleccionar)

    def _al_seleccionar(self, tipo: str, item):
        """al quedar algo seleccionado (a mano o tras dibujarlo), la barra
        marca la herramienta de selección y carga sus propiedades."""
        if item is not None and self._canvas.tool == "select":
            self._barra.activate("select")
        self._barra.configure(tipo, item)

    def _cambiar_tool(self, nombre: str):
        self._canvas.commit_texto()
        self._canvas.tool = nombre
        if nombre != "select":
            self._canvas.activo = None
        self._canvas.setCursor({"select": Qt.ArrowCursor,
                                "text": Qt.IBeamCursor}.get(nombre, Qt.CrossCursor))
        self._canvas.update()

    def _aplicar(self, atributo_defecto: str, atributo_item: str):
        """fabrica el manejador de una propiedad: actualiza el valor por
        defecto del lienzo y, si hay un elemento tomado, también el suyo."""
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
        """ctrl+v pega la imagen del portapapeles sobre el lienzo."""
        c = self._canvas
        imagen = QGuiApplication.clipboard().image()
        if imagen.isNull():
            return
        factor = min(1.0, c.width() * 0.6 / max(1, imagen.width()),
                     c.height() * 0.6 / max(1, imagen.height()))
        ancho, alto = imagen.width() * factor, imagen.height() * factor
        nuevo = an.ImageItem(QRectF((c.width() - ancho) / 2, (c.height() - alto) / 2,
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
        self.close()
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
            # con un texto a medio escribir, esc lo confirma y selecciona;
            # sin nada pendiente, cierra el editor
            if self._canvas._editor is not None:
                self._canvas.finalizar_texto()
            else:
                self.close()
        else:
            super().keyPressEvent(e)

    def closeEvent(self, e):
        self.closed.emit()
        super().closeEvent(e)
