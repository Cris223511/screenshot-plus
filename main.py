"""punto de entrada de screenshot plus.

lo único que pasa acá es el arranque ordenado: control de instancia única,
la aplicación qt con su escalado correcto, el tema visual, la sincronía del
autoarranque y el bucle de eventos. toda la lógica vive en src/.
"""

import os
import sys

# pynput tiene que entrar antes que pyside6: el sistema de firmas de
# shiboken se tropieza con el importador de six (que pynput trae adentro)
# cuando llega en el orden inverso, y la app moriría recién al registrar
# los atajos globales, que es mucho más difícil de diagnosticar
import pynput  # noqa: F401

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from src import APP_NAME
from src.app import ScreenshotApp
from src.config import paths
from src.config.settings import settings
from src.utils import autostart
from src.utils.single_instance import SingleInstance


def main() -> int:
    # en desarrollo, ctrl+c en la consola debe matar la app; python solo
    # atiende la señal si nadie la secuestra, y el bucle de qt lo hace
    import signal
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    aplicacion = QApplication(sys.argv)
    aplicacion.setApplicationName(APP_NAME)
    aplicacion.setWindowIcon(QIcon(paths.resource_path(os.path.join("assets", "logo", "logo.jpg"))))
    # con la app viva en la bandeja, cerrar ventanas no debe terminarla
    aplicacion.setQuitOnLastWindowClosed(False)

    # si ya hay una copia corriendo, esta solo le avisa y termina
    instancia = SingleInstance()
    if not instancia.is_primary():
        return 0

    from src.ui.themes.theme_manager import theme
    theme.apply()

    # todos los tooltips de la app salen como burbuja redondeada, al
    # instante, en lugar del rectángulo tardío de windows
    from src.ui.widgets import tooltip
    tooltip.install(aplicacion)

    # los diálogos propios de qt (selector de color, botones estándar)
    # hablan el idioma de la app cargando las traducciones que qt trae;
    # sin esto salían en inglés
    from PySide6.QtCore import QLibraryInfo, QTranslator
    from src.i18n.translator import translator
    traductor_qt = QTranslator(aplicacion)

    def instalar_qt(codigo: str):
        aplicacion.removeTranslator(traductor_qt)
        especiales = {"zh": "zh_CN"}
        archivo = f"qtbase_{especiales.get(codigo, codigo)}"
        ruta = QLibraryInfo.path(QLibraryInfo.TranslationsPath)
        if traductor_qt.load(archivo, ruta):
            aplicacion.installTranslator(traductor_qt)

    translator.language_changed.connect(instalar_qt)
    instalar_qt(translator.language)

    # el registro de windows queda alineado con la preferencia guardada,
    # útil cuando el usuario movió el ejecutable de carpeta
    autostart.sync(settings.get("autostart", False))

    app = ScreenshotApp()
    instancia.another_launched.connect(app.mostrar_panel)

    return aplicacion.exec()


if __name__ == "__main__":
    sys.exit(main())
