"""overlay de captura: la pantalla congelada, la selección y el editor.

al disparar una captura de región, este widget cubre todos los monitores
con una foto congelada de la pantalla. el usuario arrastra para elegir la
zona y, al soltar, aparece debajo la barra de herramientas para anotar.
la selección no queda fija: se puede mover arrastrándola desde adentro y
redimensionar por sus tiradores, igual que cualquier elemento dibujado.

cada anotación es editable después de creada: con la herramienta de
selección se toma un elemento, la barra muestra sus propiedades (color,
grosor, trazo, remates, tipografía según el caso) y cualquier cambio se
aplica al instante sobre él.

ctrl+c copia, ctrl+s pide guardar, ctrl+z deshace, supr borra el elemento
seleccionado y esc cancela todo. el overlay avisa por señales y la app se
encarga del portapapeles, el diálogo de guardar y las notificaciones.
"""

from PySide6.QtCore import (QEasingCurve, QPointF, QPropertyAnimation, QRect,
                            QRectF, QSize, Qt, Signal)
from PySide6.QtGui import (QColor, QFont, QGuiApplication, QImage,
                           QKeySequence, QPainter, QPen)
from PySide6.QtWidgets import (QComboBox, QFrame, QGraphicsOpacityEffect,
                               QHBoxLayout, QLabel, QLineEdit, QMenu,
                               QSlider, QSpinBox, QVBoxLayout, QWidget)

from src.core import capture
from src.i18n.translator import t
from src.ui.overlays import annotation_tools as an
from src.ui.themes.theme_manager import theme
from src.ui.widgets.animated_button import AnimatedButton
from src.ui.widgets.color_palette import ColorPalette
from src.ui.widgets.icons import icon

# lado de los cuadraditos de agarre, tanto de la selección como de los items
_LADO_TIRADOR = 8.0

# tipografías que ofrece el desplegable de texto; una selección amplia de
# las que vienen con windows, sin obligar a nadie a escribir nombres
FONTS = ["Segoe UI", "Arial", "Verdana", "Tahoma", "Calibri", "Cambria",
         "Georgia", "Times New Roman", "Trebuchet MS", "Garamond",
         "Palatino Linotype", "Book Antiqua", "Century Gothic", "Candara",
         "Constantia", "Corbel", "Franklin Gothic Medium", "Impact",
         "Comic Sans MS", "Segoe Print", "Segoe Script", "Gabriola",
         "Courier New", "Consolas", "Lucida Console", "Sitka Text"]


