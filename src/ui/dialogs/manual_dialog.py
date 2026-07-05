"""manual de usuario dentro de la propia aplicación.

el contenido vive en docs/manual.md y acá solo se muestra; así el manual se
lee igual en github y en la app, sin duplicar textos ni redirigir a nadie
fuera del programa.
"""

import os

from PySide6.QtWidgets import QDialog, QTextBrowser, QVBoxLayout

from src.config import paths
from src.i18n.translator import t


class ManualDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(t("man.title"))
        self.resize(560, 520)

        columna = QVBoxLayout(self)
        columna.setContentsMargins(10, 10, 10, 10)

        visor = QTextBrowser()
        visor.setOpenExternalLinks(True)
        ruta = paths.resource_path(os.path.join("docs", "manual.md"))
        try:
            with open(ruta, "r", encoding="utf-8") as f:
                visor.setMarkdown(f.read())
        except OSError:
            visor.setPlainText(t("man.title"))
        columna.addWidget(visor)
