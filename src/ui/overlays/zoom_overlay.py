"""modo presentación con la pantalla en vivo, sin congelar nada.

tres ventanas cooperan: el panel lateral con las herramientas (siempre
visible, arrastrable, fijable), una capa transparente donde viven el láser
y los dibujos, y la vista de zoom, que es una ventana aparte. la pantalla
de verdad sigue corriendo detrás: los videos se reproducen, las ventanas
se mueven, todo normal.

la vista de zoom va separada por una razón técnica concreta: windows no
permite excluir de la captura a las ventanas translúcidas, y el zoom
necesita esa exclusión para fotografiar la pantalla muchas veces por
segundo sin verse a sí mismo en un espejo infinito. como la vista amplada
cubre todo de forma opaca, no pierde nada siendo una ventana común.

el puntero láser deja una estela que se desvanece sola, con el tamaño y el
color que el usuario haya elegido en opciones. pincel, resaltador, línea y
flecha dibujan encima de la pantalla y se borran con una tecla.
"""

import time

from PySide6.QtCore import QObject, QPointF, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QGuiApplication, QPainter, QRadialGradient
from PySide6.QtWidgets import QWidget

from src.config.settings import settings
from src.core import capture
from src.ui.overlays import annotation_tools as an
from src.ui.overlays.floating_toolbar import FloatingToolbar

# cadencia del zoom en vivo: 25 cuadros por segundo se sienten fluidos sin
# castigar el procesador
_REFRESCO_MS = 40

# vida de cada punto de la estela del láser, en segundos
_VIDA_ESTELA = 0.65

# teclas rápidas compartidas por las ventanas del modo
_ATAJOS_MODO = {Qt.Key_Z: "zoom", Qt.Key_L: "laser", Qt.Key_P: "brush",
                Qt.Key_R: "highlight", Qt.Key_I: "line", Qt.Key_F: "arrow"}


