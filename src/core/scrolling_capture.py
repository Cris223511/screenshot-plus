"""unión de fotogramas para la captura con desplazamiento.

mientras el usuario hace scroll se toman capturas de la misma zona y cada
una se pega debajo de la anterior. lo delicado es medir cuánto se
desplazó el contenido entre un fotograma y el siguiente, y hacerlo con
tolerancia: el suavizado de fuentes, un cursor parpadeando o un video de
fondo cambian píxeles sueltos aunque el texto sea el mismo, así que
comparar bytes exactos fallaba a la primera.

la medición trabaja sobre una huella barata de cada fila: la franja
central del fotograma se reduce a una tira gris de 32 columnas (pillow lo
hace en c, muy rápido) y cada fila queda descrita por esos 32 valores. la
franja final del fotograma anterior se busca dentro del nuevo comparando
huellas con distancia absoluta; el mejor calce con poca diferencia dice
cuántas filas nuevas trae el scroll. si ningún calce es confiable, el
fotograma se descarta en lugar de ensuciar el resultado con duplicados.
"""

from PIL import Image
from PySide6.QtGui import QImage, QPainter


def _huellas(imagen: QImage) -> list[bytes]:
    """una huella de 32 bytes por cada fila del fotograma.

    solo se mira la franja central (60 por ciento del ancho) para esquivar
    barras de scroll y bordes de ventana, que cambian sin que el contenido
    se haya movido.
    """
    convertida = imagen.convertToFormat(QImage.Format_ARGB32)
    ancho, alto = convertida.width(), convertida.height()
    crudo = bytes(convertida.constBits())
    pil = Image.frombuffer("RGBA", (ancho, alto), crudo, "raw", "BGRA",
                           convertida.bytesPerLine(), 1)
    franja = pil.crop((int(ancho * 0.2), 0, int(ancho * 0.8), alto)).convert("L")
    tira = franja.resize((32, alto), Image.BILINEAR).tobytes()
    return [tira[i * 32:(i + 1) * 32] for i in range(alto)]


def _distancia(a: bytes, b: bytes) -> int:
    return sum(abs(x - y) for x, y in zip(a, b))


class ScrollStitcher:
    """acumulador que va cosiendo fotogramas verticalmente."""

    # filas de la franja de búsqueda y umbral de diferencia media por byte
    # a partir del cual un calce deja de ser confiable
    _BANDA = 40
    _UMBRAL = 8.0

    def __init__(self):
        self._resultado: QImage | None = None
        self._huellas_ultimo: list[bytes] | None = None

    @property
    def image(self) -> QImage | None:
        return self._resultado

    @property
    def height(self) -> int:
        return self._resultado.height() if self._resultado else 0

    def add_frame(self, frame: QImage) -> bool:
        """incorpora un fotograma nuevo; True cuando aportó filas.

        un fotograma sin desplazamiento medible (la página no se movió) o
        sin calce confiable (cambió demasiado, por ejemplo apareció un
        menú encima) se descarta sin tocar el resultado.
        """
        if frame.isNull():
            return False
        frame = frame.convertToFormat(QImage.Format_ARGB32)
        huellas = _huellas(frame)

        if self._resultado is None:
            self._resultado = frame.copy()
            self._huellas_ultimo = huellas
            return True

        desplazamiento = self._medir(self._huellas_ultimo, huellas)
        if desplazamiento is None or desplazamiento <= 0:
            return False

        nuevo = frame.copy(0, frame.height() - desplazamiento, frame.width(), desplazamiento)
        combinado = QImage(self._resultado.width(), self._resultado.height() + nuevo.height(),
                           QImage.Format_ARGB32)
        pintor = QPainter(combinado)
        pintor.drawImage(0, 0, self._resultado)
        pintor.drawImage(0, self._resultado.height(), nuevo)
        pintor.end()

        self._resultado = combinado
        self._huellas_ultimo = huellas
        return True

    def _medir(self, anteriores: list[bytes], nuevas: list[bytes]) -> int | None:
        """cuántas filas subió el contenido entre fotogramas.

        la franja final del fotograma anterior se busca dentro del nuevo.
        el barrido va desde el desplazamiento más chico hacia el más
        grande: en zonas lisas hay empates, y quedarse con el menor evita
        duplicar contenido. cada calce se evalúa muestreando una de cada
        cuatro filas de la franja, suficiente y cuatro veces más barato.
        """
        alto = len(anteriores)
        if alto < self._BANDA * 2 or len(nuevas) != alto:
            return None

        base = alto - self._BANDA
        franja = anteriores[base:]
        muestras = range(0, self._BANDA, 4)
        limite = self._UMBRAL * 32 * len(muestras)

        mejor_y = None
        mejor_dist = None
        for y in range(alto - self._BANDA, -1, -1):
            dist = 0
            for i in muestras:
                dist += _distancia(franja[i], nuevas[y + i])
                if mejor_dist is not None and dist >= mejor_dist:
                    break
            if (mejor_dist is None or dist < mejor_dist) and dist <= limite:
                mejor_dist = dist
                mejor_y = y

        if mejor_y is None:
            return None
        return base - mejor_y
