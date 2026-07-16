"""overlay de captura de región: pantalla congelada, selección y edición.

cubre todos los monitores con una foto de la pantalla, deja recortar la
zona arrastrando y abre debajo la barra para anotarla. la selección y cada
anotación se pueden mover y redimensionar, y sus propiedades se editan en
vivo. ctrl+c copia, ctrl+s guarda, ctrl+z deshace y esc cancela; el
resultado sale por señales y la app resuelve portapapeles y guardado.
"""

from PySide6.QtCore import (QEasingCurve, QPointF, QPropertyAnimation, QRect,
                            QRectF, QSize, Qt, QTimer, Signal)
from PySide6.QtGui import (QColor, QFont, QGuiApplication, QImage,
                           QKeySequence, QPainter, QPainterPath, QPen)
from PySide6.QtWidgets import (QCheckBox, QComboBox, QFrame,
                               QGraphicsOpacityEffect, QHBoxLayout, QLabel,
                               QLineEdit, QMenu, QMessageBox, QSlider,
                               QSpinBox, QVBoxLayout, QWidget)

from src.core import capture
from src.i18n.translator import t
from src.ui.overlays import annotation_tools as an
from src.ui.themes.theme_manager import theme
from src.ui.widgets.animated_button import AnimatedButton
from src.ui.widgets.color_palette import ColorPalette
from src.ui.widgets.icons import icon

# lado de los cuadraditos de agarre, tanto de la selección como de los items
_LADO_TIRADOR = 8.0

