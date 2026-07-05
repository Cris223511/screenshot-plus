"""panel principal: la barrita compacta desde donde se dispara todo.

una ventana sin marco con fondo sólido y esquinas redondeadas, pintados a
mano para que se vean igual en cualquier windows. de izquierda a derecha:
el logo con sus bordes suavizados, el botón grande de capturar, los
accesos a pantalla completa, ventana actual, captura con desplazamiento y
panel de presentación, luego ajustes, el menú, el pin de siempre adelante,
minimizar y cerrar (que en realidad manda la app a la bandeja).

se arrastra desde cualquier zona libre, entra con un fundido suave, y si
el usuario cambia de idioma o de tema se repinta en caliente, sin
reiniciar nada.
"""

import os
import webbrowser

from PySide6.QtCore import (QEasingCurve, QPoint, QPropertyAnimation, QRectF,
                            QSize, Qt, Signal)
from PySide6.QtGui import QColor, QIcon, QPainter, QPainterPath, QPixmap
from PySide6.QtWidgets import (QFrame, QHBoxLayout, QLabel, QMenu,
                               QPushButton, QWidget)

from src import APP_NAME, APP_REPO
from src.config import paths, shortcuts
from src.i18n.translator import t, translator
from src.ui.themes.theme_manager import theme
from src.ui.widgets.animated_button import AnimatedButton
from src.ui.widgets.icons import icon


