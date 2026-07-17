"""interfaz de la captura con desplazamiento.

primero un selector marca la zona sobre la ventana que se quiere capturar.
después, mientras dura la captura, todo queda enjaulado: un velo oscurece
todos los monitores, los clics y el teclado se bloquean por completo y lo
único que pasa a la ventana de atrás es el giro de la rueda, que la scrollea
de verdad. cada giro captura la franja visible y el cosedor la une a la
imagen larga.

del teclado solo se atienden esc (cancelar), enter (abrir el editor), ctrl+c
(copiar y cerrar) y ctrl+s (guardar y cerrar); el resto se traga para que no
haya alt+tab, tecla windows ni forma de irse a otra ventana o monitor.
"""

from pynput import keyboard, mouse
from PySide6.QtCore import QObject, QRect, QRectF, QTimer, Qt, Signal
from PySide6.QtGui import (QColor, QGuiApplication, QImage, QPainter, QPen,
                           QPixmap)
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from src.core import capture
from src.core.scrolling_capture import ScrollStitcher
from src.i18n.translator import t
from src.ui.themes.theme_manager import theme

# mensajes del hook de ratón de bajo nivel
_WM_MOUSEWHEEL = 0x020A
_WM_MOUSEHWHEEL = 0x020E
_BOTONES_MOUSE = {0x0201, 0x0202, 0x0204, 0x0205, 0x0207, 0x0208, 0x020B, 0x020C}

# mensajes del hook de teclado y códigos de tecla que sí atendemos
_TECLA_ABAJO = {0x0100, 0x0104}   # WM_KEYDOWN, WM_SYSKEYDOWN
_TECLA_ARRIBA = {0x0101, 0x0105}  # WM_KEYUP, WM_SYSKEYUP
_VK_CONTROL = {0x11, 0xA2, 0xA3}
_VK_ESC = 0x1B
_VK_ENTER = 0x0D
_VK_C = 0x43
_VK_S = 0x53


class _RegionPicker(QWidget):
    """selector de zona minimalista: velo oscuro, arrastre y listo."""

    region_ready = Signal(QRect, QRect)   # zona en píxeles físicos y lógicos
    cancelled = Signal()

    def __init__(self):
        super().__init__(None, Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_DeleteOnClose, True)
        self._imagen = capture.grab_virtual_screen()
        self._dpr = capture.device_pixel_ratio()
        # geometría de todo el escritorio virtual; su esquina puede ser
        # negativa si hay un monitor a la izquierda o arriba del principal, y
        # esa esquina hay que sumarla luego para acertar las coordenadas
        self._vg = QGuiApplication.primaryScreen().virtualGeometry()
        self.setGeometry(self._vg)
        self._origen = None
        self._sel = QRectF()
        self.setCursor(Qt.CrossCursor)
        # con foco de teclado el esc cancela desde que aparece el selector
        self.setFocusPolicy(Qt.StrongFocus)

    def showEvent(self, e):
        super().showEvent(e)
        # se fuerza el foco para que el esc cancele a la primera aunque el
        # selector se abra por encima de otra aplicación
        self.activateWindow()
        self.setFocus()
        capture.force_foreground(int(self.winId()))

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._origen = e.position()
            self._sel = QRectF(self._origen, self._origen)

    def mouseMoveEvent(self, e):
        if self._origen is not None:
            self._sel = QRectF(self._origen, e.position()).normalized()
            self.update()

    def mouseReleaseEvent(self, e):
        if e.button() != Qt.LeftButton or self._origen is None:
            return
        sel = self._sel
        self.close()
        if sel.width() >= 30 and sel.height() >= 30:
            # las coordenadas del arrastre son relativas a esta ventana, que
            # arranca en la esquina del escritorio virtual; se le suma esa
            # esquina para tener la posición real en pantalla y recién ahí se
            # pasa a píxeles físicos, que es lo que lee la captura
            ax = self._vg.x() + sel.x()
            ay = self._vg.y() + sel.y()
            fisico = QRect(round(ax * self._dpr), round(ay * self._dpr),
                           round(sel.width() * self._dpr), round(sel.height() * self._dpr))
            self.region_ready.emit(fisico, sel.toRect())
        else:
            self.cancelled.emit()

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Escape:
            self.close()
            self.cancelled.emit()

    def paintEvent(self, _):
        pintor = QPainter(self)
        pintor.drawImage(self.rect(), self._imagen)
        velo = QColor(0, 0, 0, 110)
        if self._sel.isValid() and self._sel.width() > 0:
            s = self._sel
            pintor.fillRect(QRectF(0, 0, self.width(), s.top()), velo)
            pintor.fillRect(QRectF(0, s.bottom(), self.width(), self.height() - s.bottom()), velo)
            pintor.fillRect(QRectF(0, s.top(), s.left(), s.height()), velo)
            pintor.fillRect(QRectF(s.right(), s.top(), self.width() - s.right(), s.height()), velo)
            pintor.setPen(QPen(QColor(theme.accent()), 1.6))
            pintor.setBrush(Qt.NoBrush)
            pintor.drawRect(s)
        else:
            pintor.fillRect(self.rect(), velo)
        pintor.end()


