"""ventana de opciones, organizada en pestañas como la referencia de itop.

general reúne idioma, tema y comportamiento; captura define la carpeta de
guardado; formato elige entre png y jpeg con su calidad; y acceso rápido
lista los atajos globales, cada uno editable con solo presionar la
combinación nueva. nada se toca de verdad hasta apretar guardar.
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (QCheckBox, QColorDialog, QComboBox, QDialog,
                               QFileDialog, QFormLayout, QGridLayout,
                               QHBoxLayout, QKeySequenceEdit, QLabel,
                               QLineEdit, QPushButton, QSlider, QTabWidget,
                               QVBoxLayout, QWidget)

from src.config import paths, shortcuts
from src.config.settings import settings
from src.i18n.translator import LANGUAGES, t, translator
from src.ui.themes.theme_manager import theme
from src.utils import autostart


class SettingsDialog(QDialog):
    # aviso para que la app recargue los atajos globales tras un cambio
    shortcuts_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(t("set.title"))
        # ancho suficiente para que las cinco pestañas entren sin que la
        # barra muestre sus flechas de desplazamiento, que se ven mal
        self.setMinimumWidth(560)

        columna = QVBoxLayout(self)
        columna.setContentsMargins(16, 14, 16, 14)
        columna.setSpacing(12)

        pestanas = QTabWidget()
        pestanas.addTab(self._tab_general(), t("set.general"))
        pestanas.addTab(self._tab_captura(), t("set.capture"))
        pestanas.addTab(self._tab_formato(), t("set.format"))
        pestanas.addTab(self._tab_presentacion(), t("set.presentation"))
        pestanas.addTab(self._tab_atajos(), t("set.shortcuts"))
        columna.addWidget(pestanas)

        botones = QHBoxLayout()
        botones.addStretch()
        cancelar = QPushButton(t("set.cancel"))
        guardar = QPushButton(t("set.save"))
        guardar.setObjectName("primario")
        botones.addWidget(cancelar)
        botones.addWidget(guardar)
        columna.addLayout(botones)

        cancelar.clicked.connect(self.reject)
        guardar.clicked.connect(self._guardar)

    # ------------------------------------------------------------------ #

    def _tab_general(self) -> QWidget:
        tab = QWidget()
        forma = QFormLayout(tab)
        forma.setContentsMargins(8, 14, 8, 8)
        forma.setSpacing(12)

        self._idioma = QComboBox()
        for codigo, (nombre, pais) in LANGUAGES.items():
            self._idioma.addItem(f"{nombre}  ·  {pais}", codigo)
            if codigo == translator.language:
                self._idioma.setCurrentIndex(self._idioma.count() - 1)
        forma.addRow(t("set.language"), self._idioma)

        self._tema = QComboBox()
        self._tema.addItem(t("set.theme_light"), "light")
        self._tema.addItem(t("set.theme_dark"), "dark")
        self._tema.setCurrentIndex(0 if theme.theme == "light" else 1)
        forma.addRow(t("set.theme"), self._tema)

        self._autostart = QCheckBox(t("set.autostart"))
        self._autostart.setChecked(settings.get("autostart", False))
        forma.addRow(self._autostart)

        self._en_bandeja = QCheckBox(t("set.start_tray"))
        self._en_bandeja.setChecked(settings.get("start_in_tray", False))
        forma.addRow(self._en_bandeja)

        self._ocultar = QCheckBox(t("set.hide_main"))
        self._ocultar.setChecked(settings.get("hide_main_on_capture", True))
        forma.addRow(self._ocultar)

        self._avisos = QCheckBox(t("set.notify"))
        self._avisos.setChecked(settings.get("show_notifications", True))
        forma.addRow(self._avisos)
        return tab

    def _tab_captura(self) -> QWidget:
        tab = QWidget()
        forma = QFormLayout(tab)
        forma.setContentsMargins(8, 14, 8, 8)
        forma.setSpacing(12)

        fila = QHBoxLayout()
        self._carpeta = QLineEdit(settings.get("save_dir") or paths.default_captures_dir())
        self._carpeta.setReadOnly(True)
        examinar = QPushButton(t("set.browse"))
        examinar.clicked.connect(self._elegir_carpeta)
        fila.addWidget(self._carpeta)
        fila.addWidget(examinar)
        forma.addRow(t("set.savedir"), fila)

        self._abrir_carpeta = QCheckBox(t("set.open_folder"))
        self._abrir_carpeta.setChecked(settings.get("open_folder_after_save", False))
        forma.addRow(self._abrir_carpeta)
        return tab

    def _tab_formato(self) -> QWidget:
        tab = QWidget()
        forma = QFormLayout(tab)
        forma.setContentsMargins(8, 14, 8, 8)
        forma.setSpacing(12)

        # todos los formatos que este equipo puede escribir, tal cual
        from src.core import storage
        self._formato = QComboBox()
        for clave in storage.available_formats():
            self._formato.addItem(clave.upper(), clave)
        indice = self._formato.findData(settings.get("image_format", "png"))
        self._formato.setCurrentIndex(max(0, indice))
        forma.addRow(t("set.format_save"), self._formato)

        fila = QHBoxLayout()
        self._calidad = QSlider(Qt.Horizontal)
        self._calidad.setRange(40, 100)
        self._calidad.setValue(settings.get("jpeg_quality", 90))
        self._valor_calidad = QLabel(f"{self._calidad.value()}%")
        self._valor_calidad.setFixedWidth(42)
        self._calidad.valueChanged.connect(lambda v: self._valor_calidad.setText(f"{v}%"))
        fila.addWidget(self._calidad)
        fila.addWidget(self._valor_calidad)
        forma.addRow(t("set.quality"), fila)

        # la calidad solo aplica a los formatos con compresión con pérdida
        def alternar():
            self._calidad.setEnabled(storage.is_lossy(self._formato.currentData()))
        self._formato.currentIndexChanged.connect(lambda _: alternar())
        alternar()
        return tab

    def _tab_presentacion(self) -> QWidget:
        tab = QWidget()
        forma = QFormLayout(tab)
        forma.setContentsMargins(8, 14, 8, 8)
        forma.setSpacing(12)

        # el color del láser se muestra como un botón teñido; el clic abre
        # el selector del sistema
        self._laser_color = QColor(settings.get("laser_color", "#ff3b30"))
        self._boton_laser = QPushButton()
        self._boton_laser.setFixedSize(64, 28)
        self._pintar_boton_laser()
        self._boton_laser.clicked.connect(self._elegir_color_laser)
        forma.addRow(t("set.laser_color"), self._boton_laser)

        fila = QHBoxLayout()
        self._laser_tamano = QSlider(Qt.Horizontal)
        self._laser_tamano.setRange(6, 40)
        self._laser_tamano.setValue(settings.get("laser_size", 14))
        self._valor_laser = QLabel(f"{self._laser_tamano.value()} px")
        self._valor_laser.setFixedWidth(48)
        self._laser_tamano.valueChanged.connect(lambda v: self._valor_laser.setText(f"{v} px"))
        fila.addWidget(self._laser_tamano)
        fila.addWidget(self._valor_laser)
        forma.addRow(t("set.laser_size"), fila)

        self._laser_estela = QCheckBox(t("set.laser_trail"))
        self._laser_estela.setChecked(settings.get("laser_trail", True))
        forma.addRow(self._laser_estela)

        self._confirmar_descarte = QCheckBox(t("set.confirm_discard"))
        self._confirmar_descarte.setChecked(settings.get("confirm_discard_board", True))
        forma.addRow(self._confirmar_descarte)

        # las letras de las herramientas del panel lateral, cada una con el
        # nombre de su herramienta al lado para que se entienda qué es qué
        titulo_teclas = QLabel(t("set.board_keys"))
        titulo_teclas.setObjectName("secundario")
        forma.addRow(titulo_teclas)
        from src.ui.overlays.floating_toolbar import DEFAULT_KEYS, board_key
        from src.ui.widgets.icons import icon as icono_svg
        from src.ui.themes.theme_manager import theme as tema
        iconos = {"zoom": "zoom", "select": "select", "hand": "hand",
                  "laser": "laser", "brush": "brush", "highlight": "highlighter",
                  "line": "line", "arrow": "arrow", "shape": "shape-rect",
                  "eraser": "eraser", "text": "text"}
        nombres = {"zoom": t("zoom.live"), "select": t("tool.select"),
                   "hand": t("zoom.hand"), "laser": t("zoom.laser"),
                   "brush": t("zoom.brush"), "highlight": t("zoom.highlight"),
                   "line": t("tool.line"), "arrow": t("tool.arrow"),
                   "shape": t("tool.shapes"), "eraser": t("tool.eraser"),
                   "text": t("tool.text")}
        rejilla = QGridLayout()
        rejilla.setHorizontalSpacing(10)
        rejilla.setVerticalSpacing(6)
        self._teclas_panel: dict[str, QLineEdit] = {}
        for i, modo in enumerate(DEFAULT_KEYS):
            fila_g, col = divmod(i, 2)
            simbolo = QLabel()
            simbolo.setPixmap(icono_svg(iconos[modo], tema.icon_color()).pixmap(16, 16))
            etiqueta = QLabel(nombres[modo].split(",")[0])
            campo = QLineEdit(board_key(modo))
            campo.setMaxLength(1)
            campo.setFixedWidth(34)
            campo.setAlignment(Qt.AlignCenter)
            self._teclas_panel[modo] = campo
            base = col * 3
            rejilla.addWidget(simbolo, fila_g, base)
            rejilla.addWidget(etiqueta, fila_g, base + 1)
            rejilla.addWidget(campo, fila_g, base + 2)
        rejilla.setColumnStretch(1, 1)
        rejilla.setColumnStretch(4, 1)
        forma.addRow(rejilla)
        return tab

    def _pintar_boton_laser(self):
        self._boton_laser.setStyleSheet(
            f"background: {self._laser_color.name()}; border-radius: 8px; border: 1px solid rgba(0,0,0,40);")

    def _elegir_color_laser(self):
        color = QColorDialog.getColor(self._laser_color, self)
        if color.isValid():
            self._laser_color = color
            self._pintar_boton_laser()

    def _tab_atajos(self) -> QWidget:
        tab = QWidget()
        forma = QFormLayout(tab)
        forma.setContentsMargins(8, 14, 8, 8)
        forma.setSpacing(10)

        etiquetas = {
            "capture_region": t("set.sc_region"),
            "capture_fullscreen": t("set.sc_full"),
            "capture_window": t("set.sc_window"),
            "capture_scroll": t("set.sc_scroll"),
            "zoom_mode": t("set.sc_zoom"),
            "toggle_panel": t("set.sc_panel"),
        }
        self._editores: dict[str, QKeySequenceEdit] = {}
        for accion, etiqueta in etiquetas.items():
            editor = QKeySequenceEdit()
            # el atajo guardado tipo "alt+a" se convierte a la forma que qt
            # entiende, "Alt+A", pieza por pieza
            combinacion = "+".join(p.capitalize() for p in shortcuts.get(accion).split("+"))
            editor.setKeySequence(combinacion)
            self._editores[accion] = editor
            forma.addRow(etiqueta, editor)
        return tab

    # ------------------------------------------------------------------ #

    def _elegir_carpeta(self):
        carpeta = QFileDialog.getExistingDirectory(self, t("dlg.folder_title"), self._carpeta.text())
        if carpeta:
            self._carpeta.setText(carpeta)

    def _guardar(self):
        settings.set("hide_main_on_capture", self._ocultar.isChecked())
        settings.set("show_notifications", self._avisos.isChecked())
        settings.set("start_in_tray", self._en_bandeja.isChecked())
        settings.set("open_folder_after_save", self._abrir_carpeta.isChecked())
        settings.set("confirm_discard_board", self._confirmar_descarte.isChecked())
        settings.set("save_dir", self._carpeta.text())
        settings.set("image_format", self._formato.currentData())
        settings.set("jpeg_quality", self._calidad.value())
        settings.set("laser_color", self._laser_color.name())
        settings.set("laser_size", self._laser_tamano.value())
        settings.set("laser_trail", self._laser_estela.isChecked())

        # solo letras válidas y sin repetir; una vacía o duplicada vuelve
        # a su valor de fábrica
        letras = {}
        usadas = set()
        for modo, campo in self._teclas_panel.items():
            letra = campo.text().strip().upper()
            if letra.isalpha() and letra not in usadas:
                letras[modo] = letra
                usadas.add(letra)
        settings.set("board_keys", letras)

        settings.set("autostart", self._autostart.isChecked())
        autostart.sync(self._autostart.isChecked())

        hubo_cambio_atajos = False
        for accion, editor in self._editores.items():
            texto = editor.keySequence().toString().lower()
            if texto and texto != shortcuts.get(accion):
                shortcuts.set_shortcut(accion, texto)
                hubo_cambio_atajos = True

        # idioma y tema van al final porque disparan el repintado general
        translator.set_language(self._idioma.currentData())
        theme.set_theme(self._tema.currentData())

        if hubo_cambio_atajos:
            self.shortcuts_changed.emit()
        self.accept()
