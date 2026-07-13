"""modo presentación: pausar la pantalla, señalar, dibujar y capturar.

al elegir una herramienta se congela lo que hay en pantalla y sobre esa
foto se dibuja, se anota y se hace zoom hacia el cursor con la rueda. las
anotaciones quedan pegadas al contenido y escalan con él; deshacer y
rehacer trabajan por acciones. ctrl+c copia la pizarra, ctrl+s la guarda,
ctrl+a recorta un pedazo y esc despausa.
"""

import time

from PySide6.QtCore import (QEvent, QObject, QPointF, QRect, QRectF, Qt,
                            QTimer, Signal)
from PySide6.QtGui import (QColor, QFont, QGuiApplication, QImage,
                           QKeySequence, QPainter, QPen, QRadialGradient)
from PySide6.QtWidgets import (QCheckBox, QFileDialog, QLineEdit, QMessageBox,
                               QPushButton, QWidget)

from src.config.settings import settings
from src.core import capture
from src.i18n.translator import t
from src.ui.overlays import annotation_tools as an
from src.ui.overlays.floating_toolbar import DEFAULT_KEYS, FloatingToolbar, board_key
from src.ui.overlays.properties_panel import PropertiesPanel
from src.ui.themes.theme_manager import theme

# vida de cada punto de la estela del láser, en segundos
_VIDA_ESTELA = 0.65

_LADO_TIRADOR = 8.0

# duración del aviso flotante (por ejemplo al limpiar la pizarra)
_VIDA_AVISO = 1.4

def _atajos_vigentes() -> dict:
    """mapa tecla → herramienta, con las letras que el usuario configuró."""
    mapa = {}
    for modo in DEFAULT_KEYS:
        letra = board_key(modo)
        tecla = getattr(Qt, f"Key_{letra}", None)
        if tecla is not None:
            mapa[tecla] = modo
    return mapa


