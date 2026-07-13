"""orquestación de toda la aplicación.

acá se conecta cada pieza con las demás: los atajos globales con las
capturas, el panel con los diálogos, los overlays con el portapapeles y el
guardado. las ventanas no se conocen entre sí; todas hablan por señales y
este módulo decide qué pasa con cada una.
"""

import os
import sys

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
from src.utils import autostart
from src.utils.hotkeys import HotkeyManager

# pequeña pausa entre ocultar el panel y fotografiar la pantalla, para que
# windows alcance a quitarlo de la imagen
_ESPERA_OCULTAR = 180


class ScreenshotApp(QObject):
    def __init__(self):
        super().__init__()
        self._overlay = None          # overlay de captura activo (región, scroll)
        self._presentacion = None     # el modo presentación, que convive aparte
        self._editor = None           # editor de la captura larga, si está abierto
        self._panel_estaba_visible = False

        self.window = MainWindow()
        self.tray = TrayIcon(self)
        self.hotkeys = HotkeyManager()

        self._conectar_panel()
        self._conectar_bandeja()
        self._conectar_atajos()

        # si el registro de arranque automático sigue apuntando a una versión
        # vieja del comando, se refresca para que lleve la bandera de bandeja
        if settings.get("autostart", False):
            autostart.enable()

        self.tray.show()
        # arrancar oculto en la bandeja cuando lo lanzó windows al encender
        # (viene con la bandera) o cuando el usuario lo pidió en opciones; el
        # pin no influye, esto solo decide si el panel se muestra o no
        arranque_bandeja = (autostart.ARG_BANDEJA in sys.argv
                            or settings.get("start_in_tray", False))
        if not arranque_bandeja:
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
        w.minimized_changed.connect(self._sincronizar_minimizado)

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
        # el hide previo dispara el guardado de la posición del panel,
        # así la próxima sesión abre donde el usuario lo dejó
        self.window.hide()
        self.hotkeys.stop()
        self.tray.hide()
        QApplication.quit()

    def _sincronizar_minimizado(self, minimizada: bool):
        """el panel lateral acompaña la minimización del principal.

        al minimizar la app se ocultan ambos paneles, salvo el que tenga el
        pin puesto para quedarse siempre adelante.
        """
        modo = self._presentacion
        if modo is None:
            return
        if minimizada:
            if not modo.toolbar.is_pinned() and modo.toolbar.isVisible():
                modo.toolbar.hide()
                self._lateral_escondido = True
        elif getattr(self, "_lateral_escondido", False):
            # respeta el chip: si el usuario había recogido el panel, no se
            # resucita al volver de minimizar la ventana principal
            modo.toolbar.mostrar_si_procede()
            self._lateral_escondido = False

    # ------------------------------------------------------------------ #
    # capturas

    def _ocultar_y(self, continuar):
        """prepara la pantalla para fotografiar y después ejecuta.

        cuando windows soporta la exclusión de captura, el panel puede
        quedarse donde está: no va a salir en la foto de todos modos. en
        sistemas viejos se esconde con una pausa para que el escritorio
        alcance a repintarse sin él.
        """
        # una captura a la vez; el panel de presentación abierto no
        # estorba, salvo que la pantalla esté pausada en la pizarra
        pausado = self._presentacion is not None and self._presentacion.overlay is not None
        if self._overlay is not None or pausado:
            return
        # se recuerda la ventana en la que estaba el usuario para devolverle
        # el foco cuando termine con la captura
        self._ventana_previa = capture.foreground_window()
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
        # el foco regresa a la aplicación previa (el navegador, un editor),
        # de modo que el usuario siga donde estaba sin un clic extra
        capture.restore_foreground(getattr(self, "_ventana_previa", None))
        self._ventana_previa = None

    def iniciar_captura_region(self):
        self._ocultar_y(self._abrir_overlay_seleccion)

    def _abrir_overlay_seleccion(self, preset=None):
        overlay = SelectionOverlay(preset)
        overlay.copied.connect(self._copiar_imagen)
        overlay.save_requested.connect(self._guardar_imagen)
        overlay.closed.connect(self._restaurar_panel)
        overlay.show()
        overlay.activateWindow()
        overlay.setFocus()
        self._overlay = overlay

    def capturar_pantalla_completa(self):
        """el mismo editor de siempre, con toda la pantalla ya seleccionada."""
        self._ocultar_y(lambda: self._abrir_overlay_seleccion("full"))

    def capturar_ventana(self):
        """el editor con la ventana activa preseleccionada.

        el rectángulo se lee antes de abrir el overlay, porque al abrirse
        el foco pasa a ser nuestro y la ventana activa cambiaría.
        """
        zona = capture.active_window_rect()
        self._ocultar_y(lambda: self._abrir_overlay_seleccion(zona or "full"))

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

        el modo vive en su propia referencia y convive con las capturas:
        con el panel abierto se puede seguir capturando desde los botones,
        y solo la pantalla pausada bloquea momentáneamente.
        """
        if self._presentacion is not None:
            self._presentacion.close()
            return
        # mientras el modo presentación viva, mandan sus atajos alt+letra;
        # los globales de captura se apagan para que alt+s o alt+z no
        # disparen dos cosas a la vez, y vuelven al cerrar el panel
        self.hotkeys.stop()
        modo = PresentationMode()
        modo.closed.connect(self._cerrar_presentacion)
        # las capturas hechas desde la pantalla pausada siguen el mismo
        # camino que cualquier otra: portapapeles o diálogo de guardado
        modo.copied.connect(self._copiar_imagen)
        modo.save_requested.connect(self._guardar_imagen)
        self._presentacion = modo

    def _cerrar_presentacion(self):
        self._presentacion = None
        self.hotkeys.restart()

    # ------------------------------------------------------------------ #
    # portapapeles y guardado

    def _copiar_imagen(self, imagen, aviso: str = "notify.copied"):
        if clipboard.copy_image(imagen):
            notify(t(aviso), "copy")

    def _guardar_imagen(self, imagen):
        """diálogo de guardar que arranca en la última carpeta usada.

        todos los formatos disponibles van en el desplegable del diálogo,
        con el formato preferido de opciones como primera opción.
        """
        disponibles = storage.available_formats()
        preferido = settings.get("image_format", "png")
        orden = ([preferido] if preferido in disponibles else []) + \
            [f for f in disponibles if f != preferido]
        filtros = ";;".join(f"{clave.upper()} (*.{disponibles[clave][0]})" for clave in orden)
        ruta, _ = QFileDialog.getSaveFileName(None, t("dlg.save_title"),
                                              storage.suggested_path(), filtros)
        if not ruta:
            return
        if storage.save_image(imagen, ruta):
            notify(t("notify.saved", ruta=os.path.basename(ruta)), "save")
            # si el usuario lo pidió en opciones, el explorador se abre
            # señalando el archivo recién guardado
            if settings.get("open_folder_after_save", False):
                import subprocess
                subprocess.Popen(["explorer", "/select,", os.path.normpath(ruta)])
        else:
            notify(t("notify.save_error"), "close")

    # ------------------------------------------------------------------ #
    # diálogos

    def abrir_opciones(self):
        """mientras opciones esté abierto, los atajos globales duermen.

        así escribir una combinación en el editor de atajos no dispara
        una captura de verdad; al cerrar, el registro se rearma leyendo
        la configuración fresca, cambios incluidos.
        """
        self.hotkeys.stop()
        dialogo = SettingsDialog(self.window)
        try:
            dialogo.exec()
        finally:
            self.hotkeys.restart()
            self.window.refresh_tooltips()

    def _comprobar_actualizaciones(self):
        dialogo = AboutDialog(self.window)
        dialogo.show()
        dialogo._comprobar()
