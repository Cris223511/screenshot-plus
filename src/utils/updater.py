"""actualizaciones desde las releases de github.

no hace falta ningún servidor propio: la api pública de github expone las
versiones publicadas del repositorio. todo el trabajo de red corre en hilos
para que la interfaz no se congele, y los resultados vuelven al hilo principal
por señales.

hay tres piezas:
- comprobar si existe una versión más nueva (UpdateChecker).
- descargarla e instalarla reemplazando el propio ejecutable (UpdateChecker
  también), con un pequeño script que espera a que la app cierre, cambia el
  archivo y vuelve a abrirla ya actualizada.
- traer la lista completa de versiones para mostrarla dentro de la app
  (ReleasesFetcher).
"""

import json
import os
import subprocess
import sys
import tempfile
import threading
import urllib.request

from PySide6.QtCore import QObject, Signal

from src import APP_REPO, APP_REPO_API, APP_VERSION

# la api de todas las releases sale de la misma base que la de la última
_RELEASES_API = APP_REPO_API.replace("/releases/latest", "/releases")


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


def _url_exe(datos: dict) -> str:
    """url de descarga directa del .exe adjunto a una release, o cadena vacía."""
    for activo in datos.get("assets", []):
        nombre = activo.get("name", "").lower()
        if nombre.endswith(".exe"):
            return activo.get("browser_download_url", "")
    return ""


def es_ejecutable() -> bool:
    """True cuando corremos como el .exe empaquetado y no como python."""
    return getattr(sys, "frozen", False)


class UpdateChecker(QObject):
    # hay_nueva, versión encontrada, url del .exe para instalar, url de la
    # página de la release (por si se prefiere abrir en el navegador)
    finished = Signal(bool, str, str, str)
    failed = Signal()

    # avance de la descarga (0 a 100) y avisos del final de la instalación
    progress = Signal(int)
    install_ready = Signal()
    install_failed = Signal()

    def check(self):
        """lanza la consulta en segundo plano y retorna de inmediato."""
        threading.Thread(target=self._worker, daemon=True).start()

    def _worker(self):
        try:
            peticion = urllib.request.Request(APP_REPO_API, headers={"User-Agent": "screenshot-plus"})
            with urllib.request.urlopen(peticion, timeout=10) as respuesta:
                datos = json.loads(respuesta.read().decode("utf-8"))
            ultima = datos.get("tag_name", "")
            if not ultima:
                self.failed.emit()
                return
            hay_nueva = _a_tupla(ultima) > _a_tupla(APP_VERSION)
            self.finished.emit(hay_nueva, ultima.lstrip("vV"),
                               _url_exe(datos), datos.get("html_url", "") or APP_REPO)
        except Exception:
            # sin internet, con github caído o si el repo aún no tiene
            # releases, el aviso es el mismo: no se pudo consultar
            self.failed.emit()

    def install(self, url_exe: str):
        """descarga el .exe nuevo e instala reemplazando el actual.

        al terminar la descarga emite install_ready; a partir de ahí quien
        llama debe cerrar la app para que el script de cambio haga su parte y
        la vuelva a abrir ya actualizada.
        """
        threading.Thread(target=self._descargar_e_instalar, args=(url_exe,), daemon=True).start()

    def _descargar_e_instalar(self, url_exe: str):
        try:
            if not es_ejecutable() or not url_exe:
                self.install_failed.emit()
                return
            actual = os.path.abspath(sys.executable)
            nuevo = actual + ".new"

            peticion = urllib.request.Request(url_exe, headers={"User-Agent": "screenshot-plus"})
            with urllib.request.urlopen(peticion, timeout=30) as respuesta:
                total = int(respuesta.headers.get("Content-Length", 0))
                leido = 0
                with open(nuevo, "wb") as destino:
                    while True:
                        trozo = respuesta.read(65536)
                        if not trozo:
                            break
                        destino.write(trozo)
                        leido += len(trozo)
                        if total:
                            self.progress.emit(int(leido * 100 / total))

            # una descarga cortada dejaría un exe inservible; se exige un
            # tamaño mínimo razonable antes de dar el cambio por bueno
            if os.path.getsize(nuevo) < 1_000_000:
                os.remove(nuevo)
                self.install_failed.emit()
                return

            self._lanzar_cambio(actual, nuevo)
            self.install_ready.emit()
        except Exception:
            self.install_failed.emit()

    @staticmethod
    def _lanzar_cambio(actual: str, nuevo: str):
        """deja corriendo un script que espera a que la app cierre, pone el
        exe nuevo en lugar del viejo y vuelve a abrir la app."""
        pid = os.getpid()
        script = (
            "@echo off\r\n"
            "setlocal\r\n"
            f'set "PID={pid}"\r\n'
            f'set "NUEVO={nuevo}"\r\n'
            f'set "VIEJO={actual}"\r\n'
            ":esperar\r\n"
            'tasklist /fi "PID eq %PID%" 2>nul | find "%PID%" >nul\r\n'
            "if not errorlevel 1 (\r\n"
            "  ping -n 2 127.0.0.1 >nul\r\n"
            "  goto esperar\r\n"
            ")\r\n"
            "ping -n 2 127.0.0.1 >nul\r\n"
            'move /y "%NUEVO%" "%VIEJO%" >nul\r\n'
            'start "" "%VIEJO%"\r\n'
            'del "%~f0"\r\n'
        )
        ruta_bat = os.path.join(tempfile.gettempdir(), "screenshot_plus_update.bat")
        with open(ruta_bat, "w", encoding="ascii") as f:
            f.write(script)
        # se lanza sin ventana y desligado, para que siga vivo cuando la app
        # se cierre
        creacion = 0x08000000 | 0x00000200  # CREATE_NO_WINDOW | CREATE_NEW_PROCESS_GROUP
        subprocess.Popen(["cmd", "/c", ruta_bat], creationflags=creacion, close_fds=True)


class ReleasesFetcher(QObject):
    """trae la lista completa de versiones publicadas para leerlas en la app."""

    # lista de dicts con version, fecha y notas de cada release
    loaded = Signal(list)
    failed = Signal()

    def fetch(self):
        threading.Thread(target=self._worker, daemon=True).start()

    def _worker(self):
        try:
            peticion = urllib.request.Request(_RELEASES_API, headers={"User-Agent": "screenshot-plus"})
            with urllib.request.urlopen(peticion, timeout=10) as respuesta:
                datos = json.loads(respuesta.read().decode("utf-8"))
            versiones = []
            for r in datos:
                if r.get("draft"):
                    continue
                versiones.append({
                    "version": (r.get("name") or r.get("tag_name") or "").strip(),
                    "fecha": (r.get("published_at") or "")[:10],
                    "notas": r.get("body") or "",
                })
            self.loaded.emit(versiones)
        except Exception:
            self.failed.emit()