class _Toolbar(QWidget):
    """barra de herramientas que aparece bajo la selección.

    la fila principal tiene las herramientas y acciones; la contextual
    muestra únicamente lo que aplica a la herramienta activa o al elemento
    seleccionado, y cuando hay un elemento tomado, los controles cargan
    sus valores reales para editarlo en vivo.
    """

    tool_changed = Signal(str)
    shape_changed = Signal(str)
    color_changed = Signal(QColor)
    width_changed = Signal(int)
    dash_changed = Signal(str)
    cap_start_changed = Signal(str)
    cap_end_changed = Signal(str)
    font_changed = Signal(str)
    font_size_changed = Signal(int)
    bold_toggled = Signal(bool)
    italic_toggled = Signal(bool)
    undo_clicked = Signal()
    clear_clicked = Signal()
    copy_clicked = Signal()
    save_clicked = Signal()
    cancel_clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("barraFlotante")
        self.setAttribute(Qt.WA_StyledBackground, True)
        # sobre la barra el mouse es una flecha normal, no la cruz del
        # overlay que tiene debajo
        self.setCursor(Qt.ArrowCursor)

        columna = QVBoxLayout(self)
        columna.setContentsMargins(8, 6, 8, 6)
        columna.setSpacing(4)

        fila = QHBoxLayout()
        fila.setSpacing(2)
        columna.addLayout(fila)

        self._botones: dict[str, AnimatedButton] = {}

        def boton(nombre_icono: str, tooltip: str, marcable: bool = False) -> AnimatedButton:
            b = AnimatedButton()
            b.setIcon(icon(nombre_icono, theme.icon_color()))
            b.setIconSize(QSize(20, 20))
            b.setToolTip(tooltip)
            b.setCheckable(marcable)
            b.setCursor(Qt.PointingHandCursor)
            fila.addWidget(b)
            return b

        def separador():
            linea = QFrame()
            linea.setFrameShape(QFrame.VLine)
            linea.setStyleSheet("color: rgba(128,128,128,60);")
            fila.addWidget(linea)

        self._botones["select"] = boton("select", t("tool.select"), True)
        self._botones["shape"] = boton("shape-rect", t("tool.shapes"), True)
        self._menu_formas(self._botones["shape"])
        self._botones["line"] = boton("line", t("tool.line"), True)
        self._botones["arrow"] = boton("arrow", t("tool.arrow"), True)
        self._botones["brush"] = boton("brush", t("tool.brush"), True)
        self._botones["text"] = boton("text", t("tool.text"), True)
        self._botones["pixelate"] = boton("pixelate", t("tool.pixelate"), True)
        separador()
        deshacer = boton("undo", t("tool.undo"))
        limpiar = boton("clear", t("tool.clear"))
        separador()
        copiar = boton("copy", t("tool.copy") + "  (Ctrl+C)")
        guardar = boton("save", t("tool.save") + "  (Ctrl+S)")
        cancelar = boton("close", t("tool.cancel") + "  (Esc)")

        for nombre, b in self._botones.items():
            if nombre != "shape":
                b.clicked.connect(lambda _=False, n=nombre: self.activate(n))
        deshacer.clicked.connect(self.undo_clicked)
        limpiar.clicked.connect(self.clear_clicked)
        copiar.clicked.connect(self.copy_clicked)
        guardar.clicked.connect(self.save_clicked)
        cancelar.clicked.connect(self.cancel_clicked)

        self._armar_contextual(columna)
        self.activate("select")

    # ------------------------------------------------------------------ #
    # construcción

    def _menu_formas(self, boton: AnimatedButton):
        menu = QMenu(self)
        nombres = {"rect": t("tool.rect"), "rounded": t("tool.rounded"),
                   "ellipse": t("tool.ellipse"), "triangle": t("tool.triangle"),
                   "diamond": t("tool.diamond"), "pentagon": t("tool.pentagon"),
                   "hexagon": t("tool.hexagon"), "star": t("tool.star")}
        for clave, (icono, _clase) in an.SHAPES.items():
            accion = menu.addAction(icon(icono, theme.icon_color()), nombres[clave])
            accion.triggered.connect(lambda _=False, c=clave, i=icono: self._elegir_forma(c, i))
        boton.setMenu(menu)
        boton.setPopupMode(AnimatedButton.InstantPopup)

    def _armar_contextual(self, columna: QVBoxLayout):
        self._contextual = QWidget()
        ctx = QHBoxLayout(self._contextual)
        ctx.setContentsMargins(2, 0, 2, 0)
        ctx.setSpacing(8)
        columna.addWidget(self._contextual)

        self._paleta = ColorPalette()
        self._paleta.color_selected.connect(self.color_changed)
        ctx.addWidget(self._paleta)

        self._rotulo_grosor = QLabel(t("tool.thickness"))
        self._rotulo_grosor.setObjectName("secundario")
        ctx.addWidget(self._rotulo_grosor)
        self._grosor = QSlider(Qt.Horizontal)
        self._grosor.setRange(1, 24)
        self._grosor.setValue(3)
        self._grosor.setFixedWidth(80)
        self._grosor.valueChanged.connect(self.width_changed)
        ctx.addWidget(self._grosor)

        # estilo del trazo: continuo, discontinuo o punteado
        self._trazo = QComboBox()
        for clave, texto in (("solid", t("tool.dash_solid")), ("dashed", t("tool.dash_dashed")),
                             ("dotted", t("tool.dash_dotted"))):
            self._trazo.addItem(texto, clave)
        self._trazo.currentIndexChanged.connect(
            lambda i: self.dash_changed.emit(self._trazo.itemData(i)))
        ctx.addWidget(self._trazo)

        # remates de inicio y de final para líneas y flechas
        nombres_cap = {"none": t("tool.cap_none"), "arrow": t("tool.cap_arrow"),
                       "arrow_filled": t("tool.cap_arrow_filled"), "dot": t("tool.cap_dot"),
                       "square": t("tool.cap_square"), "diamond": t("tool.cap_diamond")}
        self._cap_inicio = QComboBox()
        self._cap_fin = QComboBox()
        for clave in an.CAPS:
            self._cap_inicio.addItem(f'{t("tool.line_start")}: {nombres_cap[clave]}', clave)
            self._cap_fin.addItem(f'{t("tool.line_end")}: {nombres_cap[clave]}', clave)
        self._cap_inicio.currentIndexChanged.connect(
            lambda i: self.cap_start_changed.emit(self._cap_inicio.itemData(i)))
        self._cap_fin.currentIndexChanged.connect(
            lambda i: self.cap_end_changed.emit(self._cap_fin.itemData(i)))
        ctx.addWidget(self._cap_inicio)
        ctx.addWidget(self._cap_fin)

        # tipografía en desplegable, cada nombre pintado con su propia letra
        self._fuente = QComboBox()
        self._fuente.setFixedWidth(160)
        for familia in FONTS:
            self._fuente.addItem(familia)
            self._fuente.setItemData(self._fuente.count() - 1, QFont(familia), Qt.FontRole)
        self._fuente.currentTextChanged.connect(self.font_changed)
        ctx.addWidget(self._fuente)

        self._tamano = QSpinBox()
        self._tamano.setRange(8, 96)
        self._tamano.setValue(18)
        self._tamano.setToolTip(t("tool.fontsize"))
        self._tamano.valueChanged.connect(self.font_size_changed)
        ctx.addWidget(self._tamano)

        self._negrita = AnimatedButton()
        self._negrita.setIcon(icon("bold", theme.icon_color()))
        self._negrita.setCheckable(True)
        self._negrita.setToolTip(t("tool.bold"))
        self._negrita.toggled.connect(self.bold_toggled)
        ctx.addWidget(self._negrita)

        self._cursiva = AnimatedButton()
        self._cursiva.setIcon(icon("italic", theme.icon_color()))
        self._cursiva.setCheckable(True)
        self._cursiva.setToolTip(t("tool.italic"))
        self._cursiva.toggled.connect(self.italic_toggled)
        ctx.addWidget(self._cursiva)

        ctx.addStretch()

    # ------------------------------------------------------------------ #
    # estado

    def _elegir_forma(self, clave: str, icono: str):
        self._botones["shape"].setIcon(icon(icono, theme.icon_color()))
        self.activate("shape")
        self.shape_changed.emit(clave)

    def activate(self, nombre: str):
        for n, b in self._botones.items():
            b.setChecked(n == nombre)
        self.tool_changed.emit(nombre)
        self.configure(nombre)

    def configure(self, tipo: str, item: an.Item | None = None):
        """decide qué controles se ven y con qué valores.

        sin item, los controles muestran los valores por defecto de la
        herramienta; con item, cargan los del elemento para editarlo. las
        señales se silencian durante la carga, si no cada setValue
        dispararía un cambio fantasma sobre el propio elemento.
        """
        es_forma = tipo in ("shape",)
        es_lineal = tipo in ("line", "arrow")
        es_trazo = es_forma or es_lineal or tipo == "brush"
        es_texto = tipo == "text"
        es_pixel = tipo == "pixelate"

        self._contextual.setVisible(es_trazo or es_texto or es_pixel)
        self._paleta.setVisible(es_trazo or es_texto)
        self._rotulo_grosor.setVisible(es_trazo or es_pixel)
        self._grosor.setVisible(es_trazo or es_pixel)
        self._trazo.setVisible(es_forma or es_lineal)
        self._cap_inicio.setVisible(es_lineal)
        self._cap_fin.setVisible(es_lineal)
        self._fuente.setVisible(es_texto)
        self._tamano.setVisible(es_texto)
        self._negrita.setVisible(es_texto)
        self._cursiva.setVisible(es_texto)

        if item is not None:
            for control in (self._grosor, self._trazo, self._cap_inicio, self._cap_fin,
                            self._fuente, self._tamano, self._negrita, self._cursiva):
                control.blockSignals(True)
            self._grosor.setValue(int(item.width))
            self._trazo.setCurrentIndex(max(0, self._trazo.findData(item.dash)))
            if isinstance(item, an.LineItem):
                self._cap_inicio.setCurrentIndex(max(0, self._cap_inicio.findData(item.cap_start)))
                self._cap_fin.setCurrentIndex(max(0, self._cap_fin.findData(item.cap_end)))
            if isinstance(item, an.TextItem):
                indice = self._fuente.findText(item.font.family())
                if indice >= 0:
                    self._fuente.setCurrentIndex(indice)
                self._tamano.setValue(item.font.pointSize())
                self._negrita.setChecked(item.font.bold())
                self._cursiva.setChecked(item.font.italic())
            for control in (self._grosor, self._trazo, self._cap_inicio, self._cap_fin,
                            self._fuente, self._tamano, self._negrita, self._cursiva):
                control.blockSignals(False)

        self.adjustSize()


