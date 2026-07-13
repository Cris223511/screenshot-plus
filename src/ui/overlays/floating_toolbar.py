"""barra de herramientas flotante del modo presentación.

es una columna de botones que vive sobre las demás aplicaciones,
arrastrable y fijable con el pin. cada botón activa una herramienta de la
pizarra y muestra su letra de atajo debajo del ícono. puede recogerse en
un chip para quitarla de en medio sin cerrar la pizarra.
"""

from PySide6.QtCore import (QEasingCurve, QPoint, QPropertyAnimation, QRectF,
                            QSize, Qt, Signal)
from PySide6.QtGui import (QColor, QGuiApplication, QPainter, QPainterPath,
                           QPen, QRegion)
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout, QWidget

from src.config.settings import settings
from src.core import capture
from src.i18n.translator import t
from src.ui.themes.theme_manager import theme
from src.ui.widgets.animated_button import AnimatedButton
from src.ui.widgets.icons import icon

# letras de fábrica de cada herramienta; el usuario puede cambiarlas en
# opciones y acá se leen las vigentes
DEFAULT_KEYS = {"zoom": "Z", "select": "V", "hand": "H", "laser": "L",
                "brush": "P", "highlight": "R", "line": "I", "arrow": "F",
                "shape": "S", "eraser": "E", "text": "T", "pixelate": "X"}


def board_key(modo: str) -> str:
    """la letra vigente de una herramienta del panel."""
    personalizadas = settings.get("board_keys", {})
    letra = str(personalizadas.get(modo, DEFAULT_KEYS.get(modo, ""))).upper()
    return letra[:1]


