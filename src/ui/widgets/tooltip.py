"""tooltip propio de la app: burbuja redondeada con fundido suave.

los tooltips nativos de windows son rectángulos secos, tardan en salir y
qt no permite redondearlos de verdad. esta burbuja es una ventanita
translúcida pintada a mano que aparece con una animación corta, y un
filtro global instalado en la aplicación la muestra para cualquier widget
que tenga tooltip, apenas el mouse entra, sin espera. así todos los
tooltips de la app se ven iguales.
"""

from PySide6.QtCore import (QEasingCurve, QEvent, QObject, QPoint,
                            QPropertyAnimation, QRectF, Qt, QTimer)
from PySide6.QtGui import (QColor, QCursor, QFont, QFontMetrics, QPainter,
                           QPainterPath)
from PySide6.QtWidgets import QWidget

from src.ui.themes.theme_manager import theme


class _Bubble(QWidget):
    def __init__(self):
        super().__init__(None, Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.ToolTip)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self._texto = ""
        self._fuente = QFont("Segoe UI", 9)
        self._auto = QTimer(self)
        self._auto.setSingleShot(True)
        self._auto.timeout.connect(self.hide)

    def mostrar(self, texto: str, ancla: QWidget):
        self._texto = texto
        medidas = QFontMetrics(self._fuente).boundingRect(
            0, 0, 360, 200, Qt.TextWordWrap, texto)
        self.resize(medidas.width() + 22, medidas.height() + 14)

        # la burbuja vive arriba del control, centrada respecto a él; si el
        # control está pegado al borde superior, baja al otro lado
        esquina = ancla.mapToGlobal(QPoint(0, 0))
        x = esquina.x() + (ancla.width() - self.width()) // 2
        y = esquina.y() - self.height() - 8
        pantalla = ancla.screen().availableGeometry() if ancla.screen() else None
        if pantalla:
            if y < pantalla.top() + 4:
                y = esquina.y() + ancla.height() + 8
            x = max(pantalla.left() + 4, min(x, pantalla.right() - self.width() - 4))
        self.move(x, y)

        self.setWindowOpacity(0.0)
        self.show()
        self._entrada = QPropertyAnimation(self, b"windowOpacity", self)
        self._entrada.setDuration(160)
        self._entrada.setStartValue(0.0)
        self._entrada.setEndValue(1.0)
        self._entrada.setEasingCurve(QEasingCurve.OutCubic)
        self._entrada.start()
        self._auto.start(4500)
        self.update()

    def paintEvent(self, _):
        pintor = QPainter(self)
        pintor.setRenderHint(QPainter.Antialiasing)
        camino = QPainterPath()
        camino.addRoundedRect(QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5), 8, 8)
        fondo = QColor("#2b3140") if theme.theme == "light" else QColor("#d6d9e0")
        letra = QColor("#ffffff") if theme.theme == "light" else QColor("#1b202b")
        pintor.fillPath(camino, fondo)
        pintor.setPen(letra)
        pintor.setFont(self._fuente)
        pintor.drawText(self.rect().adjusted(11, 7, -11, -7),
                        Qt.TextWordWrap | Qt.AlignLeft | Qt.AlignVCenter, self._texto)
        pintor.end()


# una sola burbuja compartida por toda la app; se reubica en cada uso
_burbuja: _Bubble | None = None


def show_tip(texto: str, ancla: QWidget):
    global _burbuja
    if _burbuja is None:
        _burbuja = _Bubble()
    _burbuja.mostrar(texto, ancla)


def hide_tip():
    if _burbuja is not None:
        _burbuja.hide()


class _FiltroGlobal(QObject):
    """intercepta el paso del mouse por cualquier widget con tooltip.

    al entrar, la burbuja sale de inmediato; al salir, al hacer clic o al
    esconderse el widget, se va. el evento de tooltip nativo se consume
    para que el rectángulo clásico de windows no aparezca nunca.
    """

    def eventFilter(self, objeto, evento):
        if not isinstance(objeto, QWidget):
            return False
        tipo = evento.type()
        if tipo == QEvent.ToolTip:
            return bool(objeto.toolTip())
        if tipo in (QEvent.Enter, QEvent.HoverEnter):
            if objeto.toolTip():
                show_tip(objeto.toolTip(), objeto)
        elif tipo in (QEvent.Leave, QEvent.HoverLeave, QEvent.Hide,
                      QEvent.MouseButtonPress):
            if objeto.toolTip():
                hide_tip()
        return False


_filtro: _FiltroGlobal | None = None


def install(aplicacion):
    """activa la burbuja para toda la app; se llama una vez al arrancar."""
    global _filtro
    _filtro = _FiltroGlobal()
    aplicacion.installEventFilter(_filtro)