class SelectionOverlay(QWidget):
    copied = Signal(QImage)
    save_requested = Signal(QImage)
    closed = Signal()

    def __init__(self):
        super().__init__(None, Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_DeleteOnClose, True)
        self.setMouseTracking(True)

        # la foto congelada de todos los monitores, en resolución física
        self._imagen = capture.grab_virtual_screen()
        self._dpr = capture.device_pixel_ratio()
        self.setGeometry(QGuiApplication.primaryScreen().virtualGeometry())

        self._fase = "seleccionando"          # seleccionando | editando
        self._sel = QRectF()
        self._origen: QPointF | None = None
        self._items: list[an.Item] = []
        self._activo: an.Item | None = None
        self._arrastre: dict | None = None

        # valores por defecto de cada herramienta nueva
        self._tool = "select"
        self._forma = "rect"
        self._color = QColor("#e5484d")
        self._ancho = 3
        self._dash = "solid"
        self._cap_inicio = "none"
        self._cap_fin = "arrow_filled"
        self._fuente = QFont("Segoe UI", 18)

        self._editor: QLineEdit | None = None
        self._editor_pos = QPointF()

        self._barra = _Toolbar(self)
        self._barra.hide()
        self._conectar_barra()

        self.setCursor(Qt.CrossCursor)

    def _conectar_barra(self):
        b = self._barra
        b.tool_changed.connect(self._cambiar_tool)
        b.shape_changed.connect(lambda f: setattr(self, "_forma", f))
        b.color_changed.connect(self._aplicar_color)
        b.width_changed.connect(self._aplicar_grosor)
        b.dash_changed.connect(self._aplicar_dash)
        b.cap_start_changed.connect(lambda c: self._aplicar_cap("cap_start", c))
        b.cap_end_changed.connect(lambda c: self._aplicar_cap("cap_end", c))
        b.font_changed.connect(self._aplicar_fuente)
        b.font_size_changed.connect(self._aplicar_tamano)
        b.bold_toggled.connect(lambda v: self._aplicar_estilo_fuente("setBold", v))
        b.italic_toggled.connect(lambda v: self._aplicar_estilo_fuente("setItalic", v))
        b.undo_clicked.connect(self._deshacer)
        b.clear_clicked.connect(self._limpiar)
        b.copy_clicked.connect(self._copiar)
        b.save_clicked.connect(self._guardar)
        b.cancel_clicked.connect(self.close)

    # ------------------------------------------------------------------ #
    # propiedades: cada cambio afecta al elemento seleccionado si lo hay,
    # y de paso queda como valor por defecto para el próximo dibujo

    def _cambiar_tool(self, nombre: str):
        self._tool = nombre
        self._commit_texto()
        if nombre != "select":
            self._activo = None
        self.setCursor({"select": Qt.ArrowCursor, "text": Qt.IBeamCursor}.get(nombre, Qt.CrossCursor))
        self.update()

    def _aplicar_color(self, color: QColor):
        self._color = QColor(color)
        if self._activo is not None and not isinstance(self._activo, an.PixelateItem):
            self._activo.color = QColor(color)
            self.update()

    def _aplicar_grosor(self, valor: int):
        self._ancho = valor
        if self._activo is not None:
            self._activo.width = valor
            self.update()

    def _aplicar_dash(self, dash: str):
        self._dash = dash
        if self._activo is not None:
            self._activo.dash = dash
            self.update()

    def _aplicar_cap(self, extremo: str, remate: str):
        if extremo == "cap_start":
            self._cap_inicio = remate
        else:
            self._cap_fin = remate
        if isinstance(self._activo, an.LineItem):
            setattr(self._activo, extremo, remate)
            self.update()

    def _aplicar_fuente(self, familia: str):
        self._fuente.setFamily(familia)
        if isinstance(self._activo, an.TextItem):
            self._activo.font.setFamily(familia)
            self.update()

    def _aplicar_tamano(self, puntos: int):
        self._fuente.setPointSize(puntos)
        if isinstance(self._activo, an.TextItem):
            self._activo.font.setPointSize(puntos)
            self.update()

    def _aplicar_estilo_fuente(self, metodo: str, valor: bool):
        getattr(self._fuente, metodo)(valor)
        if isinstance(self._activo, an.TextItem):
            getattr(self._activo.font, metodo)(valor)
            self.update()

    # ------------------------------------------------------------------ #
    # acciones

    def _deshacer(self):
        self._commit_texto()
        if self._items:
            quitado = self._items.pop()
            if quitado is self._activo:
                self._activo = None
            self.update()

    def _limpiar(self):
        self._commit_texto()
        self._items.clear()
        self._activo = None
        self.update()

    def _copiar(self):
        imagen = self._exportar()
        if not imagen.isNull():
            self.copied.emit(imagen)
        self.close()

    def _guardar(self):
        imagen = self._exportar()
        self.close()
        if not imagen.isNull():
            self.save_requested.emit(imagen)

    def _exportar(self) -> QImage:
        """imagen final: el recorte a resolución nativa más las anotaciones.

        el pintor se escala al factor de la pantalla y se corre al origen de
        la selección; los elementos, que viven en coordenadas lógicas, caen
        exactos sobre los píxeles físicos.
        """
        self._commit_texto()
        if self._sel.width() < 1 or self._sel.height() < 1:
            return QImage()
        fisico = QRect(round(self._sel.x() * self._dpr), round(self._sel.y() * self._dpr),
                       round(self._sel.width() * self._dpr), round(self._sel.height() * self._dpr))
        salida = self._imagen.copy(fisico)
        pintor = QPainter(salida)
        pintor.setRenderHint(QPainter.Antialiasing)
        pintor.setRenderHint(QPainter.TextAntialiasing)
        pintor.scale(self._dpr, self._dpr)
        pintor.translate(-self._sel.x(), -self._sel.y())
        for item in self._items:
            item.paint(pintor)
        pintor.end()
        return salida

    # ------------------------------------------------------------------ #
    # texto en línea

    def _abrir_editor(self, pos: QPointF, existente: an.TextItem | None = None):
        """caja de texto que se escribe directamente sobre la captura."""
        self._commit_texto()
        editor = QLineEdit(self)
        editor.setPlaceholderText(t("tool.text_placeholder"))
        editor.setFont(self._fuente if existente is None else existente.font)
        color = self._color if existente is None else existente.color
        editor.setStyleSheet(
            f"background: rgba(255,255,255,235); border: 1px dashed {theme.accent()};"
            f" border-radius: 4px; padding: 2px 6px; color: {color.name()};")
        if existente is not None:
            editor.setText(existente.text)
            posicion = existente.pos
            self._items.remove(existente)
            if self._activo is existente:
                self._activo = None
        else:
            posicion = pos
        editor.move(int(posicion.x()) - 4, int(posicion.y()) - 6)
        editor.setMinimumWidth(180)
        editor.show()
        editor.setFocus()
        editor.returnPressed.connect(self._commit_texto)
        self._editor = editor
        self._editor_pos = QPointF(posicion)

    def _commit_texto(self):
        if self._editor is None:
            return
        texto = self._editor.text().strip()
        fuente = QFont(self._editor.font())
        self._editor.deleteLater()
        self._editor = None
        if texto:
            self._items.append(an.TextItem(self._editor_pos, texto, fuente, self._color))
        self.update()

    # ------------------------------------------------------------------ #
    # eventos de mouse

    def mousePressEvent(self, e):
        if e.button() != Qt.LeftButton:
            return
        punto = QPointF(e.position())

        if self._fase == "seleccionando":
            self._origen = punto
            self._sel = QRectF(punto, punto)
            self.update()
            return

        if self._editor is not None:
            self._commit_texto()

        if self._tool == "select":
            self._press_seleccion(punto)
        elif self._tool == "text":
            if self._sel.contains(punto):
                self._abrir_editor(punto)
        else:
            self._press_dibujo(punto)
        self.update()

    def _tiradores_seleccion(self) -> list[QPointF]:
        r = self._sel
        return [r.topLeft(), QPointF(r.center().x(), r.top()), r.topRight(),
                QPointF(r.right(), r.center().y()), r.bottomRight(),
                QPointF(r.center().x(), r.bottom()), r.bottomLeft(),
                QPointF(r.left(), r.center().y())]

    def _press_seleccion(self, punto: QPointF):
        """el clic con la herramienta de selección resuelve, en orden: un
        tirador del elemento activo, un elemento para tomarlo, un tirador
        de la propia selección para redimensionarla, o el interior de la
        selección para moverla entera."""
        if self._activo is not None:
            for i, tirador in enumerate(self._activo.handles()):
                if (tirador - punto).manhattanLength() <= _LADO_TIRADOR + 4:
                    self._arrastre = {"modo": "tirador", "indice": i}
                    return
        for item in reversed(self._items):
            if item.contains(punto):
                self._activo = item
                self._barra.configure(self._tipo_de(item), item)
                self._arrastre = {"modo": "mover", "desde": punto}
                return
        self._activo = None
        self._barra.configure("select")
        for i, tirador in enumerate(self._tiradores_seleccion()):
            if (tirador - punto).manhattanLength() <= _LADO_TIRADOR + 4:
                self._arrastre = {"modo": "sel_tirador", "indice": i}
                return
        if self._sel.contains(punto):
            self._arrastre = {"modo": "sel_mover", "desde": punto}

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
        if not self._sel.contains(punto):
            return
        if self._tool == "shape":
            clase = an.SHAPES[self._forma][1]
            nuevo = clase(QRectF(punto, punto), self._color, self._ancho)
            nuevo.dash = self._dash
        elif self._tool == "line":
            nuevo = an.LineItem(punto, punto, self._color, self._ancho)
            nuevo.dash = self._dash
        elif self._tool == "arrow":
            nuevo = an.LineItem(punto, punto, self._color, self._ancho,
                                self._cap_inicio, self._cap_fin)
            nuevo.dash = self._dash
        elif self._tool == "brush":
            nuevo = an.BrushItem(punto, self._color, self._ancho)
        elif self._tool == "pixelate":
            nuevo = an.PixelateItem(QRectF(punto, punto), self._imagen, self._dpr, self._ancho + 9)
        else:
            return
        self._items.append(nuevo)
        self._arrastre = {"modo": "crear", "item": nuevo, "origen": punto}

    def mouseMoveEvent(self, e):
        punto = QPointF(e.position())

        if self._fase == "seleccionando":
            if self._origen is not None:
                self._sel = QRectF(self._origen, punto).normalized()
                self.update()
            return

        if not self._arrastre:
            self._actualizar_cursor_hover(punto)
            return
        modo = self._arrastre["modo"]
        if modo == "crear":
            item = self._arrastre["item"]
            if isinstance(item, an.BrushItem):
                item.add_point(punto)
            elif isinstance(item, an.ShapeItem):
                item.rect = QRectF(self._arrastre["origen"], punto).normalized()
            elif isinstance(item, an.LineItem):
                item.p2 = punto
        elif modo == "mover":
            delta = punto - self._arrastre["desde"]
            self._activo.move_by(delta.x(), delta.y())
            self._arrastre["desde"] = punto
        elif modo == "tirador":
            self._activo.set_handle(self._arrastre["indice"], punto)
        elif modo == "sel_mover":
            delta = punto - self._arrastre["desde"]
            movida = self._sel.translated(delta)
            # la selección se queda dentro de la pantalla, nunca a medias
            if self.rect().contains(movida.toRect()):
                self._sel = movida
                self._arrastre["desde"] = punto
        elif modo == "sel_tirador":
            self._redimensionar_seleccion(self._arrastre["indice"], punto)
        self.update()

    def _actualizar_cursor_hover(self, punto: QPointF):
        """con la herramienta de selección, el cursor anticipa qué se puede
        agarrar: flecha de tamaño sobre tiradores, mano abierta sobre
        elementos, flecha normal en el resto."""
        if self._tool != "select":
            return
        objetivo = Qt.ArrowCursor
        tiradores = (self._activo.handles() if self._activo is not None else []) or []
        for tirador in list(tiradores) + self._tiradores_seleccion():
            if (tirador - punto).manhattanLength() <= _LADO_TIRADOR + 4:
                objetivo = Qt.SizeAllCursor
                break
        else:
            for item in reversed(self._items):
                if item.contains(punto):
                    objetivo = Qt.OpenHandCursor
                    break
        self.setCursor(objetivo)

    def _redimensionar_seleccion(self, indice: int, pos: QPointF):
        r = QRectF(self._sel)
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
        r = r.normalized()
        if r.width() >= 20 and r.height() >= 20:
            self._sel = r

    def mouseReleaseEvent(self, e):
        if e.button() != Qt.LeftButton:
            return

        if self._fase == "seleccionando":
            self._origen = None
            if self._sel.width() >= 5 and self._sel.height() >= 5:
                self._fase = "editando"
                self.setCursor(Qt.ArrowCursor)
                self._mostrar_barra()
            self.update()
            return

        if self._arrastre and self._arrastre["modo"] == "crear":
            item = self._arrastre["item"]
            # un clic sin arrastre deja una figura de tamaño cero que solo
            # estorba; se descarta en silencio
            if item.bounding().width() < 8 and item.bounding().height() < 8:
                if item in self._items:
                    self._items.remove(item)
            else:
                if self._tool != "brush":
                    self._activo = item
                    self._barra.configure(self._tipo_de(item), item)
        elif self._arrastre and self._arrastre["modo"] in ("sel_mover", "sel_tirador"):
            # tras mover o agrandar la selección, la barra se reacomoda
            self._posicionar_barra()
        self._arrastre = None
        self.update()

    def mouseDoubleClickEvent(self, e):
        if self._fase != "editando":
            return
        punto = QPointF(e.position())
        for item in reversed(self._items):
            if isinstance(item, an.TextItem) and item.contains(punto):
                self._abrir_editor(punto, existente=item)
                return

    # ------------------------------------------------------------------ #
    # teclado

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Escape:
            if self._editor is not None:
                self._editor.deleteLater()
                self._editor = None
                return
            self.close()
        elif e.matches(QKeySequence.Copy):
            self._copiar()
        elif e.matches(QKeySequence.Save):
            self._guardar()
        elif e.matches(QKeySequence.Undo):
            self._deshacer()
        elif e.key() == Qt.Key_Delete and self._activo is not None:
            self._items.remove(self._activo)
            self._activo = None
            self.update()
        else:
            super().keyPressEvent(e)

    def closeEvent(self, e):
        self.closed.emit()
        super().closeEvent(e)

    # ------------------------------------------------------------------ #
    # barra de herramientas

    def _posicionar_barra(self):
        """la barra vive pegada bajo la selección; si no hay lugar abajo se
        acomoda arriba, y como último recurso dentro de la selección."""
        self._barra.adjustSize()
        alto = self._barra.height()
        ancho = self._barra.width()
        x = min(max(self._sel.left(), 0), self.width() - ancho - 8)
        if self._sel.bottom() + alto + 10 <= self.height():
            y = self._sel.bottom() + 8
        elif self._sel.top() - alto - 10 >= 0:
            y = self._sel.top() - alto - 8
        else:
            y = self._sel.bottom() - alto - 8
        self._barra.move(int(x), int(y))

    def _mostrar_barra(self):
        self._posicionar_barra()
        efecto = QGraphicsOpacityEffect(self._barra)
        self._barra.setGraphicsEffect(efecto)
        self._barra.show()
        animacion = QPropertyAnimation(efecto, b"opacity", self._barra)
        animacion.setDuration(180)
        animacion.setStartValue(0.0)
        animacion.setEndValue(1.0)
        animacion.setEasingCurve(QEasingCurve.OutCubic)
        animacion.start(QPropertyAnimation.DeleteWhenStopped)

    # ------------------------------------------------------------------ #
    # pintura

    def paintEvent(self, _):
        pintor = QPainter(self)
        pintor.setRenderHint(QPainter.Antialiasing)

        pintor.drawImage(self.rect(), self._imagen)

        # el velo oscuro cubre todo menos la selección, que queda limpia
        velo = QColor(0, 0, 0, 110)
        if self._sel.isValid() and self._sel.width() > 0:
            s = self._sel
            pintor.fillRect(QRectF(0, 0, self.width(), s.top()), velo)
            pintor.fillRect(QRectF(0, s.bottom(), self.width(), self.height() - s.bottom()), velo)
            pintor.fillRect(QRectF(0, s.top(), s.left(), s.height()), velo)
            pintor.fillRect(QRectF(s.right(), s.top(), self.width() - s.right(), s.height()), velo)

            pintor.setPen(QPen(QColor(theme.accent()), 1.6))
            pintor.setBrush(Qt.NoBrush)
            pintor.drawRect(s)
            self._pintar_medidas(pintor)
        else:
            pintor.fillRect(self.rect(), velo)

        if self._fase == "seleccionando":
            self._pintar_pista(pintor)

        if self._fase == "editando":
            pintor.save()
            pintor.setClipRect(self._sel)
            for item in self._items:
                item.paint(pintor)
            pintor.restore()

            # los tiradores de la selección se muestran cuando no hay un
            # elemento tomado, para invitar a moverla o agrandarla
            if self._activo is not None:
                self._pintar_tiradores(pintor, self._activo.handles(), self._activo)
            elif self._tool == "select":
                self._pintar_tiradores(pintor, self._tiradores_seleccion())

        pintor.end()

    def _pintar_medidas(self, pintor: QPainter):
        """chip con el tamaño real de la captura, en píxeles físicos."""
        texto = f"{round(self._sel.width() * self._dpr)} × {round(self._sel.height() * self._dpr)}"
        pintor.setFont(QFont("Segoe UI", 9))
        medidas = pintor.fontMetrics().boundingRect(texto).adjusted(-8, -4, 8, 4)
        x = self._sel.left()
        y = self._sel.top() - medidas.height() - 6
        if y < 0:
            y = self._sel.top() + 6
        chip = QRectF(x, y, medidas.width(), medidas.height())
        pintor.setPen(Qt.NoPen)
        pintor.setBrush(QColor(0, 0, 0, 170))
        pintor.drawRoundedRect(chip, 5, 5)
        pintor.setPen(QColor("#ffffff"))
        pintor.drawText(chip, Qt.AlignCenter, texto)

    def _pintar_pista(self, pintor: QPainter):
        """instrucción flotante arriba al centro mientras no hay selección."""
        texto = t("sel.hint")
        pintor.setFont(QFont("Segoe UI", 10))
        medidas = pintor.fontMetrics().boundingRect(texto).adjusted(-14, -8, 14, 8)
        chip = QRectF((self.width() - medidas.width()) / 2, 28, medidas.width(), medidas.height())
        pintor.setPen(Qt.NoPen)
        pintor.setBrush(QColor(0, 0, 0, 170))
        pintor.drawRoundedRect(chip, 8, 8)
        pintor.setPen(QColor("#ffffff"))
        pintor.drawText(chip, Qt.AlignCenter, texto)

    def _pintar_tiradores(self, pintor: QPainter, tiradores: list[QPointF], item: an.Item | None = None):
        pintor.setPen(QPen(QColor(theme.accent()), 1.2))
        pintor.setBrush(QColor("#ffffff"))
        mitad = _LADO_TIRADOR / 2
        for tirador in tiradores:
            pintor.drawRect(QRectF(tirador.x() - mitad, tirador.y() - mitad, _LADO_TIRADOR, _LADO_TIRADOR))
        if item is not None and not tiradores:
            # los elementos sin tiradores (pincel, texto) marcan su contorno
            # punteado para que se note cuál está tomado
            pluma = QPen(QColor(theme.accent()), 1)
            pluma.setStyle(Qt.DashLine)
            pintor.setPen(pluma)
            pintor.setBrush(Qt.NoBrush)
            pintor.drawRect(item.bounding())