class _FreezeOverlay(QWidget):
    """la pantalla pausada: foto congelada, zoom, dibujo y edición."""

    escape_pressed = Signal()
    mode_key_pressed = Signal(str)
    selection_changed = Signal()
    item_reclicked = Signal()
    window_activated = Signal()
    copied = Signal(QImage)
    save_requested = Signal(QImage)

    def event(self, e):
        # cada vez que la pausa gana el foco (por ejemplo al clicar para
        # dibujar), windows la sube por encima de los paneles flotantes,
        # que también son siempre-adelante, y los tapa; el aviso permite
        # que el coordinador los vuelva a subir al instante
        if e.type() == QEvent.WindowActivate:
            self.window_activated.emit()
        return super().event(e)

    def showEvent(self, e):
        super().showEvent(e)
        # la primera vez que la pizarra aparece, un aviso al centro deja
        # claro cómo se sale; después queda la pista fija de la esquina
        if not self._aviso_inicial_dado:
            self._aviso_inicial_dado = True
            # la bienvenida dura más que los avisos comunes, lo justo para
            # leerla sin que estorbe
            self._mostrar_aviso(t("zoom.esc_note"), duracion=3.0)

    def __init__(self):
        super().__init__(None, Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_DeleteOnClose, True)
        self.setMouseTracking(True)

        self._imagen = capture.grab_virtual_screen()
        self._dpr = capture.device_pixel_ratio()
        geometria = QGuiApplication.primaryScreen().virtualGeometry()
        self.setGeometry(geometria)
        # el corrimiento del escritorio virtual: con dos monitores, las
        # pistas deben ubicarse respecto del monitor principal, no del
        # lienzo combinado
        self._offset_virtual = geometria.topLeft()
        self._aviso_inicial_dado = False

        self.mode = "zoom"
        # los valores por defecto que gobierna la ventanita de propiedades
        self.color = QColor("#e5484d")
        self.fuente = QFont("Segoe UI", 18)
        self.texto_rotacion = 0.0
        self.texto_bg = "none"
        self.texto_bg_color = QColor("#ffffff")
        self.texto_sombra = False
        self.texto_contorno = False
        self.forma = "rect"
        self.ancho = 4.0
        self.dash = "solid"
        self.cap_inicio = "none"
        self.cap_fin = "arrow_filled"
        self.opacidad = 1.0
        # opciones del pincel de ocultar; no se guardan, arrancan igual
        self.pixel_modo = an.PIXEL_MODO
        self.pixel_cantidad = an.PIXEL_CANTIDAD
        self.pixel_grosor = an.PIXEL_GROSOR
        self._atajos = _atajos_vigentes()

        # la vista: cuánto zoom hay y qué esquina de la imagen se ve
        self._zoom = 1.0
        self._offset = QPointF(0, 0)
        self._paneo: QPointF | None = None
        self._cursor_pincel: QPointF | None = None  # en coordenadas base

        # los dibujos viven en coordenadas de la imagen base, por eso se
        # quedan pegados al contenido al acercar y alejar
        self._items: list[an.Item] = []
        self._seleccion: list[an.Item] = []
        self._arrastre: dict | None = None
        self._banda: QRectF | None = None

        # historial por acciones: agregar, quitar o limpiar; así el
        # deshacer también revive lo que borró el borrador o el tacho
        self._historial: list[tuple] = []
        self._rehacer_pila: list[tuple] = []
        self._borrando: list[tuple[int, an.Item]] = []

        self._cursor = QPointF(-100, -100)
        self._estela: list[tuple[QPointF, float]] = []
        self._aviso: tuple[str, float] | None = None
        self._reloj = QTimer(self)
        # 16 ms ≈ 60 repintados por segundo: el desvanecido del láser se ve
        # continuo en lugar de a saltos
        self._reloj.setInterval(16)
        self._reloj.timeout.connect(self._tic)

        self._editor: QLineEdit | None = None
        self._editor_base = QPointF()
        self._editor_fuente: QFont | None = None
        self._editor_color: QColor | None = None

        # submodo de captura: arrastrar para recortar lo que se ve
        self._cap_activa = False
        self._cap_sel = QRectF()
        self._cap_origen: QPointF | None = None
        self._boton_copiar = QPushButton(t("tool.copy"), self)
        self._boton_guardar = QPushButton(t("tool.save"), self)
        self._boton_guardar.setObjectName("primario")
        for b in (self._boton_copiar, self._boton_guardar):
            b.hide()
            b.setCursor(Qt.PointingHandCursor)
        self._boton_copiar.clicked.connect(self._cap_copiar)
        self._boton_guardar.clicked.connect(self._cap_guardar)

    # ------------------------------------------------------------------ #
    # vista

    def _a_base(self, punto: QPointF) -> QPointF:
        return self._offset + punto / self._zoom

    def _a_vista(self, punto: QPointF) -> QPointF:
        return (punto - self._offset) * self._zoom

    def _limitar_offset(self):
        maximo_x = self.width() - self.width() / self._zoom
        maximo_y = self.height() - self.height() / self._zoom
        self._offset.setX(max(0.0, min(self._offset.x(), maximo_x)))
        self._offset.setY(max(0.0, min(self._offset.y(), maximo_y)))

    def zoom_step(self, factor: float, ancla: QPointF | None = None):
        """acerca o aleja manteniendo quieto el punto bajo el ancla."""
        if ancla is None:
            ancla = self._cursor if self.rect().contains(self._cursor.toPoint()) \
                else QPointF(self.width() / 2, self.height() / 2)
        punto_base = self._a_base(ancla)
        self._zoom = max(1.0, min(self._zoom * factor, 6.0))
        self._offset = punto_base - ancla / self._zoom
        self._limitar_offset()
        self._reubicar_editor()
        self.update()

    def _reubicar_editor(self):
        """el cuadro de texto en edición acompaña al zoom y al paneo:
        se muda al lugar del texto y escala su letra a lo que se ve."""
        if self._editor is None:
            return
        fuente_base = self._editor_fuente or self.fuente
        visual = QFont(fuente_base)
        visual.setPointSizeF(max(8.0, fuente_base.pointSizeF() * self._zoom))
        self._editor.setFont(visual)
        # el tamaño visible vive en el estilo, no en el setFont, porque la
        # hoja de estilos global lo pisaría
        hoja = self._editor.styleSheet()
        import re
        self._editor.setStyleSheet(re.sub(r"font-size: \d+pt",
                                          f"font-size: {visual.pointSizeF():.0f}pt", hoja))
        vista = self._a_vista(self._editor_base)
        self._editor.move(int(vista.x()) - 4, int(vista.y()) - 6)

    # ------------------------------------------------------------------ #
    # historial por acciones

    def _registrar(self, accion: tuple):
        self._historial.append(accion)
        self._rehacer_pila.clear()

    def _aplicar_inversa(self, accion: tuple):
        tipo, datos = accion
        if tipo == "agregar":
            for item in datos:
                if item in self._items:
                    self._items.remove(item)
                if item in self._seleccion:
                    self._seleccion.remove(item)
        elif tipo == "quitar":
            # los elementos vuelven a su posición original de la lista
            # para respetar qué tapa a qué
            for indice, item in sorted(datos, key=lambda par: par[0]):
                self._items.insert(min(indice, len(self._items)), item)
        elif tipo == "estado":
            # un movimiento o estirada se deshace volviendo a la geometría
            # que el elemento tenía antes del arrastre
            for item, antes, _despues in datos:
                an.restore(item, antes)

    def undo(self):
        if not self._historial:
            return
        accion = self._historial.pop()
        self._aplicar_inversa(accion)
        self._rehacer_pila.append(accion)
        self.selection_changed.emit()
        self.update()

    def redo(self):
        if not self._rehacer_pila:
            return
        accion = self._rehacer_pila.pop()
        tipo, datos = accion
        if tipo == "agregar":
            self._items.extend(datos)
        elif tipo == "quitar":
            for indice, item in datos:
                if item in self._items:
                    self._items.remove(item)
        elif tipo == "estado":
            for item, _antes, despues in datos:
                an.restore(item, despues)
        self._historial.append(accion)
        self.selection_changed.emit()
        self.update()

    def clear_drawings(self):
        """el tacho: limpia todo, con vuelta atrás y aviso animado."""
        self._commit_texto()
        if not self._items:
            return
        self._registrar(("quitar", list(enumerate(self._items))))
        self._items.clear()
        if self._seleccion:
            self._seleccion.clear()
            self.selection_changed.emit()
        self._mostrar_aviso(t("zoom.cleared"))
        self.update()

    def _mostrar_aviso(self, texto: str, duracion: float = _VIDA_AVISO):
        self._aviso = (texto, time.monotonic(), duracion)
        self._reloj.start()

    # ------------------------------------------------------------------ #
    # herramientas

    def set_mode(self, modo: str):
        self._commit_texto()
        self.mode = modo
        if modo != "select" and self._seleccion:
            self._seleccion.clear()
            self.selection_changed.emit()
        if modo not in ("highlight", "pixelate"):
            self._cursor_pincel = None
        # el resaltador y el pincel de ocultar muestran el círculo de grosor
        # (cursor oculto); el láser su punto; el pincel normal pinta y ya
        cursores = {"laser": Qt.BlankCursor, "zoom": Qt.ArrowCursor,
                    "select": Qt.ArrowCursor, "hand": Qt.OpenHandCursor,
                    "text": Qt.IBeamCursor,
                    "highlight": Qt.BlankCursor, "pixelate": Qt.BlankCursor}
        self.setCursor(cursores.get(modo, Qt.CrossCursor))
        if modo == "laser":
            self._reloj.start()
        self.update()

    def _tic(self):
        """latido de las animaciones: poda la estela y apaga el aviso."""
        ahora = time.monotonic()
        self._estela = [(p, n) for p, n in self._estela if ahora - n < _VIDA_ESTELA]
        if self._aviso and ahora - self._aviso[1] > self._aviso[2]:
            self._aviso = None
        if self.mode != "laser" and not self._aviso and not self._estela:
            self._reloj.stop()
        self.update()

    # ------------------------------------------------------------------ #
    # texto directo sobre la pizarra

    def _abrir_editor(self, base: QPointF, existente: an.TextItem | None = None):
        self._commit_texto()
        editor = QLineEdit(self)
        editor.setPlaceholderText(t("tool.text_placeholder"))
        fuente_base = existente.font if existente is not None else self.fuente
        color = existente.color if existente is not None else self.color
        # el texto se escribe al tamaño visual del zoom actual para que lo
        # tecleado coincida con lo que quedará en la pizarra
        visual = QFont(fuente_base)
        visual.setPointSizeF(max(8.0, fuente_base.pointSizeF() * self._zoom))
        editor.setFont(visual)
        # sin caja ni fondo, y con la fuente puesta en el propio estilo:
        # la hoja de estilos global fija 13px para todo y pisaría el
        # setFont, dejando el texto chico mientras se escribe
        editor.setStyleSheet(
            f"background: transparent; border: none; color: {color.name()};"
            f" font-family: '{visual.family()}'; font-size: {visual.pointSizeF():.0f}pt;"
            f" font-weight: {'bold' if visual.bold() else 'normal'};"
            f" font-style: {'italic' if visual.italic() else 'normal'};")
        if existente is not None:
            # editar un texto lo saca de la pizarra mientras se escribe; el
            # historial registra la salida para que ctrl+z lo devuelva
            editor.setText(existente.text)
            base = existente.pos
            indice = self._items.index(existente)
            self._items.remove(existente)
            if existente in self._seleccion:
                self._seleccion.remove(existente)
                self.selection_changed.emit()
            self._registrar(("quitar", [(indice, existente)]))
            self._editor_fuente = QFont(existente.font)
            self._editor_color = QColor(existente.color)
        else:
            self._editor_fuente = QFont(self.fuente)
            self._editor_color = QColor(self.color)
        vista = self._a_vista(base)
        editor.move(int(vista.x()) - 4, int(vista.y()) - 6)
        editor.setMinimumWidth(200)
        editor.show()
        editor.setFocus()
        editor.returnPressed.connect(self._finalizar_texto)
        self._editor = editor
        self._editor_base = QPointF(base)
        self.update()

    def _commit_texto(self):
        """confirma el texto en edición; devuelve el elemento creado."""
        if self._editor is None:
            return None
        texto = self._editor.text().strip()
        self._editor.deleteLater()
        self._editor = None
        nuevo = None
        if texto:
            fuente = getattr(self, "_editor_fuente", None) or QFont(self.fuente)
            color = getattr(self, "_editor_color", None) or self.color
            nuevo = an.TextItem(self._editor_base, texto, QFont(fuente), QColor(color))
            nuevo.opacity = self.opacidad
            nuevo.rotation = self.texto_rotacion
            nuevo.bg = self.texto_bg
            nuevo.bg_color = QColor(self.texto_bg_color)
            nuevo.shadow = self.texto_sombra
            nuevo.outline = self.texto_contorno
            self._items.append(nuevo)
            self._registrar(("agregar", [nuevo]))
        self._editor_fuente = None
        self._editor_color = None
        self.update()
        return nuevo

    def _finalizar_texto(self):
        """cierre definitivo de la escritura: el texto queda confirmado,
        seleccionado y con la herramienta en V, listo para acomodarlo.

        se dispara con esc, con enter o al clicar en otro lado; cambiar de
        herramienta sigue confirmando sin robar la herramienta elegida.
        """
        nuevo = self._commit_texto()
        if nuevo is not None:
            self._seleccion = [nuevo]
            self.selection_changed.emit()
            if self.mode != "select":
                self.mode_key_pressed.emit("select")

    # ------------------------------------------------------------------ #
    # captura de lo que se ve

    def enter_capture(self):
        """arranca el recorte: arrastrar sobre la vista y elegir qué hacer."""
        self._commit_texto()
        self._cap_activa = True
        self._cap_sel = QRectF()
        self._cap_origen = None
        self._ocultar_botones_cap()
        self.setCursor(Qt.CrossCursor)
        self.update()

    def _salir_captura(self):
        self._cap_activa = False
        self._cap_sel = QRectF()
        self._ocultar_botones_cap()
        self.set_mode(self.mode)
        self.update()

    def _ocultar_botones_cap(self):
        self._boton_copiar.hide()
        self._boton_guardar.hide()

    def _mostrar_botones_cap(self):
        """los botones aparecen pegados bajo el recorte, dentro de pantalla."""
        ancho = self._boton_copiar.sizeHint().width() + self._boton_guardar.sizeHint().width() + 8
        x = min(max(int(self._cap_sel.left()), 8), self.width() - ancho - 8)
        y = int(self._cap_sel.bottom()) + 10
        if y + 40 > self.height():
            y = int(self._cap_sel.top()) - 44
        self._boton_copiar.move(x, y)
        self._boton_guardar.move(x + self._boton_copiar.sizeHint().width() + 8, y)
        self._boton_copiar.show()
        self._boton_guardar.show()

    def _exportar_base(self, base: QRectF) -> QImage:
        """un rectángulo de la pizarra a resolución nativa, con dibujos."""
        fisico = QRect(round(base.x() * self._dpr), round(base.y() * self._dpr),
                       round(base.width() * self._dpr), round(base.height() * self._dpr))
        salida = self._imagen.copy(fisico)
        pintor = QPainter(salida)
        pintor.setRenderHint(QPainter.Antialiasing)
        pintor.scale(self._dpr, self._dpr)
        pintor.translate(-base.x(), -base.y())
        for item in self._items:
            an.paint_item(pintor, item)
        pintor.end()
        return salida

    def _exportar_cap(self) -> QImage:
        if self._cap_sel.width() < 2 or self._cap_sel.height() < 2:
            return QImage()
        base = QRectF(self._a_base(self._cap_sel.topLeft()),
                      self._cap_sel.size() / self._zoom)
        return self._exportar_base(base)

    def copiar_todo(self):
        """ctrl+c sin recorte: toda la pizarra con sus dibujos."""
        self._commit_texto()
        self.copied.emit(self._exportar_base(QRectF(0, 0, self.width(), self.height())))

    def guardar_todo(self):
        self._commit_texto()
        self.save_requested.emit(self._exportar_base(QRectF(0, 0, self.width(), self.height())))

    def _cap_copiar(self):
        imagen = self._exportar_cap()
        self._salir_captura()
        if not imagen.isNull():
            self.copied.emit(imagen)

    def _cap_guardar(self):
        imagen = self._exportar_cap()
        self._salir_captura()
        if not imagen.isNull():
            self.save_requested.emit(imagen)

    # ------------------------------------------------------------------ #
    # mouse

    def wheelEvent(self, e):
        self.zoom_step(1.15 if e.angleDelta().y() > 0 else 1 / 1.15, QPointF(e.position()))

    def mousePressEvent(self, e):
        # cinturón extra al de la activación de ventana: cada clic sobre
        # la pausa reafirma a los paneles por encima
        self.window_activated.emit()
        punto = QPointF(e.position())
        if e.button() == Qt.RightButton and self._zoom > 1.0:
            self._paneo = punto
            return
        if e.button() != Qt.LeftButton:
            return

        # clicar en otro lado con un texto a medio escribir lo confirma y
        # lo deja seleccionado; el clic no hace nada más
        if self._editor is not None:
            self._finalizar_texto()
            return

        if self._cap_activa:
            self._cap_origen = punto
            self._cap_sel = QRectF(punto, punto)
            self._ocultar_botones_cap()
            self.update()
            return

        base = self._a_base(punto)
        if self.mode == "select":
            self._press_seleccion(base, bool(e.modifiers() & Qt.AltModifier))
        elif self.mode in ("zoom", "hand"):
            if self._zoom > 1.0:
                self._paneo = punto
                self.setCursor(Qt.ClosedHandCursor)
        elif self.mode == "eraser":
            self._borrando = []
            self._borrar_en(base)
            self._arrastre = {"modo": "borrar"}
        elif self.mode == "text":
            self._abrir_editor(base)
        elif self.mode == "brush":
            self._crear(an.BrushItem(base, self.color, self.ancho))
        elif self.mode == "highlight":
            tinta = QColor(self.color)
            tinta.setAlpha(110)
            self._crear(an.BrushItem(base, tinta, max(10.0, self.ancho * 4)))
        elif self.mode == "pixelate":
            # el trazo va sobre la pantalla congelada; se pinta como pincel
            # y al soltar deja pixelado o difuminado lo que cubrió
            self._crear(an.PixelateItem(base, self._imagen, self._dpr,
                                        self.pixel_modo, self.pixel_cantidad,
                                        self.pixel_grosor))
        elif self.mode == "line":
            nuevo = an.LineItem(base, base, self.color, self.ancho)
            nuevo.dash = self.dash
            self._crear(nuevo)
        elif self.mode == "arrow":
            nuevo = an.LineItem(base, base, self.color, self.ancho,
                                self.cap_inicio, self.cap_fin)
            nuevo.dash = self.dash
            self._crear(nuevo, base)
        elif self.mode == "shape":
            clase = an.SHAPES[self.forma][1]
            nuevo = clase(QRectF(base, base), self.color, self.ancho)
            nuevo.dash = self.dash
            self._crear(nuevo, base)
        self.update()

    def _crear(self, item: an.Item, origen: QPointF | None = None):
        item.opacity = self.opacidad
        self._items.append(item)
        self._arrastre = {"modo": "crear", "item": item, "origen": origen}

    def insert_image(self, imagen: QImage | None = None):
        """suma una imagen a la pizarra, desde archivo o del portapapeles.

        entra centrada en la vista actual, a un tamaño cómodo, y queda
        seleccionada con V para acomodarla de inmediato.
        """
        if imagen is None or imagen.isNull():
            ruta, _ = QFileDialog.getOpenFileName(
                self, t("tool.image"), "",
                "Imágenes (*.png *.jpg *.jpeg *.bmp *.gif *.webp)")
            if not ruta:
                return
            imagen = QImage(ruta)
            if imagen.isNull():
                return
        # el lado mayor entra a un 40 por ciento de la vista, sin agrandar
        # imágenes chicas
        factor = min(1.0, (self.width() * 0.4) / max(1, imagen.width()),
                     (self.height() * 0.4) / max(1, imagen.height()))
        ancho, alto = imagen.width() * factor, imagen.height() * factor
        centro = self._a_base(QPointF(self.width() / 2, self.height() / 2))
        nuevo = an.ImageItem(QRectF(centro.x() - ancho / 2, centro.y() - alto / 2,
                                    ancho, alto), imagen)
        self._items.append(nuevo)
        self._registrar(("agregar", [nuevo]))
        self._seleccion = [nuevo]
        self.selection_changed.emit()
        if self.mode != "select":
            self.mode_key_pressed.emit("select")
        self.update()

    def _press_seleccion(self, base: QPointF, alt: bool = False):
        """con V, el clic resuelve en orden: tirador del único
        seleccionado, un elemento (para tomarlo o para mover el grupo si
        ya era parte), o el vacío, donde nace el recuadro elástico.

        con alt, en lugar de mover el elemento se duplica y se arrastra la
        copia, como en los editores de diseño.
        """
        tolerancia = (_LADO_TIRADOR + 4) / self._zoom
        if len(self._seleccion) == 1:
            for i, tirador in enumerate(self._seleccion[0].handles()):
                if (tirador - base).manhattanLength() <= tolerancia:
                    unico = self._seleccion[0]
                    self._arrastre = {"modo": "tirador", "indice": i,
                                      "antes": [(unico, an.snapshot(unico))]}
                    # datos para shift (proporción) y alt (desde el centro)
                    if isinstance(unico, an.ShapeItem):
                        r = unico.rect
                        self._arrastre["centro"] = QPointF(r.center())
                        self._arrastre["aspecto"] = (r.width() / r.height()
                                                     if r.height() > 0 else 0)
                    # el texto escala contra su estado inicial, con el
                    # ancla quieta, para que no persiga al mouse
                    elif isinstance(unico, an.TextItem):
                        self._arrastre["texto0"] = (QRectF(unico._rect()),
                                                    unico.font.pointSizeF())
                    return
        for item in reversed(self._items):
            # el trazo de ocultar no se toma ni se mueve; solo el borrador lo quita
            if isinstance(item, an.PixelateItem):
                continue
            if item.contains(base):
                # el texto se selecciona y arrastra como cualquier otro
                # elemento; el doble clic es el que abre su edición
                ya_estaba = item in self._seleccion and len(self._seleccion) == 1
                if not ya_estaba and item not in self._seleccion:
                    self._seleccion = [item]
                    self.selection_changed.emit()
                if alt:
                    # se duplica lo seleccionado y el arrastre mueve las
                    # copias; el propio duplicado ya sirve de paso de
                    # deshacer, así que el movimiento no registra otro
                    copias = [an.clonar(i) for i in self._seleccion]
                    self._items.extend(copias)
                    self._registrar(("agregar", list(copias)))
                    self._seleccion = copias
                    self.selection_changed.emit()
                    self._arrastre = {"modo": "mover", "inicio": base,
                                      "duplicado": True,
                                      "antes": [(c, an.snapshot(c)) for c in copias]}
                    return
                self._arrastre = {"modo": "mover", "inicio": base, "re_clic": ya_estaba,
                                  "antes": [(i, an.snapshot(i)) for i in self._seleccion]}
                return
        if self._seleccion:
            self._seleccion = []
            self.selection_changed.emit()
        self._banda = QRectF(base, base)
        self._arrastre = {"modo": "banda", "origen": base}

    def _borrar_en(self, base: QPointF):
        """el borrador quita lo que toca; el conjunto de la pasada se
        registra como una sola acción al soltar."""
        for item in reversed(self._items):
            if item.contains(base):
                indice = self._items.index(item)
                self._items.remove(item)
                if item in self._seleccion:
                    self._seleccion.remove(item)
                self._borrando.append((indice, item))
                break

    def _grosor_pincel(self) -> float:
        """el grosor del trazo según el pincel activo, para el círculo guía."""
        if self.mode == "pixelate":
            return self.pixel_grosor
        if self.mode == "highlight":
            return max(10.0, self.ancho * 4)
        return self.ancho

    def mouseMoveEvent(self, e):
        punto = QPointF(e.position())
        self._cursor = punto
        # el círculo de tamaño sigue al cursor, guardado en coordenadas base
        # para que el zoom lo agrande junto con el trazo
        if self.mode in ("highlight", "pixelate") and not self._cap_activa:
            self._cursor_pincel = self._a_base(punto)
            self.update()

        if self._paneo is not None:
            delta = (self._paneo - punto) / self._zoom
            self._offset += delta
            self._limitar_offset()
            self._paneo = punto
            self._reubicar_editor()
            self.update()
            return

        if self._cap_activa:
            if self._cap_origen is not None:
                self._cap_sel = QRectF(self._cap_origen, punto).normalized()
            self.update()
            return

        if self.mode == "laser":
            ahora = time.monotonic()
            # con el mouse rápido los eventos llegan muy separados y la
            # estela salía como bolitas sueltas; rellenar el tramo con
            # puntos intermedios la vuelve una línea continua
            if self._estela:
                ultimo = self._estela[-1][0]
                delta = punto - ultimo
                distancia = (delta.x() ** 2 + delta.y() ** 2) ** 0.5
                pasos = int(distancia // 5)
                for i in range(1, pasos + 1):
                    self._estela.append((ultimo + delta * (i / (pasos + 1)), ahora))
            self._estela.append((QPointF(punto), ahora))
            self._reloj.start()
            self.update()
            return

        base = self._a_base(punto)
        if not self._arrastre:
            if self.mode == "select":
                self._cursor_seleccion(base)
            elif self.mode in ("zoom", "hand"):
                self.setCursor(Qt.OpenHandCursor if self._zoom > 1.0 else
                               (Qt.OpenHandCursor if self.mode == "hand" else Qt.ArrowCursor))
            return

        # shift endereza y proporciona; alt crece desde el centro, como en
        # los editores de adobe; funcionan al crear y al estirar cualquier
        # cosa: líneas, flechas, formas, imágenes
        # el evento trae los modificadores reales; la caché de la app
        # no se entera si shift ya venía presionado desde antes del clic
        mods = e.modifiers()
        shift = bool(mods & Qt.ShiftModifier)
        alt = bool(mods & Qt.AltModifier)

        modo = self._arrastre["modo"]
        if modo == "crear":
            item = self._arrastre["item"]
            origen = self._arrastre.get("origen")
            if isinstance(item, (an.BrushItem, an.PixelateItem)):
                if shift:
                    # con shift el trazo sale recto desde donde empezó
                    item.points = [QPointF(item.points[0]), QPointF(base)]
                else:
                    item.add_point(base)
            elif isinstance(item, an.LineItem):
                destino = an.snap_45(origen, base) if shift and origen else base
                item.p2 = destino
                if origen is not None:
                    item.p1 = (QPointF(2 * origen.x() - destino.x(),
                                       2 * origen.y() - destino.y())
                               if alt else QPointF(origen))
            elif isinstance(item, an.ShapeItem) and origen is not None:
                if alt:
                    espejo = QPointF(2 * origen.x() - base.x(), 2 * origen.y() - base.y())
                    rect = QRectF(espejo, base).normalized()
                    if shift:
                        lado = max(rect.width(), rect.height())
                        rect = QRectF(origen.x() - lado / 2, origen.y() - lado / 2, lado, lado)
                    item.rect = rect
                else:
                    item.rect = (an.cuadrar_rect(origen, base) if shift
                                 else QRectF(origen, base).normalized())
        elif modo == "mover":
            # el desplazamiento se calcula desde el punto de agarre y se
            # reaplica sobre la geometría inicial: así shift puede pegarlo
            # a un eje recto en cualquier momento del arrastre
            delta = base - self._arrastre["inicio"]
            if shift:
                delta = an.restringir_eje(delta)
            if abs(delta.x()) + abs(delta.y()) > 0.5:
                self._arrastre["movio"] = True
            for item, antes in self._arrastre.get("antes", []):
                an.restore(item, antes)
                item.move_by(delta.x(), delta.y())
        elif modo == "tirador":
            item = self._seleccion[0]
            indice = self._arrastre["indice"]
            if isinstance(item, an.TextItem) and "texto0" in self._arrastre:
                rect0, tam0 = self._arrastre["texto0"]
                an.escalar_texto(item, indice, base, rect0, tam0)
            elif isinstance(item, an.LineItem) and shift:
                fijo = item.p2 if indice == 0 else item.p1
                item.set_handle(indice, an.snap_45(fijo, base))
            else:
                item.set_handle(indice, base)
            if isinstance(item, an.ShapeItem):
                if shift and self._arrastre.get("aspecto"):
                    item.rect = an.ajustar_aspecto(item.rect, self._arrastre["aspecto"], indice)
                if alt and self._arrastre.get("centro") is not None:
                    item.rect.moveCenter(self._arrastre["centro"])
        elif modo == "banda":
            self._banda = QRectF(self._arrastre["origen"], base).normalized()
        elif modo == "borrar":
            self._borrar_en(base)
        self.update()

    def _cursor_seleccion(self, base: QPointF):
        tolerancia = (_LADO_TIRADOR + 4) / self._zoom
        if len(self._seleccion) == 1:
            for i, tirador in enumerate(self._seleccion[0].handles()):
                if (tirador - base).manhattanLength() <= tolerancia:
                    # la flechita de redimensión que apunta según el tirador
                    self.setCursor(an.cursor_tirador(self._seleccion[0], i))
                    return
        for item in reversed(self._items):
            if item.contains(base):
                # cursor normal sobre todo, texto incluido; el doble clic
                # ya se encarga de abrir la edición
                self.setCursor(Qt.ArrowCursor)
                return
        self.setCursor(Qt.ArrowCursor)

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.RightButton:
            self._paneo = None
            return
        if e.button() != Qt.LeftButton:
            return
        if self._paneo is not None:
            self._paneo = None
            if self.mode in ("zoom", "hand"):
                self.setCursor(Qt.OpenHandCursor if self._zoom > 1.0 or self.mode == "hand"
                               else Qt.ArrowCursor)
            return
        if self._cap_activa:
            self._cap_origen = None
            if self._cap_sel.width() >= 10 and self._cap_sel.height() >= 10:
                self._mostrar_botones_cap()
            self.update()
            return

        if not self._arrastre:
            return
        modo = self._arrastre["modo"]
        if modo == "crear":
            item = self._arrastre["item"]
            if isinstance(item, an.PixelateItem):
                item.editando = False
            if item.bounding().width() < 8 and item.bounding().height() < 8:
                if item in self._items:
                    self._items.remove(item)
            else:
                self._registrar(("agregar", [item]))
                # la figura, línea o flecha recién puesta queda
                # seleccionada y la herramienta pasa a V, lista para
                # acomodarla; el pincel y el pincel de ocultar se quedan
                # activos para seguir trazando
                if not isinstance(item, (an.BrushItem, an.PixelateItem)):
                    self._seleccion = [item]
                    self.selection_changed.emit()
                    self.mode_key_pressed.emit("select")
        elif modo in ("mover", "tirador"):
            # un duplicado ya quedó registrado como "agregar" al empezar,
            # su movimiento no necesita otro paso de deshacer
            if not self._arrastre.get("duplicado"):
                # el arrastre completo entra al historial como un solo paso:
                # ctrl+z devuelve el elemento a donde estaba
                cambio = [(item, antes, an.snapshot(item))
                          for item, antes in self._arrastre.get("antes", [])
                          if antes != an.snapshot(item)]
                if cambio:
                    self._registrar(("estado", cambio))
                # un clic quieto sobre el elemento ya seleccionado alterna
                # su ventanita de opciones: clic muestra, clic esconde
                elif self._arrastre.get("re_clic") and not self._arrastre.get("movio"):
                    self.item_reclicked.emit()
        elif modo == "banda":
            if self._banda is not None:
                self._seleccion = [i for i in self._items
                                   if self._banda.intersects(i.bounding())
                                   and not isinstance(i, an.PixelateItem)]
                self.selection_changed.emit()
            self._banda = None
        elif modo == "borrar":
            if self._borrando:
                self._registrar(("quitar", list(self._borrando)))
            self._borrando = []
        self._arrastre = None
        self.update()

    def leaveEvent(self, e):
        # el círculo del pincel no debe quedar dibujado si el mouse se fue
        if self._cursor_pincel is not None:
            self._cursor_pincel = None
            self.update()
        super().leaveEvent(e)

    def mouseDoubleClickEvent(self, e):
        # doble clic sobre un texto, con la herramienta de selección, lo
        # reabre para corregirlo
        if self.mode != "select" or self._cap_activa:
            return
        base = self._a_base(QPointF(e.position()))
        for item in reversed(self._items):
            if isinstance(item, an.TextItem) and item.contains(base):
                self._abrir_editor(base, existente=item)
                return

    # ------------------------------------------------------------------ #
    # teclado

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Escape:
            # esc va cediendo por capas: cierra el texto en edición, luego
            # el recorte, luego devuelve el zoom a la normalidad (lo
            # dibujado se queda), y recién con todo en reposo pregunta si
            # salir de la pizarra
            if self._editor is not None:
                # esc confirma el texto y lo deja seleccionado en V, en
                # lugar de tirarlo en silencio
                self._finalizar_texto()
            elif self._cap_activa:
                self._salir_captura()
            elif self._zoom > 1.001:
                self._zoom = 1.0
                self._offset = QPointF(0, 0)
                self.update()
            else:
                self.escape_pressed.emit()
        elif self._cap_activa and e.matches(QKeySequence.Copy):
            self._cap_copiar()
        elif self._cap_activa and e.matches(QKeySequence.Save):
            self._cap_guardar()
        elif e.matches(QKeySequence.Copy):
            self.copiar_todo()
        elif e.matches(QKeySequence.Save):
            self.guardar_todo()
        elif e.matches(QKeySequence.SelectAll):
            self.enter_capture()
        elif e.matches(QKeySequence.Undo):
            self.undo()
        elif e.matches(QKeySequence.Redo):
            self.redo()
        elif e.key() == Qt.Key_Delete and self._seleccion:
            quitados = [(self._items.index(i), i) for i in self._seleccion if i in self._items]
            for _, item in quitados:
                self._items.remove(item)
            self._seleccion = []
            self.selection_changed.emit()
            self._registrar(("quitar", quitados))
            self.update()
        elif e.matches(QKeySequence.Paste):
            imagen = QGuiApplication.clipboard().image()
            if not imagen.isNull():
                self.insert_image(imagen)
        elif e.key() in self._atajos and self._editor is None:
            self.mode_key_pressed.emit(self._atajos[e.key()])
        elif e.key() == Qt.Key_C and self._editor is None:
            self.clear_drawings()
        elif e.key() in (Qt.Key_Plus, Qt.Key_Equal):
            self.zoom_step(1.25)
        elif e.key() == Qt.Key_Minus:
            self.zoom_step(1 / 1.25)
        else:
            super().keyPressEvent(e)

    # ------------------------------------------------------------------ #
    # pintura

    def paintEvent(self, _):
        pintor = QPainter(self)
        pintor.setRenderHint(QPainter.Antialiasing)
        pintor.setRenderHint(QPainter.SmoothPixmapTransform)

        # imagen y dibujos comparten la transformación de la vista; así el
        # zoom acerca el contenido con todo lo dibujado encima
        pintor.save()
        pintor.scale(self._zoom, self._zoom)
        pintor.translate(-self._offset)
        pintor.drawImage(QRectF(0, 0, self.width(), self.height()), self._imagen)
        for item in self._items:
            an.paint_item(pintor, item)
        if self.mode == "select" and not self._cap_activa:
            self._pintar_seleccion(pintor)
        pintor.restore()

        # el círculo del pincel se pinta en coordenadas de pantalla, con el
        # radio ya escalado por el zoom, para que la línea quede fina
        if (self.mode in ("highlight", "pixelate") and not self._cap_activa
                and self._cursor_pincel is not None):
            centro = self._a_vista(self._cursor_pincel)
            an.pintar_circulo_pincel(pintor, centro, self._grosor_pincel() * self._zoom)

        if self._cap_activa:
            self._pintar_captura(pintor)
        elif self.mode == "laser":
            self._pintar_laser(pintor)

        if self._aviso is not None:
            self._pintar_aviso(pintor)

        # el recordatorio de teclas estorba durante el recorte; ahí manda
        # la misma pista que usa la captura de región
        if not self._cap_activa:
            self._pintar_pista(pintor)
        pintor.end()

    def _pintar_seleccion(self, pintor: QPainter):
        acento = QColor(theme.accent())
        # cada elemento seleccionado marca su contorno; el único además
        # muestra tiradores para estirar
        for item in self._seleccion:
            pluma = QPen(acento, 1.2 / self._zoom)
            pluma.setStyle(Qt.DashLine)
            pintor.setPen(pluma)
            pintor.setBrush(Qt.NoBrush)
            pintor.drawRect(item.bounding())
        if len(self._seleccion) == 1:
            pintor.setPen(QPen(acento, 1.2 / self._zoom))
            pintor.setBrush(QColor("#ffffff"))
            mitad = _LADO_TIRADOR / 2 / self._zoom
            for tirador in self._seleccion[0].handles():
                pintor.drawRect(QRectF(tirador.x() - mitad, tirador.y() - mitad,
                                       mitad * 2, mitad * 2))
        if self._banda is not None:
            tinta = QColor(acento)
            tinta.setAlpha(40)
            pintor.setPen(QPen(acento, 1 / self._zoom))
            pintor.setBrush(tinta)
            pintor.drawRect(self._banda)

    def _pintar_captura(self, pintor: QPainter):
        """el recorte con la misma cara que una captura de región: velo
        oscuro, borde de acento, tamaño real junto a la selección y la
        instrucción flotante arriba mientras no se ha arrastrado."""
        velo = QColor(0, 0, 0, 110)
        if self._cap_sel.isValid() and self._cap_sel.width() > 0:
            s = self._cap_sel
            pintor.fillRect(QRectF(0, 0, self.width(), s.top()), velo)
            pintor.fillRect(QRectF(0, s.bottom(), self.width(), self.height() - s.bottom()), velo)
            pintor.fillRect(QRectF(0, s.top(), s.left(), s.height()), velo)
            pintor.fillRect(QRectF(s.right(), s.top(), self.width() - s.right(), s.height()), velo)
            pintor.setPen(QPen(QColor(theme.accent()), 1.6))
            pintor.setBrush(Qt.NoBrush)
            pintor.drawRect(s)
            self._pintar_medidas_cap(pintor)
        else:
            pintor.fillRect(self.rect(), velo)
            self._pintar_chip(pintor, t("sel.hint"),
                              QPointF(self.width() / 2, 40), 10)

    def _pintar_medidas_cap(self, pintor: QPainter):
        """chip con los píxeles reales que va a medir el recorte; con zoom
        puesto, la zona de imagen es más chica que lo que se ve."""
        ancho = round(self._cap_sel.width() / self._zoom * self._dpr)
        alto = round(self._cap_sel.height() / self._zoom * self._dpr)
        y = self._cap_sel.top() - 18
        if y < 14:
            y = self._cap_sel.top() + 18
        self._pintar_chip(pintor, f"{ancho} × {alto}",
                          QPointF(self._cap_sel.left() + 40, y), 9)

    def _pintar_aviso(self, pintor: QPainter):
        """mensaje central que aparece y se apaga solo, con fundido."""
        texto, nacimiento, duracion = self._aviso
        edad = (time.monotonic() - nacimiento) / duracion
        alfa = 1.0 if edad < 0.6 else max(0.0, 1.0 - (edad - 0.6) / 0.4)
        pintor.setOpacity(alfa)
        principal = QGuiApplication.primaryScreen().geometry().translated(
            -self._offset_virtual.x(), -self._offset_virtual.y())
        self._pintar_chip(pintor, texto, QPointF(principal.center()), 12)
        pintor.setOpacity(1.0)

    def _pintar_chip(self, pintor: QPainter, texto: str, centro: QPointF, puntos: int):
        pintor.setFont(QFont("Segoe UI", puntos))
        medidas = pintor.fontMetrics().boundingRect(texto).adjusted(-10, -6, 10, 6)
        chip = QRectF(centro.x() - medidas.width() / 2, centro.y() - medidas.height() / 2,
                      medidas.width(), medidas.height())
        pintor.setPen(Qt.NoPen)
        pintor.setBrush(QColor(0, 0, 0, 170))
        pintor.drawRoundedRect(chip, 6, 6)
        pintor.setPen(QColor("#ffffff"))
        pintor.drawText(chip, Qt.AlignCenter, texto)

    def _pintar_laser(self, pintor: QPainter):
        """punto láser con halo y estela continua que muere sola.

        la estela se dibuja como segmentos unidos con puntas redondas, no
        como círculos sueltos: cada tramo pierde grosor y opacidad con la
        edad y el resultado es el barrido fluido de un láser real.
        """
        base = QColor(settings.get("laser_color", "#ff3b30"))
        radio = settings.get("laser_size", 14) / 2 + 2

        if settings.get("laser_trail", True) and self._estela:
            ahora = time.monotonic()
            puntos = self._estela + [(self._cursor, ahora)]
            for (p1, n1), (p2, _n2) in zip(puntos, puntos[1:]):
                edad = (ahora - n1) / _VIDA_ESTELA
                if edad >= 1.0:
                    continue
                tinta = QColor(base)
                tinta.setAlphaF(max(0.0, 0.45 * (1 - edad)))
                grosor = max(1.2, radio * 1.1 * (1 - edad * 0.75))
                pintor.setPen(QPen(tinta, grosor, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
                pintor.drawLine(p1, p2)

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

    def _pintar_pista(self, pintor: QPainter):
        """recordatorio de teclas en la esquina inferior izquierda del
        monitor principal; con dos pantallas, la esquina del escritorio
        combinado podía caer fuera de la vista del usuario."""
        texto = t("zoom.hint")
        pintor.setFont(QFont("Segoe UI", 9))
        medidas = pintor.fontMetrics().boundingRect(texto).adjusted(-10, -6, 10, 6)
        principal = QGuiApplication.primaryScreen().geometry().translated(
            -self._offset_virtual.x(), -self._offset_virtual.y())
        chip = QRectF(principal.left() + 16,
                      principal.bottom() - medidas.height() - 16,
                      medidas.width(), medidas.height())
        pintor.setPen(Qt.NoPen)
        pintor.setBrush(QColor(0, 0, 0, 150))
        pintor.drawRoundedRect(chip, 7, 7)
        pintor.setPen(QColor(255, 255, 255, 220))
        pintor.drawText(chip, Qt.AlignCenter, texto)


class _GlobalBridge(QObject):
    """trae los avisos del hilo de pynput al hilo de la interfaz."""
    tool = Signal(str)


class PresentationMode(QObject):
    """coordinador del modo: el panel manda, la pantalla pausada obedece.

    la pausa se crea recién cuando se activa una herramienta, con una foto
    fresca de ese momento; al despausar se descarta, así la próxima pausa
    muestra lo que de verdad esté en pantalla.
    """

    closed = Signal()
    copied = Signal(QImage)
    save_requested = Signal(QImage)

    def __init__(self):
        super().__init__()
        self.toolbar = FloatingToolbar()
        self.props = PropertiesPanel()
        self.overlay: _FreezeOverlay | None = None

        b = self.toolbar
        b.mode_changed.connect(self._cambiar_modo)
        b.shape_changed.connect(self._cambiar_forma)
        b.active_reclicked.connect(self._alternar_props)
        b.undo_clicked.connect(lambda: self._con_overlay(lambda o: o.undo(), crear=False))
        b.redo_clicked.connect(lambda: self._con_overlay(lambda o: o.redo(), crear=False))
        b.clear_clicked.connect(lambda: self._con_overlay(lambda o: o.clear_drawings(), crear=False))
        b.capture_clicked.connect(lambda: self._con_overlay(lambda o: o.enter_capture()))
        b.image_clicked.connect(lambda: self._con_overlay(lambda o: o.insert_image()))
        b.exit_clicked.connect(self.close)
        b.moved.connect(lambda: self.props.place_near(self.toolbar))

        self.props.prop_changed.connect(self._aplicar_prop)
        self.props.minimized.connect(self._alternar_props)

        # atajos globales del panel: viven exactamente mientras el modo
        # presentación esté abierto (panel visible o minimizado al chip) y
        # van con alt más la letra de cada herramienta; con alt de por
        # medio no interfieren al escribir en otras aplicaciones
        self._listener_global = None
        self._puente_global = _GlobalBridge()
        self._puente_global.tool.connect(self._bind_herramienta)
        self._armar_listener_global()

        # el panel abre en reposo: ninguna herramienta activa hasta que el
        # usuario elija una
        self.toolbar.clear_mode()
        self.toolbar.fade_in()

    # ------------------------------------------------------------------ #
    # atajos globales del panel

    def _armar_listener_global(self):
        from pynput import keyboard as _kb
        from src.ui.overlays.floating_toolbar import DEFAULT_KEYS, board_key
        if self._listener_global is not None:
            self._listener_global.stop()
            self._listener_global = None
        mapa = {}
        for modo in DEFAULT_KEYS:
            letra = board_key(modo).lower()
            if letra:
                mapa[f"<alt>+{letra}"] = (
                    lambda m=modo: self._puente_global.tool.emit(m))
        try:
            self._listener_global = _kb.GlobalHotKeys(mapa)
            self._listener_global.daemon = True
            self._listener_global.start()
        except Exception:
            self._listener_global = None

    def _bind_herramienta(self, modo: str):
        # el modo presentación se calla ante un juego u otra app a pantalla
        # completa con prioridad; un navegador a pantalla completa no cuenta
        from src.core.capture import bloquea_presentacion
        if bloquea_presentacion():
            return
        self.toolbar.toggle_mode(modo)

    def _con_overlay(self, accion, crear: bool = True):
        """ejecuta una acción sobre la pantalla pausada.

        si no hay pausa y la acción la necesita (capturar), primero se
        activa el zoom; deshacer o limpiar sin pausa no hacen nada.
        """
        if self.overlay is None:
            if not crear:
                return
            self.toolbar.toggle_mode("zoom")
            if self.overlay is None:
                return
        accion(self.overlay)

    def _aplicar_prop(self, nombre: str, valor):
        """un cambio en la ventanita de propiedades ajusta el valor por
        defecto de la pizarra y, si hay selección, también los elementos
        seleccionados, en vivo."""
        o = self.overlay
        if o is None:
            return
        # con el láser activo, color y grosor editan al puntero mismo y
        # quedan guardados en las preferencias
        if self.toolbar.current_mode() == "laser":
            if nombre == "color":
                settings.set("laser_color", QColor(valor).name())
            elif nombre == "width":
                settings.set("laser_size", int(valor))
            o.update()
            return
        # con el pincel de ocultar activo, sus tres controles editan lo suyo
        # y no el trazo de dibujo; el grosor viaja como "width"
        pixel_activo = (self.toolbar.current_mode() == "pixelate"
                        or any(isinstance(i, an.PixelateItem) for i in o._seleccion))
        if nombre == "pixel_mode":
            o.pixel_modo = valor
            o.update()
            return
        if nombre == "pixel_amount":
            o.pixel_cantidad = int(valor)
            o.update()
            return
        if nombre == "width" and pixel_activo:
            o.pixel_grosor = int(valor)
            o.update()
            return
        if nombre == "color":
            o.color = QColor(valor)
        elif nombre == "width":
            o.ancho = float(valor)
        elif nombre == "dash":
            o.dash = valor
        elif nombre == "cap_start":
            o.cap_inicio = valor
        elif nombre == "cap_end":
            o.cap_fin = valor
        elif nombre == "opacity":
            o.opacidad = float(valor)
        elif nombre == "font_family":
            o.fuente.setFamily(valor)
        elif nombre == "font_size":
            o.fuente.setPointSize(int(valor))
        elif nombre == "bold":
            o.fuente.setBold(bool(valor))
        elif nombre == "italic":
            o.fuente.setItalic(bool(valor))
        elif nombre == "underline":
            o.fuente.setUnderline(bool(valor))
        elif nombre == "strike":
            o.fuente.setStrikeOut(bool(valor))
        elif nombre == "letter_spacing":
            o.fuente.setLetterSpacing(QFont.AbsoluteSpacing, float(valor))
        elif nombre == "rotation":
            o.texto_rotacion = float(valor)
        elif nombre == "text_bg":
            o.texto_bg = valor
        elif nombre == "text_bg_color":
            o.texto_bg_color = QColor(valor)
        elif nombre == "shadow":
            o.texto_sombra = bool(valor)
        elif nombre == "outline":
            o.texto_contorno = bool(valor)

        for item in o._seleccion:
            if nombre == "color" and not isinstance(item, an.ImageItem):
                item.color = QColor(valor)
            elif nombre == "width":
                item.width = float(valor)
            elif nombre == "dash":
                item.dash = valor
            elif nombre in ("cap_start", "cap_end") and isinstance(item, an.LineItem):
                setattr(item, nombre, valor)
            elif nombre == "opacity":
                item.opacity = float(valor)
            elif isinstance(item, an.TextItem):
                if nombre == "font_family":
                    item.font.setFamily(valor)
                elif nombre == "font_size":
                    item.font.setPointSize(int(valor))
                elif nombre == "bold":
                    item.font.setBold(bool(valor))
                elif nombre == "italic":
                    item.font.setItalic(bool(valor))
                elif nombre == "underline":
                    item.font.setUnderline(bool(valor))
                elif nombre == "strike":
                    item.font.setStrikeOut(bool(valor))
                elif nombre == "letter_spacing":
                    item.font.setLetterSpacing(QFont.AbsoluteSpacing, float(valor))
                elif nombre == "rotation":
                    item.rotation = float(valor)
                elif nombre == "text_bg":
                    item.bg = valor
                elif nombre == "text_bg_color":
                    item.bg_color = QColor(valor)
                elif nombre == "shadow":
                    item.shadow = bool(valor)
                elif nombre == "outline":
                    item.outline = bool(valor)
        o.update()

    def _cambiar_forma(self, forma: str):
        self._forma = forma
        if self.overlay is not None:
            self.overlay.forma = forma

    def _alternar_props(self):
        """re-clic sobre la herramienta activa: esconde o trae de vuelta la
        ventanita de propiedades; el estado se recuerda hasta cambiar de
        herramienta o seleccionar algo."""
        if self.props.isVisible():
            self._props_apagadas = True
            self.props.hide()
        else:
            self._props_apagadas = False
            self._actualizar_props()

    def _actualizar_props(self):
        """decide si la ventanita se ve y con qué contenido.

        regla simple y estable: visible con cualquier herramienta de
        dibujo o texto, y en selección solo cuando hay algo seleccionado
        (con los valores de ese algo cargados). el re-clic de la
        herramienta activa la alterna; seleccionar algo la trae siempre.
        """
        modo = self.toolbar.current_mode()
        o = self.overlay
        # con el panel recogido en el chip, las propiedades tampoco asoman
        if self.toolbar._minimizado:
            self.props.hide()
            return
        if o is not None and o._seleccion:
            self._props_apagadas = False
        if getattr(self, "_props_apagadas", False):
            self.props.hide()
            return
        con_props = (modo in ("brush", "highlight", "line", "arrow", "shape",
                              "text", "laser", "pixelate")
                     or (modo == "select" and o is not None and bool(o._seleccion)))
        if not con_props or o is None:
            self.props.hide()
            return
        if modo == "laser":
            self.props.load_defaults({"color": settings.get("laser_color", "#ff3b30"),
                                      "width": settings.get("laser_size", 14)})
        elif len(o._seleccion) != 1:
            # el grosor visible es el del pincel de ocultar cuando esa
            # herramienta manda, si no el del trazo de dibujo
            grosor = o.pixel_grosor if modo == "pixelate" else o.ancho
            self.props.load_defaults({"color": o.color.name(), "width": grosor,
                                      "dash": o.dash, "cap_start": o.cap_inicio,
                                      "cap_end": o.cap_fin, "opacity": o.opacidad,
                                      "font": o.fuente, "pixel_mode": o.pixel_modo,
                                      "pixel_amount": o.pixel_cantidad})
        self.props.show_for(modo, o._seleccion)
        self.props.place_near(self.toolbar)
        if not self.props.isVisible():
            self.props.fade_in()

    def _confirmar_descarte(self) -> bool:
        """antes de despausar con dibujos hechos, se pregunta.

        el aviso trae su casilla de no volver a mostrar (desmarcada por
        defecto); si el usuario la marca, la advertencia se apaga y puede
        reactivarla en opciones, pestaña presentación.
        """
        o = self.overlay
        if o is None or not o._items:
            return True
        if not settings.get("confirm_discard_board", True):
            return True
        aviso = QMessageBox()
        aviso.setWindowTitle(t("zoom.discard_title"))
        aviso.setText(t("zoom.discard_q"))
        aviso.setIcon(QMessageBox.Warning)
        # sin esta bandera el aviso nacería detrás de la pantalla pausada,
        # que es siempre-adelante, y la app parecería colgada
        aviso.setWindowFlag(Qt.WindowStaysOnTopHint, True)
        descartar = aviso.addButton(t("zoom.discard_yes"), QMessageBox.DestructiveRole)
        aviso.addButton(t("tool.cancel"), QMessageBox.RejectRole)
        casilla = QCheckBox(t("zoom.discard_dontask"))
        aviso.setCheckBox(casilla)
        aviso.exec()
        if casilla.isChecked():
            settings.set("confirm_discard_board", False)
        return aviso.clickedButton() is descartar

    def _cambiar_modo(self, modo: str):
        # cambiar de herramienta limpia el escondido manual de propiedades
        self._props_apagadas = False
        if modo == "none":
            if not self._confirmar_descarte():
                # el usuario se arrepintió: el botón de la herramienta
                # vuelve a marcarse y la pausa sigue tal cual
                if self.overlay is not None:
                    self.toolbar.set_checked_silent(self.overlay.mode)
                return
            self._despausar()
            return
        if self.overlay is None:
            # los paneles están excluidos de la captura a nivel de
            # windows, así que la foto congelada sale limpia sin tener
            # que esconder nada: cero parpadeos
            self.overlay = _FreezeOverlay()
            self.overlay.forma = getattr(self, "_forma", "rect")
            self.overlay.escape_pressed.connect(self._escape)
            self.overlay.mode_key_pressed.connect(self.toolbar.toggle_mode)
            self.overlay.selection_changed.connect(self._actualizar_props)
            self.overlay.item_reclicked.connect(self._alternar_props)
            self.overlay.window_activated.connect(self._subir_paneles)
            self.overlay.copied.connect(self.copied)
            self.overlay.save_requested.connect(self.save_requested)
            self.overlay.show()
        self.overlay.set_mode(modo)
        self.overlay.activateWindow()
        self.overlay.setFocus()
        self._actualizar_props()
        self._subir_paneles()

    def _subir_paneles(self):
        """los flotantes siempre por encima de la pantalla pausada.

        se llama en cada activación de la pausa: sin esto, el primer clic
        para dibujar subía el overlay y dejaba tapados el panel, las
        propiedades y hasta el chip de restaurar. con el panel minimizado
        solo se sube el chip; nunca se resucita el panel ni las propiedades.
        """
        if self.toolbar._minimizado:
            chip = self.toolbar._chip
            if chip is not None and chip.isVisible():
                chip.raise_()
            return
        self.toolbar.raise_()
        if self.props.isVisible():
            self.props.raise_()

    def _despausar(self):
        self.props.hide()
        if self.overlay is not None:
            overlay = self.overlay
            self.overlay = None
            overlay.close()

    def _escape(self):
        if not self._confirmar_descarte():
            return
        self.toolbar.clear_mode()
        self._despausar()

    def close(self):
        if not self._confirmar_descarte():
            return
        if self._listener_global is not None:
            self._listener_global.stop()
            self._listener_global = None
        self._despausar()
        self.props.close()
        self.toolbar.close()
        self.closed.emit()