class _DimOverlay(QWidget):
    """velo que oscurece todos los monitores alrededor de la zona a capturar.

    la ventana es transparente al ratón (WindowTransparentForInput) para que
    el giro de la rueda atraviese hacia la ventana de atrás y la scrollee de
    verdad. de bloquear los clics y el teclado se encargan los hooks de la
    ventana de control, no este velo. cubre todo el escritorio virtual, así
    que el oscurecido se ve también en el segundo monitor.
    """

    def __init__(self, zona_logica: QRect):
        super().__init__(None, Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint
                         | Qt.Tool | Qt.WindowTransparentForInput)
        self.setAttribute(Qt.WA_DeleteOnClose, True)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setGeometry(QGuiApplication.primaryScreen().virtualGeometry())
        self._zona = zona_logica

    def paintEvent(self, _):
        pintor = QPainter(self)
        velo = QColor(0, 0, 0, 120)
        z = QRectF(self._zona)
        # cuatro franjas alrededor de la zona; el centro queda transparente
        pintor.fillRect(QRectF(0, 0, self.width(), z.top()), velo)
        pintor.fillRect(QRectF(0, z.bottom(), self.width(), self.height() - z.bottom()), velo)
        pintor.fillRect(QRectF(0, z.top(), z.left(), z.height()), velo)
        pintor.fillRect(QRectF(z.right(), z.top(), self.width() - z.right(), z.height()), velo)
        pintor.setPen(QPen(QColor(theme.accent()), 3))
        pintor.setBrush(Qt.NoBrush)
        pintor.drawRect(z.adjusted(-1.5, -1.5, 1.5, 1.5))
        pintor.end()


class _InputBridge(QObject):
    """puente entre los hilos de pynput y el hilo de la interfaz."""
    scrolled = Signal()
    finish_key = Signal()
    cancel_key = Signal()
    copy_key = Signal()
    save_key = Signal()


