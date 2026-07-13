"""panel principal: la barra compacta desde donde se dispara todo.

una ventana sin marco, con fondo sólido y esquinas redondeadas, que reúne
el logo, el botón de capturar, los accesos a los modos de captura y de
presentación, ajustes, menú, pin y los botones de ventana. se arrastra
desde cualquier zona libre y se repinta en caliente al cambiar tema o
idioma.
"""

import os
import webbrowser

from PySide6.QtCore import (QEasingCurve, QEvent, QPoint, QPropertyAnimation,
                            QRectF, QSize, Qt, Signal)
from PySide6.QtGui import QColor, QGuiApplication, QIcon, QPainter, QPainterPath, QPixmap
from PySide6.QtWidgets import (QFrame, QHBoxLayout, QLabel, QMenu,
                               QPushButton, QWidget)

from src import APP_NAME, APP_REPO
from src.config import paths, shortcuts
from src.config.settings import settings
from src.i18n.translator import t, translator
from src.ui.themes.theme_manager import theme
from src.ui.widgets.animated_button import AnimatedButton
from src.ui.widgets.icons import icon


from src.ui.widgets.icons import rounded_logo as _logo_redondeado


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
    # avisa cuando el panel pasa a minimizado o vuelve, para que la app
    # coordine el panel lateral de presentación
    minimized_changed = Signal(bool)

    def __init__(self):
        # el estado del pin, guardado, decide si el panel nace siempre
        # adelante o no, en vez de forzarlo
        banderas = Qt.FramelessWindowHint
        if settings.get("panel_pinned", False):
            banderas |= Qt.WindowStaysOnTopHint
        super().__init__(None, banderas)
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

        # el cambio rápido entre tema claro y oscuro; los ajustes viven
        # dentro del menú, no vale la pena duplicar el botón
        self._tema = boton(self._alternar_tema)

        self._menu_boton = AnimatedButton()
        self._menu_boton.setIconSize(QSize(20, 20))
        self._menu_boton.setCursor(Qt.PointingHandCursor)
        self._menu_boton.setPopupMode(AnimatedButton.InstantPopup)
        fila.addWidget(self._menu_boton)

        # el pin controla si el panel se queda por encima de las demás
        # ventanas; arranca apagado y su estado se recuerda entre sesiones
        self._pin = AnimatedButton()
        self._pin.setIconSize(QSize(20, 20))
        self._pin.setCursor(Qt.PointingHandCursor)
        self._pin.setCheckable(True)
        self._pin.setChecked(settings.get("panel_pinned", False))
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
        # el botón de tema muestra a dónde vas a cambiar, no dónde estás:
        # luna en tema claro, sol en tema oscuro
        self._tema.setIcon(icon("moon" if theme.theme == "light" else "sun", color))
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
        self._tema.setToolTip(t("main.tip_theme"))
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

    def _alternar_tema(self):
        theme.set_theme("dark" if theme.theme == "light" else "light")

    def _alternar_pin(self, fijado: bool):
        """siempre adelante o comportamiento normal, a elección.

        qt recrea la ventana al cambiar la bandera, de ahí el show()
        inmediato para que el panel no desaparezca en el cambio. la
        elección se recuerda para la próxima sesión.
        """
        settings.set("panel_pinned", fijado)
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

    def hideEvent(self, e):
        # el lugar donde quedó el panel se guarda para reaparecer ahí
        # mismo, incluso en la próxima sesión
        settings.set("panel_pos", [self.x(), self.y()])
        super().hideEvent(e)

    def changeEvent(self, e):
        if e.type() == QEvent.WindowStateChange:
            self.minimized_changed.emit(bool(self.windowState() & Qt.WindowMinimized))
        super().changeEvent(e)

    def _restaurar_posicion(self):
        """vuelve a la última posición guardada, si sigue dentro de alguna
        pantalla; un monitor desconectado no debe dejar el panel perdido."""
        guardada = settings.get("panel_pos")
        if not guardada or len(guardada) != 2:
            return
        destino = QPoint(int(guardada[0]), int(guardada[1]))
        virtual = QGuiApplication.primaryScreen().virtualGeometry()
        if virtual.adjusted(0, 0, -60, -30).contains(destino):
            self.move(destino)

    def showEvent(self, e):
        super().showEvent(e)
        self._restaurar_posicion()
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
        if self._arrastre is not None:
            # al soltar tras arrastrar, la posición queda registrada para
            # recuperarla exactamente en la próxima sesión
            settings.set("panel_pos", [self.x(), self.y()])
        self._arrastre = None
