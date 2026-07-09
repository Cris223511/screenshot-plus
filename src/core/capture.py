"""captura de pantalla en píxeles físicos, sin pérdida de calidad.

la librería mss lee directamente el framebuffer de windows, así que la imagen
sale a la resolución real del monitor aunque el sistema tenga escalado al
125 o 150 por ciento. las funciones devuelven QImage porque es lo que la
interfaz consume; la conversión a PIL solo ocurre al guardar o al unir la
captura con desplazamiento.
"""

import ctypes

import mss
from PySide6.QtGui import QGuiApplication, QImage

# valor de la api de windows que vuelve una ventana invisible para las
# capturas de pantalla, disponible desde windows 10 2004
_WDA_EXCLUDEFROMCAPTURE = 0x00000011


def exclude_from_capture(widget) -> bool:
    """marca una ventana propia para que no salga en ninguna captura.

    gracias a esto el panel y los overlays de presentación nunca aparecen
    en las fotos ni en el zoom en vivo, sin trucos de ocultar y esperar.
    devuelve False en versiones viejas de windows, donde simplemente se
    sigue usando el ocultamiento clásico.
    """
    try:
        hwnd = int(widget.winId())
        return bool(ctypes.windll.user32.SetWindowDisplayAffinity(hwnd, _WDA_EXCLUDEFROMCAPTURE))
    except Exception:
        return False


def make_tool_window(widget) -> None:
    """saca la ventana de la barra de tareas sin usar qt.tool.

    las ventanas qt.tool se esconden solas cuando la aplicación pierde el
    foco, y eso hacía desaparecer los paneles flotantes en pleno uso. el
    estilo nativo WS_EX_TOOLWINDOW logra lo mismo (sin entrada en la barra
    de tareas) pero la ventana se queda quieta donde está.
    """
    try:
        GWL_EXSTYLE = -20
        WS_EX_TOOLWINDOW = 0x00000080
        WS_EX_APPWINDOW = 0x00040000
        hwnd = int(widget.winId())
        estilo = ctypes.windll.user32.GetWindowLongPtrW(hwnd, GWL_EXSTYLE)
        ctypes.windll.user32.SetWindowLongPtrW(
            hwnd, GWL_EXSTYLE, (estilo | WS_EX_TOOLWINDOW) & ~WS_EX_APPWINDOW)
    except Exception:
        pass


def foreground_fullscreen() -> bool:
    """True cuando la ventana con foco ocupa su monitor entero.

    los juegos y las apps a pantalla completa se detectan así; con eso los
    atajos globales se quedan callados para no interrumpir la partida.
    """
    try:
        import win32api
        import win32gui
        hwnd = win32gui.GetForegroundWindow()
        if not hwnd:
            return False
        clase = win32gui.GetClassName(hwnd)
        # el escritorio y la shell también miden pantalla completa, pero
        # no son juegos
        if clase in ("Progman", "WorkerW", "Shell_TrayWnd"):
            return False
        rect = win32gui.GetWindowRect(hwnd)
        monitor = win32api.MonitorFromWindow(hwnd, 2)
        info = win32api.GetMonitorInfo(monitor)
        return tuple(rect) == tuple(info["Monitor"])
    except Exception:
        return False


def _grab(region: dict) -> QImage:
    """lectura cruda de una zona de pantalla y conversión a QImage.

    el buffer que entrega mss viene en formato bgra y pertenece a la propia
    librería, por eso el .copy(): la QImage necesita ser dueña de sus datos
    cuando el contexto de mss se cierra.
    """
    with mss.mss() as sct:
        frame = sct.grab(region)
        imagen = QImage(frame.bgra, frame.width, frame.height, frame.width * 4, QImage.Format_ARGB32)
        return imagen.copy()


def virtual_screen_region() -> dict:
    """rectángulo que abarca todos los monitores juntos.

    en mss el monitor con índice cero es el escritorio virtual completo, lo
    que permite capturar y dibujar overlays aunque haya varias pantallas.
    """
    with mss.mss() as sct:
        m = sct.monitors[0]
        return {"left": m["left"], "top": m["top"], "width": m["width"], "height": m["height"]}


def grab_virtual_screen() -> QImage:
    """captura de todo el escritorio virtual, monitores incluidos."""
    return _grab(virtual_screen_region())


def grab_region(left: int, top: int, width: int, height: int) -> QImage:
    """captura de una zona concreta, en coordenadas físicas de pantalla."""
    if width < 1 or height < 1:
        return QImage()
    return _grab({"left": left, "top": top, "width": width, "height": height})


def active_window_rect():
    """rectángulo de la ventana con foco, en píxeles físicos, o None.

    sirve para preseleccionar esa zona en el editor de capturas: el
    usuario ve la ventana ya enmarcada y decide si ajusta, anota, copia
    o guarda.
    """
    try:
        import win32gui
        hwnd = win32gui.GetForegroundWindow()
        izquierda, arriba, derecha, abajo = win32gui.GetWindowRect(hwnd)
        if derecha - izquierda > 0 and abajo - arriba > 0:
            from PySide6.QtCore import QRect
            return QRect(izquierda, arriba, derecha - izquierda, abajo - arriba)
    except Exception:
        pass
    return None


def grab_active_window() -> QImage:
    """captura de la ventana que tiene el foco en este momento.

    windows entrega el rectángulo de la ventana en píxeles físicos; si por
    cualquier motivo no hay ventana válida, se captura la pantalla completa
    para que el atajo nunca quede en nada.
    """
    try:
        import win32gui
        hwnd = win32gui.GetForegroundWindow()
        izquierda, arriba, derecha, abajo = win32gui.GetWindowRect(hwnd)
        if derecha - izquierda > 0 and abajo - arriba > 0:
            return grab_region(izquierda, arriba, derecha - izquierda, abajo - arriba)
    except Exception:
        pass
    return grab_virtual_screen()


def device_pixel_ratio() -> float:
    """factor de escalado del monitor principal.

    sirve para convertir entre las coordenadas lógicas en las que trabaja qt
    y los píxeles físicos en los que captura mss.
    """
    pantalla = QGuiApplication.primaryScreen()
    return pantalla.devicePixelRatio() if pantalla else 1.0
