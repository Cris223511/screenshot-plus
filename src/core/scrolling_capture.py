"""unión de fotogramas para la captura con desplazamiento.

cada giro de scroll captura la misma zona y hay que medir cuánto avanzó el
contenido para pegar solo lo nuevo. la medición trabaja sobre una huella
barata de cada fila (una tira gris de 32 columnas) y busca dónde calza una
franja de referencia del fotograma anterior dentro del nuevo, con tolerancia
al suavizado de fuentes o al parpadeo del cursor. según hacia dónde calce, lo
nuevo se pega abajo (se bajó en la página) o arriba (se subió). un fotograma
sin desplazamiento medible, casi uniforme o sin calce confiable se descarta
antes que ensuciar el resultado con duplicados.
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

    # alto de la franja de referencia y umbral de diferencia media por byte a
    # partir del cual un calce deja de ser confiable
    _BANDA = 48
    _UMBRAL = 12.0

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

        se descarta el que no se movió, el casi uniforme (una zona en blanco o
        el velo de la ventana) o el que cambió demasiado para calzar con
        confianza (por ejemplo apareció un menú encima).
        """
        if frame.isNull():
            return False
        frame = frame.convertToFormat(QImage.Format_ARGB32)
        huellas = _huellas(frame)
        if self._casi_uniforme(huellas):
            return False

        if self._resultado is None:
            self._resultado = frame.copy()
            self._huellas_ultimo = huellas
            return True

        desplazamiento = self._medir(self._huellas_ultimo, huellas)
        if desplazamiento is None or desplazamiento == 0:
            return False

        if desplazamiento > 0:
            # el contenido subió en pantalla (se scrolleó hacia abajo): lo
            # nuevo asoma abajo y se pega debajo de lo acumulado
            alto = min(desplazamiento, frame.height())
            nuevo = frame.copy(0, frame.height() - alto, frame.width(), alto)
            combinado = QImage(self._resultado.width(),
                               self._resultado.height() + nuevo.height(), QImage.Format_ARGB32)
            pintor = QPainter(combinado)
            pintor.drawImage(0, 0, self._resultado)
            pintor.drawImage(0, self._resultado.height(), nuevo)
            pintor.end()
        else:
            # bajó en pantalla (se scrolleó hacia arriba): lo nuevo asoma
            # arriba y se pega encima de lo acumulado
            alto = min(-desplazamiento, frame.height())
            nuevo = frame.copy(0, 0, frame.width(), alto)
            combinado = QImage(self._resultado.width(),
                               self._resultado.height() + nuevo.height(), QImage.Format_ARGB32)
            pintor = QPainter(combinado)
            pintor.drawImage(0, 0, nuevo)
            pintor.drawImage(0, nuevo.height(), self._resultado)
            pintor.end()

        self._resultado = combinado
        self._huellas_ultimo = huellas
        return True

    @staticmethod
    def _casi_uniforme(huellas: list[bytes]) -> bool:
        """True si el fotograma es casi todo del mismo tono (una zona vacía o
        el velo), sin nada con qué calzar."""
        if len(huellas) < 4:
            return True
        referencia = huellas[len(huellas) // 2]
        paso = max(1, len(huellas) // 10)
        for i in range(0, len(huellas), paso):
            if _distancia(referencia, huellas[i]) > 3 * 32:
                return False
        return True

    def _medir(self, anteriores: list[bytes], nuevas: list[bytes]) -> int | None:
        """cuántas filas se movió el contenido entre fotogramas, con signo.

        se toma una franja de referencia del centro del fotograma anterior y
        se busca dónde calza dentro del nuevo. positivo significa que el
        contenido bajó (se scrolleó hacia arriba) y negativo que subió (hacia
        abajo). cada calce se evalúa muestreando una de cada cuatro filas de la
        franja, suficiente y cuatro veces más barato.
        """
        alto = len(anteriores)
        if alto < self._BANDA * 2 or len(nuevas) != alto:
            return None

        banda = self._BANDA
        y0 = (alto - banda) // 2
        referencia = anteriores[y0:y0 + banda]
        muestras = range(0, banda, 4)
        limite = self._UMBRAL * 32 * len(muestras)

        mejor_y = None
        mejor_dist = None
        for y in range(0, alto - banda + 1):
            dist = 0
            for i in muestras:
                dist += _distancia(referencia[i], nuevas[y + i])
                if mejor_dist is not None and dist >= mejor_dist:
                    break
            if (mejor_dist is None or dist < mejor_dist) and dist <= limite:
                mejor_dist = dist
                mejor_y = y

        if mejor_y is None:
            return None
        # >0: el contenido está más abajo en el nuevo (se subió en la página)
        return mejor_y - y0
