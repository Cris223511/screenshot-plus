"""manual de usuario dentro de la propia aplicación.

arma el manual como una página con diseño (tarjeta de bienvenida, pasos
numerados, teclas dibujadas como chips y tablas de atajos), adaptada al
tema claro u oscuro. es la versión visual del contenido que también vive
en markdown en docs/manual.md.
"""

import os

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (QDialog, QHBoxLayout, QLabel, QTextBrowser,
                               QVBoxLayout)

from src import APP_NAME
from src.config import paths
from src.i18n.translator import t
from src.ui.themes.theme_manager import theme


def _html() -> str:
    """el manual completo como html con estilos según el tema activo."""
    claro = theme.theme == "light"
    texto = "#2b3140" if claro else "#d6d9e0"
    suave = "#6b7280" if claro else "#8b93a7"
    acento = theme.accent()
    tarjeta = "#eef2f9" if claro else "#242b38"
    zebra = "#f7f9fc" if claro else "#1f2530"

    def kbd(tecla: str) -> str:
        return (f'<span style="background-color:{tarjeta}; color:{acento};'
                f' font-weight:bold;">&nbsp;{tecla}&nbsp;</span>')

    def esp(px: int) -> str:
        # separador vertical de altura fija; qt respeta el tamaño de fuente
        # de un bloque para calcular su alto, así se logran huecos finos
        return f'<div style="font-size:{px}px; line-height:{px}px">&nbsp;</div>'

    def seccion(titulo: str, apretado: bool = False) -> str:
        # una sola celda con fondo suave y el marcador del color de acento.
        # arriba un separador corto para no despegarlo tanto del bloque
        # anterior; después, amplio cuando siguen pasos o tablas y mínimo
        # cuando sigue un párrafo, que ya trae su propio margen
        cierre = esp(3) if apretado else '<br>'
        return (f'{esp(7)}<table width="100%" cellspacing="0" cellpadding="7">'
                f'<tr><td bgcolor="{tarjeta}">'
                f'<span style="color:{acento}; font-size:15px; font-weight:bold;">'
                f'▌ {titulo}</span></td></tr></table>{cierre}')

    def paso(numero: int, contenido: str) -> str:
        return (f'<table width="100%" cellspacing="0" cellpadding="5"><tr>'
                f'<td width="26" bgcolor="{acento}" align="center">'
                f'<span style="color:#ffffff; font-weight:bold;">{numero}</span></td>'
                f'<td>{contenido}</td></tr></table>')

    def fila(a: str, b: str, sombreada: bool) -> str:
        fondo = f' bgcolor="{zebra}"' if sombreada else ""
        return (f'<tr><td{fondo} style="padding:5px;">{a}</td>'
                f'<td{fondo} style="padding:5px;">{b}</td></tr>')

    atajos = [("Capturar región", "Alt + A"), ("Pantalla completa", "Alt + S"),
              ("Ventana actual", "Alt + W"), ("Captura con desplazamiento", "Alt + D"),
              ("Panel de presentación", "Alt + Z"), ("Mostrar u ocultar el panel", "Alt + Q")]
    filas_atajos = "".join(fila(a, kbd(k), i % 2 == 0) for i, (a, k) in enumerate(atajos))

    pizarra = [("Z", "Pausa y zoom con la rueda; arrastra la vista con el clic"),
               ("V", "Selecciona, mueve y estira; recuadro elástico para varios"),
               ("H", "Mano para arrastrar la vista"),
               ("L", "Láser con estela (color y grosor en propiedades)"),
               ("P / R", "Pincel y resaltador"),
               ("I / F", "Línea y flecha, con extremos configurables"),
               ("S", "Formas; repetir la tecla rota entre las ocho"),
               ("E", "Borrador de lo que toca"),
               ("T", "Texto directo, con doble clic para reeditar"),
               ("Ctrl + Z / Y", "Deshacer y rehacer, movimientos incluidos"),
               ("Ctrl + C / S", "Copiar o guardar toda la pizarra"),
               ("Ctrl + A", "Recortar solo un pedazo de lo que se ve"),
               ("Esc", "Cierra el texto, el recorte, el zoom y al final la pizarra")]
    filas_pizarra = "".join(fila(kbd(k), d, i % 2 == 0) for i, (k, d) in enumerate(pizarra))

    return f"""
    <div style="color:{texto}; font-size:13px;">

    <table width="100%" cellspacing="0" cellpadding="10">
    <tr><td bgcolor="{tarjeta}">
      <span style="font-size:15px; font-weight:bold; color:{acento};">Bienvenido a {APP_NAME}</span><br>
      Capturas en un atajo, anotaciones completas, páginas largas con scroll y una pizarra
      de presentación con zoom en vivo. Todo desde la bandeja del sistema, gratis y sin cuentas.
    </td></tr>
    </table>

    {seccion("Primeros pasos")}
    {paso(1, "Abre el ejecutable: aparece el panel y la app queda viva en la bandeja, junto al reloj.")}
    {paso(2, f'Presiona {kbd("Alt + A")} y arrastra sobre la zona que quieras capturar.')}
    {paso(3, f'Anota con la barra de herramientas y termina con {kbd("Ctrl + C")} para copiar o {kbd("Ctrl + S")} para guardar.')}
    <br>

    {seccion("Atajos globales")}
    <table width="100%" cellspacing="0" cellpadding="0">
    <tr><td bgcolor="{acento}" style="padding:6px;"><span style="color:#ffffff; font-weight:bold;">Acción</span></td>
        <td bgcolor="{acento}" style="padding:6px;"><span style="color:#ffffff; font-weight:bold;">Atajo</span></td></tr>
    {filas_atajos}
    </table>
    <p style="margin-top:4px; color:{suave};">Todos se cambian en Opciones, pestaña Acceso rápido. Con un juego a
    pantalla completa al frente, los atajos se silencian solos.</p>

    {seccion("Editor de capturas", apretado=True)}
    <p style="margin-top:2px;">Al soltar la selección aparece la barra: <b>ocho formas</b>, líneas y flechas con
    <b>remates configurables en cada extremo</b> y cinco estilos de trazo, pincel, texto con
    todas las tipografías del sistema (negrita y cursiva), <b>pixelado</b> para datos sensibles,
    opacidad, e imágenes pegadas con {kbd("Ctrl + V")}.</p>
    <p>Todo queda editable: con la herramienta de selección tomas cualquier elemento, lo mueves,
    lo estiras por sus cuadraditos y la barra carga sus propiedades para cambiarlas en vivo.
    La propia zona de selección también se mueve y redimensiona. {kbd("Supr")} borra,
    {kbd("Ctrl + Z")} deshace y {kbd("Ctrl + Y")} rehace.</p>

    {seccion("Captura con desplazamiento")}
    {paso(1, f'{kbd("Alt + D")} y eliges la zona; el resto de la pantalla queda bloqueado con un velo.')}
    {paso(2, "Haces scroll hacia abajo y la imagen se va cosiendo con vista previa en vivo.")}
    {paso(3, f'{kbd("Enter")} abre el resultado en el editor con scroll; {kbd("Esc")} cancela.')}
    <br>

    {seccion("Pizarra de presentación", apretado=True)}
    <p style="margin-top:2px; margin-bottom:2px;">{kbd("Alt + Z")} abre el panel lateral (arrastrable desde su agarre, con minimizar a un
    chip flotante). Al activar una herramienta, la pantalla se pausa y trabajas sobre ella;
    la ventanita de propiedades trae colores con recientes y código hex, grosor, estilos,
    extremos y tipografía. Re-clic en la herramienta activa la esconde o la trae.</p>
    {esp(8)}
    <table width="100%" cellspacing="0" cellpadding="0">
    <tr><td bgcolor="{acento}" style="padding:6px;"><span style="color:#ffffff; font-weight:bold;">Tecla</span></td>
        <td bgcolor="{acento}" style="padding:6px;"><span style="color:#ffffff; font-weight:bold;">Qué hace</span></td></tr>
    {filas_pizarra}
    </table>
    <p style="margin-top:4px; color:{suave};">Con el panel abierto (o minimizado al chip), cada herramienta
    también responde de forma global con {kbd("Alt + letra")}: por ejemplo {kbd("Alt + S")}
    activa las formas y repetirlo rota entre ellas. Al cerrar el panel, esos atajos se apagan.
    Las letras se personalizan en Opciones, pestaña Presentación.</p>

    {seccion("Guardado y formatos", apretado=True)}
    <p style="margin-top:2px;">La primera vez las capturas van a una carpeta propia dentro de tus Imágenes; después,
    la última carpeta que uses será la que se abra. Formatos: <b>PNG, JPEG, BMP, TIFF y WEBP</b>,
    con calidad ajustable donde aplica, y opción de abrir la carpeta al guardar.</p>

    {seccion("Idiomas y actualizaciones", apretado=True)}
    <p style="margin-top:2px;">Nueve idiomas con cambio instantáneo. La opción Comprobar actualizaciones consulta las
    versiones publicadas en GitHub; nada se instala solo y la app no recolecta ningún dato.</p>

    </div>
    """


class ManualDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(t("man.title"))
        self.resize(660, 640)

        columna = QVBoxLayout(self)
        columna.setContentsMargins(22, 18, 22, 18)
        columna.setSpacing(10)

        # el encabezado con el logo le da cara de documento, no de txt
        encabezado = QHBoxLayout()
        logo = QLabel()
        from src.ui.widgets.icons import rounded_logo
        logo.setPixmap(rounded_logo(46))
        encabezado.addWidget(logo)
        titulos = QVBoxLayout()
        titulos.setSpacing(0)
        nombre = QLabel(APP_NAME)
        nombre.setObjectName("titulo")
        subtitulo = QLabel(t("man.title"))
        subtitulo.setObjectName("secundario")
        titulos.addWidget(nombre)
        titulos.addWidget(subtitulo)
        encabezado.addSpacing(10)
        encabezado.addLayout(titulos)
        encabezado.addStretch()
        columna.addLayout(encabezado)

        visor = QTextBrowser()
        visor.setOpenExternalLinks(True)
        visor.document().setDocumentMargin(14)
        visor.setHtml(_html())
        columna.addWidget(visor)
