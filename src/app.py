"""orquestación de toda la aplicación.

acá se conecta cada pieza con las demás: los atajos globales con las
capturas, el panel con los diálogos, los overlays con el portapapeles y el
guardado. las ventanas no se conocen entre sí; todas hablan por señales y
este módulo decide qué pasa con cada una.
"""

import os

from PySide6.QtCore import QObject, QTimer
from PySide6.QtWidgets import QApplication, QFileDialog

from src.config import shortcuts
from src.config.settings import settings
from src.core import capture, clipboard, storage
from src.i18n.translator import t
from src.ui import scroll_capture_window
from src.ui.dialogs.about_dialog import AboutDialog
from src.ui.dialogs.language_dialog import LanguageDialog
from src.ui.dialogs.manual_dialog import ManualDialog
from src.ui.dialogs.settings_dialog import SettingsDialog
from src.ui.editor_window import EditorWindow
from src.ui.main_window import MainWindow
from src.ui.notifications import notify
from src.ui.overlays.selection_overlay import SelectionOverlay
from src.ui.overlays.zoom_overlay import PresentationMode
from src.ui.tray_icon import TrayIcon
from src.utils.hotkeys import HotkeyManager

# pequeña pausa entre ocultar el panel y fotografiar la pantalla, para que
# windows alcance a quitarlo de la imagen
_ESPERA_OCULTAR = 180


