<p align="center">
  <img src="assets/logo/logo.jpg" alt="logo de Screenshot Plus" width="140">
</p>

<h1 align="center">Screenshot Plus</h1>

<p align="center">
  Herramienta de capturas de pantalla para Windows, con zoom en vivo, anotaciones y atajos de teclado.
  <br>
  Gratuita, de código abierto y sin nada de pago dentro. Para siempre.
</p>

---

## ¿Qué es Screenshot Plus?

Screenshot Plus es una aplicación de escritorio pensada para que tomar una captura sea cuestión de un atajo y nada más. Presionas la tecla, seleccionas la zona arrastrando el mouse, y al soltar aparece una barra de herramientas para anotar lo capturado: flechas, formas, texto, pincel, pixelado y más. Con Ctrl+C ya la tienes copiada, con Ctrl+S guardada en tu carpeta de siempre.

Además incluye un modo pensado para presentaciones: zoom sobre cualquier parte de la pantalla, puntero láser, subrayado y dibujo en vivo, todo controlado por teclado.

Es un único ejecutable portable. Lo abres y ya está funcionando: no requiere instalación, y si cierras la ventana sigue activo en la bandeja del sistema, listo para el siguiente atajo.

## Descargas

| Versión | Archivo | Estado |
| ------- | ------- | ------ |
| 1.0.0 | [ScreenshotPlus.exe](https://github.com/Cris223511/screenshot-plus/releases/download/v1.0.0/ScreenshotPlus.exe) | Disponible |

Basta con descargar el `.exe` y ejecutarlo. No hay instalador ni pasos adicionales; todas las versiones viven en la sección de [releases](https://github.com/Cris223511/screenshot-plus/releases).

## Características

- Captura por región, pantalla completa o ventana activa, siempre a resolución nativa. El panel de la aplicación nunca sale en las fotos: queda excluido de la captura por el propio Windows.
- Editor de anotaciones al soltar la selección: ocho formas (rectángulo, rectángulo redondeado, elipse, triángulo, rombo, pentágono, hexágono y estrella), líneas y flechas con remates configurables en cada extremo (flecha, flecha rellena, punto, cuadrado, rombo) y trazo continuo, discontinuo o punteado, pincel con grosor, texto con más de veinticinco tipografías en desplegable, tamaño, negrita, cursiva y color, y pixelado para ocultar información sensible.
- Todo es editable después de dibujado: seleccionas cualquier elemento, lo mueves, lo redimensionas por sus tiradores y le cambias color, grosor o estilo desde la misma barra. La propia zona de selección también se puede mover y agrandar.
- Captura con desplazamiento: seleccionas la zona, el resto de la pantalla queda bloqueado con un velo, haces scroll y la app une el contenido en una sola imagen larga con vista previa en vivo. Al finalizar, la imagen se abre en un editor con scroll y las mismas herramientas de anotación.
- Copiado al portapapeles y guardado a disco con atajos, con notificación de confirmación.
- La carpeta de guardado se recuerda entre sesiones; la última que uses será la próxima en abrirse.
- Modo presentación con la pantalla en vivo, sin congelar nada: un panel lateral fijable trae zoom en vivo sobre lo que está pasando, puntero láser con estela que se desvanece (color y tamaño configurables), pincel, resaltador, líneas y flechas sobre la pantalla.
- Atajos de teclado globales, ya configurados por defecto y personalizables desde las opciones.
- Interfaz en varios idiomas: español, inglés, portugués, francés, alemán e italiano. El español es el idioma por defecto.
- Tema claro y tema oscuro, panel siempre adelante con su pin, y arranque minimizado en la bandeja si lo prefieres.
- Comprobación de actualizaciones contra las versiones publicadas en este repositorio.
- Manual de usuario y ventana de acerca de integrados en la propia aplicación, sin redirecciones externas.

## Atajos por defecto

| Acción | Atajo |
| ------ | ----- |
| Capturar región | Alt + A |
| Capturar pantalla completa | Alt + S |
| Capturar ventana actual | Alt + W |
| Captura con desplazamiento | Alt + D |
| Modo presentación (zoom) | Alt + Z |
| Mostrar u ocultar el panel | Alt + Q |
| Copiar la captura | Ctrl + C |
| Guardar la captura | Ctrl + S |

Todos se pueden cambiar desde Opciones, en la pestaña de acceso rápido.

## Cómo usarlo

1. Abre el ejecutable. El panel principal aparece y la app queda viva en la bandeja del sistema.
2. Presiona Alt + A (o el botón Capturar) y arrastra el mouse sobre la zona que quieres.
3. Al soltar aparecen las herramientas de anotación debajo de la selección. Dibuja lo que necesites.
4. Ctrl+C para copiar, Ctrl+S para guardar, Esc para cancelar. Al copiar o guardar te avisa con una notificación.

## Ejecutar desde el código fuente

Si prefieres correrlo en local o quieres contribuir, solo necesitas Python 3.10 o superior en Windows:

```
git clone https://github.com/Cris223511/screenshot-plus.git
cd screenshot-plus
pip install -r requirements.txt
python main.py
```

## Generar el ejecutable

```
scripts\build.bat
```

El script instala PyInstaller si hace falta, convierte el logo al formato de ícono de Windows y deja el ejecutable portable en la carpeta `dist`.

## Requisitos

- Windows 10 u 11. Por el momento la aplicación es exclusiva de Windows.

## Tecnologías

La aplicación está escrita en Python. La interfaz usa PySide6 (Qt), la captura de pantalla corre sobre mss, el procesamiento de imagen sobre Pillow, los atajos globales sobre pynput y la integración con Windows sobre pywin32. El ejecutable se genera con PyInstaller.

## Estructura del proyecto

```
screenshot-plus/
├── main.py            punto de entrada de la aplicación
├── assets/            logo, íconos vectoriales y tipografías
├── docs/              fuente del manual de usuario
├── scripts/           script de construcción del ejecutable
└── src/
    ├── config/        preferencias, rutas y atajos del usuario
    ├── core/          lógica de captura, portapapeles y guardado
    ├── ui/            ventanas, overlays, diálogos, widgets y temas
    ├── i18n/          textos de la interfaz por idioma
    └── utils/         atajos globales, instancia única, actualizaciones
```

## Licencia

Este proyecto se distribuye bajo la licencia MIT: úsalo, modifícalo y compártelo con libertad. El texto completo está en el archivo [LICENSE](LICENSE).

Si la aplicación te resulta útil, una estrella en el repositorio siempre ayuda a que más personas la encuentren.
