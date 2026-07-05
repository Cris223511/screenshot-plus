"""paleta de colores compacta para las herramientas de dibujo.

una fila de muestras redondas con los colores más usados al anotar, más un
último botón que abre el selector completo del sistema para cualquier otro.
el color activo se distingue por un anillo alrededor de la muestra.
"""

from PySide6.QtCore import QRectF, Signal, Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import (QColorDialog, QHBoxLayout, QPushButton,
                               QVBoxLayout, QWidget)

# colores pensados para resaltar sobre capturas: fuertes y distinguibles
_COLORES = ["#e5484d", "#ff8c00", "#f5d90a", "#30a46c", "#2f7df6", "#8e4ec6", "#111111", "#ffffff"]


class _Swatch(QPushButton):
    def __init__(self, color: str, parent=None):
        super().__init__(parent)
        self.color = QColor(color)
        self.activo = False
        self.setFixedSize(22, 22)
        self.setCursor(Qt.PointingHandCursor)

    def paintEvent(self, evento):
        pintor = QPainter(self)
        pintor.setRenderHint(QPainter.Antialiasing)
        r = QRectF(self.rect()).adjusted(4, 4, -4, -4)
        pintor.setPen(QPen(QColor(0, 0, 0, 50), 1))
        pintor.setBrush(self.color)
        pintor.drawEllipse(r)
        if self.activo or self.underMouse():
            anillo = QPen(QColor("#2f7df6"), 2)
            pintor.setPen(anillo)
            pintor.setBrush(Qt.NoBrush)
            pintor.drawEllipse(QRectF(self.rect()).adjusted(1.5, 1.5, -1.5, -1.5))
        pintor.end()


class ColorPalette(QWidget):
    color_selected = Signal(QColor)

    def __init__(self, parent=None, vertical: bool = False):
        super().__init__(parent)
        # en el panel lateral del modo presentación la paleta va en columna;
        # en las barras horizontales, en fila
        fila = QVBoxLayout(self) if vertical else QHBoxLayout(self)
        fila.setContentsMargins(2, 0, 2, 0)
        fila.setSpacing(2)

        self._muestras: list[_Swatch] = []
        for hexa in _COLORES:
            muestra = _Swatch(hexa)
            muestra.clicked.connect(lambda _=False, m=muestra: self._elegir(m.color, m))
            fila.addWidget(muestra)
            self._muestras.append(muestra)

        # la última muestra abre el selector del sistema; su circulito va
        # mostrando el color personalizado vigente
        self._personalizado = _Swatch("#999999")
        self._personalizado.setToolTip("+")
        self._personalizado.clicked.connect(self._abrir_selector)
        fila.addWidget(self._personalizado)

        # el rojo arranca activo porque es el color clásico para señalar
        self._muestras[0].activo = True

    def _elegir(self, color: QColor, muestra: _Swatch):
        for m in self._muestras + [self._personalizado]:
            m.activo = m is muestra
            m.update()
        self.color_selected.emit(color)

    def _abrir_selector(self):
        color = QColorDialog.getColor(self._personalizado.color, self)
        if color.isValid():
            self._personalizado.color = color
            self._elegir(color, self._personalizado)
