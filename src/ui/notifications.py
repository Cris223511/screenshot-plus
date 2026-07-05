"""notificaciones propias de la app, discretas y con animación.

son tarjetitas que aparecen abajo a la derecha con un deslizamiento suave,
confirman el copiado o el guardado y se van solas. se usan las propias en
lugar de las de windows para controlar el estilo y que respondan al tema.
"""

from PySide6.QtCore import (QEasingCurve, QPoint, QPropertyAnimation, QSize,
                            Qt, QTimer)
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QHBoxLayout, QLabel, QWidget

from src.config.settings import settings
from src.ui.themes.theme_manager import theme
from src.ui.widgets.icons import icon


class _Toast(QWidget):
    _DURACION = 2600

    def __init__(self, texto: str, nombre_icono: str):
        super().__init__(None, Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_DeleteOnClose, True)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self.setObjectName("barraFlotante")
        self.setAttribute(Qt.WA_StyledBackground, True)

        fila = QHBoxLayout(self)
        fila.setContentsMargins(14, 10, 16, 10)
        fila.setSpacing(10)

        simbolo = QLabel()
        simbolo.setPixmap(icon(nombre_icono, theme.accent()).pixmap(QSize(18, 18)))
        fila.addWidget(simbolo)

        mensaje = QLabel(texto)
        mensaje.setMaximumWidth(380)
        fila.addWidget(mensaje)

        self.adjustSize()

        # posición final abajo a la derecha; la entrada arranca unos
        # píxeles más abajo y sube con el fundido, esa es la animación
        pantalla = QGuiApplication.primaryScreen().availableGeometry()
        destino = QPoint(pantalla.right() - self.width() - 20, pantalla.bottom() - self.height() - 20)
        inicio = destino + QPoint(0, 24)
        self.move(inicio)
        self.setWindowOpacity(0.0)
        self.show()

        self._entrada_pos = QPropertyAnimation(self, b"pos", self)
        self._entrada_pos.setDuration(240)
        self._entrada_pos.setStartValue(inicio)
        self._entrada_pos.setEndValue(destino)
        self._entrada_pos.setEasingCurve(QEasingCurve.OutCubic)
        self._entrada_pos.start()

        self._entrada_op = QPropertyAnimation(self, b"windowOpacity", self)
        self._entrada_op.setDuration(240)
        self._entrada_op.setStartValue(0.0)
        self._entrada_op.setEndValue(1.0)
        self._entrada_op.start()

        QTimer.singleShot(self._DURACION, self._salir)

    def _salir(self):
        self._salida = QPropertyAnimation(self, b"windowOpacity", self)
        self._salida.setDuration(260)
        self._salida.setStartValue(1.0)
        self._salida.setEndValue(0.0)
        self._salida.finished.connect(self.close)
        self._salida.start()


def notify(texto: str, nombre_icono: str = "check"):
    """muestra el aviso, salvo que el usuario los tenga apagados en opciones."""
    if settings.get("show_notifications", True):
        _Toast(texto, nombre_icono)
