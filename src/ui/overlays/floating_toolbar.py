"""panel flotante del modo presentación.

una columna de bordes redondos que aparece pegada al borde derecho de la
pantalla (y se puede arrastrar a donde sea): zoom en vivo, puntero láser,
pincel, resaltador, línea, flecha, la paleta de colores, limpiar, el pin
para fijarlo siempre adelante y el botón de cierre. es una ventana propia,
independiente del overlay de dibujo, así queda visible aunque no haya
ninguna herramienta activa y la pantalla siga funcionando normal.
"""

from PySide6.QtCore import (QEasingCurve, QPoint, QPropertyAnimation, QRectF,
                            QSize, Qt, Signal)
from PySide6.QtGui import QColor, QGuiApplication, QPainter, QPainterPath
from PySide6.QtWidgets import QFrame, QVBoxLayout, QWidget

from src.i18n.translator import t
from src.ui.themes.theme_manager import theme
from src.ui.widgets.animated_button import AnimatedButton
from src.ui.widgets.color_palette import ColorPalette
from src.ui.widgets.icons import icon


class FloatingToolbar(QWidget):
    zoom_in_clicked = Signal()
    zoom_out_clicked = Signal()
    mode_changed = Signal(str)
    color_changed = Signal(QColor)
    clear_clicked = Signal()
    exit_clicked = Signal()

    def __init__(self):
        super().__init__(None, Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setObjectName("barraFlotante")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self._arrastre: QPoint | None = None

        columna = QVBoxLayout(self)
        columna.setContentsMargins(6, 10, 6, 10)
        columna.setSpacing(2)

        self._modos: dict[str, AnimatedButton] = {}

        def boton(nombre_icono: str, tooltip: str, marcable: bool = False) -> AnimatedButton:
            b = AnimatedButton()
            b.setIcon(icon(nombre_icono, theme.icon_color()))
            b.setIconSize(QSize(20, 20))
            b.setToolTip(tooltip)
            b.setCheckable(marcable)
            b.setCursor(Qt.PointingHandCursor)
            columna.addWidget(b, 0, Qt.AlignHCenter)
            return b

        def separador():
            linea = QFrame()
            linea.setFrameShape(QFrame.HLine)
            linea.setStyleSheet("color: rgba(128,128,128,60);")
            columna.addWidget(linea)

        self._modos["zoom"] = boton("zoom", t("zoom.live") + "  (Z)", True)
        acercar = boton("zoom-in", t("zoom.in") + "  (+)")
        alejar = boton("zoom-out", t("zoom.out") + "  (-)")
        separador()
        self._modos["laser"] = boton("laser", t("zoom.laser") + "  (L)", True)
        self._modos["brush"] = boton("brush", t("zoom.brush") + "  (P)", True)
        self._modos["highlight"] = boton("highlighter", t("zoom.highlight") + "  (R)", True)
        self._modos["line"] = boton("line", t("tool.line") + "  (I)", True)
        self._modos["arrow"] = boton("arrow", t("tool.arrow") + "  (F)", True)
        limpiar = boton("clear", t("zoom.clear") + "  (C)")
        separador()

        # la paleta en vertical acompaña la forma del panel
        self._paleta = ColorPalette(vertical=True)
        self._paleta.color_selected.connect(self.color_changed)
        columna.addWidget(self._paleta, 0, Qt.AlignHCenter)

        separador()
        self._pin = boton("pin", t("zoom.pin"), True)
        self._pin.setChecked(True)
        salir = boton("exit", t("zoom.exit") + "  (Esc)")

        acercar.clicked.connect(self.zoom_in_clicked)
        alejar.clicked.connect(self.zoom_out_clicked)
        limpiar.clicked.connect(self.clear_clicked)
        salir.clicked.connect(self.exit_clicked)
        self._pin.toggled.connect(self._alternar_pin)
        for nombre, b in self._modos.items():
            b.clicked.connect(lambda _=False, n=nombre: self.set_mode(n))

        self.adjustSize()
        self._acomodar_derecha()

    def _acomodar_derecha(self):
        """posición inicial: centrado verticalmente contra el borde derecho."""
        pantalla = QGuiApplication.primaryScreen().availableGeometry()
        self.move(pantalla.right() - self.width() - 16,
                  pantalla.center().y() - self.height() // 2)

    def _alternar_pin(self, fijado: bool):
        """el pin decide si el panel queda siempre por encima de todo.

        cambiar banderas de ventana en qt la recrea, por eso el show()
        inmediato: sin él, el panel desaparecería al soltar el pin.
        """
        self.setWindowFlag(Qt.WindowStaysOnTopHint, fijado)
        self.show()

    def set_mode(self, nombre: str):
        """activa un modo; repetirlo lo apaga y vuelve el cursor normal.

        el clic del botón llega con el estado ya alternado por qt, así que
        el botón mismo dice si el modo quedó activo o no; solo hay que
        apagar a los demás y avisar.
        """
        activo = self._modos[nombre].isChecked()
        for n, b in self._modos.items():
            b.setChecked(activo and n == nombre)
        self.mode_changed.emit(nombre if activo else "none")

    def toggle_mode(self, nombre: str):
        """alternancia desde el teclado, donde el botón no se toca solo."""
        self._modos[nombre].setChecked(not self._modos[nombre].isChecked())
        self.set_mode(nombre)

    def clear_mode(self):
        """apaga todos los modos sin emitir nada; el que llama decide qué sigue."""
        for b in self._modos.values():
            b.setChecked(False)

    def current_mode(self) -> str:
        for nombre, b in self._modos.items():
            if b.isChecked():
                return nombre
        return "none"

    def paintEvent(self, _):
        """fondo sólido de esquinas redondeadas, pintado a mano igual que
        el panel principal, para que nunca quede transparente."""
        pintor = QPainter(self)
        pintor.setRenderHint(QPainter.Antialiasing)
        camino = QPainterPath()
        camino.addRoundedRect(QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5), 13, 13)
        pintor.fillPath(camino, QColor(theme.panel_bg()))
        pintor.setPen(QColor(theme.panel_border()))
        pintor.drawPath(camino)
        pintor.end()

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
        self._arrastre = None