class ScreenshotApp(QObject):
    def __init__(self):
        super().__init__()
        self._overlay = None          # referencia viva al overlay activo
        self._editor = None           # editor de la captura larga, si está abierto
        self._panel_estaba_visible = False

        self.window = MainWindow()
        self.tray = TrayIcon(self)
        self.hotkeys = HotkeyManager()

        self._conectar_panel()
        self._conectar_bandeja()
        self._conectar_atajos()

        self.tray.show()
        if not settings.get("start_in_tray", False):
            self.window.show()

        # el intento de excluir el panel de las capturas casi siempre va a
        # fallar: windows no acepta la exclusión en ventanas translúcidas
        # como esta. se intenta igual por si algún día el panel deja de
        # serlo; mientras devuelva False, el ocultamiento clásico manda
        self._panel_invisible_en_capturas = capture.exclude_from_capture(self.window)

        self.hotkeys.start()

    # ------------------------------------------------------------------ #
    # cableado

    def _conectar_panel(self):
        w = self.window
        w.capture_region.connect(self.iniciar_captura_region)
        w.capture_fullscreen.connect(self.capturar_pantalla_completa)
        w.capture_window.connect(self.capturar_ventana)
        w.capture_scroll.connect(self.iniciar_captura_scroll)
        w.zoom_mode.connect(self.abrir_modo_zoom)
        w.options_requested.connect(self.abrir_opciones)
        w.manual_requested.connect(lambda: ManualDialog(self.window).exec())
        w.language_requested.connect(lambda: LanguageDialog(self.window).exec())
        w.about_requested.connect(lambda: AboutDialog(self.window).exec())
        w.updates_requested.connect(self._comprobar_actualizaciones)
        w.quit_requested.connect(self.salir)

    def _conectar_bandeja(self):
        self.tray.show_requested.connect(self.mostrar_panel)
        self.tray.capture_requested.connect(self.iniciar_captura_region)
        self.tray.quit_requested.connect(self.salir)

    def _conectar_atajos(self):
        h = self.hotkeys
        h.capture_region.connect(self.iniciar_captura_region)
        h.capture_fullscreen.connect(self.capturar_pantalla_completa)
        h.capture_window.connect(self.capturar_ventana)
        h.capture_scroll.connect(self.iniciar_captura_scroll)
        h.zoom_mode.connect(self.abrir_modo_zoom)
        h.toggle_panel.connect(self.alternar_panel)

    # ------------------------------------------------------------------ #
    # panel

    def mostrar_panel(self):
        self.window.show()
        self.window.raise_()
        self.window.activateWindow()

    def alternar_panel(self):
        if self.window.isVisible():
            self.window.hide()
        else:
            self.mostrar_panel()

    def salir(self):
        self.hotkeys.stop()
        self.tray.hide()
        QApplication.quit()

    # ------------------------------------------------------------------ #
    # capturas

    def _ocultar_y(self, continuar):
        """prepara la pantalla para fotografiar y después ejecuta.

        cuando windows soporta la exclusión de captura, el panel puede
        quedarse donde está: no va a salir en la foto de todos modos. en
        sistemas viejos se esconde con una pausa para que el escritorio
        alcance a repintarse sin él.
        """
        if self._overlay is not None:
            return
        self._panel_estaba_visible = self.window.isVisible()
        debe_ocultar = (settings.get("hide_main_on_capture", True)
                        and self._panel_estaba_visible
                        and not self._panel_invisible_en_capturas)
        if debe_ocultar:
            self.window.hide()
            QTimer.singleShot(_ESPERA_OCULTAR, continuar)
        else:
            continuar()

    def _restaurar_panel(self):
        self._overlay = None
        if self._panel_estaba_visible and not self.window.isVisible():
            self.window.show()

    def iniciar_captura_region(self):
        self._ocultar_y(self._abrir_overlay_seleccion)

    def _abrir_overlay_seleccion(self):
        overlay = SelectionOverlay()
        overlay.copied.connect(self._copiar_imagen)
        overlay.save_requested.connect(self._guardar_imagen)
        overlay.closed.connect(self._restaurar_panel)
        overlay.show()
        overlay.activateWindow()
        overlay.setFocus()
        self._overlay = overlay

    def capturar_pantalla_completa(self):
        self._ocultar_y(lambda: self._captura_directa(capture.grab_virtual_screen()))

    def capturar_ventana(self):
        self._ocultar_y(lambda: self._captura_directa(capture.grab_active_window()))

    def _captura_directa(self, imagen):
        """las capturas sin selección van directo al portapapeles."""
        self._copiar_imagen(imagen)
        self._restaurar_panel()

    def iniciar_captura_scroll(self):
        self._ocultar_y(self._abrir_captura_scroll)

    def _abrir_captura_scroll(self):
        self._overlay = scroll_capture_window.pick_region_and_start(
            self._terminar_scroll, self._restaurar_panel)

    def _terminar_scroll(self, imagen):
        """la captura larga pasa al editor, igual que una captura normal.

        ahí el usuario anota, mueve, redimensiona y decide si copia o
        guarda; el editor avisa por señales y los flujos son los mismos.
        """
        self._restaurar_panel()
        editor = EditorWindow(imagen)
        editor.copied.connect(self._copiar_imagen)
        editor.save_requested.connect(self._guardar_imagen)
        editor.closed.connect(lambda: setattr(self, "_editor", None))
        self._editor = editor
        editor.show()
        editor.raise_()
        editor.activateWindow()

    def abrir_modo_zoom(self):
        """abre o cierra el panel de presentación; el mismo atajo alterna.

        la pantalla no se congela: el panel lateral flota sobre el trabajo
        normal y las herramientas se activan solo cuando se necesitan.
        """
        if isinstance(self._overlay, PresentationMode):
            self._overlay.close()
            return
        if self._overlay is not None:
            return
        self._panel_estaba_visible = self.window.isVisible()
        modo = PresentationMode()
        modo.closed.connect(self._restaurar_panel)
        self._overlay = modo

    # ------------------------------------------------------------------ #
    # portapapeles y guardado

    def _copiar_imagen(self, imagen, aviso: str = "notify.copied"):
        if clipboard.copy_image(imagen):
            notify(t(aviso), "copy")

    def _guardar_imagen(self, imagen):
        """diálogo de guardar que arranca en la última carpeta usada."""
        filtros = f'{t("dlg.filter_png")};;{t("dlg.filter_jpg")}'
        if settings.get("image_format") == "jpeg":
            filtros = f'{t("dlg.filter_jpg")};;{t("dlg.filter_png")}'
        ruta, _ = QFileDialog.getSaveFileName(None, t("dlg.save_title"),
                                              storage.suggested_path(), filtros)
        if not ruta:
            return
        if storage.save_image(imagen, ruta):
            notify(t("notify.saved", ruta=os.path.basename(ruta)), "save")
        else:
            notify(t("notify.save_error"), "close")

    # ------------------------------------------------------------------ #
    # diálogos

    def abrir_opciones(self):
        dialogo = SettingsDialog(self.window)
        dialogo.shortcuts_changed.connect(self.hotkeys.restart)
        dialogo.shortcuts_changed.connect(self.window.refresh_tooltips)
        dialogo.exec()
        self.window.refresh_tooltips()

    def _comprobar_actualizaciones(self):
        dialogo = AboutDialog(self.window)
        dialogo.show()
        dialogo._comprobar()