class _DrawOverlay(QWidget):
    """capa transparente para el láser y los dibujos sobre pantalla viva."""

    escape_pressed = Signal()
    mode_key_pressed = Signal(str)

    def __init__(self, items: list):
        super().__init__(None, Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_DeleteOnClose, True)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setMouseTracking(True)
        self.setGeometry(QGuiApplication.primaryScreen().virtualGeometry())

        self.mode = "none"
        self.color = QColor("#e5484d")

        # los dibujos son compartidos con la vista de zoom, que los pinta
        # transformados para que acompañen el contenido ampliado
        self._items = items
        self._creando: an.Item | None = None

        # estela del láser: pares de punto y momento de nacimiento
        self._estela: list[tuple[QPointF, float]] = []
        self._cursor = QPointF(-100, -100)

        self._reloj = QTimer(self)
        self._reloj.setInterval(30)
        self._reloj.timeout.connect(self._tic)

    def set_mode(self, modo: str):
        self.mode = modo
        if modo in ("none", "zoom"):
            self._reloj.stop()
            self.hide()
            return
        self.setCursor(Qt.BlankCursor if modo == "laser" else Qt.CrossCursor)
        if modo == "laser":
            self._reloj.start()
        else:
            self._reloj.stop()
        self.show()
        self.activateWindow()
        self.setFocus()
        self.update()

    def clear_drawings(self):
        self._items.clear()
        self._creando = None
        self.update()

    def _tic(self):
        """poda de la estela: los puntos que ya vivieron su tiempo se van."""
        ahora = time.monotonic()
        self._estela = [(p, n) for p, n in self._estela if ahora - n < _VIDA_ESTELA]
        self.update()

    # ------------------------------------------------------------------ #

    def mouseMoveEvent(self, e):
        self._cursor = QPointF(e.position())
        if self.mode == "laser":
            self._estela.append((QPointF(self._cursor), time.monotonic()))
        elif self._creando is not None:
            if isinstance(self._creando, an.BrushItem):
                self._creando.add_point(self._cursor)
            elif isinstance(self._creando, an.LineItem):
                self._creando.p2 = self._cursor
        self.update()

    def mousePressEvent(self, e):
        if e.button() != Qt.LeftButton:
            return
        punto = QPointF(e.position())
        if self.mode == "brush":
            self._creando = an.BrushItem(punto, self.color, 3.5)
        elif self.mode == "highlight":
            tinta = QColor(self.color)
            tinta.setAlpha(110)
            self._creando = an.BrushItem(punto, tinta, 16.0)
        elif self.mode == "line":
            self._creando = an.LineItem(punto, punto, self.color, 3.5)
        elif self.mode == "arrow":
            self._creando = an.LineItem(punto, punto, self.color, 3.5,
                                        cap_end="arrow_filled")
        if self._creando is not None:
            self._items.append(self._creando)

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._creando = None

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Escape:
            self.escape_pressed.emit()
        elif e.key() in _ATAJOS_MODO:
            self.mode_key_pressed.emit(_ATAJOS_MODO[e.key()])
        elif e.key() == Qt.Key_C:
            self.clear_drawings()
        else:
            super().keyPressEvent(e)

    # ------------------------------------------------------------------ #

    def paintEvent(self, _):
        pintor = QPainter(self)
        pintor.setRenderHint(QPainter.Antialiasing)
        for item in self._items:
            item.paint(pintor)
        if self.mode == "laser":
            self._pintar_laser(pintor)
        pintor.end()

    def _pintar_laser(self, pintor: QPainter):
        """punto láser con halo y estela que muere sola.

        cada punto de la estela envejece perdiendo tamaño y opacidad hasta
        desaparecer; el resultado es el barrido suave de un láser real.
        """
        base = QColor(settings.get("laser_color", "#ff3b30"))
        radio = settings.get("laser_size", 14) / 2 + 4

        if settings.get("laser_trail", True):
            ahora = time.monotonic()
            for punto, nacimiento in self._estela:
                edad = (ahora - nacimiento) / _VIDA_ESTELA
                tinta = QColor(base)
                tinta.setAlphaF(max(0.0, 0.5 * (1 - edad)))
                pintor.setPen(Qt.NoPen)
                pintor.setBrush(tinta)
                encogido = radio * (1 - edad * 0.6)
                pintor.drawEllipse(punto, encogido, encogido)

        halo = QRadialGradient(self._cursor, radio * 2.4)
        for parada, alfa in ((0.0, 200), (0.4, 80), (1.0, 0)):
            tinta = QColor(base)
            tinta.setAlpha(alfa)
            halo.setColorAt(parada, tinta)
        pintor.setPen(Qt.NoPen)
        pintor.setBrush(halo)
        pintor.drawEllipse(self._cursor, radio * 2.4, radio * 2.4)
        pintor.setBrush(base)
        pintor.drawEllipse(self._cursor, radio * 0.45, radio * 0.45)


