"""sistema de idiomas de la interfaz.

cada idioma es un json plano en locales/, con las mismas claves. la función
`t` busca la clave en el idioma activo y, si falta, cae al español, que es el
idioma de referencia y siempre está completo. cuando el usuario cambia de
idioma se emite una señal y cada ventana abierta vuelve a pintar sus textos,
sin reiniciar nada.
"""

import json
import os

from PySide6.QtCore import QObject, Signal

from src.config import paths
from src.config.settings import settings

# idiomas disponibles con su nombre nativo y el país que se muestra al lado;
# agregar uno nuevo es solo sumar su json en locales/ y una entrada acá
LANGUAGES = {
    "es": ("Español", "España"),
    "en": ("English", "United Kingdom"),
    "pt": ("Português", "Brasil"),
    "fr": ("Français", "France"),
    "de": ("Deutsch", "Deutschland"),
    "it": ("Italiano", "Italia"),
    "ja": ("日本語", "日本"),
    "zh": ("中文", "中国"),
    "ru": ("Русский", "Россия"),
}

FALLBACK = "es"


class Translator(QObject):
    # aviso para que las ventanas abiertas actualicen sus textos al momento
    language_changed = Signal(str)

    def __init__(self):
        super().__init__()
        self._cache: dict[str, dict] = {}
        self._lang = settings.get("language", FALLBACK)
        if self._lang not in LANGUAGES:
            self._lang = FALLBACK

    def _load(self, codigo: str) -> dict:
        """el json de cada idioma se lee una sola vez y queda en memoria."""
        if codigo not in self._cache:
            ruta = paths.resource_path(os.path.join("src", "i18n", "locales", f"{codigo}.json"))
            try:
                with open(ruta, "r", encoding="utf-8") as f:
                    self._cache[codigo] = json.load(f)
            except (OSError, json.JSONDecodeError):
                self._cache[codigo] = {}
        return self._cache[codigo]

    @property
    def language(self) -> str:
        return self._lang

    def set_language(self, codigo: str):
        if codigo not in LANGUAGES or codigo == self._lang:
            return
        self._lang = codigo
        settings.set("language", codigo)
        self.language_changed.emit(codigo)

    def t(self, clave: str, **valores) -> str:
        """texto traducido para una clave, con relleno de variables.

        los textos pueden llevar marcadores como {ruta} o {version}; si la
        clave no existe en ningún idioma se devuelve la clave misma, que en
        pantalla delata el faltante en lugar de esconderlo.
        """
        texto = self._load(self._lang).get(clave) or self._load(FALLBACK).get(clave) or clave
        if valores:
            try:
                texto = texto.format(**valores)
            except (KeyError, IndexError):
                pass
        return texto


# instancia única compartida; el alias t es la forma corta de usarla
translator = Translator()
t = translator.t
