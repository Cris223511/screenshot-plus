"""comprobación de actualizaciones contra las releases de github.

no hace falta ningún servidor propio: la api pública de github ya expone la
última versión publicada del repositorio. la consulta corre en un hilo para
que la interfaz no se congele esperando la red, y el resultado vuelve al
hilo principal por una señal.
"""

import json
import threading
import urllib.request

from PySide6.QtCore import QObject, Signal

from src import APP_REPO_API, APP_VERSION


def _a_tupla(version: str) -> tuple:
    """versión "1.2.3" convertida a (1, 2, 3) para poder comparar bien.

    comparar strings diría que "1.10" es menor que "1.9"; con tuplas de
    números la comparación es la correcta.
    """
    limpia = version.strip().lstrip("vV")
    partes = []
    for pieza in limpia.split("."):
        numero = "".join(c for c in pieza if c.isdigit())
        partes.append(int(numero) if numero else 0)
    return tuple(partes)


class UpdateChecker(QObject):
    # el bool indica si hay versión nueva; los strings traen la versión
    # encontrada y la url de descarga. en error, finished no se emite
    finished = Signal(bool, str, str)
    failed = Signal()

    def check(self):
        """lanza la consulta en segundo plano y retorna de inmediato."""
        threading.Thread(target=self._worker, daemon=True).start()

    def _worker(self):
        try:
            peticion = urllib.request.Request(APP_REPO_API, headers={"User-Agent": "screenshot-plus"})
            with urllib.request.urlopen(peticion, timeout=10) as respuesta:
                datos = json.loads(respuesta.read().decode("utf-8"))
            ultima = datos.get("tag_name", "")
            url = datos.get("html_url", "")
            if not ultima:
                self.failed.emit()
                return
            hay_nueva = _a_tupla(ultima) > _a_tupla(APP_VERSION)
            self.finished.emit(hay_nueva, ultima.lstrip("vV"), url)
        except Exception:
            # sin internet, con github caído o si el repo aún no tiene
            # releases, el aviso es el mismo: no se pudo consultar
            self.failed.emit()