# el desplegable de texto ofrece todas las tipografías del sistema, las
# mismas que la pizarra de presentación
from src.ui.overlays.properties_panel import system_fonts


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
    opacity_changed = Signal(float)
    font_changed = Signal(str)
    font_size_changed = Signal(int)
    bold_toggled = Signal(bool)
    italic_toggled = Signal(bool)
    pixel_mode_changed = Signal(str)
    pixel_amount_changed = Signal(int)
    pixel_size_changed = Signal(int)
    eraser_size_changed = Signal(int)
    layout_changed = Signal()
    undo_clicked = Signal()
    redo_clicked = Signal()
    clear_clicked = Signal()
    copy_clicked = Signal()
    save_clicked = Signal()
    cancel_clicked = Signal()

    def __init__(self, parent=None, opciones_flotantes=False):
        super().__init__(parent)
        self.setObjectName("barraFlotante")
        self.setAttribute(Qt.WA_StyledBackground, True)
        # sobre la barra el mouse es una flecha normal, no la cruz del
        # overlay que tiene debajo
        self.setCursor(Qt.ArrowCursor)
        # en el overlay de captura la barra de opciones flota aparte para no
        # estirar las herramientas; en el editor de ventana va embebida
        self._opciones_flotantes = opciones_flotantes

        columna = QVBoxLayout(self)
        columna.setContentsMargins(8, 6, 8, 6)
        columna.setSpacing(4)
        self._columna = columna

        fila = QHBoxLayout()
        fila.setSpacing(2)
        columna.addLayout(fila)
        self._fila = fila
        self._separadores: list[QFrame] = []
        self._vertical = False

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
            self._separadores.append(linea)

        self._botones["select"] = boton("select", t("tool.select"), True)
        self._botones["shape"] = boton("shape-rect", t("tool.shapes"), True)
        self._menu_formas(self._botones["shape"])
        self._botones["line"] = boton("line", t("tool.line"), True)
        self._botones["arrow"] = boton("arrow", t("tool.arrow"), True)
        self._botones["brush"] = boton("brush", t("tool.brush"), True)
        self._botones["text"] = boton("text", t("tool.text"), True)
        self._botones["pixelate"] = boton("pixelate", t("tool.pixelate"), True)
        self._botones["eraser"] = boton("eraser", t("tool.eraser"), True)
        separador()
        deshacer = boton("undo", t("tool.undo") + "  (Ctrl+Z)")
        rehacer = boton("redo", t("tool.redo") + "  (Ctrl+Y)")
        limpiar = boton("clear", t("tool.clear"))
        separador()
        copiar = boton("copy", t("tool.copy") + "  (Ctrl+C)")
        guardar = boton("save", t("tool.save") + "  (Ctrl+S)")
        cancelar = boton("close", t("tool.cancel") + "  (Esc)")

        for nombre, b in self._botones.items():
            if nombre != "shape":
                b.clicked.connect(lambda _=False, n=nombre: self.activate(n))
        deshacer.clicked.connect(self.undo_clicked)
        rehacer.clicked.connect(self.redo_clicked)
        limpiar.clicked.connect(self.clear_clicked)
        copiar.clicked.connect(self.copy_clicked)
        guardar.clicked.connect(self.save_clicked)
        cancelar.clicked.connect(self.cancel_clicked)

        self._armar_contextual()
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

    def _armar_contextual(self):
        self._hay_opciones = False
        if self._opciones_flotantes:
            # ventanita aparte, hija del overlay, para no estirar la barra de
            # herramientas; el overlay la ubica flotando debajo
            self._contextual = QWidget(self.parent())
            self._contextual.setObjectName("barraFlotante")
            self._contextual.setAttribute(Qt.WA_StyledBackground, True)
            self._contextual.setCursor(Qt.ArrowCursor)
            self._contextual.hide()
            ctx = QHBoxLayout(self._contextual)
            ctx.setContentsMargins(8, 6, 8, 6)
            ctx.setSpacing(8)
        else:
            # embebida como segunda fila de la propia barra
            self._contextual = QWidget()
            self._columna.addWidget(self._contextual)
            ctx = QHBoxLayout(self._contextual)
            ctx.setContentsMargins(2, 0, 2, 0)
            ctx.setSpacing(8)
        self._ctx = ctx

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

        # todos los estilos de trazo del modelo, en el mismo orden
        nombres_dash = {"solid": t("tool.dash_solid"), "dashed": t("tool.dash_dashed"),
                        "dotted": t("tool.dash_dotted"), "dashdot": t("tool.dash_dashdot"),
                        "dashdotdot": t("tool.dash_dashdotdot")}
        self._trazo = QComboBox()
        for clave in an.DASHES:
            self._trazo.addItem(nombres_dash[clave], clave)
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
        for familia in system_fonts():
            self._fuente.addItem(familia)
            self._fuente.setItemData(self._fuente.count() - 1, QFont(familia), Qt.FontRole)
        indice_defecto = self._fuente.findText("Segoe UI")
        if indice_defecto >= 0:
            self._fuente.setCurrentIndex(indice_defecto)
        self._fuente.currentTextChanged.connect(self.font_changed)
        ctx.addWidget(self._fuente)

        self._tamano = QSpinBox()
        self._tamano.setRange(8, 96)
        self._tamano.setValue(18)
        self._tamano.setToolTip(t("tool.fontsize"))
        self._tamano.valueChanged.connect(self.font_size_changed)
        ctx.addWidget(self._tamano)

        # opacidad del elemento, de translúcido a sólido
        self._rotulo_opacidad = QLabel(t("tool.opacity"))
        self._rotulo_opacidad.setObjectName("secundario")
        ctx.addWidget(self._rotulo_opacidad)
        self._opacidad = QSlider(Qt.Horizontal)
        self._opacidad.setRange(10, 100)
        self._opacidad.setValue(100)
        self._opacidad.setFixedWidth(70)
        self._opacidad.valueChanged.connect(lambda v: self.opacity_changed.emit(v / 100.0))
        ctx.addWidget(self._opacidad)

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

        # controles del pincel de ocultar: efecto, intensidad y grosor. sus
        # valores por defecto no se guardan, arrancan siempre igual
        self._pixel_modo = QComboBox()
        self._pixel_modo.addItem(t("pixel.pixelate"), "pixelate")
        self._pixel_modo.addItem(t("pixel.blur"), "blur")
        self._pixel_modo.setCurrentIndex(
            max(0, self._pixel_modo.findData(an.PIXEL_MODO)))
        self._pixel_modo.currentIndexChanged.connect(
            lambda i: self.pixel_mode_changed.emit(self._pixel_modo.itemData(i)))
        ctx.addWidget(self._pixel_modo)
        self._rotulo_pixel = QLabel(t("pixel.amount"))
        self._rotulo_pixel.setObjectName("secundario")
        ctx.addWidget(self._rotulo_pixel)
        self._pixel_cantidad = QSlider(Qt.Horizontal)
        self._pixel_cantidad.setRange(2, 40)
        self._pixel_cantidad.setValue(an.PIXEL_CANTIDAD)
        self._pixel_cantidad.setFixedWidth(70)
        self._pixel_cantidad.valueChanged.connect(self.pixel_amount_changed)
        ctx.addWidget(self._pixel_cantidad)
        self._rotulo_pixel_g = QLabel(t("pixel.brush"))
        self._rotulo_pixel_g.setObjectName("secundario")
        ctx.addWidget(self._rotulo_pixel_g)
        self._pixel_grosor = QSlider(Qt.Horizontal)
        self._pixel_grosor.setRange(6, 120)
        self._pixel_grosor.setValue(an.PIXEL_GROSOR)
        self._pixel_grosor.setFixedWidth(70)
        self._pixel_grosor.valueChanged.connect(self.pixel_size_changed)
        ctx.addWidget(self._pixel_grosor)

        # el borrador solo tiene grosor: el tamaño del área que limpia
        self._rotulo_borrador = QLabel(t("tool.thickness"))
        self._rotulo_borrador.setObjectName("secundario")
        ctx.addWidget(self._rotulo_borrador)
        self._borrador_grosor = QSlider(Qt.Horizontal)
        self._borrador_grosor.setRange(6, 120)
        self._borrador_grosor.setValue(an.BORRADOR_GROSOR)
        self._borrador_grosor.setFixedWidth(70)
        self._borrador_grosor.valueChanged.connect(self.eraser_size_changed)
        ctx.addWidget(self._borrador_grosor)

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
        es_borrador = tipo == "eraser"

        es_imagen = isinstance(item, an.ImageItem)
        # el overlay se encarga de mostrar y ubicar la ventanita; aquí solo
        # se anota si hay algo que ofrecer para la herramienta actual
        self._hay_opciones = es_trazo or es_texto or es_pixel or es_borrador or es_imagen
        for w in (self._rotulo_borrador, self._borrador_grosor):
            w.setVisible(es_borrador)
        self._paleta.setVisible((es_trazo or es_texto) and not es_imagen)
        self._rotulo_grosor.setVisible(es_trazo and not es_imagen)
        self._grosor.setVisible(es_trazo and not es_imagen)
        self._rotulo_opacidad.setVisible(es_trazo or es_texto or es_imagen)
        self._opacidad.setVisible(es_trazo or es_texto or es_imagen)
        self._trazo.setVisible((es_forma or es_lineal) and not es_imagen)
        self._cap_inicio.setVisible(es_lineal)
        self._cap_fin.setVisible(es_lineal)
        self._fuente.setVisible(es_texto)
        self._tamano.setVisible(es_texto)
        self._negrita.setVisible(es_texto)
        self._cursiva.setVisible(es_texto)
        # los controles del pincel de ocultar solo con esa herramienta
        for w in (self._pixel_modo, self._rotulo_pixel, self._pixel_cantidad,
                  self._rotulo_pixel_g, self._pixel_grosor):
            w.setVisible(es_pixel)

        if isinstance(item, an.PixelateItem):
            for control in (self._pixel_modo, self._pixel_cantidad, self._pixel_grosor):
                control.blockSignals(True)
            self._pixel_modo.setCurrentIndex(max(0, self._pixel_modo.findData(item.mode)))
            self._pixel_cantidad.setValue(int(item.amount))
            self._pixel_grosor.setValue(int(item.width))
            for control in (self._pixel_modo, self._pixel_cantidad, self._pixel_grosor):
                control.blockSignals(False)

        if item is not None:
            for control in (self._grosor, self._trazo, self._cap_inicio, self._cap_fin,
                            self._fuente, self._tamano, self._negrita, self._cursiva,
                            self._opacidad):
                control.blockSignals(True)
            self._opacidad.setValue(int(item.opacity * 100))
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
                            self._fuente, self._tamano, self._negrita, self._cursiva,
                            self._opacidad):
                control.blockSignals(False)

        self._sincronizar_contextual()

    def configure_multi(self, items: list):
        """con varios elementos tomados, se muestran solo las opciones que
        aplican a todos a la vez: el color si todos lo tienen, el grosor si
        ninguno es texto, etc. así se editan en conjunto sin ofrecer algo
        que a alguno no le sirve."""
        def apoya(it, cual):
            if cual == "color":
                return not isinstance(it, (an.PixelateItem, an.ImageItem))
            if cual == "grosor":
                return not isinstance(it, (an.TextItem, an.ImageItem, an.PixelateItem))
            if cual == "opacidad":
                return not isinstance(it, an.PixelateItem)
            if cual == "dash":
                return isinstance(it, (an.ShapeItem, an.LineItem)) and not isinstance(it, an.ImageItem)
            if cual == "caps":
                return isinstance(it, an.LineItem)
            if cual == "texto":
                return isinstance(it, an.TextItem)
            return False

        color = all(apoya(i, "color") for i in items)
        grosor = all(apoya(i, "grosor") for i in items)
        opac = all(apoya(i, "opacidad") for i in items)
        dash = all(apoya(i, "dash") for i in items)
        caps = all(apoya(i, "caps") for i in items)
        texto = all(apoya(i, "texto") for i in items)

        self._hay_opciones = color or grosor or opac or dash or caps or texto
        self._paleta.setVisible(color)
        self._rotulo_grosor.setVisible(grosor)
        self._grosor.setVisible(grosor)
        self._rotulo_opacidad.setVisible(opac)
        self._opacidad.setVisible(opac)
        self._trazo.setVisible(dash)
        self._cap_inicio.setVisible(caps)
        self._cap_fin.setVisible(caps)
        for w in (self._fuente, self._tamano, self._negrita, self._cursiva):
            w.setVisible(texto)
        # ni pixelado ni borrador tienen sentido en conjunto
        for w in (self._pixel_modo, self._rotulo_pixel, self._pixel_cantidad,
                  self._rotulo_pixel_g, self._pixel_grosor,
                  self._rotulo_borrador, self._borrador_grosor):
            w.setVisible(False)
        self._sincronizar_contextual()

    def _sincronizar_contextual(self):
        # embebida, la barra decide sola si la fila de opciones se ve;
        # flotante, es el overlay quien la muestra y ubica
        if not self._opciones_flotantes:
            self._contextual.setVisible(self._hay_opciones)
        self.adjustSize()
        self._contextual.adjustSize()
        self.layout_changed.emit()

    def orientar(self, vertical: bool):
        """cambia la barra entre horizontal y en columna al costado.

        cuando la selección llega abajo del monitor y no cabe ni arriba ni
        debajo, la barra se planta vertical a un lado, con las mismas
        herramientas y controles, solo que apilados.
        """
        if vertical == self._vertical:
            return
        self._vertical = vertical
        from PySide6.QtWidgets import QBoxLayout
        dir_botones = QBoxLayout.TopToBottom if vertical else QBoxLayout.LeftToRight
        self._fila.setDirection(dir_botones)
        self._ctx.setDirection(dir_botones)
        for linea in self._separadores:
            linea.setFrameShape(QFrame.HLine if vertical else QFrame.VLine)
        # apilados, los deslizadores y menús se ven mejor con ancho fijo y
        # alineados al inicio; en fila vuelven a su medida natural
        estirar = (self._grosor, self._pixel_cantidad, self._pixel_grosor, self._opacidad)
        for w in estirar:
            w.setFixedWidth(120 if vertical else 70)
        self._ctx.setSpacing(4 if vertical else 8)
        self.adjustSize()
        self._contextual.adjustSize()
        self.layout_changed.emit()


