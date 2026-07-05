"""selector de idioma con su bandera y su país.

las banderas no son emojis ni imágenes descargadas: se pintan acá mismo
como franjas de color redondeadas, lo que les da un aspecto propio y
uniforme en cualquier tamaño. al elegir un idioma, el cambio se aplica al
instante en toda la interfaz gracias a la señal del traductor.
"""

from PySide6.QtCore import QRectF, QSize, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPainterPath, QPixmap
from PySide6.QtWidgets import QDialog, QLabel, QListWidget, QListWidgetItem, QVBoxLayout

from src.i18n.translator import LANGUAGES, t, translator

# franjas de cada bandera: orientación y lista de (color, proporción)
_BANDERAS = {
    "es": ("h", [("#c60b1e", 1), ("#ffc400", 2), ("#c60b1e", 1)]),
    "en": ("uk", []),
    "pt": ("v", [("#046a38", 2), ("#da291c", 3)]),
    "fr": ("v", [("#0055a4", 1), ("#ffffff", 1), ("#ef4135", 1)]),
    "de": ("h", [("#000000", 1), ("#dd0000", 1), ("#ffce00", 1)]),
    "it": ("v", [("#009246", 1), ("#ffffff", 1), ("#ce2b37", 1)]),
}


def _bandera(codigo: str, ancho: int = 30, alto: int = 20) -> QIcon:
    """banderita pintada a mano, con esquinas redondeadas y borde sutil."""
    pixmap = QPixmap(ancho * 2, alto * 2)
    pixmap.fill(Qt.transparent)
    pintor = QPainter(pixmap)
    pintor.setRenderHint(QPainter.Antialiasing)

    camino = QPainterPath()
    camino.addRoundedRect(QRectF(0, 0, ancho * 2, alto * 2), 6, 6)
    pintor.setClipPath(camino)

    orientacion, franjas = _BANDERAS.get(codigo, ("h", [("#888888", 1)]))
    if orientacion == "uk":
        # versión simplificada de la union jack: fondo azul y las cruces
        # blanca y roja, suficiente para reconocerla en tamaño chico
        pintor.fillRect(0, 0, ancho * 2, alto * 2, QColor("#012169"))
        pintor.setPen(Qt.NoPen)
        pintor.setBrush(QColor("#ffffff"))
        pintor.drawRect(0, alto - 7, ancho * 2, 14)
        pintor.drawRect(ancho - 7, 0, 14, alto * 2)
        pintor.setBrush(QColor("#c8102e"))
        pintor.drawRect(0, alto - 4, ancho * 2, 8)
        pintor.drawRect(ancho - 4, 0, 8, alto * 2)
    else:
        total = sum(peso for _, peso in franjas)
        avance = 0.0
        for color, peso in franjas:
            tramo = (ancho * 2 if orientacion == "v" else alto * 2) * peso / total
            if orientacion == "v":
                pintor.fillRect(QRectF(avance, 0, tramo, alto * 2), QColor(color))
            else:
                pintor.fillRect(QRectF(0, avance, ancho * 2, tramo), QColor(color))
            avance += tramo

    pintor.setClipping(False)
    pintor.setPen(QColor(0, 0, 0, 40))
    pintor.setBrush(Qt.NoBrush)
    pintor.drawRoundedRect(QRectF(1, 1, ancho * 2 - 2, alto * 2 - 2), 6, 6)
    pintor.end()

    pixmap.setDevicePixelRatio(2.0)
    return QIcon(pixmap)


class LanguageDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(t("lang.title"))
        self.setFixedWidth(320)

        columna = QVBoxLayout(self)
        columna.setContentsMargins(18, 16, 18, 16)
        columna.setSpacing(10)

        pista = QLabel(t("lang.hint"))
        pista.setObjectName("secundario")
        pista.setWordWrap(True)
        columna.addWidget(pista)

        self._lista = QListWidget()
        self._lista.setIconSize(QSize(30, 20))
        for codigo, (nombre, pais) in LANGUAGES.items():
            item = QListWidgetItem(_bandera(codigo), f"{nombre}  ·  {pais}")
            item.setData(Qt.UserRole, codigo)
            self._lista.addItem(item)
            if codigo == translator.language:
                item.setSelected(True)
                self._lista.setCurrentItem(item)
        columna.addWidget(self._lista)

        self._lista.itemClicked.connect(self._elegir)

    def _elegir(self, item: QListWidgetItem):
        translator.set_language(item.data(Qt.UserRole))
        self.accept()
