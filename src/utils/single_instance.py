"""control de instancia única del ejecutable.

si el usuario abre el .exe cuando la app ya está corriendo, la copia nueva no
arranca por duplicado: le avisa a la que ya existe y termina en silencio. la
comunicación va por un socket local con nombre fijo, que en windows es un pipe
con permisos del propio usuario.

el aviso depende de cómo se lanzó esa copia nueva. un doble clic normal pide
traer el panel al frente; un arranque en segundo plano (la bandera de bandeja,
la que usa windows al encender) no pide nada, para que la app siga oculta.
esta distinción importa porque el arranque automático se registra por dos vías
y ambas se disparan al encender: sin ella, la segunda haría aparecer el panel
aunque las dos vinieran con la bandera de bandeja.
"""

import sys

from PySide6.QtCore import QObject, Signal
from PySide6.QtNetwork import QLocalServer, QLocalSocket

from src.utils.autostart import ARG_BANDEJA

_NOMBRE = "screenshot-plus-instancia"


class SingleInstance(QObject):
    # se dispara cuando otra copia del ejecutable se abrió con un doble clic
    # normal; la app responde trayendo el panel al frente
    another_launched = Signal()

    def __init__(self):
        super().__init__()
        self._server: QLocalServer | None = None

    def is_primary(self) -> bool:
        """True cuando esta es la primera copia y debe arrancar completa.

        el intento de conexión al pipe decide todo: si alguien responde, ya
        hay una app viva y esta copia solo le manda el aviso y se va. el aviso
        es "tray" cuando se arrancó en segundo plano, para que la que ya corre
        no muestre el panel, o "show" en un arranque normal.
        """
        sonda = QLocalSocket()
        sonda.connectToServer(_NOMBRE)
        if sonda.waitForConnected(300):
            mensaje = b"tray" if ARG_BANDEJA in sys.argv else b"show"
            sonda.write(mensaje)
            sonda.waitForBytesWritten(300)
            sonda.disconnectFromServer()
            return False

        # un cierre forzado previo puede dejar el pipe registrado; se limpia
        # antes de escuchar para que el arranque no falle por ese residuo
        QLocalServer.removeServer(_NOMBRE)
        self._server = QLocalServer()
        self._server.newConnection.connect(self._on_connection)
        self._server.listen(_NOMBRE)
        return True

    def _on_connection(self):
        conexion = self._server.nextPendingConnection()
        if conexion:
            conexion.readyRead.connect(lambda: self._leer(conexion))
            conexion.disconnected.connect(conexion.deleteLater)

    def _leer(self, conexion):
        # solo el aviso de un arranque normal trae el panel al frente; el de
        # bandeja se ignora, así el arranque con windows se queda oculto
        datos = bytes(conexion.readAll())
        if b"show" in datos:
            self.another_launched.emit()
