"""ventana de acerca de: la identidad de la aplicación en un solo lugar.

muestra el logo, la versión, quién la creó y la licencia, con el enlace al
repositorio para quien quiera ver el código o dejar una estrella, y el
botón para comprobar si hay una versión más nueva publicada.
"""

import os
import webbrowser

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (QDialog, QLabel, QMessageBox, QPushButton,
                               QVBoxLayout)

from src import APP_AUTHOR, APP_NAME, APP_REPO, APP_VERSION, APP_YEAR
from src.config import paths
from src.i18n.translator import t
from src.ui.themes.theme_manager import theme
from src.ui.widgets.icons import icon
from src.utils.updater import UpdateChecker


class AboutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(t("about.title"))
        self.setFixedWidth(360)

        columna = QVBoxLayout(self)
        columna.setContentsMargins(26, 24, 26, 20)
        columna.setSpacing(6)

        logo = QLabel()
        pixmap = QPixmap(paths.resource_path(os.path.join("assets", "logo", "logo.jpg")))
        logo.setPixmap(pixmap.scaled(84, 84, Qt.KeepAspectRatio, Qt.SmoothTransformation))
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

    def _comprobar(self):
        QMessageBox.information(self, t("upd.title"), t("upd.checking"))
        self._checker.check()

    def _resultado(self, hay_nueva: bool, version: str, url: str):
        if hay_nueva:
            aviso = QMessageBox(self)
            aviso.setWindowTitle(t("upd.title"))
            aviso.setText(t("upd.available", version=version))
            abrir = aviso.addButton(t("upd.open"), QMessageBox.AcceptRole)
            aviso.addButton(QMessageBox.Close)
            aviso.exec()
            if aviso.clickedButton() is abrir:
                webbrowser.open(url or APP_REPO)
        else:
            QMessageBox.information(self, t("upd.title"), t("upd.uptodate", version=APP_VERSION))

    def _fallo(self):
        QMessageBox.warning(self, t("upd.title"), t("upd.error"))
