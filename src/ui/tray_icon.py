"""ícono en la bandeja del sistema, el que mantiene viva la app.

cerrar la ventana principal no termina el programa: queda acá, listo para
los atajos globales. el clic izquierdo trae el panel de vuelta y el menú
contextual ofrece lo esencial, incluida la única forma real de salir.
"""

import os

from PySide6.QtCore import Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QMenu, QSystemTrayIcon

from src import APP_NAME, APP_VERSION
from src.config import paths
from src.i18n.translator import t, translator


class TrayIcon(QSystemTrayIcon):
    show_requested = Signal()
    capture_requested = Signal()
    quit_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setIcon(QIcon(paths.resource_path(os.path.join("assets", "logo", "logo-circle.png"))))
        # el tooltip lleva el número de versión, así se ve de un vistazo cuál
        # tienes instalada al pasar el cursor por el ícono de la bandeja
        self.setToolTip(f"{APP_NAME} {APP_VERSION}")

        self._menu = QMenu()
        self.setContextMenu(self._menu)
        self._armar_menu()
        translator.language_changed.connect(lambda _: self._armar_menu())

        self.activated.connect(self._activado)

    def _armar_menu(self):
        self._menu.clear()
        mostrar = self._menu.addAction(t("tray.show"))
        capturar = self._menu.addAction(t("tray.capture"))
        self._menu.addSeparator()
        salir = self._menu.addAction(t("tray.quit"))

        mostrar.triggered.connect(self.show_requested)
        capturar.triggered.connect(self.capture_requested)
        salir.triggered.connect(self.quit_requested)

    def _activado(self, motivo):
        if motivo == QSystemTrayIcon.Trigger:
            self.show_requested.emit()