class ScrollCaptureWindow(QWidget):
    """ventanita de control con la vista previa de la imagen larga."""

    finished = Signal(QImage)
    copy_requested = Signal(QImage)
    save_requested = Signal(QImage)
    cancelled = Signal()

    _ANCHO_PREVIA = 240

    def __init__(self, region_fisica: QRect, region_logica: QRect):
        super().__init__(None, Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setObjectName("ventanaScroll")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setAttribute(Qt.WA_DeleteOnClose, True)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)

        self._region = region_fisica
        self._stitcher = ScrollStitcher()
        self._terminada = False
        self._ctrl = False
        # identificador de esta ventana; el hook deja pasar los clics que caen
        # sobre ella para que sus botones sigan respondiendo. se guarda en
        # showEvent, cuando la ventana ya tiene su hwnd nativo
        self._hwnd = 0

        # aunque la ventana quedara dentro de la zona elegida, la exclusión
        # evita que salga en los fotogramas; es opaca, así que windows la
        # acepta sin problema
        capture.exclude_from_capture(self)

        self._velo = _DimOverlay(region_logica)
        self._velo.show()
        capture.exclude_from_capture(self._velo)

        columna = QVBoxLayout(self)
        columna.setContentsMargins(14, 12, 14, 12)
        columna.setSpacing(8)

        titulo = QLabel(t("scroll.title"))
        titulo.setObjectName("titulo")
        columna.addWidget(titulo)

        pista = QLabel(t("scroll.hint"))
        pista.setObjectName("secundario")
        pista.setWordWrap(True)
        pista.setMaximumWidth(self._ANCHO_PREVIA)
        columna.addWidget(pista)

        self._previa = QLabel()
        self._previa.setFixedWidth(self._ANCHO_PREVIA)
        self._previa.setMinimumHeight(160)
        self._previa.setAlignment(Qt.AlignTop | Qt.AlignHCenter)
        self._previa.setStyleSheet("background: rgba(128,128,128,25); border-radius: 8px;")
        columna.addWidget(self._previa)

        self._altura = QLabel(f'{t("scroll.height")}: 0 px')
        self._altura.setObjectName("secundario")
        columna.addWidget(self._altura)

        botones = QHBoxLayout()
        cancelar = QPushButton(t("scroll.cancel") + "  (Esc)")
        finalizar = QPushButton(t("scroll.finish") + "  (Enter)")
        finalizar.setObjectName("primario")
        botones.addWidget(cancelar)
        botones.addWidget(finalizar)
        columna.addLayout(botones)

        cancelar.clicked.connect(self._cancelar)
        finalizar.clicked.connect(self._finalizar)

        self._acomodar(region_logica)

        # la rueda y las teclas se escuchan globales: el foco lo tiene la
        # página que el usuario scrollea, no esta ventana. el puente trae cada
        # aviso al hilo de qt, y el temporizador junta ráfagas de scroll en una
        # sola captura cuando la pantalla asienta
        self._puente = _InputBridge()
        self._puente.scrolled.connect(self._programar_captura)
        self._puente.finish_key.connect(self._finalizar)
        self._puente.cancel_key.connect(self._cancelar)
        self._puente.copy_key.connect(self._copiar)
        self._puente.save_key.connect(self._guardar)

        # la espera junta la ráfaga de scroll en una captura cuando la pantalla
        # asienta; corta, para tomar incrementos chicos cuando se scrollea
        # despacio y no perder tramos si el contenido salta mucho
        self._espera = QTimer(self)
        self._espera.setSingleShot(True)
        self._espera.setInterval(120)
        self._espera.timeout.connect(self._capturar_tramo)

        # el filtro del ratón bloquea clics y deja pasar solo la rueda; el del
        # teclado enjaula todo salvo esc, enter, ctrl+c y ctrl+s
        self._raton = mouse.Listener(win32_event_filter=self._filtro_raton)
        self._raton.daemon = True
        self._raton.start()
        self._teclado = keyboard.Listener(win32_event_filter=self._filtro_teclado)
        self._teclado.daemon = True
        self._teclado.start()

        QTimer.singleShot(300, self._capturar_tramo)

    def showEvent(self, e):
        super().showEvent(e)
        # ya con la ventana creada se guarda su identificador nativo, que el
        # hook usa para reconocer los clics de sus propios botones
        try:
            self._hwnd = int(self.winId())
        except Exception:
            self._hwnd = 0

    # ------------------------------------------------------------------ #
    # entrada global (corre en los hilos de pynput; solo emite señales)

    def _sobre_control(self, x: int, y: int) -> bool:
        """True si el punto cae sobre el panel de control, para no bloquear el
        clic de sus botones. se resuelve preguntando qué ventana hay bajo el
        punto, más fiable que comparar rectángulos entre monitores con
        distinto escalado."""
        if not self._hwnd:
            return False
        try:
            import win32gui
            hwnd = win32gui.WindowFromPoint((int(x), int(y)))
            while hwnd:
                if hwnd == self._hwnd:
                    return True
                hwnd = win32gui.GetParent(hwnd)
        except Exception:
            pass
        return False

    def _filtro_raton(self, msg, data):
        # ojo: suppress_event() bloquea lanzando una excepción que pynput
        # atrapa arriba, así que nunca debe quedar dentro de un try que la
        # capture; por eso va siempre como última instrucción
        if msg == _WM_MOUSEWHEEL:
            # la rueda vertical se deja pasar tal cual a la ventana de atrás,
            # que scrollea de verdad; solo avisamos para programar la captura
            self._puente.scrolled.emit()
            return
        if msg == _WM_MOUSEHWHEEL:
            # el scroll horizontal no aporta a la imagen larga; se bloquea
            self._raton.suppress_event()
        elif msg in _BOTONES_MOUSE:
            # los clics se bloquean para no colarse en la ventana de atrás,
            # salvo los que caen sobre el propio panel de control
            sobre = False
            try:
                sobre = self._sobre_control(data.pt.x, data.pt.y)
            except Exception:
                sobre = False
            if not sobre:
                self._raton.suppress_event()

    def _filtro_teclado(self, msg, data):
        # todo el teclado queda enjaulado: nada llega a la ventana de atrás ni
        # a otra app (ni alt+tab, ni la tecla windows). solo reconocemos las
        # combinaciones útiles y emitimos su señal antes de tragar la tecla
        vk = getattr(data, "vkCode", None)
        if vk in _VK_CONTROL:
            if msg in _TECLA_ABAJO:
                self._ctrl = True
            elif msg in _TECLA_ARRIBA:
                self._ctrl = False
        elif msg in _TECLA_ABAJO:
            if vk == _VK_ESC:
                self._puente.cancel_key.emit()
            elif vk == _VK_ENTER:
                self._puente.finish_key.emit()
            elif vk == _VK_C and self._ctrl:
                self._puente.copy_key.emit()
            elif vk == _VK_S and self._ctrl:
                self._puente.save_key.emit()
        self._teclado.suppress_event()

    # ------------------------------------------------------------------ #
    # captura y vista previa

    def _acomodar(self, zona: QRect):
        """la ventana busca un lugar fuera de la zona elegida.

        primero intenta el borde derecho; si la zona vive justo ahí, se
        pasa al izquierdo. mejor no taparle al usuario lo que capturará.
        """
        pantalla = QGuiApplication.primaryScreen().availableGeometry()
        self.adjustSize()
        x_derecha = pantalla.right() - self.width() - 24
        candidata = QRect(x_derecha, pantalla.top() + 80, self.width(), self.height())
        if candidata.intersects(zona):
            self.move(pantalla.left() + 24, pantalla.top() + 80)
        else:
            self.move(x_derecha, pantalla.top() + 80)

    def _programar_captura(self):
        self._espera.start()

    def _capturar_tramo(self):
        frame = capture.grab_region(self._region.x(), self._region.y(),
                                    self._region.width(), self._region.height())
        if self._stitcher.add_frame(frame):
            self._refrescar_previa()

    def _refrescar_previa(self):
        imagen = self._stitcher.image
        if imagen is None:
            return
        pixmap = QPixmap.fromImage(imagen).scaledToWidth(self._ANCHO_PREVIA, Qt.SmoothTransformation)
        # la vista muestra el extremo recién cosido: abajo si se scrolleó hacia
        # abajo, arriba si fue hacia arriba
        maximo = 320
        if pixmap.height() > maximo:
            if self._stitcher.last_side == "arriba":
                pixmap = pixmap.copy(0, 0, pixmap.width(), maximo)
            else:
                pixmap = pixmap.copy(0, pixmap.height() - maximo, pixmap.width(), maximo)
        self._previa.setFixedHeight(min(pixmap.height(), maximo))
        self._previa.setPixmap(pixmap)
        self._altura.setText(f'{t("scroll.height")}: {self._stitcher.height} px')

    # ------------------------------------------------------------------ #
    # cierre por cada camino

    def _imagen_capturada(self) -> QImage | None:
        """recoge una última toma, detiene todo y devuelve la imagen o None."""
        self._espera.stop()
        self._capturar_tramo()
        self._detener()
        imagen = self._stitcher.image
        return imagen if (imagen is not None and not imagen.isNull()) else None

    def _detener(self):
        if self._raton is not None:
            self._raton.stop()
            self._raton = None
        if self._teclado is not None:
            self._teclado.stop()
            self._teclado = None
        self._espera.stop()
        if self._velo is not None:
            self._velo.close()
            self._velo = None

    def _finalizar(self):
        # enter: lo capturado pasa al editor para anotar antes de decidir
        if self._terminada:
            return
        self._terminada = True
        imagen = self._imagen_capturada()
        self.close()
        if imagen is not None:
            self.finished.emit(imagen)
        else:
            self.cancelled.emit()

    def _copiar(self):
        # ctrl+c: se copia lo capturado y se cierra todo el flujo
        if self._terminada:
            return
        self._terminada = True
        imagen = self._imagen_capturada()
        self.close()
        if imagen is not None:
            self.copy_requested.emit(imagen)
        else:
            self.cancelled.emit()

    def _guardar(self):
        # ctrl+s: se guarda lo capturado y se cierra todo el flujo
        if self._terminada:
            return
        self._terminada = True
        imagen = self._imagen_capturada()
        self.close()
        if imagen is not None:
            self.save_requested.emit(imagen)
        else:
            self.cancelled.emit()

    def _cancelar(self):
        if self._terminada:
            return
        self._terminada = True
        self._detener()
        self.close()
        self.cancelled.emit()

    def closeEvent(self, e):
        self._detener()
        super().closeEvent(e)


def pick_region_and_start(al_terminar, al_cancelar, al_copiar, al_guardar) -> _RegionPicker:
    """arranque completo del flujo: selector primero, control después.

    devuelve el selector para que quien llama conserve la referencia; sin
    ella el recolector de basura podría cerrar el overlay antes de tiempo.
    """
    selector = _RegionPicker()

    def con_region(fisica: QRect, logica: QRect):
        ventana = ScrollCaptureWindow(fisica, logica)
        ventana.finished.connect(al_terminar)
        ventana.cancelled.connect(al_cancelar)
        ventana.copy_requested.connect(al_copiar)
        ventana.save_requested.connect(al_guardar)
        # la referencia se cuelga del selector para mantenerla viva
        selector._ventana_control = ventana
        ventana.show()

    selector.region_ready.connect(con_region)
    selector.cancelled.connect(al_cancelar)
    selector.show()
    selector.activateWindow()
    return selector
