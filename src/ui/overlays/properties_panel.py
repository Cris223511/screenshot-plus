"""panel de propiedades del modo presentación.

flota junto a la barra de herramientas y muestra solo los controles que
aplican a la herramienta activa (color, grosor, trazo, opacidad,
tipografía, opciones del pincel de ocultar). con un elemento seleccionado
carga sus valores y lo edita en vivo. todo sale por una señal genérica
(nombre, valor) que el coordinador del modo aplica.
"""

from PySide6.QtCore import (QEasingCurve, QPropertyAnimation, QRectF, QSize,
                            Qt, Signal)
from PySide6.QtGui import QColor, QFont, QFontDatabase, QPainter, QPainterPath
from PySide6.QtWidgets import (QColorDialog, QComboBox, QGridLayout,
                               QHBoxLayout, QLabel, QLineEdit, QPushButton,
                               QSlider, QSpinBox, QVBoxLayout, QWidget)

from src.config.settings import settings
from src.i18n.translator import t
from src.ui.overlays import annotation_tools as an
from src.ui.themes.theme_manager import theme
from src.ui.widgets.animated_button import AnimatedButton
from src.ui.widgets.icons import icon

# la carta de colores: fuertes para señalar, tonos medios y neutros
_COLORES = ["#e5484d", "#ff8c00", "#f5d90a", "#30a46c", "#12a594", "#2f7df6",
            "#6e56cf", "#e93d82", "#8e4ec6", "#f76b15", "#86efac", "#7dd3fc",
            "#fda4af", "#a16207", "#111111", "#6b7280", "#d1d5db", "#ffffff"]

def system_fonts() -> list[str]:
    """todas las tipografías instaladas, sin las variantes verticales."""
    return [f for f in QFontDatabase.families() if not f.startswith("@")]


class _Muestra(QPushButton):
    """cuadradito de color con esquinas suaves y anillo cuando está activo."""

    def __init__(self, color: str):
        super().__init__()
        self.color = QColor(color)
        self.activo = False
        self.setFixedSize(24, 24)
        self.setCursor(Qt.PointingHandCursor)

    def paintEvent(self, _):
        pintor = QPainter(self)
        pintor.setRenderHint(QPainter.Antialiasing)
        camino = QPainterPath()
        camino.addRoundedRect(QRectF(self.rect()).adjusted(3, 3, -3, -3), 6, 6)
        pintor.fillPath(camino, self.color)
        pintor.setPen(QColor(0, 0, 0, 50))
        pintor.drawPath(camino)
        if self.activo or self.underMouse():
            pintor.setPen(QColor(theme.accent()))
            anillo = QPainterPath()
            anillo.addRoundedRect(QRectF(self.rect()).adjusted(1, 1, -1, -1), 7, 7)
            pintor.drawPath(anillo)
        pintor.end()