class SelectionOverlay(QWidget):
    copied = Signal(QImage)
    save_requested = Signal(QImage)
    closed = Signal()

    def __init__(self, preset=None):
        """preset permite arrancar con la zona ya elegida.

        las capturas de pantalla completa y de ventana activa pasan por el
        mismo editor que la de región: llegan con "full" o con el
        rectángulo físico de la ventana, la selección aparece hecha y la
        barra de herramientas sale de inmediato. el usuario puede ajustar
        la zona, anotar y decidir si copia o guarda, todo igual.
        """
        super().__init__(None, Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_DeleteOnClose, True)
        self.setMouseTracking(True)
        # sin foco de teclado, el esc de la fase de selección no llegaba
        # hasta el primer clic; con esto responde desde que aparece
        self.setFocusPolicy(Qt.StrongFocus)

        # la foto congelada de todos los monitores, en resolución física
        self._imagen = capture.grab_virtual_screen()
        self._dpr = capture.device_pixel_ratio()
        geometria = QGuiApplication.primaryScreen().virtualGeometry()
        self.setGeometry(geometria)

        self._fase = "seleccionando"          # seleccionando | editando
        self._sel = QRectF()
        self._origen: QPointF | None = None
        self._cursor: QPointF | None = None   # posición para la lupa de zoom
        self._cursor_pincel: QPointF | None = None  # círculo de grosor del pincel
        self._items: list[an.Item] = []
        self._rehechos: list[an.Item] = []
        self._seleccion: list[an.Item] = []   # elementos tomados (uno o varios)
        self._banda: QRectF | None = None      # recuadro elástico de selección
        self._arrastre: dict | None = None

        self._preset = preset
        if preset == "full":
            self._sel = QRectF(0, 0, geometria.width(), geometria.height())
        elif preset is not None:
            # un rectángulo físico de ventana se traduce a las coordenadas
            # lógicas del overlay, recortado a la pantalla por si la
            # ventana cuelga fuera del borde
            logico = QRectF(preset.x() / self._dpr - geometria.x(),
                            preset.y() / self._dpr - geometria.y(),
                            preset.width() / self._dpr, preset.height() / self._dpr)
            self._sel = logico.intersected(QRectF(0, 0, geometria.width(), geometria.height()))
        if preset is not None and self._sel.width() >= 5 and self._sel.height() >= 5:
            self._fase = "editando"

        # valores por defecto de cada herramienta nueva
        self._tool = "select"
        self._forma = "rect"
        self._color = QColor("#e5484d")
        self._ancho = 3
        self._dash = "solid"
        self._cap_inicio = "none"
        self._cap_fin = "arrow_filled"
        self._opacidad = 1.0
        self._fuente = QFont("Segoe UI", 18)
        # opciones del pincel de ocultar y del borrador; arrancan en su valor
        # por defecto y no se guardan, se reinician en cada sesión
        self._pixel_modo = an.PIXEL_MODO
        self._pixel_cantidad = an.PIXEL_CANTIDAD
        self._pixel_grosor = an.PIXEL_GROSOR
        self._borrador_grosor = an.BORRADOR_GROSOR

        self._editor: QLineEdit | None = None
        self._editor_pos = QPointF()

        self._barra = _Toolbar(self, opciones_flotantes=True)
        self._barra.hide()
        self._conectar_barra()

        self.setCursor(Qt.ArrowCursor if self._fase == "editando" else Qt.CrossCursor)

    # el elemento único seleccionado, cuando hay exactamente uno; sirve para
    # las operaciones que solo aplican de a uno, como redimensionar. asignar
    # None o un elemento se traduce a la lista de selección, así el código
    # que ya trabajaba con un solo activo sigue funcionando
    @property
    def _activo(self):
        return self._seleccion[0] if len(self._seleccion) == 1 else None

    @_activo.setter
    def _activo(self, item):
        self._seleccion = [item] if item is not None else []

    def _configurar_barra(self):
        """acomoda la barra de opciones según lo que haya seleccionado: las
        de un elemento, las comunes de varios, o las de la herramienta."""
        if len(self._seleccion) == 1:
            it = self._seleccion[0]
            self._barra.configure(self._tipo_de(it), it)
        elif len(self._seleccion) > 1:
            self._barra.configure_multi(self._seleccion)
        else:
            self._barra.configure("select")

    def showEvent(self, e):
        super().showEvent(e)
        # se reclama el foco de teclado apenas aparece, así el esc cancela
        # aunque todavía no se haya tocado nada con el mouse. cuando la captura
        # se dispara desde otra app (el navegador), windows no cede el foco sin
        # más: el forzado engancha la entrada del hilo activo y trae el overlay
        # de verdad al frente, para que el esc responda a la primera siempre
        self.activateWindow()
        self.setFocus()
        capture.force_foreground(int(self.winId()))
        # una segunda pasada apenas termina de mapearse la ventana asegura el
        # foco incluso si la primera llegó demasiado pronto
        QTimer.singleShot(0, lambda: capture.force_foreground(int(self.winId())))
        # con selección preestablecida, la barra aparece apenas el overlay
        # está en pantalla; el retraso de cero cede el turno al layout
        if self._fase == "editando" and not self._barra.isVisible():
            QTimer.singleShot(0, self._mostrar_barra)

    def _conectar_barra(self):
        b = self._barra
        b.layout_changed.connect(self._posicionar_opciones)
        b.tool_changed.connect(self._cambiar_tool)
        b.shape_changed.connect(lambda f: setattr(self, "_forma", f))
        b.color_changed.connect(self._aplicar_color)
        b.width_changed.connect(self._aplicar_grosor)
        b.dash_changed.connect(self._aplicar_dash)
        b.cap_start_changed.connect(lambda c: self._aplicar_cap("cap_start", c))
        b.cap_end_changed.connect(lambda c: self._aplicar_cap("cap_end", c))
        b.opacity_changed.connect(self._aplicar_opacidad)
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
        b.cancel_clicked.connect(self._cancelar)

    def _cancelar(self):
        """salir de la captura pidiendo confirmación si hay algo dibujado."""
        if self._confirmar_descarte():
            self.close()

    def _confirmar_descarte(self) -> bool:
        """avisa antes de tirar lo anotado, con la opción de no volver a
        preguntar. comparte el ajuste con la pizarra de presentación: lo que
        el usuario decida acá vale para los dos y se configura en opciones."""
        from src.config.settings import settings
        if not self._items:
            return True
        if not settings.get("confirm_discard_board", True):
            return True
        aviso = QMessageBox()
        aviso.setWindowTitle(t("zoom.discard_title"))
        aviso.setText(t("zoom.discard_q"))
        aviso.setIcon(QMessageBox.Warning)
        # el overlay es siempre-adelante; sin esta bandera el aviso nacería
        # detrás y la app parecería trabada
        aviso.setWindowFlag(Qt.WindowStaysOnTopHint, True)
        descartar = aviso.addButton(t("zoom.discard_yes"), QMessageBox.DestructiveRole)
        aviso.addButton(t("tool.cancel"), QMessageBox.RejectRole)
        casilla = QCheckBox(t("zoom.discard_dontask"))
        aviso.setCheckBox(casilla)
        aviso.exec()
        if casilla.isChecked():
            settings.set("confirm_discard_board", False)
        return aviso.clickedButton() is descartar

    # ------------------------------------------------------------------ #
    # propiedades: cada cambio afecta al elemento seleccionado si lo hay,
    # y de paso queda como valor por defecto para el próximo dibujo

    def _cambiar_tool(self, nombre: str):
        self._tool = nombre
        self._commit_texto()
        if nombre != "select":
            self._activo = None
        if nombre not in ("pixelate", "eraser"):
            # solo el pincel de ocultar y el borrador muestran el círculo de
            # tamaño; el pincel normal pinta y ya, sin nada alrededor
            self._cursor_pincel = None
        self.setCursor({"select": Qt.ArrowCursor,
                        "text": Qt.IBeamCursor}.get(nombre, Qt.CrossCursor))
        self.update()

    def _aplicar_color(self, color: QColor):
        self._color = QColor(color)
        cambio = False
        for it in self._seleccion:
            if not isinstance(it, (an.PixelateItem, an.ImageItem)):
                it.color = QColor(color)
                cambio = True
        if cambio:
            self.update()

    def _aplicar_grosor(self, valor: int):
        self._ancho = valor
        cambio = False
        for it in self._seleccion:
            if not isinstance(it, (an.TextItem, an.ImageItem, an.PixelateItem)):
                it.width = valor
                cambio = True
        if cambio:
            self.update()

    def _aplicar_dash(self, dash: str):
        self._dash = dash
        cambio = False
        for it in self._seleccion:
            if isinstance(it, (an.ShapeItem, an.LineItem)) and not isinstance(it, an.ImageItem):
                it.dash = dash
                cambio = True
        if cambio:
            self.update()

    def _aplicar_cap(self, extremo: str, remate: str):
        if extremo == "cap_start":
            self._cap_inicio = remate
        else:
            self._cap_fin = remate
        cambio = False
        for it in self._seleccion:
            if isinstance(it, an.LineItem):
                setattr(it, extremo, remate)
                cambio = True
        if cambio:
            self.update()

    def _aplicar_opacidad(self, valor: float):
        self._opacidad = valor
        cambio = False
        for it in self._seleccion:
            if not isinstance(it, an.PixelateItem):
                it.opacity = valor
                cambio = True
        if cambio:
            self.update()

    def _aplicar_pixel(self, campo: str, valor):
        """las opciones del pincel de ocultar quedan como valor por defecto
        para el próximo trazo de esta sesión; no se guardan a disco."""
        if campo == "mode":
            self._pixel_modo = valor
        elif campo == "amount":
            self._pixel_cantidad = int(valor)
        elif campo == "size":
            self._pixel_grosor = int(valor)
        # si hay un trazo de ocultar seleccionado, se reajusta en vivo
        if isinstance(self._activo, an.PixelateItem):
            if campo == "mode":
                self._activo.mode = valor
            elif campo == "amount":
                self._activo.amount = int(valor)
            elif campo == "size":
                self._activo.width = int(valor)
            self.update()

    def _aplicar_borrador(self, valor: int):
        self._borrador_grosor = int(valor)
        self.update()

    def _pegar_imagen(self):
        """ctrl+v suma la imagen del portapapeles como un elemento más."""
        imagen = QGuiApplication.clipboard().image()
        if imagen.isNull() or not self._sel.isValid():
            return
        factor = min(1.0, self._sel.width() * 0.6 / max(1, imagen.width()),
                     self._sel.height() * 0.6 / max(1, imagen.height()))
        ancho, alto = imagen.width() * factor, imagen.height() * factor
        centro = self._sel.center()
        nuevo = an.ImageItem(QRectF(centro.x() - ancho / 2, centro.y() - alto / 2,
                                    ancho, alto), imagen)
        nuevo.opacity = self._opacidad
        self._items.append(nuevo)
        self._rehechos.clear()
        self._activo = nuevo
        self._barra.activate("select")
        self.update()

    def _aplicar_fuente(self, familia: str):
        self._fuente.setFamily(familia)
        cambio = False
        for it in self._seleccion:
            if isinstance(it, an.TextItem):
                it.font.setFamily(familia)
                cambio = True
        if cambio:
            self.update()

    def _aplicar_tamano(self, puntos: int):
        self._fuente.setPointSize(puntos)
        cambio = False
        for it in self._seleccion:
            if isinstance(it, an.TextItem):
                it.font.setPointSize(puntos)
                cambio = True
        if cambio:
            self.update()

    def _aplicar_estilo_fuente(self, metodo: str, valor: bool):
        getattr(self._fuente, metodo)(valor)
        cambio = False
        for it in self._seleccion:
            if isinstance(it, an.TextItem):
                getattr(it.font, metodo)(valor)
                cambio = True
        if cambio:
            self.update()

    # ------------------------------------------------------------------ #
    # acciones

    def _deshacer(self):
        self._commit_texto()
        if self._items:
            quitado = self._items.pop()
            self._rehechos.append(quitado)
            if quitado in self._seleccion:
                self._seleccion.remove(quitado)
            self.update()

    def _rehacer(self):
        if self._rehechos:
            self._items.append(self._rehechos.pop())
            self.update()

    def _limpiar(self):
        self._commit_texto()
        self._items.clear()
        self._seleccion = []
        self.update()

    def _copiar(self):
        imagen = self._exportar()
        if not imagen.isNull():
            self.copied.emit(imagen)
        self.close()

    def _guardar(self):
        # se exporta y se avisa a la app; el diálogo de guardar aparece encima.
        # si el usuario confirma, la app cierra este overlay al terminar; si
        # cancela el diálogo, la edición sigue tal cual sobre la misma captura
        imagen = self._exportar()
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
            an.paint_item(pintor, item)
        pintor.end()
        return salida

    # ------------------------------------------------------------------ #
    # texto en línea

    def _abrir_editor(self, pos: QPointF, existente: an.TextItem | None = None):
        """caja de texto que se escribe directamente sobre la captura."""
        self._commit_texto()
        editor = QLineEdit(self)
        editor.setPlaceholderText(t("tool.text_placeholder"))
        fuente = self._fuente if existente is None else existente.font
        editor.setFont(fuente)
        color = self._color if existente is None else existente.color
        # sin caja ni fondo, con la fuente dentro del estilo: la hoja de
        # estilos global fija 13px y pisaría el setFont, dejando el texto
        # chico mientras se escribe
        editor.setStyleSheet(
            f"background: transparent; border: none; color: {color.name()};"
            f" font-family: '{fuente.family()}'; font-size: {fuente.pointSizeF():.0f}pt;"
            f" font-weight: {'bold' if fuente.bold() else 'normal'};"
            f" font-style: {'italic' if fuente.italic() else 'normal'};")
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
        editor.returnPressed.connect(self._finalizar_texto)
        self._editor = editor
        self._editor_pos = QPointF(posicion)

    def _commit_texto(self):
        """confirma el texto en edición; devuelve el elemento creado."""
        if self._editor is None:
            return None
        texto = self._editor.text().strip()
        fuente = QFont(self._editor.font())
        self._editor.deleteLater()
        self._editor = None
        nuevo = None
        if texto:
            nuevo = an.TextItem(self._editor_pos, texto, fuente, self._color)
            self._items.append(nuevo)
            self._rehechos.clear()
        self.update()
        return nuevo

    def _finalizar_texto(self):
        """esc, enter o un clic afuera confirman el texto y lo dejan
        seleccionado con la herramienta en selección."""
        nuevo = self._commit_texto()
        if nuevo is not None:
            self._activo = nuevo
            self._barra.activate("select")
            self._barra.configure(self._tipo_de(nuevo), nuevo)
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
            # el clic afuera confirma el texto y lo deja seleccionado
            self._finalizar_texto()
            return

        if self._tool == "select":
            self._press_seleccion(punto, bool(e.modifiers() & Qt.ShiftModifier),
                                  bool(e.modifiers() & Qt.AltModifier))
        elif self._tool == "text":
            if self._sel.contains(punto):
                self._abrir_editor(punto)
        elif self._tool == "eraser":
            self._arrastre = {"modo": "borrar"}
            self._borrar_en(punto)
        else:
            self._press_dibujo(punto)
        self.update()

    def _tiradores_seleccion(self) -> list[QPointF]:
        r = self._sel
        return [r.topLeft(), QPointF(r.center().x(), r.top()), r.topRight(),
                QPointF(r.right(), r.center().y()), r.bottomRight(),
                QPointF(r.center().x(), r.bottom()), r.bottomLeft(),
                QPointF(r.left(), r.center().y())]

    def _press_seleccion(self, punto: QPointF, shift: bool = False, alt: bool = False):
        """resuelve el clic con la herramienta de selección, en orden: un
        tirador del elemento único, el agarre para mover el recorte, un
        elemento para tomarlo (con shift se suma o quita de la selección),
        un tirador del recorte para redimensionarlo, o el vacío para trazar
        un recuadro elástico.

        con alt sobre un elemento, se duplica lo seleccionado y se arrastra
        la copia. el recorte ya no se mueve arrastrando su interior: para eso
        está el agarre, así no se corre sin querer al ir a copiar."""
        unico = self._activo
        if unico is not None:
            for i, tirador in enumerate(unico.handles()):
                if (tirador - punto).manhattanLength() <= _LADO_TIRADOR + 4:
                    self._arrastre = {"modo": "tirador", "indice": i}
                    if isinstance(unico, an.ShapeItem):
                        r = unico.rect
                        self._arrastre["centro"] = QPointF(r.center())
                        self._arrastre["aspecto"] = (r.width() / r.height()
                                                     if r.height() > 0 else 0)
                    elif isinstance(unico, an.TextItem):
                        # el texto escala anclado a su estado inicial
                        self._arrastre["texto0"] = (QRectF(unico._rect()),
                                                    unico.font.pointSizeF())
                    return

        # el agarre mueve el recorte; arrastrar el interior ya no lo mueve
        if self._grip_mover().contains(punto):
            self._arrastre = {"modo": "sel_mover", "desde": punto}
            return

        objetivo = None
        for item in reversed(self._items):
            # el trazo de ocultar no se toma ni se mueve; solo el borrador lo quita
            if isinstance(item, an.PixelateItem):
                continue
            if item.contains(punto):
                objetivo = item
                break
        if objetivo is not None:
            if alt:
                # se duplica todo lo tomado y se arrastran las copias
                base = self._seleccion if objetivo in self._seleccion else [objetivo]
                copias = [an.clonar(i) for i in base]
                self._items.extend(copias)
                self._rehechos.clear()
                self._seleccion = copias
            elif shift:
                # sumar o quitar de la selección múltiple
                if objetivo in self._seleccion:
                    self._seleccion.remove(objetivo)
                else:
                    self._seleccion.append(objetivo)
            elif objetivo not in self._seleccion:
                self._seleccion = [objetivo]
            self._configurar_barra()
            if self._seleccion:
                self._arrastre = {"modo": "mover", "inicio": punto,
                                  "antes": [(i, an.snapshot(i)) for i in self._seleccion]}
            return

        # nada bajo el cursor: se prueba redimensionar el recorte por su tirador
        for i, tirador in enumerate(self._tiradores_seleccion()):
            if (tirador - punto).manhattanLength() <= _LADO_TIRADOR + 4:
                if not shift:
                    self._seleccion = []
                    self._configurar_barra()
                # se guarda el recorte de partida para redimensionar contra
                # un ancla fijo, así se puede voltear al pasarse de largo
                self._arrastre = {"modo": "sel_tirador", "indice": i,
                                  "rect0": QRectF(self._sel)}
                return

        # vacío: recuadro elástico que toma todo lo que abarque
        if not shift:
            self._seleccion = []
            self._configurar_barra()
        self._banda = QRectF(punto, punto)
        self._arrastre = {"modo": "banda", "origen": punto}

    def _borrar_en(self, punto: QPointF):
        """el borrador quita cualquier anotación que su círculo toque, del
        tamaño que marque su grosor."""
        radio = max(2.0, self._borrador_grosor / 2)
        circulo = QPainterPath()
        circulo.addEllipse(punto, radio, radio)
        borrado = False
        for item in reversed(list(self._items)):
            trazo = an._trazo_ancho(item.path(), max(1.0, item.width))
            if trazo.intersects(circulo) or item.contains(punto):
                self._items.remove(item)
                if item in self._seleccion:
                    self._seleccion.remove(item)
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
            nuevo = an.PixelateItem(punto, self._imagen, self._dpr, self._pixel_modo,
                                    self._pixel_cantidad, self._pixel_grosor)
        else:
            return
        nuevo.opacity = self._opacidad
        self._items.append(nuevo)
        # dibujar algo nuevo invalida la rama de rehechos, como en
        # cualquier editor
        self._rehechos.clear()
        self._arrastre = {"modo": "crear", "item": nuevo, "origen": punto}

    def mouseMoveEvent(self, e):
        punto = QPointF(e.position())

        if self._fase == "seleccionando":
            # la lupa sigue al cursor tanto antes como durante el arrastre
            self._cursor = punto
            if self._origen is not None:
                self._sel = QRectF(self._origen, punto).normalized()
            self.update()
            return

        # el círculo de tamaño sigue al cursor con el pincel de ocultar y el
        # borrador; el pincel normal no lleva nada alrededor
        if self._tool in ("pixelate", "eraser"):
            self._cursor_pincel = punto
            self.update()

        if not self._arrastre:
            self._actualizar_cursor_hover(punto)
            return

        # con el borrador apretado, se va limpiando lo que toca
        if self._arrastre.get("modo") == "borrar":
            self._borrar_en(punto)
            return
        # shift endereza y proporciona; alt crece desde el centro; los
        # mismos modificadores que en la pizarra de presentación
        # el evento trae los modificadores reales; la caché de la app
        # no se entera si shift ya venía presionado desde antes del clic
        mods = e.modifiers()
        shift = bool(mods & Qt.ShiftModifier)
        alt = bool(mods & Qt.AltModifier)
        modo = self._arrastre["modo"]
        if modo == "crear":
            item = self._arrastre["item"]
            origen = self._arrastre.get("origen")
            if isinstance(item, (an.BrushItem, an.PixelateItem)):
                if shift:
                    # con shift el trazo sale recto desde donde empezó, como
                    # una regla; sin shift sigue a pulso
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
            # desplazamiento absoluto desde el agarre; con shift se pega al
            # eje recto. mueve todo lo seleccionado a la vez
            delta = punto - self._arrastre["inicio"]
            if shift:
                delta = an.restringir_eje(delta)
            for it, antes in self._arrastre["antes"]:
                an.restore(it, antes)
                it.move_by(delta.x(), delta.y())
        elif modo == "tirador":
            unico = self._activo
            if unico is None:
                self.update()
                return
            indice = self._arrastre["indice"]
            if isinstance(unico, an.TextItem) and "texto0" in self._arrastre:
                rect0, tam0 = self._arrastre["texto0"]
                an.escalar_texto(unico, indice, punto, rect0, tam0)
            elif isinstance(unico, an.LineItem) and shift:
                fijo = unico.p2 if indice == 0 else unico.p1
                unico.set_handle(indice, an.snap_45(fijo, punto))
            else:
                unico.set_handle(indice, punto)
            if isinstance(unico, an.ShapeItem):
                if shift and self._arrastre.get("aspecto"):
                    unico.rect = an.ajustar_aspecto(
                        unico.rect, self._arrastre["aspecto"], indice)
                if alt and self._arrastre.get("centro") is not None:
                    unico.rect.moveCenter(self._arrastre["centro"])
        elif modo == "banda":
            self._banda = QRectF(self._arrastre["origen"], punto).normalized()
        elif modo == "sel_mover":
            delta = punto - self._arrastre["desde"]
            movida = self._sel.translated(delta)
            # la selección se queda dentro de la pantalla, nunca a medias
            if self.rect().contains(movida.toRect()):
                self._sel = movida
                self._arrastre["desde"] = punto
                # la barra acompaña el movimiento en vivo, no al soltar
                self._posicionar_barra()
        elif modo == "sel_tirador":
            self._redimensionar_seleccion(self._arrastre["indice"], punto)
            # la barra se reacomoda mientras se agranda o achica la selección
            self._posicionar_barra()
        self.update()

    # cursores de redimensión de los ocho tiradores de un rectángulo, en el
    # orden de _tiradores_seleccion (esquinas y puntos medios)
    _CURSORES_RECT = [Qt.SizeFDiagCursor, Qt.SizeVerCursor, Qt.SizeBDiagCursor,
                      Qt.SizeHorCursor, Qt.SizeFDiagCursor, Qt.SizeVerCursor,
                      Qt.SizeBDiagCursor, Qt.SizeHorCursor]

    def _actualizar_cursor_hover(self, punto: QPointF):
        """con la herramienta de selección, el cursor anticipa qué se puede
        agarrar: la flechita de redimensión que apunta según el tirador,
        mano abierta sobre elementos, flecha normal en el resto."""
        if self._tool != "select":
            return
        if self._grip_mover().contains(punto):
            self.setCursor(Qt.SizeAllCursor)
            return
        unico = self._activo
        if unico is not None:
            for i, tirador in enumerate(unico.handles()):
                if (tirador - punto).manhattanLength() <= _LADO_TIRADOR + 4:
                    self.setCursor(an.cursor_tirador(unico, i))
                    return
        for i, tirador in enumerate(self._tiradores_seleccion()):
            if (tirador - punto).manhattanLength() <= _LADO_TIRADOR + 4:
                self.setCursor(self._CURSORES_RECT[i])
                return
        for item in reversed(self._items):
            if item.contains(punto):
                self.setCursor(Qt.OpenHandCursor)
                return
        self.setCursor(Qt.ArrowCursor)

    _MIN_SEL = 30   # lado mínimo del recorte, en píxeles lógicos

    def _redimensionar_seleccion(self, indice: int, pos: QPointF):
        """mueve el borde o esquina que se arrastra dejando el opuesto de
        ancla. si el mouse se pasa del ancla, el recorte se voltea y crece
        hacia ese lado; nunca baja de un tamaño mínimo, así no se traba."""
        r0 = self._arrastre.get("rect0", self._sel)
        # el cursor se limita a la pantalla para no salirse del área
        px = max(0.0, min(pos.x(), float(self.width())))
        py = max(0.0, min(pos.y(), float(self.height())))

        mueve_izq = indice in (0, 6, 7)
        mueve_der = indice in (2, 3, 4)
        mueve_arr = indice in (0, 1, 2)
        mueve_aba = indice in (4, 5, 6)

        def con_minimo(movil, ancla):
            # el borde móvil no puede acercarse al ancla más que el mínimo;
            # si el mouse cruza el ancla, salta al otro lado y crece
            if abs(movil - ancla) < self._MIN_SEL:
                return ancla - self._MIN_SEL if movil <= ancla else ancla + self._MIN_SEL
            return movil

        izq = con_minimo(px, r0.right()) if mueve_izq else r0.left()
        der = con_minimo(px, r0.left()) if mueve_der else r0.right()
        arr = con_minimo(py, r0.bottom()) if mueve_arr else r0.top()
        aba = con_minimo(py, r0.top()) if mueve_aba else r0.bottom()

        self._sel = QRectF(QPointF(izq, arr), QPointF(der, aba)).normalized()

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
            if isinstance(item, an.PixelateItem):
                # el trazo de ocultar deja de marcarse en azul al soltar y
                # la herramienta se queda activa para seguir pintando
                item.editando = False
            # un clic sin arrastre deja una figura de tamaño cero que solo
            # estorba; se descarta en silencio
            if item.bounding().width() < 8 and item.bounding().height() < 8:
                if item in self._items:
                    self._items.remove(item)
            elif self._tool not in ("brush", "pixelate"):
                # lo recién dibujado queda seleccionado y la herramienta
                # pasa a selección, lista para acomodar
                self._seleccion = [item]
                self._barra.activate("select")
                self._configurar_barra()
        elif self._arrastre and self._arrastre["modo"] == "banda":
            # el recuadro elástico toma todo lo que abarque, salvo el ocultar
            if self._banda is not None:
                abarcados = [it for it in self._items
                             if not isinstance(it, an.PixelateItem)
                             and self._banda.intersects(it.bounding())]
                if abarcados:
                    for it in abarcados:
                        if it not in self._seleccion:
                            self._seleccion.append(it)
                self._configurar_barra()
            self._banda = None
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

    # letras que cambian de herramienta al vuelo, al estilo de los editores
    # de siempre; V vuelve a selección, lista para tomar y arrastrar
    _ATAJOS_TOOL = {Qt.Key_V: "select", Qt.Key_S: "shape", Qt.Key_L: "line",
                    Qt.Key_F: "arrow", Qt.Key_B: "brush", Qt.Key_T: "text",
                    Qt.Key_P: "pixelate", Qt.Key_E: "eraser"}

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Escape:
            if self._editor is not None:
                # esc confirma y selecciona el texto en lugar de tirarlo
                self._finalizar_texto()
                return
            self._cancelar()
        elif (self._editor is None and e.key() in self._ATAJOS_TOOL
              and not (e.modifiers() & (Qt.ControlModifier | Qt.AltModifier))):
            # la letra sola cambia de herramienta; con el texto abierto no,
            # para poder escribir esas letras
            self._barra.activate(self._ATAJOS_TOOL[e.key()])
        elif e.matches(QKeySequence.Copy):
            self._copiar()
        elif e.matches(QKeySequence.Save):
            self._guardar()
        elif e.matches(QKeySequence.Undo):
            self._deshacer()
        elif e.matches(QKeySequence.Redo):
            self._rehacer()
        elif e.matches(QKeySequence.Paste):
            self._pegar_imagen()
        elif e.key() == Qt.Key_Delete and self._seleccion:
            # suprimir borra todo lo que esté tomado, sea uno o varios
            for it in list(self._seleccion):
                if it in self._items:
                    self._items.remove(it)
            self._seleccion = []
            self._configurar_barra()
            self.update()
        else:
            super().keyPressEvent(e)

    def leaveEvent(self, e):
        # al salir el mouse del overlay, el círculo del pincel no debe quedar
        # dibujado en el último punto
        if self._cursor_pincel is not None:
            self._cursor_pincel = None
            self.update()
        super().leaveEvent(e)

    def closeEvent(self, e):
        self.closed.emit()
        super().closeEvent(e)

    # ------------------------------------------------------------------ #
    # barra de herramientas

    def _posicionar_barra(self):
        """la barra vive pegada bajo la selección; si no hay lugar abajo se
        acomoda arriba. cuando tampoco cabe arriba (selección muy alta o
        pegada a los bordes) pasa a vertical y se planta a un costado."""
        # primero se prueba horizontal, la forma preferida
        self._barra.orientar(False)
        self._barra.adjustSize()
        alto = self._barra.height()
        ancho = self._barra.width()
        cabe_abajo = self._sel.bottom() + alto + 10 <= self.height()
        cabe_arriba = self._sel.top() - alto - 10 >= 0
        if cabe_abajo or cabe_arriba:
            x = min(max(self._sel.left(), 0), self.width() - ancho - 8)
            y = self._sel.bottom() + 8 if cabe_abajo else self._sel.top() - alto - 8
            self._barra.move(int(x), int(y))
            self._posicionar_opciones()
            return

        # sin lugar arriba ni abajo, la barra se vuelve columna a un lado
        self._barra.orientar(True)
        self._barra.adjustSize()
        alto = self._barra.height()
        ancho = self._barra.width()
        # se prefiere el lado derecho de la selección; si no entra, el izquierdo
        if self._sel.right() + ancho + 10 <= self.width():
            x = self._sel.right() + 8
        elif self._sel.left() - ancho - 10 >= 0:
            x = self._sel.left() - ancho - 8
        else:
            # ninguno de los dos lados: se pega al borde con más aire
            x = (self.width() - ancho - 8 if self._sel.center().x() < self.width() / 2 else 8)
        y = min(max(self._sel.top(), 8), self.height() - alto - 8)
        self._barra.move(int(x), int(y))
        self._posicionar_opciones()

    def _posicionar_opciones(self):
        """la ventanita de opciones flota justo debajo de la barra, con un
        respiro. solo asoma en edición y cuando la herramienta tiene algo
        que ofrecer; si no, se esconde."""
        ctx = self._barra._contextual
        if (self._fase != "editando" or not self._barra.isVisible()
                or not self._barra._hay_opciones):
            ctx.hide()
            return
        ctx.adjustSize()
        ancho, alto = ctx.width(), ctx.height()
        x = self._barra.x()
        y = self._barra.y() + self._barra.height() + 6
        # nunca fuera de pantalla
        x = min(max(8, x), self.width() - ancho - 8)
        if y + alto + 8 > self.height():
            # sin lugar debajo, se coloca encima de la barra
            y = self._barra.y() - alto - 6
        y = max(8, y)
        ctx.move(int(x), int(y))
        ctx.show()
        ctx.raise_()

    def _mostrar_barra(self):
        self._posicionar_barra()
        efecto = QGraphicsOpacityEffect(self._barra)
        self._barra.setGraphicsEffect(efecto)
        self._barra.show()
        self._posicionar_opciones()
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
            if self._cursor is not None:
                self._pintar_lupa(pintor, self._cursor)

        if self._fase == "editando":
            pintor.save()
            pintor.setClipRect(self._sel)
            for item in self._items:
                an.paint_item(pintor, item)
            pintor.restore()

            if self._tool == "select":
                # el recorte muestra siempre sus tiradores para agrandarlo y
                # el agarre para moverlo
                self._pintar_tiradores(pintor, self._tiradores_seleccion())
                self._pintar_grip(pintor)

            # cada elemento tomado marca su contorno; el único además saca
            # tiradores para redimensionarlo
            self._pintar_contornos(pintor)
            unico = self._activo
            if unico is not None:
                self._pintar_tiradores(pintor, unico.handles(), unico)

            # el recuadro elástico mientras se arrastra
            if self._banda is not None:
                tinta = QColor(theme.accent())
                tinta.setAlpha(40)
                pintor.setPen(QPen(QColor(theme.accent()), 1))
                pintor.setBrush(tinta)
                pintor.drawRect(self._banda)
                pintor.setBrush(Qt.NoBrush)

            # el círculo de tamaño (ocultar y borrador) se recorta a la
            # selección para que nunca asome nada sobre el velo de afuera
            if self._tool in ("pixelate", "eraser") and self._cursor_pincel is not None:
                grosor = self._pixel_grosor if self._tool == "pixelate" else self._borrador_grosor
                pintor.save()
                pintor.setClipRect(self._sel)
                an.pintar_circulo_pincel(pintor, self._cursor_pincel, grosor)
                pintor.restore()

        pintor.end()

    def _pintar_medidas(self, pintor: QPainter):
        """chip con el tamaño real de la captura, en píxeles físicos."""
        # el save/restore evita dejar el brush oscuro puesto y que luego un
        # trazo cerrado lo herede y se rellene
        pintor.save()
        texto = f"{round(self._sel.width() * self._dpr)} × {round(self._sel.height() * self._dpr)}"
        pintor.setFont(QFont("Segoe UI", 9))
        medidas = pintor.fontMetrics().boundingRect(texto).adjusted(-8, -4, 8, 4)
        # con la herramienta de selección, el chip se corre a la derecha del
        # agarre de mover para no quedar uno encima del otro
        x = self._grip_mover().right() + 8 if self._tool == "select" else self._sel.left()
        y = self._sel.top() - medidas.height() - 6
        if y < 0:
            y = self._sel.top() + 6
        chip = QRectF(x, y, medidas.width(), medidas.height())
        pintor.setPen(Qt.NoPen)
        pintor.setBrush(QColor(0, 0, 0, 170))
        pintor.drawRoundedRect(chip, 5, 5)
        pintor.setPen(QColor("#ffffff"))
        pintor.drawText(chip, Qt.AlignCenter, texto)
        pintor.restore()

    def _pintar_lupa(self, pintor: QPainter, cursor: QPointF):
        """recuadro que amplía los píxeles bajo el cursor mientras se
        recorta, para acertar el borde exacto de la zona.

        toma un trozo pequeño de la captura alrededor del cursor a
        resolución física y lo agranda sin suavizar, así se ven los píxeles
        cuadrados. debajo van las coordenadas y el tamaño de la selección.
        """
        lado = 132            # tamaño del recuadro en pantalla
        muestra = 22          # cuántos píxeles lógicos se abarcan a lo ancho
        # el recuadro se ubica en diagonal al cursor y salta de esquina si
        # se saldría del borde, para no taparse a sí mismo
        margen = 24
        x = cursor.x() + margen
        y = cursor.y() + margen
        alto_total = lado + 26
        if x + lado > self.width():
            x = cursor.x() - margen - lado
        if y + alto_total > self.height():
            y = cursor.y() - margen - alto_total
        x = max(4, min(x, self.width() - lado - 4))
        y = max(4, min(y, self.height() - alto_total - 4))

        # trozo físico centrado en el cursor
        cx = cursor.x() * self._dpr
        cy = cursor.y() * self._dpr
        med_fis = muestra * self._dpr
        origen = QRectF(cx - med_fis / 2, cy - med_fis / 2, med_fis, med_fis).toRect()
        recorte = self._imagen.copy(origen)

        pintor.save()
        marco = QRectF(x, y, lado, lado)
        ruta = QPainterPath()
        ruta.addRoundedRect(marco, 8, 8)
        pintor.setClipPath(ruta)
        if not recorte.isNull():
            ampliada = recorte.scaled(lado, lado, Qt.KeepAspectRatioByExpanding,
                                      Qt.FastTransformation)
            pintor.drawImage(marco, ampliada)
        pintor.setClipping(False)

        # la cruz marca el píxel exacto que quedará en la esquina
        escala = lado / muestra
        pintor.setPen(QPen(QColor(theme.accent()), 1))
        centro = marco.center()
        pintor.drawLine(QPointF(marco.left(), centro.y()), QPointF(marco.right(), centro.y()))
        pintor.drawLine(QPointF(centro.x(), marco.top()), QPointF(centro.x(), marco.bottom()))
        # cuadrito resaltando el píxel central
        pintor.setBrush(Qt.NoBrush)
        pintor.setPen(QPen(QColor(255, 255, 255, 200), 1))
        pintor.drawRect(QRectF(centro.x() - escala / 2, centro.y() - escala / 2, escala, escala))

        pintor.setPen(QPen(QColor(theme.accent()), 1.4))
        pintor.setBrush(Qt.NoBrush)
        pintor.drawRoundedRect(marco, 8, 8)

        # etiqueta con la coordenada física bajo el cursor
        etiqueta = QRectF(x, y + lado + 2, lado, 22)
        pintor.setPen(Qt.NoPen)
        pintor.setBrush(QColor(0, 0, 0, 180))
        pintor.drawRoundedRect(etiqueta, 5, 5)
        pintor.setPen(QColor("#ffffff"))
        pintor.setFont(QFont("Segoe UI", 8))
        texto = f"{round(cx)}, {round(cy)}"
        if self._sel.isValid() and self._sel.width() > 0:
            texto = f"{round(self._sel.width() * self._dpr)} × {round(self._sel.height() * self._dpr)}"
        pintor.drawText(etiqueta, Qt.AlignCenter, texto)
        pintor.restore()

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

    def _pintar_contornos(self, pintor: QPainter):
        """con varios elementos tomados, cada uno marca su contorno punteado
        (el caso de uno solo lo resuelven sus tiradores)."""
        if len(self._seleccion) < 2:
            return
        pluma = QPen(QColor(theme.accent()), 1.2)
        pluma.setStyle(Qt.DashLine)
        pintor.setPen(pluma)
        pintor.setBrush(Qt.NoBrush)
        for it in self._seleccion:
            pintor.drawRect(it.bounding())

    def _grip_mover(self) -> QRectF:
        """el recuadro del agarre para mover el recorte, pegado a su esquina
        superior izquierda; si no cabe arriba, baja dentro."""
        lado = 26
        x = self._sel.left()
        y = self._sel.top() - lado - 6
        if y < 4:
            y = self._sel.top() + 6
        return QRectF(x, y, lado, lado)

    def _pintar_grip(self, pintor: QPainter):
        g = self._grip_mover()
        pintor.setPen(Qt.NoPen)
        pintor.setBrush(QColor(theme.accent()))
        pintor.drawRoundedRect(g, 6, 6)
        pix = icon("grip", "#ffffff", 16).pixmap(16, 16)
        pintor.drawPixmap(int(g.center().x() - 8), int(g.center().y() - 8), pix)
