"""unión de fotogramas para la captura con desplazamiento.

cada giro de rueda captura la misma zona y hay que medir cuánto avanzó el
contenido para pegar solo lo nuevo. la medición trabaja sobre una huella
barata de cada fila (una tira gris de 32 columnas) y busca dónde calza una
franja de referencia del fotograma anterior dentro del nuevo, con tolerancia
al suavizado de fuentes o al parpadeo del cursor.

el signo del desplazamiento dice hacia dónde se movió el contenido. al
scrollear hacia abajo la página sube en pantalla, la franja de referencia
aparece más arriba en el fotograma nuevo y lo que asoma nuevo está abajo, así
que se pega debajo. al scrollear hacia arriba pasa lo contrario y se pega
encima. un fotograma sin desplazamiento medible, casi uniforme, con un salto
demasiado grande (poco solape para fiarse) o con un calce ambiguo se descarta
antes que ensuciar el resultado con duplicados.
"""

from PIL import Image
from PySide6.QtGui import QImage, QPainter

# ancho de la huella de cada fila, en columnas
_ANCHO_HUELLA = 32


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
    tira = franja.resize((_ANCHO_HUELLA, alto), Image.BILINEAR).tobytes()
    return [tira[i * _ANCHO_HUELLA:(i + 1) * _ANCHO_HUELLA] for i in range(alto)]


def _distancia(a: bytes, b: bytes) -> int:
    return sum(abs(x - y) for x, y in zip(a, b))


class ScrollStitcher:
    """acumulador que va cosiendo fotogramas verticalmente."""

    # alto de la franja de referencia y umbral de diferencia media por byte a
    # partir del cual un calce deja de ser confiable
    _BANDA = 48
    _UMBRAL = 12.0
    # un paso más chico que esto es ruido (la pantalla no se movió de verdad);
    # uno mayor que esta fracción del alto significa que casi no quedó solape
    # con el fotograma anterior y el calce no es de fiar
    _PASO_MINIMO = 3
    _FRACCION_MAXIMA = 0.6
    # tope duro de altura para que un caso raro no dispare la imagen a un
    # tamaño imposible; a partir de aquí se dejan de aceptar fotogramas
    _ALTO_MAXIMO = 20000

    def __init__(self):
        self._resultado: QImage | None = None
        self._huellas_ultimo: list[bytes] | None = None
        self._ultimo_lado: str | None = None  # "abajo" o "arriba"

    @property
    def image(self) -> QImage | None:
        return self._resultado

    @property
    def height(self) -> int:
        return self._resultado.height() if self._resultado else 0

    @property
    def last_side(self) -> str | None:
        """lado por el que creció la última vez, para orientar la vista previa."""
        return self._ultimo_lado

    def add_frame(self, frame: QImage) -> bool:
        """incorpora un fotograma nuevo; True cuando aportó filas.

        se descarta el que no se movió, el casi uniforme (una zona en blanco o
        el velo), el que saltó tanto que quedó sin solape confiable y el que
        cambió demasiado para calzar con seguridad.
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
        if desplazamiento is None:
            return False

        paso = abs(desplazamiento)
        if paso < self._PASO_MINIMO:
            return False
        if paso > frame.height() * self._FRACCION_MAXIMA:
            return False
        if self._resultado.height() + paso > self._ALTO_MAXIMO:
            return False

        if desplazamiento < 0:
            # se scrolleó hacia abajo: lo nuevo asoma por abajo y se pega
            # debajo de lo ya acumulado
            nuevo = frame.copy(0, frame.height() - paso, frame.width(), paso)
            combinado = QImage(self._resultado.width(),
                               self._resultado.height() + paso, QImage.Format_ARGB32)
            pintor = QPainter(combinado)
            pintor.drawImage(0, 0, self._resultado)
            pintor.drawImage(0, self._resultado.height(), nuevo)
            pintor.end()
            self._ultimo_lado = "abajo"
        else:
            # se scrolleó hacia arriba: lo nuevo asoma por arriba y se pega
            # encima
            nuevo = frame.copy(0, 0, frame.width(), paso)
            combinado = QImage(self._resultado.width(),
                               self._resultado.height() + paso, QImage.Format_ARGB32)
            pintor = QPainter(combinado)
            pintor.drawImage(0, 0, nuevo)
            pintor.drawImage(0, paso, self._resultado)
            pintor.end()
            self._ultimo_lado = "arriba"

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
            if _distancia(referencia, huellas[i]) > 3 * _ANCHO_HUELLA:
                return False
        return True

    def _medir(self, anteriores: list[bytes], nuevas: list[bytes]) -> int | None:
        """cuántas filas se movió el contenido entre fotogramas, con signo.

        se toma una franja de referencia del centro del fotograma anterior y
        se busca dónde calza dentro del nuevo. negativo significa que el
        contenido subió (se scrolleó hacia abajo) y positivo que bajó (hacia
        arriba). se muestrea una de cada cuatro filas de la franja, suficiente
        y cuatro veces más barato. el calce solo se acepta si su diferencia
        queda bajo el umbral y además destaca con claridad frente a cualquier
        otro calce lejano, para no confundirse con contenido repetitivo.
        """
        alto = len(anteriores)
        if alto < self._BANDA * 2 or len(nuevas) != alto:
            return None

        banda = self._BANDA
        y0 = (alto - banda) // 2
        referencia = anteriores[y0:y0 + banda]
        muestras = list(range(0, banda, 4))
        limite = self._UMBRAL * _ANCHO_HUELLA * len(muestras)

        # primer barrido: el mejor calce, con corte temprano cuando la suma
        # parcial ya supera al mejor encontrado (esquiva la mayoría del cálculo)
        mejor = None
        mejor_y = None
        for y in range(0, alto - banda + 1):
            suma = 0
            for i in muestras:
                suma += _distancia(referencia[i], nuevas[y + i])
                if mejor is not None and suma >= mejor:
                    break
            if mejor is None or suma < mejor:
                mejor = suma
                mejor_y = y
        if mejor is None or mejor > limite:
            return None

        # segundo barrido: el mejor calce debe destacar frente a cualquier otro
        # lejano; si uno alejado empata casi igual, el contenido es repetitivo y
        # no se puede fiar cuánto se movió. el corte se para en cuanto la suma
        # pasa el tope, así los no-calces se descartan rápido
        tope = mejor * 1.4
        for y in range(0, alto - banda + 1):
            if abs(y - mejor_y) <= banda:
                continue
            suma = 0
            for i in muestras:
                suma += _distancia(referencia[i], nuevas[y + i])
                if suma >= tope:
                    break
            else:
                # el bucle terminó sin cortar: hay un calce lejano casi igual
                return None

        return mejor_y - y0