class _ZoomView(QWidget):
    """la pantalla viva ampliada alrededor del cursor.

    ventana opaca a propósito: así windows acepta excluirla de la captura
    y el temporizador puede fotografiar el escritorio real sin que la
    propia vista salga en la foto. la rueda ajusta el aumento y el cuadro
    sigue al mouse, como una lupa gigante.
    """

    escape_pressed = Signal()
    mode_key_pressed = Signal(str)

    def __init__(self, items: list):
        super().__init__(None, Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_DeleteOnClose, True)
        self.setMouseTracking(True)
        self.setGeometry(QGuiApplication.primaryScreen().virtualGeometry())

        self._items = items
        self._zoom = 2.0
        self._cuadro = None
        self._dpr = capture.device_pixel_ratio()
        self._cursor = QPointF(self.width() / 2, self.height() / 2)

        self._reloj = QTimer(self)
        self._reloj.setInterval(_REFRESCO_MS)
        self._reloj.timeout.connect(self._tic)

        # sin la exclusión el zoom se vería a sí mismo; el intento va acá
        # porque necesita el identificador nativo de la ventana ya creado
        capture.exclude_from_capture(self)

    def start(self):
        self._cuadro = capture.grab_virtual_screen()
        self._reloj.start()
        self.show()
        self.activateWindow()
        self.setFocus()

    def stop(self):
        self._reloj.stop()
        self.hide()

    def zoom_step(self, factor: float):
        self._zoom = max(1.2, min(self._zoom * factor, 6.0))
        self.update()

    def _tic(self):
        self._cuadro = capture.grab_virtual_screen()
        self.update()

    # ------------------------------------------------------------------ #

    def mouseMoveEvent(self, e):
        self._cursor = QPointF(e.position())
        self.update()

    def wheelEvent(self, e):
        self.zoom_step(1.15 if e.angleDelta().y() > 0 else 1 / 1.15)

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Escape:
            self.escape_pressed.emit()
        elif e.key() in _ATAJOS_MODO:
            self.mode_key_pressed.emit(_ATAJOS_MODO[e.key()])
        elif e.key() in (Qt.Key_Plus, Qt.Key_Equal):
            self.zoom_step(1.25)
        elif e.key() == Qt.Key_Minus:
            self.zoom_step(1 / 1.15)
        else:
            super().keyPressEvent(e)

    # ------------------------------------------------------------------ #

    def paintEvent(self, _):
        if self._cuadro is None:
            return
        pintor = QPainter(self)
        pintor.setRenderHint(QPainter.SmoothPixmapTransform)

        # el recorte fuente se elige para que el punto bajo el mouse quede
        # en su mismo lugar de pantalla, que es lo natural al acercarse
        ancho, alto = self.width(), self.height()
        visible_w = ancho / self._zoom
        visible_h = alto / self._zoom
        cx, cy = self._cursor.x(), self._cursor.y()
        origen_x = max(0.0, min(cx - cx / self._zoom, ancho - visible_w))
        origen_y = max(0.0, min(cy - cy / self._zoom, alto - visible_h))

        fuente = QRectF(origen_x * self._dpr, origen_y * self._dpr,
                        visible_w * self._dpr, visible_h * self._dpr)
        pintor.drawImage(QRectF(0, 0, ancho, alto), self._cuadro, fuente)

        # los dibujos acompañan el contenido con la misma transformación
        pintor.setRenderHint(QPainter.Antialiasing)
        pintor.save()
        pintor.scale(self._zoom, self._zoom)
        pintor.translate(-origen_x, -origen_y)
        for item in self._items:
            item.paint(pintor)
        pintor.restore()
        pintor.end()


class PresentationMode(QObject):
    """coordinador del modo: junta el panel lateral, el overlay y el zoom.

    el panel manda las órdenes; este objeto decide qué ventana trabaja en
    cada momento. cerrar el panel termina el modo completo y avisa a la
    app para que restaure lo suyo.
    """

    closed = Signal()

    def __init__(self):
        super().__init__()
        self._items: list[an.Item] = []

        self.toolbar = FloatingToolbar()
        self.overlay = _DrawOverlay(self._items)
        self.zoomview = _ZoomView(self._items)

        self.toolbar.mode_changed.connect(self._cambiar_modo)
        self.toolbar.color_changed.connect(lambda c: setattr(self.overlay, "color", QColor(c)))
        self.toolbar.zoom_in_clicked.connect(self._acercar)
        self.toolbar.zoom_out_clicked.connect(lambda: self.zoomview.zoom_step(1 / 1.25))
        self.toolbar.clear_clicked.connect(self.overlay.clear_drawings)
        self.toolbar.exit_clicked.connect(self.close)
        for ventana in (self.overlay, self.zoomview):
            ventana.escape_pressed.connect(self._escape)
            ventana.mode_key_pressed.connect(self.toolbar.toggle_mode)

        self.toolbar.fade_in()

    def _cambiar_modo(self, modo: str):
        if modo == "zoom":
            self.overlay.set_mode("zoom")
            self.zoomview.start()
        else:
            self.zoomview.stop()
            self.overlay.set_mode(modo)
        # el panel sigue mandando por encima de la ventana que haya subido
        self.toolbar.raise_()

    def _acercar(self):
        """el botón de acercar también sirve de entrada al zoom."""
        if self.toolbar.current_mode() != "zoom":
            self.toolbar.toggle_mode("zoom")
        else:
            self.zoomview.zoom_step(1.25)

    def _escape(self):
        """esc apaga la herramienta activa; con todo apagado, cierra el modo."""
        if self.toolbar.current_mode() != "none":
            self.toolbar.clear_mode()
            self._cambiar_modo("none")
        else:
            self.close()

    def close(self):
        self.zoomview.close()
        self.overlay.close()
        self.toolbar.close()
        self.closed.emit()