class PropertiesPanel(QWidget):
    # una sola señal genérica: nombre de la propiedad y su valor nuevo
    prop_changed = Signal(str, object)
    minimized = Signal()

    def __init__(self):
        super().__init__(None, Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setObjectName("barraFlotante")
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self.setAttribute(Qt.WA_AlwaysShowToolTips, True)
        self.setFixedWidth(232)

        columna = QVBoxLayout(self)
        columna.setContentsMargins(14, 6, 14, 12)
        columna.setSpacing(6)

        # el botoncito de arriba recoge la ventanita; vuelve con el re-clic
        # de la herramienta o al seleccionar algo
        encabezado = QHBoxLayout()
        encabezado.addStretch()
        self._boton_min = AnimatedButton()
        self._boton_min.setIcon(icon("minimize", theme.icon_color()))
        self._boton_min.setIconSize(QSize(15, 15))
        self._boton_min.setToolTip(t("main.tip_minimize"))
        self._boton_min.setCursor(Qt.PointingHandCursor)
        self._boton_min.clicked.connect(self.minimized)
        encabezado.addWidget(self._boton_min)
        columna.addLayout(encabezado)

        # el registro de botones con ícono permite repintarlos cuando el
        # usuario cambia entre tema claro y oscuro
        self._recolor: list[tuple] = [(self._boton_min, "minimize")]
        theme.theme_changed.connect(self._refrescar_tema)

        def rotulo(clave: str) -> QLabel:
            r = QLabel(t(clave))
            r.setObjectName("secundario")
            columna.addWidget(r)
            return r


        # colores en rejilla, con los recientes del usuario y el campo hex
        self._rotulo_color = rotulo("tool.color")
        rejilla = QGridLayout()
        rejilla.setSpacing(2)
        self._muestras: list[_Muestra] = []
        for i, hexa in enumerate(_COLORES):
            m = _Muestra(hexa)
            m.clicked.connect(lambda _=False, mm=m: self._elegir_color(mm.color, mm))
            rejilla.addWidget(m, i // 6, i % 6)
            self._muestras.append(m)
        self._caja_colores = QWidget()
        self._caja_colores.setLayout(rejilla)
        columna.addWidget(self._caja_colores)

        self._rotulo_recientes = rotulo("prop.recent")
        rejilla_r = QGridLayout()
        rejilla_r.setSpacing(2)
        self._caja_recientes = QWidget()
        self._caja_recientes.setLayout(rejilla_r)
        columna.addWidget(self._caja_recientes)
        self._rejilla_recientes = rejilla_r
        self._cargar_recientes()

        fila_hex = QHBoxLayout()
        self._hex = QLineEdit()
        self._hex.setPlaceholderText("#rrggbb")
        self._hex.setMaxLength(7)
        self._hex.returnPressed.connect(self._aplicar_hex)
        selector = QPushButton("+")
        selector.setFixedWidth(34)
        selector.setToolTip(t("tool.color"))
        selector.clicked.connect(self._abrir_selector)
        fila_hex.addWidget(self._hex)
        fila_hex.addWidget(selector)
        self._caja_hex = QWidget()
        self._caja_hex.setLayout(fila_hex)
        columna.addWidget(self._caja_hex)

        # grosor
        self._rotulo_grosor = rotulo("tool.thickness")
        self._grosor = QSlider(Qt.Horizontal)
        self._grosor.setRange(1, 30)
        self._grosor.setValue(4)
        self._grosor.valueChanged.connect(lambda v: self.prop_changed.emit("width", v))
        columna.addWidget(self._grosor)

        # estilo de trazo como botones gráficos: se ve lo que se elige
        nombres_dash = {"solid": t("tool.dash_solid"), "dashed": t("tool.dash_dashed"),
                        "dotted": t("tool.dash_dotted"), "dashdot": t("tool.dash_dashdot"),
                        "dashdotdot": t("tool.dash_dashdotdot")}
        self._rotulo_trazo = rotulo("prop.stroke")
        self._caja_trazo, self._trazo_botones = self._grupo_iconos(
            [(f"dash-{c}", c, nombres_dash[c]) for c in an.DASHES],
            "dash", "solid")
        columna.addWidget(self._caja_trazo)

        # extremos de línea y flecha, también gráficos, cada punta aparte
        iconos_cap = {"none": "cap-none", "arrow": "cap-arrow",
                      "arrow_filled": "cap-arrow-filled", "dot": "cap-dot",
                      "square": "cap-square", "diamond": "cap-diamond"}
        nombres_cap = {"none": t("tool.cap_none"), "arrow": t("tool.cap_arrow"),
                       "arrow_filled": t("tool.cap_arrow_filled"), "dot": t("tool.cap_dot"),
                       "square": t("tool.cap_square"), "diamond": t("tool.cap_diamond")}
        self._rotulo_cap_i = rotulo("tool.line_start")
        self._caja_cap_i, self._cap_i_botones = self._grupo_iconos(
            [(iconos_cap[c], c, nombres_cap[c]) for c in an.CAPS], "cap_start", "none")
        columna.addWidget(self._caja_cap_i)
        self._rotulo_cap_f = rotulo("tool.line_end")
        self._caja_cap_f, self._cap_f_botones = self._grupo_iconos(
            [(iconos_cap[c], c, nombres_cap[c]) for c in an.CAPS], "cap_end", "arrow_filled")
        columna.addWidget(self._caja_cap_f)

        # tipografía: todas las del sistema, cada nombre con su propia letra
        self._rotulo_fuente = rotulo("tool.font")
        self._fuente = QComboBox()
        for familia in system_fonts():
            self._fuente.addItem(familia)
            self._fuente.setItemData(self._fuente.count() - 1, QFont(familia), Qt.FontRole)
        indice_defecto = self._fuente.findText("Segoe UI")
        if indice_defecto >= 0:
            self._fuente.setCurrentIndex(indice_defecto)
        self._fuente.currentTextChanged.connect(
            lambda f: self.prop_changed.emit("font_family", f))
        columna.addWidget(self._fuente)

        fila_texto = QHBoxLayout()
        self._tamano = QSpinBox()
        self._tamano.setRange(8, 120)
        self._tamano.setValue(18)
        self._tamano.setToolTip(t("tool.fontsize"))
        self._tamano.valueChanged.connect(lambda v: self.prop_changed.emit("font_size", v))
        fila_texto.addWidget(self._tamano)
        self._negrita = AnimatedButton()
        self._recolor.append((self._negrita, "bold"))
        self._negrita.setIcon(icon("bold", theme.icon_color()))
        self._negrita.setCheckable(True)
        self._negrita.setToolTip(t("tool.bold"))
        self._negrita.toggled.connect(lambda v: self.prop_changed.emit("bold", v))
        fila_texto.addWidget(self._negrita)
        self._cursiva = AnimatedButton()
        self._recolor.append((self._cursiva, "italic"))
        self._cursiva.setIcon(icon("italic", theme.icon_color()))
        self._cursiva.setCheckable(True)
        self._cursiva.setToolTip(t("tool.italic"))
        self._cursiva.toggled.connect(lambda v: self.prop_changed.emit("italic", v))
        fila_texto.addWidget(self._cursiva)

        self._subrayado = AnimatedButton()
        self._recolor.append((self._subrayado, "underline"))
        self._subrayado.setIcon(icon("underline", theme.icon_color()))
        self._subrayado.setCheckable(True)
        self._subrayado.setToolTip(t("tool.underline"))
        self._subrayado.toggled.connect(lambda v: self.prop_changed.emit("underline", v))
        fila_texto.addWidget(self._subrayado)

        self._tachado = AnimatedButton()
        self._recolor.append((self._tachado, "strike"))
        self._tachado.setIcon(icon("strike", theme.icon_color()))
        self._tachado.setCheckable(True)
        self._tachado.setToolTip(t("tool.strike"))
        self._tachado.toggled.connect(lambda v: self.prop_changed.emit("strike", v))
        fila_texto.addWidget(self._tachado)
        fila_texto.addStretch()
        self._caja_texto = QWidget()
        self._caja_texto.setLayout(fila_texto)
        columna.addWidget(self._caja_texto)

        # espaciado entre letras y rotación del texto
        self._rotulo_espaciado = rotulo("prop.letter_spacing")
        self._espaciado = QSlider(Qt.Horizontal)
        self._espaciado.setRange(0, 24)
        self._espaciado.valueChanged.connect(
            lambda v: self.prop_changed.emit("letter_spacing", v))
        columna.addWidget(self._espaciado)

        self._rotulo_rotacion = rotulo("prop.rotation")
        fila_rot = QHBoxLayout()
        self._rotacion = QSlider(Qt.Horizontal)
        self._rotacion.setRange(-180, 180)
        self._rotacion.setValue(0)
        self._valor_rot = QLabel("0°")
        self._valor_rot.setFixedWidth(38)
        self._valor_rot.setObjectName("secundario")
        self._rotacion.valueChanged.connect(self._cambio_rotacion)
        fila_rot.addWidget(self._rotacion)
        fila_rot.addWidget(self._valor_rot)
        self._caja_rotacion = QWidget()
        self._caja_rotacion.setLayout(fila_rot)
        columna.addWidget(self._caja_rotacion)

        # fondo del texto: nada, sólido o redondeado, con su color aparte
        self._rotulo_fondo = rotulo("prop.text_bg")
        fila_fondo = QHBoxLayout()
        fila_fondo.setContentsMargins(0, 0, 0, 0)
        fila_fondo.setSpacing(2)
        nombres_bg = {"none": t("prop.bg_none"), "solid": t("prop.bg_solid"),
                      "rounded": t("prop.bg_rounded")}
        self._caja_bg, self._bg_botones = self._grupo_iconos(
            [(f"bg-{c}", c, nombres_bg[c]) for c in ("none", "solid", "rounded")],
            "text_bg", "none")
        fila_fondo.addWidget(self._caja_bg)
        self._bg_color = QPushButton()
        self._bg_color.setFixedSize(30, 26)
        self._bg_color.setToolTip(t("prop.bg_color"))
        self._bg_color.setStyleSheet("background: #ffffff; border-radius: 6px;"
                                     " border: 1px solid rgba(0,0,0,50);")
        self._bg_color.clicked.connect(self._elegir_bg_color)
        fila_fondo.addWidget(self._bg_color)
        self._caja_fondo = QWidget()
        self._caja_fondo.setLayout(fila_fondo)
        columna.addWidget(self._caja_fondo)

        # sombra y contorno del texto
        from PySide6.QtWidgets import QCheckBox
        self._sombra = QCheckBox(t("prop.shadow"))
        self._sombra.toggled.connect(lambda v: self.prop_changed.emit("shadow", v))
        columna.addWidget(self._sombra)
        self._contorno = QCheckBox(t("prop.outline"))
        self._contorno.toggled.connect(lambda v: self.prop_changed.emit("outline", v))
        columna.addWidget(self._contorno)

        # opacidad
        self._rotulo_opacidad = rotulo("tool.opacity")
        fila_op = QHBoxLayout()
        self._opacidad = QSlider(Qt.Horizontal)
        self._opacidad.setRange(10, 100)
        self._opacidad.setValue(100)
        self._valor_op = QLabel("100%")
        self._valor_op.setFixedWidth(38)
        self._valor_op.setObjectName("secundario")
        self._opacidad.valueChanged.connect(self._cambio_opacidad)
        fila_op.addWidget(self._opacidad)
        fila_op.addWidget(self._valor_op)
        self._caja_opacidad = QWidget()
        self._caja_opacidad.setLayout(fila_op)
        columna.addWidget(self._caja_opacidad)

        # pincel de ocultar: el efecto (pixelar o difuminar) y su
        # intensidad; el grosor del trazo reutiliza el slider de arriba
        self._rotulo_pixel_modo = rotulo("pixel.pixelate")
        self._rotulo_pixel_modo.setText(t("pixel.pixelate") + " / " + t("pixel.blur"))
        self._pixel_modo = QComboBox()
        self._pixel_modo.addItem(t("pixel.pixelate"), "pixelate")
        self._pixel_modo.addItem(t("pixel.blur"), "blur")
        self._pixel_modo.currentIndexChanged.connect(
            lambda i: self.prop_changed.emit("pixel_mode", self._pixel_modo.itemData(i)))
        columna.addWidget(self._pixel_modo)
        self._rotulo_pixel_cant = rotulo("pixel.amount")
        self._pixel_cant = QSlider(Qt.Horizontal)
        self._pixel_cant.setRange(2, 40)
        self._pixel_cant.setValue(an.PIXEL_CANTIDAD)
        self._pixel_cant.valueChanged.connect(
            lambda v: self.prop_changed.emit("pixel_amount", v))
        columna.addWidget(self._pixel_cant)

        columna.addStretch()

    # ------------------------------------------------------------------ #
    # grupos de botones gráficos

    def _grupo_iconos(self, opciones: list, prop: str, defecto: str):
        """una fila de botones excluyentes con ícono, estilo excalidraw.

        devuelve la caja para el layout y el mapa clave → botón, que sirve
        para marcar el vigente al cargar un elemento seleccionado.
        """
        caja = QWidget()
        fila = QHBoxLayout(caja)
        fila.setContentsMargins(0, 0, 0, 0)
        fila.setSpacing(2)
        botones: dict[str, AnimatedButton] = {}
        for icono, clave, tip in opciones:
            b = AnimatedButton()
            b.setIcon(icon(icono, theme.icon_color()))
            b.setIconSize(QSize(18, 18))
            b.setCheckable(True)
            b.setToolTip(tip)
            b.setCursor(Qt.PointingHandCursor)
            b.clicked.connect(lambda _=False, c=clave: self._elegir_grupo(prop, c, botones))
            fila.addWidget(b)
            botones[clave] = b
            self._recolor.append((b, icono))
        fila.addStretch()
        botones[defecto].setChecked(True)
        return caja, botones

    def _elegir_grupo(self, prop: str, clave: str, botones: dict):
        for c, b in botones.items():
            b.setChecked(c == clave)
        self.prop_changed.emit(prop, clave)

    @staticmethod
    def _marcar_grupo(botones: dict, clave: str):
        for c, b in botones.items():
            b.setChecked(c == clave)

    # ------------------------------------------------------------------ #
    # colores

    def _cambio_opacidad(self, v: int):
        self._valor_op.setText(f"{v}%")
        self.prop_changed.emit("opacity", v / 100.0)

    def _cambio_rotacion(self, v: int):
        self._valor_rot.setText(f"{v}°")
        self.prop_changed.emit("rotation", float(v))

    def _elegir_bg_color(self):
        color = QColorDialog.getColor(QColor("#ffffff"), self)
        if color.isValid():
            self._bg_color.setStyleSheet(
                f"background: {color.name()}; border-radius: 6px;"
                " border: 1px solid rgba(0,0,0,50);")
            self.prop_changed.emit("text_bg_color", QColor(color))

    def _elegir_color(self, color: QColor, muestra: _Muestra | None = None):
        for m in self._muestras:
            m.activo = muestra is m
            m.update()
        self._hex.setText(color.name())
        self.prop_changed.emit("color", QColor(color))

    def _aplicar_hex(self):
        color = QColor(self._hex.text().strip())
        if color.isValid():
            self._elegir_color(color)
            self._recordar_reciente(color)

    def _abrir_selector(self):
        # el selector del sistema trae rueda, rgb y valores numéricos
        color = QColorDialog.getColor(QColor(self._hex.text() or "#e5484d"), self)
        if color.isValid():
            self._elegir_color(color)
            self._recordar_reciente(color)

    def _recordar_reciente(self, color: QColor):
        recientes = [c for c in settings.get("recent_colors", []) if c != color.name()]
        recientes.insert(0, color.name())
        settings.set("recent_colors", recientes[:6])
        self._cargar_recientes()

    def _cargar_recientes(self):
        while self._rejilla_recientes.count():
            viejo = self._rejilla_recientes.takeAt(0).widget()
            if viejo:
                viejo.deleteLater()
        recientes = settings.get("recent_colors", [])
        self._rotulo_recientes.setVisible(bool(recientes))
        self._caja_recientes.setVisible(bool(recientes))
        for i, hexa in enumerate(recientes[:6]):
            m = _Muestra(hexa)
            m.clicked.connect(lambda _=False, mm=m: self._elegir_color(mm.color, None))
            self._rejilla_recientes.addWidget(m, 0, i)

    # ------------------------------------------------------------------ #
    # qué se muestra y con qué valores

    def show_for(self, modo: str, items: list | None = None):
        """adapta las secciones a la herramienta o a la selección.

        con un solo elemento seleccionado, los controles cargan sus valores
        reales; las señales se silencian durante la carga para no disparar
        cambios fantasma.
        """
        # con varios elementos tomados, se muestran solo las opciones comunes
        # a todos (la intersección), no las de la herramienta
        if items and len(items) > 1:
            self._mostrar_para_varios(items)
            return

        es_laser = modo == "laser"
        es_pixel = modo == "pixelate"
        es_trazo = modo in ("brush", "highlight", "line", "arrow", "shape",
                            "select") or es_laser
        es_lineal = modo in ("line", "arrow")
        es_texto = modo in ("text",)
        item = items[0] if items and len(items) == 1 else None
        if item is not None:
            es_lineal = isinstance(item, an.LineItem)
            es_texto = isinstance(item, an.TextItem)
            es_pixel = isinstance(item, an.PixelateItem)
            # un trazo de ocultar seleccionado también quiere ver su grosor
            if es_pixel:
                es_trazo = True

        con_color = (modo != "select" or bool(items)) and not es_pixel
        for w in (self._rotulo_color, self._caja_colores, self._caja_hex):
            w.setVisible(con_color)
        self._caja_recientes.setVisible(con_color and bool(settings.get("recent_colors", [])))
        self._rotulo_recientes.setVisible(self._caja_recientes.isVisible())

        es_imagen = isinstance(item, an.ImageItem)
        for w in (self._rotulo_grosor, self._grosor):
            w.setVisible((es_trazo or es_pixel) and not es_texto and not es_imagen)
        # el efecto e intensidad del pincel de ocultar solo con esa herramienta
        for w in (self._rotulo_pixel_modo, self._pixel_modo,
                  self._rotulo_pixel_cant, self._pixel_cant):
            w.setVisible(es_pixel)
        # el láser solo entiende de color y grosor; ni trazos ni opacidad
        for w in (self._rotulo_trazo, self._caja_trazo):
            w.setVisible(es_trazo and not es_texto and not es_imagen and not es_laser)
        for w in (self._rotulo_cap_i, self._caja_cap_i, self._rotulo_cap_f, self._caja_cap_f):
            w.setVisible(es_lineal)
        for w in (self._rotulo_fuente, self._fuente, self._caja_texto,
                  self._rotulo_espaciado, self._espaciado,
                  self._rotulo_rotacion, self._caja_rotacion,
                  self._rotulo_fondo, self._caja_fondo,
                  self._sombra, self._contorno):
            w.setVisible(es_texto)
        for w in (self._rotulo_opacidad, self._caja_opacidad):
            w.setVisible((modo != "select" or bool(items)) and not es_laser and not es_pixel)

        if item is not None:
            self._cargar_de(item)
        self.adjustSize()

    def _mostrar_para_varios(self, items: list):
        """con varios elementos, solo asoman los controles que sirven para
        todos a la vez: color si ninguno es imagen, grosor si ninguno es
        texto, tipografía solo si todos son texto, etc."""
        def apoya(it, cual):
            if cual == "color":
                return not isinstance(it, an.ImageItem)
            if cual == "grosor":
                return not isinstance(it, (an.TextItem, an.ImageItem))
            if cual == "dash":
                return isinstance(it, (an.ShapeItem, an.LineItem)) and not isinstance(it, an.ImageItem)
            if cual == "caps":
                return isinstance(it, an.LineItem)
            if cual == "texto":
                return isinstance(it, an.TextItem)
            return False

        color = all(apoya(i, "color") for i in items)
        grosor = all(apoya(i, "grosor") for i in items)
        dash = all(apoya(i, "dash") for i in items)
        caps = all(apoya(i, "caps") for i in items)
        texto = all(apoya(i, "texto") for i in items)

        for w in (self._rotulo_color, self._caja_colores, self._caja_hex):
            w.setVisible(color)
        self._caja_recientes.setVisible(color and bool(settings.get("recent_colors", [])))
        self._rotulo_recientes.setVisible(self._caja_recientes.isVisible())
        for w in (self._rotulo_grosor, self._grosor):
            w.setVisible(grosor)
        for w in (self._rotulo_pixel_modo, self._pixel_modo,
                  self._rotulo_pixel_cant, self._pixel_cant):
            w.setVisible(False)
        for w in (self._rotulo_trazo, self._caja_trazo):
            w.setVisible(dash)
        for w in (self._rotulo_cap_i, self._caja_cap_i, self._rotulo_cap_f, self._caja_cap_f):
            w.setVisible(caps)
        for w in (self._rotulo_fuente, self._fuente, self._caja_texto,
                  self._rotulo_espaciado, self._espaciado,
                  self._rotulo_rotacion, self._caja_rotacion,
                  self._rotulo_fondo, self._caja_fondo,
                  self._sombra, self._contorno):
            w.setVisible(texto)
        # la opacidad sirve para cualquier trazo, figura o texto
        for w in (self._rotulo_opacidad, self._caja_opacidad):
            w.setVisible(True)
        self.adjustSize()

    def _cargar_de(self, item: an.Item):
        controles = (self._grosor, self._fuente, self._tamano, self._negrita,
                     self._cursiva, self._opacidad, self._subrayado,
                     self._tachado, self._espaciado, self._rotacion,
                     self._sombra, self._contorno)
        for c in controles:
            c.blockSignals(True)
        self._grosor.setValue(int(item.width))
        self._marcar_grupo(self._trazo_botones, item.dash)
        if isinstance(item, an.PixelateItem):
            self._pixel_modo.blockSignals(True)
            self._pixel_cant.blockSignals(True)
            self._pixel_modo.setCurrentIndex(
                max(0, self._pixel_modo.findData(item.mode)))
            self._pixel_cant.setValue(int(item.amount))
            self._pixel_modo.blockSignals(False)
            self._pixel_cant.blockSignals(False)
        self._opacidad.setValue(int(item.opacity * 100))
        self._valor_op.setText(f"{int(item.opacity * 100)}%")
        self._hex.setText(item.color.name())
        if isinstance(item, an.LineItem):
            self._marcar_grupo(self._cap_i_botones, item.cap_start)
            self._marcar_grupo(self._cap_f_botones, item.cap_end)
        if isinstance(item, an.TextItem):
            indice = self._fuente.findText(item.font.family())
            if indice >= 0:
                self._fuente.setCurrentIndex(indice)
            self._tamano.setValue(max(8, item.font.pointSize()))
            self._negrita.setChecked(item.font.bold())
            self._cursiva.setChecked(item.font.italic())
            self._subrayado.setChecked(item.font.underline())
            self._tachado.setChecked(item.font.strikeOut())
            self._espaciado.setValue(int(max(0, item.font.letterSpacing())))
            self._rotacion.setValue(int(item.rotation))
            self._valor_rot.setText(f"{int(item.rotation)}°")
            self._marcar_grupo(self._bg_botones, item.bg)
            self._sombra.setChecked(item.shadow)
            self._contorno.setChecked(item.outline)
            self._bg_color.setStyleSheet(
                f"background: {item.bg_color.name()}; border-radius: 6px;"
                " border: 1px solid rgba(0,0,0,50);")
        for c in controles:
            c.blockSignals(False)

    # ------------------------------------------------------------------ #

    def load_defaults(self, defectos: dict):
        """sin selección, los controles muestran los valores por defecto
        de la pizarra, no los del último elemento tocado."""
        controles = (self._grosor, self._fuente, self._tamano, self._negrita,
                     self._cursiva, self._opacidad)
        for c in controles:
            c.blockSignals(True)
        self._grosor.setValue(int(defectos.get("width", 4)))
        self._marcar_grupo(self._trazo_botones, defectos.get("dash", "solid"))
        self._pixel_modo.blockSignals(True)
        self._pixel_cant.blockSignals(True)
        self._pixel_modo.setCurrentIndex(
            max(0, self._pixel_modo.findData(defectos.get("pixel_mode", "pixelate"))))
        self._pixel_cant.setValue(int(defectos.get("pixel_amount", 12)))
        self._pixel_modo.blockSignals(False)
        self._pixel_cant.blockSignals(False)
        self._marcar_grupo(self._cap_i_botones, defectos.get("cap_start", "none"))
        self._marcar_grupo(self._cap_f_botones, defectos.get("cap_end", "arrow_filled"))
        opacidad = int(defectos.get("opacity", 1.0) * 100)
        self._opacidad.setValue(opacidad)
        self._valor_op.setText(f"{opacidad}%")
        self._hex.setText(defectos.get("color", "#e5484d"))
        fuente = defectos.get("font")
        if fuente is not None:
            indice = self._fuente.findText(fuente.family())
            if indice >= 0:
                self._fuente.setCurrentIndex(indice)
            self._tamano.setValue(max(8, fuente.pointSize()))
            self._negrita.setChecked(fuente.bold())
            self._cursiva.setChecked(fuente.italic())
        for c in controles:
            c.blockSignals(False)

    def _refrescar_tema(self, _tema: str = ""):
        """al cambiar entre claro y oscuro, los íconos y el fondo se
        repintan con los colores nuevos, igual que el resto de la app."""
        for boton, nombre in self._recolor:
            boton.setIcon(icon(nombre, theme.icon_color()))
        self.update()

    def place_near(self, ancla: QWidget):
        """se acomoda al costado del panel de herramientas, hacia adentro
        de la pantalla."""
        pantalla = ancla.screen().availableGeometry()
        self.adjustSize()
        x = ancla.x() - self.width() - 10
        if x < pantalla.left() + 4:
            x = ancla.x() + ancla.width() + 10
        y = max(pantalla.top() + 8, min(ancla.y(), pantalla.bottom() - self.height() - 8))
        self.move(x, y)

    def fade_in(self):
        self.setWindowOpacity(0.0)
        self.show()
        self._entrada = QPropertyAnimation(self, b"windowOpacity", self)
        self._entrada.setDuration(200)
        self._entrada.setStartValue(0.0)
        self._entrada.setEndValue(1.0)
        self._entrada.setEasingCurve(QEasingCurve.OutCubic)
        self._entrada.start()

    def paintEvent(self, _):
        pintor = QPainter(self)
        pintor.setRenderHint(QPainter.Antialiasing)
        camino = QPainterPath()
        camino.addRoundedRect(QRectF(self.rect()), 9, 9)
        pintor.fillPath(camino, QColor(theme.panel_bg()))
        # borde pintado sobre el filo de la máscara, igual que el panel de
        # herramientas: el recorte queda teñido y las esquinas se ven bien
        from PySide6.QtGui import QPen
        pintor.setPen(QPen(QColor(theme.panel_border()), 2.5))
        pintor.drawPath(camino)
        pintor.end()

    def resizeEvent(self, e):
        # ventana opaca con esquinas recortadas por máscara: así windows
        # acepta excluirla de las capturas y nunca hay que esconderla
        from PySide6.QtGui import QRegion
        camino = QPainterPath()
        camino.addRoundedRect(QRectF(self.rect()), 9, 9)
        self.setMask(QRegion(camino.toFillPolygon().toPolygon()))
        super().resizeEvent(e)

    def showEvent(self, e):
        super().showEvent(e)
        from src.core import capture
        capture.exclude_from_capture(self)
        capture.make_tool_window(self)
