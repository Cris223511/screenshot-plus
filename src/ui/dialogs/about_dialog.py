"""ventana de acerca de: la identidad de la aplicación en un solo lugar.

muestra el logo, la versión, quién la creó y la licencia, con el enlace al
repositorio para quien quiera ver el código o dejar una estrella, y el
botón para comprobar si hay una versión más nueva publicada.
"""

import os
import webbrowser

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (QApplication, QDialog, QLabel, QMessageBox,
                               QProgressDialog, QPushButton, QVBoxLayout)

from src import APP_AUTHOR, APP_NAME, APP_REPO, APP_VERSION, APP_YEAR
from src.config import paths
from src.i18n.translator import t
from src.ui.themes.theme_manager import theme
from src.ui.widgets.icons import icon
from src.utils.updater import UpdateChecker, es_ejecutable


class AboutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(t("about.title"))
        self.setFixedWidth(360)

        columna = QVBoxLayout(self)
        columna.setContentsMargins(26, 24, 26, 20)
        columna.setSpacing(6)

        logo = QLabel()
        from src.ui.widgets.icons import rounded_logo
        logo.setPixmap(rounded_logo(84))
        logo.setAlignment(Qt.AlignCenter)
        columna.addWidget(logo)

        nombre = QLabel(APP_NAME)
        nombre.setObjectName("titulo")
        nombre.setAlignment(Qt.AlignCenter)
        columna.addWidget(nombre)

        version = QLabel(f'{t("about.version")} {APP_VERSION}')
        version.setObjectName("secundario")
        version.setAlignment(Qt.AlignCenter)
        columna.addWidget(version)

        columna.addSpacing(8)

        descripcion = QLabel(t("about.desc"))
        descripcion.setWordWrap(True)
        descripcion.setAlignment(Qt.AlignCenter)
        columna.addWidget(descripcion)

        autor = QLabel(f'{t("about.author")} {APP_AUTHOR} · {APP_YEAR}')
        autor.setObjectName("secundario")
        autor.setAlignment(Qt.AlignCenter)
        columna.addWidget(autor)

        licencia = QLabel(t("about.license"))
        licencia.setObjectName("secundario")
        licencia.setWordWrap(True)
        licencia.setAlignment(Qt.AlignCenter)
        columna.addWidget(licencia)

        columna.addSpacing(10)

        estrella = QLabel(t("about.star"))
        estrella.setWordWrap(True)
        estrella.setAlignment(Qt.AlignCenter)
        columna.addWidget(estrella)

        columna.addSpacing(6)

        # los botones van uno bajo el otro, al ancho completo del diálogo,
        # así ninguna traducción larga se sale de su botón
        repo = QPushButton(t("about.repo"))
        repo.setIcon(icon("github", theme.icon_color()))
        repo.setIconSize(QSize(16, 16))
        repo.setMinimumHeight(34)
        actualizar = QPushButton(t("about.updates"))
        actualizar.setIcon(icon("refresh", theme.icon_color()))
        actualizar.setIconSize(QSize(16, 16))
        actualizar.setMinimumHeight(34)
        columna.addWidget(repo)
        columna.addSpacing(2)
        columna.addWidget(actualizar)

        repo.clicked.connect(lambda: webbrowser.open(APP_REPO))
        actualizar.clicked.connect(self._comprobar)

        # el verificador vive en el diálogo para que sus señales no mueran
        # antes de que llegue la respuesta de la red
        self._checker = UpdateChecker()
        self._checker.finished.connect(self._resultado)
        self._checker.failed.connect(self._fallo)
        self._checker.progress.connect(self._avance)
        self._checker.install_ready.connect(self._instalacion_lista)
        self._checker.install_failed.connect(self._instalacion_fallo)
        self._checando = None
        self._barra = None
        self._url_exe = ""
        self._url_pagina = APP_REPO
        self._version_nueva = ""

    def _comprobar(self):
        # aviso de "consultando" sin botón, modeless, que se cierra solo en
        # cuanto llega la respuesta; así no bloquea el resto del flujo
        self._checando = QMessageBox(QMessageBox.Information, t("upd.title"),
                                     t("upd.checking"), QMessageBox.NoButton, self)
        self._checando.setWindowModality(Qt.NonModal)
        self._checando.show()
        self._checker.check()

    def _cerrar_checando(self):
        if self._checando is not None:
            self._checando.close()
            self._checando = None

    def _resultado(self, hay_nueva: bool, version: str, url_exe: str, url_pagina: str):
        self._cerrar_checando()
        self._url_exe = url_exe
        self._url_pagina = url_pagina or APP_REPO
        self._version_nueva = version
        if not hay_nueva:
            QMessageBox.information(self, t("upd.title"), t("upd.uptodate", version=APP_VERSION))
            return
        aviso = QMessageBox(self)
        aviso.setWindowTitle(t("upd.title"))
        aviso.setText(t("upd.available", version=version))
        instalar = aviso.addButton(t("upd.install"), QMessageBox.AcceptRole)
        ver = aviso.addButton(t("upd.open"), QMessageBox.ActionRole)
        aviso.addButton(t("upd.later"), QMessageBox.RejectRole)
        aviso.exec()
        pulsado = aviso.clickedButton()
        if pulsado is instalar:
            self._instalar()
        elif pulsado is ver:
            webbrowser.open(self._url_pagina)

    def _instalar(self):
        # sin ejecutable (modo desarrollo) no hay nada que reemplazar; ahí la
        # única salida sensata es la página de descarga
        if not es_ejecutable() or not self._url_exe:
            QMessageBox.information(self, t("upd.title"), t("upd.dev"))
            webbrowser.open(self._url_pagina)
            return
        self._barra = QProgressDialog(t("upd.downloading", version=self._version_nueva),
                                      "", 0, 100, self)
        self._barra.setWindowTitle(t("upd.title"))
        self._barra.setCancelButton(None)
        self._barra.setWindowModality(Qt.WindowModal)
        self._barra.setMinimumDuration(0)
        self._barra.setValue(0)
        self._barra.show()
        self._checker.install(self._url_exe)

    def _avance(self, pct: int):
        if self._barra is not None:
            self._barra.setValue(pct)

    def _instalacion_lista(self):
        if self._barra is not None:
            self._barra.close()
            self._barra = None
        QMessageBox.information(self, t("upd.title"), t("upd.restart"))
        # al cerrar la app, el script de cambio pone el exe nuevo y la reabre
        QApplication.quit()

    def _instalacion_fallo(self):
        if self._barra is not None:
            self._barra.close()
            self._barra = None
        QMessageBox.warning(self, t("upd.title"), t("upd.install_failed"))
        webbrowser.open(self._url_pagina)

    def _fallo(self):
        self._cerrar_checando()
        QMessageBox.warning(self, t("upd.title"), t("upd.error"))
