"""interfaz de la captura con desplazamiento.

primero un selector marca la zona; después un velo con un hueco real deja
pasar el mouse y el scroll solo dentro de esa zona. cada giro de rueda
captura la franja visible y el cosedor del núcleo la une a la imagen larga,
que al finalizar pasa al editor. enter y esc se escuchan de forma global
porque el teclado lo tiene la página que se scrollea, no esta ventana.
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


class _RegionPicker(QWidget):
    """selector de zona minimalista: velo oscuro, arrastre y listo."""

    region_ready = Signal(QRect, QRect)   # zona en píxeles físicos y lógicos
    cancelled = Signal()

    def __init__(self):
        super().__init__(None, Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_DeleteOnClose, True)
        self._imagen = capture.grab_virtual_screen()
        self._dpr = capture.device_pixel_ratio()
        self.setGeometry(QGuiApplication.primaryScreen().virtualGeometry())
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
            fisico = QRect(round(sel.x() * self._dpr), round(sel.y() * self._dpr),
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
    """velo que oscurece la pantalla alrededor de la zona a capturar.

    la ventana es transparente al ratón (WindowTransparentForInput), así que
    el scroll y los clics atraviesan hacia la página de abajo en cualquier
    punto, sin depender de una máscara recortada (que se descuadraba con el
    escalado de windows y hacía capturar una zona distinta a la elegida). la
    zona queda limpia y solo se oscurece lo de alrededor, como guía visual.
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
        velo = QColor(0, 0, 0, 100)
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


class ScrollCaptureWindow(QWidget):
    """ventanita de control con la vista previa de la imagen larga."""

    finished = Signal(QImage)
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

        # aunque la ventana quedara dentro de la zona elegida, la exclusión
        # evita que salga en los fotogramas; es opaca, así que windows la
        # acepta sin problema
        capture.exclude_from_capture(self)

        self._velo = _DimOverlay(region_logica)
        self._velo.show()

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

        # la rueda y las teclas de cierre se escuchan globales: el foco lo
        # tiene la página que el usuario scrollea, no esta ventana. el
        # puente trae cada aviso al hilo de qt, y el temporizador junta
        # ráfagas de scroll en una sola captura cuando la pantalla asienta
        self._puente = _InputBridge()
        self._puente.scrolled.connect(self._programar_captura)
        self._puente.finish_key.connect(self._finalizar)
        self._puente.cancel_key.connect(self._cancelar)

        # la espera junta la ráfaga de scroll en una captura cuando la pantalla
        # asienta; corta, para tomar incrementos chicos cuando se scrollea
        # despacio y no perder tramos si el contenido salta mucho
        self._espera = QTimer(self)
        self._espera.setSingleShot(True)
        self._espera.setInterval(140)
        self._espera.timeout.connect(self._capturar_tramo)

        self._raton = mouse.Listener(on_scroll=lambda *_: self._puente.scrolled.emit())
        self._raton.daemon = True
        self._raton.start()
        self._teclado = keyboard.Listener(on_press=self._tecla_global)
        self._teclado.daemon = True
        self._teclado.start()

        QTimer.singleShot(350, self._capturar_tramo)

    def _tecla_global(self, tecla):
        # esta función corre en el hilo de pynput; solo emite señales
        if tecla == keyboard.Key.esc:
            self._puente.cancel_key.emit()
        elif tecla == keyboard.Key.enter:
            self._puente.finish_key.emit()

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
        # con la imagen ya más larga que la ventana, la vista muestra el
        # final, que es lo recién capturado
        maximo = 320
        if pixmap.height() > maximo:
            pixmap = pixmap.copy(0, pixmap.height() - maximo, pixmap.width(), maximo)
        self._previa.setFixedHeight(min(pixmap.height(), maximo))
        self._previa.setPixmap(pixmap)
        self._altura.setText(f'{t("scroll.height")}: {self._stitcher.height} px')

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
        if self._terminada:
            return
        self._terminada = True
        # una última toma recoge lo que quedó visible al soltar, por si la
        # ráfaga de scroll terminó justo antes de la espera
        self._espera.stop()
        self._capturar_tramo()
        self._detener()
        imagen = self._stitcher.image
        self.close()
        if imagen is not None and not imagen.isNull():
            self.finished.emit(imagen)
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


def pick_region_and_start(al_terminar, al_cancelar) -> _RegionPicker:
    """arranque completo del flujo: selector primero, control después.

    devuelve el selector para que quien llama conserve la referencia; sin
    ella el recolector de basura podría cerrar el overlay antes de tiempo.
    """
    selector = _RegionPicker()

    def con_region(fisica: QRect, logica: QRect):
        ventana = ScrollCaptureWindow(fisica, logica)
        ventana.finished.connect(al_terminar)
        ventana.cancelled.connect(al_cancelar)
        # la referencia se cuelga del selector para mantenerla viva
        selector._ventana_control = ventana
        ventana.show()

    selector.region_ready.connect(con_region)
    selector.cancelled.connect(al_cancelar)
    selector.show()
    selector.activateWindow()
    return selector
