"""botón de barra con la animación de hover que usa toda la app.

en lugar de un cambio de color seco al pasar el mouse, el fondo aparece con
un fundido corto; es un detalle chico pero es lo que hace que la interfaz
se sienta viva. el fondo se pinta a mano y encima se deja que el botón
dibuje su ícono y texto como siempre.
"""

from PySide6.QtCore import Property, QEasingCurve, QPropertyAnimation, QRectF
from PySide6.QtGui import QColor, QPainter, QPainterPath
from PySide6.QtWidgets import QToolButton


class AnimatedButton(QToolButton):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._alpha = 0.0
        self._color_fondo = QColor("#2f7df6")
        self._animacion = QPropertyAnimation(self, b"hoverAlpha", self)
        self._animacion.setDuration(140)
        self._animacion.setEasingCurve(QEasingCurve.OutCubic)
        self.setCursor(self.cursor())

    def set_hover_color(self, color: str):
        self._color_fondo = QColor(color)

    def _get_alpha(self) -> float:
        return self._alpha

    def _set_alpha(self, valor: float):
        self._alpha = valor
        self.update()

    # propiedad qt sobre la que corre la animación de entrada y salida
    hoverAlpha = Property(float, _get_alpha, _set_alpha)

    def _animar(self, destino: float):
        self._animacion.stop()
        self._animacion.setStartValue(self._alpha)
        self._animacion.setEndValue(destino)
        self._animacion.start()

    def enterEvent(self, evento):
        # los botones marcados como activos (checked) ya tienen fondo fijo,
        # el hover solo aplica sobre los demás
        self._animar(1.0)
        super().enterEvent(evento)

    def leaveEvent(self, evento):
        self._animar(0.0)
        super().leaveEvent(evento)

    def paintEvent(self, evento):
        if self._alpha > 0.01 and self.isEnabled():
            pintor = QPainter(self)
            pintor.setRenderHint(QPainter.Antialiasing)
            fondo = QColor(self._color_fondo)
            fondo.setAlphaF(0.14 * self._alpha)
            camino = QPainterPath()
            camino.addRoundedRect(QRectF(self.rect()).adjusted(1, 1, -1, -1), 7, 7)
            pintor.fillPath(camino, fondo)
            pintor.end()
        super().paintEvent(evento)
