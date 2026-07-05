"""control de instancia única del ejecutable.

si el usuario abre el .exe cuando la app ya está corriendo, la copia nueva
no arranca por duplicado: le avisa a la que ya existe para que muestre su
panel y termina en silencio. la comunicación va por un socket local con
nombre fijo, que en windows es un pipe con permisos del propio usuario.
"""

from PySide6.QtCore import QObject, Signal
from PySide6.QtNetwork import QLocalServer, QLocalSocket

_NOMBRE = "screenshot-plus-instancia"


class SingleInstance(QObject):
    # se dispara cuando otra copia del ejecutable intentó abrirse; la app
    # responde trayendo el panel al frente
    another_launched = Signal()

    def __init__(self):
        super().__init__()
        self._server: QLocalServer | None = None

    def is_primary(self) -> bool:
        """True cuando esta es la primera copia y debe arrancar completa.

        el intento de conexión al pipe decide todo: si alguien responde,
        ya hay una app viva y esta copia solo le manda el aviso y se va.
        """
        sonda = QLocalSocket()
        sonda.connectToServer(_NOMBRE)
        if sonda.waitForConnected(300):
            sonda.write(b"show")
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
            conexion.readyRead.connect(lambda: self.another_launched.emit())
            conexion.disconnected.connect(conexion.deleteLater)
