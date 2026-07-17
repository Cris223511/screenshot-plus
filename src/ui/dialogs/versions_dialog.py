"""historial de versiones dentro de la propia aplicación.

trae la lista de releases publicadas en github por la api pública y las
muestra con el mismo aire que el manual: una tarjeta por versión con su fecha
y sus notas. es solo para leer; nada se descarga desde aquí. las notas vienen
en markdown y se convierten a un html sencillo (párrafos, viñetas, negrita,
código y enlaces), suficiente para cómo están redactadas.
"""

import html
import re

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QDialog, QHBoxLayout, QLabel, QTextBrowser,
                               QVBoxLayout)

from src import APP_NAME, APP_VERSION
from src.i18n.translator import t
from src.ui.themes.theme_manager import theme
from src.utils.updater import ReleasesFetcher


def _inline(texto: str, acento: str, tarjeta: str) -> str:
    """convierte los marcadores de una línea (negrita, código, enlaces)."""
    seguro = html.escape(texto)
    seguro = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", seguro)
    seguro = re.sub(r"`(.+?)`",
                    rf'<span style="background-color:{tarjeta}; color:{acento};">'
                    r'&nbsp;\1&nbsp;</span>', seguro)
    seguro = re.sub(r"\[(.+?)\]\((.+?)\)", r'<a href="\2">\1</a>', seguro)
    return seguro


def _notas_a_html(notas: str, acento: str, tarjeta: str) -> str:
    """el cuerpo markdown de una release pasado a html simple."""
    lineas = notas.replace("\r\n", "\n").split("\n")
    partes = []
    en_lista = False
    for linea in lineas:
        s = linea.strip()
        if s.startswith("- "):
            if not en_lista:
                partes.append("<ul>")
                en_lista = True
            partes.append(f"<li>{_inline(s[2:], acento, tarjeta)}</li>")
        else:
            if en_lista:
                partes.append("</ul>")
                en_lista = False
            if s:
                partes.append(f"<p>{_inline(s, acento, tarjeta)}</p>")
    if en_lista:
        partes.append("</ul>")
    return "".join(partes)


class VersionsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(t("ver.title"))
        self.resize(660, 640)

        columna = QVBoxLayout(self)
        columna.setContentsMargins(22, 18, 22, 18)
        columna.setSpacing(10)

        # encabezado con el logo, igual que el manual, para que se sienta parte
        # del mismo conjunto
        encabezado = QHBoxLayout()
        logo = QLabel()
        from src.ui.widgets.icons import rounded_logo
        logo.setPixmap(rounded_logo(46))
        encabezado.addWidget(logo)
        titulos = QVBoxLayout()
        titulos.setSpacing(0)
        nombre = QLabel(APP_NAME)
        nombre.setObjectName("titulo")
        subtitulo = QLabel(t("ver.subtitle"))
        subtitulo.setObjectName("secundario")
        titulos.addWidget(nombre)
        titulos.addWidget(subtitulo)
        encabezado.addSpacing(10)
        encabezado.addLayout(titulos)
        encabezado.addStretch()
        columna.addLayout(encabezado)

        self._visor = QTextBrowser()
        self._visor.setOpenExternalLinks(True)
        self._visor.document().setDocumentMargin(14)
        self._visor.setHtml(self._envoltura(f'<p>{t("ver.loading")}</p>'))
        columna.addWidget(self._visor)

        self._fetcher = ReleasesFetcher()
        self._fetcher.loaded.connect(self._mostrar)
        self._fetcher.failed.connect(self._error)
        self._fetcher.fetch()

    def _colores(self):
        claro = theme.theme == "light"
        return {
            "texto": "#2b3140" if claro else "#d6d9e0",
            "suave": "#6b7280" if claro else "#8b93a7",
            "acento": theme.accent(),
            "tarjeta": "#eef2f9" if claro else "#242b38",
        }

    def _envoltura(self, cuerpo: str) -> str:
        c = self._colores()
        return f'<div style="color:{c["texto"]}; font-size:13px;">{cuerpo}</div>'

    def _mostrar(self, versiones: list):
        if not versiones:
            self._error()
            return
        c = self._colores()
        bloques = []
        for v in versiones:
            titulo = v["version"] or "?"
            instalada = APP_VERSION in titulo
            etiqueta = (f' <span style="color:{c["acento"]};">({t("ver.current")})</span>'
                        if instalada else "")
            fecha = f' <span style="color:{c["suave"]};">· {v["fecha"]}</span>' if v["fecha"] else ""
            bloques.append(
                f'<table width="100%" cellspacing="0" cellpadding="8"><tr>'
                f'<td bgcolor="{c["tarjeta"]}">'
                f'<span style="color:{c["acento"]}; font-size:15px; font-weight:bold;">▌ {titulo}</span>'
                f'{etiqueta}{fecha}</td></tr></table>')
            bloques.append(_notas_a_html(v["notas"], c["acento"], c["tarjeta"]))
            bloques.append('<div style="font-size:10px; line-height:10px">&nbsp;</div>')
        self._visor.setHtml(self._envoltura("".join(bloques)))

    def _error(self):
        self._visor.setHtml(self._envoltura(f'<p>{t("ver.error")}</p>'))