def _logo_redondeado(lado: int) -> QPixmap:
    """el logo recortado en un cuadrado de esquinas redondeadas.

    la imagen original es cuadrada con fondo blanco; el recorte con máscara
    la integra al panel sin ese marco duro que se veía antes.
    """
    original = QPixmap(paths.resource_path(os.path.join("assets", "logo", "logo.jpg")))
    escalado = original.scaled(lado * 2, lado * 2, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
    salida = QPixmap(lado * 2, lado * 2)
    salida.fill(Qt.transparent)
    pintor = QPainter(salida)
    pintor.setRenderHint(QPainter.Antialiasing)
    mascara = QPainterPath()
    mascara.addRoundedRect(QRectF(0, 0, lado * 2, lado * 2), lado * 0.55, lado * 0.55)
    pintor.setClipPath(mascara)
    pintor.drawPixmap(0, 0, escalado)
    pintor.end()
    salida.setDevicePixelRatio(2.0)
    return salida


class MainWindow(QWidget):
    capture_region = Signal()
    capture_fullscreen = Signal()
    capture_window = Signal()
    capture_scroll = Signal()
    zoom_mode = Signal()
    options_requested = Signal()
    manual_requested = Signal()
    language_requested = Signal()
    updates_requested = Signal()
    about_requested = Signal()
    quit_requested = Signal()

    def __init__(self):
        super().__init__(None, Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setWindowTitle(APP_NAME)
        self.setWindowIcon(QIcon(paths.resource_path(os.path.join("assets", "logo", "logo.jpg"))))
        self._arrastre: QPoint | None = None
        self._primera_vez = True

        fila = QHBoxLayout(self)
        fila.setContentsMargins(12, 9, 10, 9)
        fila.setSpacing(4)

        # el logo con la misma altura que el botón de al lado, ya sin puntas
        logo = QLabel()
        logo.setPixmap(_logo_redondeado(34))
        fila.addWidget(logo)
        fila.addSpacing(6)

        self._capturar = QPushButton()
        self._capturar.setObjectName("primario")
        self._capturar.setIconSize(QSize(18, 18))
        self._capturar.setCursor(Qt.PointingHandCursor)
        self._capturar.setMinimumHeight(34)
        self._capturar.clicked.connect(self.capture_region)
        fila.addWidget(self._capturar)
        fila.addSpacing(4)

        fila.addWidget(self._separador())

        def boton(senal) -> AnimatedButton:
            b = AnimatedButton()
            b.setIconSize(QSize(20, 20))
            b.setCursor(Qt.PointingHandCursor)
            b.clicked.connect(senal)
            fila.addWidget(b)
            return b

        self._pantalla = boton(self.capture_fullscreen)
        self._ventana = boton(self.capture_window)
        self._scroll = boton(self.capture_scroll)
        self._panel_pres = boton(self.zoom_mode)

        fila.addWidget(self._separador())

        # ajustes a la vista, sin esconderlo en el menú
        self._ajustes = boton(self.options_requested)

        self._menu_boton = AnimatedButton()
        self._menu_boton.setIconSize(QSize(20, 20))
        self._menu_boton.setCursor(Qt.PointingHandCursor)
        self._menu_boton.setPopupMode(AnimatedButton.InstantPopup)
        fila.addWidget(self._menu_boton)

        # el pin controla si el panel se queda por encima de las demás
        # ventanas; arranca activado, que es lo cómodo para capturar
        self._pin = AnimatedButton()
        self._pin.setIconSize(QSize(20, 20))
        self._pin.setCursor(Qt.PointingHandCursor)
        self._pin.setCheckable(True)
        self._pin.setChecked(True)
        self._pin.toggled.connect(self._alternar_pin)
        fila.addWidget(self._pin)

        self._minimizar = boton(self.showMinimized)
        self._cerrar = boton(self.hide)

        self._armar_menu()
        self._aplicar_iconos()
        self._aplicar_textos()

        translator.language_changed.connect(lambda _: self._retraducir())
        theme.theme_changed.connect(lambda _: self._refrescar_tema())

    @staticmethod
    def _separador() -> QFrame:
        linea = QFrame()
        linea.setFrameShape(QFrame.VLine)
        linea.setStyleSheet("color: rgba(128,128,128,60);")
        return linea

    # ------------------------------------------------------------------ #

    def _armar_menu(self):
        menu = QMenu(self)
        color = theme.icon_color()
        menu.addAction(icon("settings", color), t("menu.options"), self.options_requested.emit)
        menu.addAction(icon("book", color), t("menu.manual"), self.manual_requested.emit)
        menu.addAction(icon("globe", color), t("menu.language"), self.language_requested.emit)
        menu.addSeparator()
        menu.addAction(icon("refresh", color), t("menu.updates"), self.updates_requested.emit)
        menu.addAction(icon("github", color), t("menu.repo"), lambda: webbrowser.open(APP_REPO))
        menu.addAction(icon("info", color), t("menu.about"), self.about_requested.emit)
        menu.addSeparator()
        menu.addAction(icon("close", color), t("menu.quit"), self.quit_requested.emit)
        self._menu_boton.setMenu(menu)

    def _aplicar_iconos(self):
        color = theme.icon_color()
        self._capturar.setIcon(icon("camera", "#ffffff"))
        self._pantalla.setIcon(icon("fullscreen", color))
        self._ventana.setIcon(icon("window", color))
        self._scroll.setIcon(icon("scroll", color))
        self._panel_pres.setIcon(icon("panel", color))
        self._ajustes.setIcon(icon("settings", color))
        self._menu_boton.setIcon(icon("menu", color))
        self._pin.setIcon(icon("pin", theme.icon_active_color() if self._pin.isChecked() else color))
        self._minimizar.setIcon(icon("minimize", color))
        self._cerrar.setIcon(icon("close", color))
        self._armar_menu()

    def _aplicar_textos(self):
        self._capturar.setText(t("main.capture"))
        atajo = lambda accion: shortcuts.display(shortcuts.get(accion))
        self._capturar.setToolTip(f'{t("main.tip_region")}  ({atajo("capture_region")})')
        self._pantalla.setToolTip(f'{t("main.tip_fullscreen")}  ({atajo("capture_fullscreen")})')
        self._ventana.setToolTip(f'{t("main.tip_window")}  ({atajo("capture_window")})')
        self._scroll.setToolTip(f'{t("main.tip_scroll")}  ({atajo("capture_scroll")})')
        self._panel_pres.setToolTip(f'{t("main.tip_panel")}  ({atajo("zoom_mode")})')
        self._ajustes.setToolTip(t("menu.options"))
        self._menu_boton.setToolTip(t("main.tip_menu"))
        self._pin.setToolTip(t("main.tip_pin"))
        self._minimizar.setToolTip(t("main.tip_minimize"))
        self._cerrar.setToolTip(t("main.tip_close"))

    def _retraducir(self):
        self._aplicar_textos()
        self._armar_menu()
        self.adjustSize()

    def _refrescar_tema(self):
        self._aplicar_iconos()
        self.update()

    def refresh_tooltips(self):
        """tras cambiar atajos en opciones, los tooltips muestran los nuevos."""
        self._aplicar_textos()

    def _alternar_pin(self, fijado: bool):
        """siempre adelante o comportamiento normal, a elección.

        qt recrea la ventana al cambiar la bandera, de ahí el show()
        inmediato para que el panel no desaparezca en el cambio.
        """
        self.setWindowFlag(Qt.WindowStaysOnTopHint, fijado)
        self.show()
        self._aplicar_iconos()

    # ------------------------------------------------------------------ #
    # fondo y animación de entrada

    def paintEvent(self, _):
        """fondo sólido con esquinas redondeadas y borde fino.

        pintado a mano en lugar de confiar en hojas de estilo: con la
        ventana translúcida es la única forma segura de que el panel nunca
        aparezca transparente.
        """
        pintor = QPainter(self)
        pintor.setRenderHint(QPainter.Antialiasing)
        camino = QPainterPath()
        camino.addRoundedRect(QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5), 13, 13)
        pintor.fillPath(camino, QColor(theme.panel_bg()))
        pintor.setPen(QColor(theme.panel_border()))
        pintor.drawPath(camino)
        pintor.end()

    def showEvent(self, e):
        super().showEvent(e)
        if self._primera_vez:
            self._primera_vez = False
            self.setWindowOpacity(0.0)
            self._entrada = QPropertyAnimation(self, b"windowOpacity", self)
            self._entrada.setDuration(260)
            self._entrada.setStartValue(0.0)
            self._entrada.setEndValue(1.0)
            self._entrada.setEasingCurve(QEasingCurve.OutCubic)
            self._entrada.start()
        else:
            self.setWindowOpacity(1.0)

    # ------------------------------------------------------------------ #
    # arrastre del panel por cualquier zona libre

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._arrastre = e.position().toPoint()

    def mouseMoveEvent(self, e):
        if self._arrastre is not None:
            self.move(e.globalPosition().toPoint() - self._arrastre)

    def mouseReleaseEvent(self, _):
        self._arrastre = None