class FloatingToolbar(QWidget):
    mode_changed = Signal(str)
    shape_changed = Signal(str)
    # el re-clic sobre la herramienta ya activa alterna la ventanita de
    # propiedades, sin apagar nada
    active_reclicked = Signal()
    undo_clicked = Signal()
    redo_clicked = Signal()
    clear_clicked = Signal()
    capture_clicked = Signal()
    image_clicked = Signal()
    props_clicked = Signal()
    exit_clicked = Signal()
    moved = Signal()

    def __init__(self):
        super().__init__(None, Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setObjectName("barraFlotante")
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self.setAttribute(Qt.WA_AlwaysShowToolTips, True)
        self._arrastre: QPoint | None = None
        self._activo = "none"
        self._chip: _RestoreChip | None = None
        # con el panel recogido en el chip, nada debe volver a mostrarlo
        # salvo un clic del usuario sobre ese chip
        self._minimizado = False
        # cada botón registra su ícono para repintarse al cambiar de tema
        self._recolor: dict = {}
        theme.theme_changed.connect(self._refrescar_tema)

        columna = QVBoxLayout(self)
        columna.setContentsMargins(9, 10, 9, 12)
        columna.setSpacing(2)

        # el agarre de arriba invita a mover el panel; en realidad todo el
        # fondo arrastra, pero sin una señal visual nadie lo descubre
        self._agarre = QLabel()
        self._agarre.setPixmap(icon("grip", theme.icon_color()).pixmap(QSize(18, 18)))
        self._agarre.setAlignment(Qt.AlignCenter)
        self._agarre.setToolTip(t("zoom.drag"))
        self._agarre.setCursor(Qt.SizeAllCursor)
        columna.addWidget(self._agarre)

        self._modos: dict[str, AnimatedButton] = {}

        def boton(nombre_icono: str, tooltip: str, letra: str = "",
                  marcable: bool = False) -> AnimatedButton:
            b = AnimatedButton()
            b.setIcon(icon(nombre_icono, theme.icon_color()))
            b.setIconSize(QSize(19, 19))
            b.setToolTip(tooltip)
            b.setCheckable(marcable)
            b.setCursor(Qt.PointingHandCursor)
            self._recolor[b] = nombre_icono
            if letra:
                # la letra del atajo va en gris bajo el ícono; el tooltip
                # aclara que dentro de la pizarra basta la letra y que
                # desde cualquier otra ventana funciona alt más la letra
                b.setText(letra)
                b.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
                b.setToolTip(f"{tooltip}  ({letra} · Alt+{letra})")
            else:
                # los botones de acción (deshacer, rehacer, imagen...) no
                # llevan letra; un mínimo más generoso los separa y les da
                # aire para que no queden apretados entre sí
                b.setMinimumSize(38, 32)
            columna.addWidget(b, 0, Qt.AlignHCenter)
            return b

        def separador():
            linea = QFrame()
            linea.setFrameShape(QFrame.HLine)
            linea.setStyleSheet("color: rgba(128,128,128,60);")
            columna.addWidget(linea)

        # arriba las herramientas de navegación (zoom, selección, mano) y
        # abajo las de dibujo: borrador, lápiz, línea, flecha, figura,
        # texto, pincel de ocultar, resaltador y láser
        self._modos["zoom"] = boton("zoom", t("zoom.live"), board_key("zoom"), True)
        self._modos["select"] = boton("select", t("tool.select"), board_key("select"), True)
        self._modos["hand"] = boton("hand", t("zoom.hand"), board_key("hand"), True)
        separador()
        self._modos["eraser"] = boton("eraser", t("tool.eraser"), board_key("eraser"), True)
        self._modos["brush"] = boton("brush", t("zoom.brush"), board_key("brush"), True)
        self._modos["line"] = boton("line", t("tool.line"), board_key("line"), True)
        self._modos["arrow"] = boton("arrow", t("tool.arrow"), board_key("arrow"), True)
        self._modos["shape"] = boton("shape-rect", t("tool.shapes"), board_key("shape"), True)
        self._menu_formas(self._modos["shape"])
        self._modos["text"] = boton("text", t("tool.text"), board_key("text"), True)
        self._modos["pixelate"] = boton("pixelate", t("tool.pixelate"), board_key("pixelate"), True)
        self._modos["highlight"] = boton("highlighter", t("zoom.highlight"), board_key("highlight"), True)
        self._modos["laser"] = boton("laser", t("zoom.laser"), board_key("laser"), True)
        separador()
        columna.addSpacing(2)
        deshacer = boton("undo", t("tool.undo") + "  (Ctrl+Z)")
        columna.addSpacing(3)
        rehacer = boton("redo", t("tool.redo") + "  (Ctrl+Y)")
        columna.addSpacing(3)
        limpiar = boton("clear", t("zoom.clear") + "  (C)")
        columna.addSpacing(3)
        capturar = boton("camera", t("zoom.capture"))
        columna.addSpacing(3)
        imagen = boton("image", t("tool.image"))
        columna.addSpacing(2)
        separador()
        minimizar = boton("minimize", t("main.tip_minimize"))
        salir = boton("exit", t("zoom.exit") + "  (Esc)")

        deshacer.clicked.connect(self.undo_clicked)
        rehacer.clicked.connect(self.redo_clicked)
        limpiar.clicked.connect(self.clear_clicked)
        capturar.clicked.connect(self.capture_clicked)
        imagen.clicked.connect(self.image_clicked)
        minimizar.clicked.connect(self.minimizar)
        salir.clicked.connect(self.exit_clicked)
        for nombre, b in self._modos.items():
            if nombre != "shape":
                b.clicked.connect(lambda _=False, n=nombre: self.set_mode(n))

        self.adjustSize()
        self._acomodar_derecha()

    def _menu_formas(self, boton: AnimatedButton):
        """el botón de formas despliega las ocho: círculo, cuadrado y compañía."""
        from PySide6.QtWidgets import QMenu
        from src.ui.overlays import annotation_tools as an
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

    def _elegir_forma(self, clave: str, icono: str):
        self._forma_actual = clave
        self._modos["shape"].setIcon(icon(icono, theme.icon_color()))
        self._recolor[self._modos["shape"]] = icono
        self.shape_changed.emit(clave)
        # elegir la misma forma otra vez no debe contar como re-clic (el
        # re-clic alterna las propiedades); solo se activa el modo si no
        # estaba puesto
        if self._activo != "shape":
            self.set_mode("shape")
        else:
            self.set_checked_silent("shape")

    def _acomodar_derecha(self):
        """posición inicial: la última que el usuario dejó, si sigue dentro
        de pantalla; de lo contrario, centrado contra el borde derecho."""
        guardada = settings.get("board_pos")
        if guardada and len(guardada) == 2:
            destino = QPoint(int(guardada[0]), int(guardada[1]))
            virtual = QGuiApplication.primaryScreen().virtualGeometry()
            if virtual.adjusted(0, 0, -40, -40).contains(destino):
                self.move(destino)
                return
        pantalla = QGuiApplication.primaryScreen().availableGeometry()
        self.move(pantalla.right() - self.width() - 16,
                  pantalla.center().y() - self.height() // 2)

    def _guardar_pos(self):
        settings.set("board_pos", [self.x(), self.y()])

    def minimizar(self):
        """el panel se recoge en un chip flotante; el chip lo restaura.

        es la única forma en que el panel deja de verse: ni las capturas
        ni el cambio de herramienta lo esconden jamás. al recogerlo, un
        aviso recuerda que las herramientas siguen a un alt+letra de
        distancia, que si no nadie lo adivina.
        """
        self._guardar_pos()
        self._minimizado = True
        if self._chip is None:
            self._chip = _RestoreChip(self)
        self._chip.move(self.x() + (self.width() - self._chip.width()) // 2, self.y())
        self._chip.show()
        self.hide()
        from src.ui.notifications import notify
        notify(t("zoom.chip_tip"), "panel")

    def restaurar(self):
        self._minimizado = False
        if self._chip is not None:
            self._chip.hide()
        self.show()

    def mostrar_si_procede(self):
        """vuelve a mostrar el panel solo si el usuario no lo minimizó; lo
        usan las operaciones que reactivan la pizarra para no resucitar un
        panel que el usuario recogió a propósito."""
        if not self._minimizado:
            self.show()

    def set_mode(self, nombre: str):
        """activa una herramienta; funcionan como radio, no como toggle.

        volver a clicar la herramienta activa (o repetir su tecla) NO la
        apaga: la pausa solo se abandona con esc o el botón de salir. esa
        decisión evita despausar y perder dibujos por un clic de más.
        """
        for n, b in self._modos.items():
            b.setChecked(n == nombre)
        if nombre != self._activo:
            self._activo = nombre
            self.mode_changed.emit(nombre)
        else:
            self.active_reclicked.emit()

    def toggle_mode(self, nombre: str):
        """entrada desde el teclado.

        repetir la letra de la herramienta activa no hace nada, con una
        excepción útil: repetir la letra de formas va rotando entre las
        ocho (rectángulo, círculo, rombo...), así se elige figura sin
        abrir el menú, incluso con el panel minimizado.
        """
        if nombre == "shape" and self._activo == "shape":
            self._siguiente_forma()
            return
        self.set_mode(nombre)

    def _siguiente_forma(self):
        from src.ui.overlays import annotation_tools as an
        claves = list(an.SHAPES)
        actual = getattr(self, "_forma_actual", "rect")
        siguiente = claves[(claves.index(actual) + 1) % len(claves)]
        self._forma_actual = siguiente
        self._modos["shape"].setIcon(icon(an.SHAPES[siguiente][0], theme.icon_color()))
        self._recolor[self._modos["shape"]] = an.SHAPES[siguiente][0]
        self.shape_changed.emit(siguiente)

    def _refrescar_tema(self, _tema: str = ""):
        """con el cambio de tema, íconos, agarre y fondo se repintan al
        instante; antes quedaban con los colores del tema anterior."""
        for boton, nombre in self._recolor.items():
            boton.setIcon(icon(nombre, theme.icon_color()))
        self._agarre.setPixmap(icon("grip", theme.icon_color()).pixmap(QSize(18, 18)))
        self.update()
        if self._chip is not None:
            self._chip.update()

    def clear_mode(self):
        """apaga todos los modos sin emitir nada; el que llama decide qué sigue."""
        for b in self._modos.values():
            b.setChecked(False)
        self._activo = "none"

    def set_checked_silent(self, nombre: str):
        """marca un modo sin emitir; sirve para restaurar el botón cuando
        el usuario se arrepiente de descartar lo dibujado."""
        for n, b in self._modos.items():
            b.setChecked(n == nombre)
        self._activo = nombre

    def is_pinned(self) -> bool:
        """el panel vive siempre adelante; el pin dejó de existir."""
        return True

    def current_mode(self) -> str:
        return self._activo

    def paintEvent(self, _):
        """fondo sólido de esquinas redondeadas, pintado a mano igual que
        el panel principal, para que nunca quede transparente."""
        pintor = QPainter(self)
        pintor.setRenderHint(QPainter.Antialiasing)
        camino = QPainterPath()
        camino.addRoundedRect(QRectF(self.rect()), 9, 9)
        pintor.fillPath(camino, QColor(theme.panel_bg()))
        # el borde va pintado justo sobre el filo de la máscara: el
        # recorte sin suavizado queda teñido del color del borde y las
        # esquinas se ven parejas, a juego con el panel principal
        pintor.setPen(QPen(QColor(theme.panel_border()), 2.5))
        pintor.drawPath(camino)
        pintor.end()

    def resizeEvent(self, e):
        # la ventana es opaca a propósito (así windows acepta excluirla de
        # las capturas); la máscara recorta las esquinas para que se vea
        # redondeada igual
        camino = QPainterPath()
        camino.addRoundedRect(QRectF(self.rect()), 9, 9)
        self.setMask(QRegion(camino.toFillPolygon().toPolygon()))
        super().resizeEvent(e)

    def showEvent(self, e):
        super().showEvent(e)
        # invisible para toda captura: ni la foto congelada de la pizarra
        # ni las capturas del usuario lo incluyen jamás; y fuera de la
        # barra de tareas sin el auto-ocultado de qt.tool
        capture.exclude_from_capture(self)
        capture.make_tool_window(self)

    def fade_in(self):
        self.setWindowOpacity(0.0)
        self.show()
        self._entrada = QPropertyAnimation(self, b"windowOpacity", self)
        self._entrada.setDuration(220)
        self._entrada.setStartValue(0.0)
        self._entrada.setEndValue(1.0)
        self._entrada.setEasingCurve(QEasingCurve.OutCubic)
        self._entrada.start()

    # el arrastre permite dejar el panel en cualquier borde: derecha,
    # izquierda, arriba o abajo, como prefiera cada quien
    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._arrastre = e.position().toPoint()

    def mouseMoveEvent(self, e):
        if self._arrastre is not None:
            self.move(e.globalPosition().toPoint() - self._arrastre)

    def mouseReleaseEvent(self, _):
        if self._arrastre is not None:
            # la posición nueva se recuerda para la próxima sesión
            self._guardar_pos()
        self._arrastre = None

    def moveEvent(self, e):
        # la ventanita de propiedades acompaña al panel donde vaya
        self.moved.emit()
        super().moveEvent(e)

    def closeEvent(self, e):
        self._guardar_pos()
        if self._chip is not None:
            self._chip.close()
        super().closeEvent(e)


class _RestoreChip(QWidget):
    """botoncito flotante que queda cuando el panel se minimiza."""

    def __init__(self, panel: FloatingToolbar):
        super().__init__(None, Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self._panel = panel
        self._arrastre: QPoint | None = None
        self._movio = False
        self.setFixedSize(40, 40)
        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip(t("zoom.chip_tip"))

    def paintEvent(self, _):
        pintor = QPainter(self)
        pintor.setRenderHint(QPainter.Antialiasing)
        camino = QPainterPath()
        camino.addRoundedRect(QRectF(self.rect()), 9, 9)
        pintor.fillPath(camino, QColor(theme.panel_bg()))
        pintor.setPen(QPen(QColor(theme.panel_border()), 2.5))
        pintor.drawPath(camino)
        icon("panel", theme.icon_active_color()).paint(pintor, 10, 10, 20, 20)
        pintor.end()

    def resizeEvent(self, e):
        camino = QPainterPath()
        camino.addRoundedRect(QRectF(self.rect()), 9, 9)
        self.setMask(QRegion(camino.toFillPolygon().toPolygon()))
        super().resizeEvent(e)

    def showEvent(self, e):
        super().showEvent(e)
        capture.exclude_from_capture(self)
        capture.make_tool_window(self)

    # arrastrable como el panel; un clic sin arrastre restaura
    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._arrastre = e.position().toPoint()
            self._movio = False

    def mouseMoveEvent(self, e):
        if self._arrastre is not None:
            destino = e.globalPosition().toPoint() - self._arrastre
            if (destino - self.pos()).manhattanLength() > 3:
                self._movio = True
            self.move(destino)

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.LeftButton and not self._movio:
            self._panel.move(self.x(), self.y())
            self._panel.restaurar()
        self._arrastre = None
