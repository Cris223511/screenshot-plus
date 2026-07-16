<p align="center">
  <img src="assets/logo/logo.jpg" alt="logo de Screenshot Plus" width="140">
</p>

<h1 align="center">Screenshot Plus</h1>

<p align="center">
  Herramienta de capturas de pantalla para Windows. Captura, anota, pixela, une páginas largas con scroll
  y presenta con zoom en vivo y puntero láser. Un solo ejecutable portable, gratuito y de código abierto.
</p>

<p align="center">
  <a href="README.md">Español</a> · <a href="README.en.md">English</a>
</p>

<p align="center">
  <a href="https://github.com/Cris223511/screenshot-plus/releases/latest"><img src="https://img.shields.io/github/v/release/Cris223511/screenshot-plus?label=versi%C3%B3n&color=2f7df6" alt="última versión"></a>
  <a href="https://github.com/Cris223511/screenshot-plus/releases"><img src="https://img.shields.io/github/downloads/Cris223511/screenshot-plus/total?label=descargas&color=2f7df6" alt="descargas"></a>
  <img src="https://img.shields.io/badge/Windows-10%20%7C%2011-2f7df6" alt="windows 10 y 11">
  <img src="https://img.shields.io/badge/Python-3.10%2B-2f7df6" alt="python 3.10 o superior">
  <a href="LICENSE"><img src="https://img.shields.io/badge/licencia-MIT-green" alt="licencia MIT"></a>
</p>

---

## Por qué

Tomar una captura, marcarla con una flecha y mandarla no debería requerir tres programas ni una suscripción. Las herramientas que hacen esto bien suelen ser de pago, meter marca de agua o vivir llenas de anuncios; las gratuitas se quedan cortas al anotar, al capturar páginas con scroll o al presentar en vivo. Screenshot Plus junta todo ese flujo en un único ejecutable portable, sin instalación, sin cuenta, sin nada de pago dentro.

## Descargas

| Versión | Archivo | Estado |
| ------- | ------- | ------ |
| 1.2.2 | [ScreenshotPlus.exe](https://github.com/Cris223511/screenshot-plus/releases/download/v1.2.2/ScreenshotPlus.exe) | Disponible |

Basta con descargar el `.exe` y ejecutarlo. No hay instalador ni pasos adicionales; todas las versiones viven en la sección de [releases](https://github.com/Cris223511/screenshot-plus/releases) y los cambios de cada una están en el [historial de cambios](CHANGELOG.md).

> **Nota sobre el aviso de Windows SmartScreen.** La primera vez que ejecutes el archivo, Windows puede mostrar "Windows protegió su PC" con editor desconocido. Es lo normal en cualquier ejecutable open source sin certificado de firma de código, que es un servicio de pago, y no señala ningún problema con la aplicación, cuyo código completo puedes revisar en este repositorio. Pulsa **Más información** y luego **Ejecutar de todas formas**. El aviso se va con el tiempo, a medida que más personas usan el mismo archivo.

## Características

### Captura

- Región (Alt + A). La pantalla se congela, arrastras sobre la zona y al soltar se abre el editor de anotaciones. La selección se mueve y se redimensiona antes de que decidas.
- Pantalla completa (Alt + S) y ventana activa (Alt + W). El mismo editor, con la zona ya elegida sola. Anotas si quieres y eliges entre copiar o guardar.
- Captura con desplazamiento (Alt + D). Marcas la zona, el resto de la pantalla se bloquea con un velo, y a medida que haces scroll la aplicación cose el contenido en una sola imagen larga con vista previa en vivo. La costura aguanta el ruido visual, como el suavizado de fuentes o el parpadeo del cursor, y descarta los fotogramas repetidos. Al final, la imagen se abre en un editor con scroll.
- Todo se captura a la resolución nativa del monitor, sin pérdida, incluso con el escalado de Windows al 125 o 150 %.
- El panel de la aplicación se aparta solo al capturar, así que nunca sale en tus fotos.

### Editor de anotaciones

- Ocho formas, del rectángulo y el rectángulo redondeado a la elipse, el triángulo, el rombo, el pentágono, el hexágono y la estrella.
- Líneas y flechas con remate configurable en cada extremo por separado (nada, flecha, flecha rellena, punto, cuadrado o rombo) y cinco estilos de trazo (continuo, discontinuo, punteado, guion-punto y guion-punto-punto).
- Pincel de trazo libre con grosor ajustable, y con Shift el trazo sale recto.
- Texto con todas las tipografías del sistema, tamaño, negrita, cursiva, subrayado, tachado, espaciado de letras, rotación, fondo (sólido o redondeado con su color), sombra y contorno. Un clic lo selecciona y el doble clic reedita su contenido.
- Pincel de ocultar para tapar correos, números o cualquier dato sensible. Se pinta como un trazo y, al soltar, queda pixelado o difuminado, con intensidad y grosor a tu elección. También hay opacidad para cualquier elemento e imágenes pegadas con Ctrl + V.
- Borrador para quitar anotaciones al tocarlas, con grosor configurable.
- Selección múltiple. Shift + clic suma o quita elementos, o los rodeas con un recuadro elástico, y los editas o borras a todos a la vez. La barra muestra solo las opciones comunes a lo que tengas seleccionado.
- Edición posterior. Cualquier elemento ya dibujado se selecciona, se mueve, se redimensiona por sus tiradores y cambia de color, grosor o estilo desde la misma barra, en vivo. Al terminar de dibujarlo queda seleccionado, listo para acomodar.
- Modificadores al estilo de un editor de diseño. Shift endereza líneas en pasos de 15°, hace formas proporcionadas, conserva la proporción al estirar y mueve en recto; Alt crece desde el centro; Alt + arrastre duplica el elemento.
- Atajos de letra para cambiar de herramienta al vuelo (V selección, S formas, L línea, F flecha, B pincel, T texto, P ocultar, E borrador).
- Deshacer (Ctrl + Z, con los movimientos incluidos), rehacer (Ctrl + Y), borrar elemento (Supr), restaurar todo, copiar (Ctrl + C) y guardar (Ctrl + S).

### Pizarra de presentación

Pensada para clases y reuniones. Es un panel lateral flotante que pausa la pantalla cuando lo necesitas, la convierte en pizarra y la devuelve intacta al salir.

- Panel lateral con las letras de atajo a la vista (y configurables), arrastrable a cualquier borde y con opción de minimizar a un chip flotante.
- Las herramientas van del zoom con la rueda (Z) a la selección con recuadro elástico y edición por tiradores (V), la mano (H), el borrador (E), el pincel (P), la línea (I), la flecha (F), las formas (S, que rotan entre las ocho al repetir), el texto (T), el resaltador (R) y el puntero láser con estela configurable (L).
- Al costado hay una ventanita de propiedades con los colores (recientes y código hex), grosor, estilos de trazo, extremos de flecha, opacidad y las opciones completas de texto. Con algo seleccionado carga sus valores y lo edita en vivo, incluso varios a la vez.
- Imágenes insertadas desde archivo o pegadas con Ctrl + V, que luego mueves y estiras.
- Con el panel minimizado, cada herramienta responde con Alt + su letra desde cualquier ventana.
- Deshacer y rehacer por acciones, que también reviven lo borrado y lo limpiado.
- Captura integrada. Ctrl + C copia toda la pizarra con los dibujos, Ctrl + S la guarda y Ctrl + A recorta solo un pedazo.

### Aplicación

- Atajos globales activos en todo momento, incluso sobre juegos y navegadores a pantalla completa, y todos personalizables. Solo la pizarra de presentación se calla ante un juego o una app a pantalla completa, no ante un navegador.
- Nueve idiomas, del español por defecto al inglés, el portugués, el francés, el alemán, el italiano, el japonés, el chino y el ruso. El cambio se aplica al instante, sin reiniciar.
- Catorce formatos de guardado, entre ellos PNG, JPG, JPEG, JFIF, WEBP, GIF, AVIF, BMP, TIFF, TIF, HEIC, HEIF, ICO y TGA, con calidad ajustable donde aplica y opción de abrir la carpeta al guardar.
- Tema claro y oscuro, panel siempre adelante con pin, notificaciones y tooltips animados propios.
- Instancia única. Ejecutar el `.exe` dos veces no duplica la app, trae la que ya corre.
- Arranque con Windows, que abre minimizado en la bandeja, y arranque directo a la bandeja, los dos opcionales.
- Restablecer la configuración desde Opciones, sin borrar ninguna captura ni cambiar tu carpeta de guardado.
- Comprobación de actualizaciones contra las releases de este repositorio, sin servidores propios ni telemetría.
- Manual de usuario y acerca de integrados, así que nada te saca de la aplicación.
- La carpeta de guardado se recuerda entre sesiones; la última que uses será la próxima en abrirse.

## Atajos por defecto

| Acción | Atajo |
| ------ | ----- |
| Capturar región | Alt + A |
| Capturar pantalla completa | Alt + S |
| Capturar ventana actual | Alt + W |
| Captura con desplazamiento | Alt + D |
| Panel de presentación | Alt + Z |
| Mostrar u ocultar el panel | Alt + Q |
| Copiar / guardar en el editor | Ctrl + C / Ctrl + S |
| Deshacer / borrar elemento | Ctrl + Z / Supr |

Todos los atajos globales se cambian desde Opciones → Acceso rápido, con solo pulsar la combinación nueva.

## Uso

1. Abre `ScreenshotPlus.exe`. El panel aparece y la app queda viva en la bandeja del sistema.
2. Alt + A, arrastra sobre la zona, anota lo que necesites con la barra de herramientas.
3. Ctrl + C para copiar o Ctrl + S para guardar. Una notificación confirma. Esc cancela en cualquier punto.

## Ejecutar desde el código fuente

Solo hace falta Python 3.10 o superior en Windows:

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

El script instala PyInstaller si hace falta, convierte el logo al formato de ícono de Windows y deja `ScreenshotPlus.exe` en la carpeta `dist`.

## Tecnologías

| Componente | Librería | Para qué |
| ---------- | -------- | -------- |
| Interfaz | [PySide6](https://doc.qt.io/qtforpython-6/) (Qt) | Ventanas, overlays, animaciones, temas, bandeja |
| Captura | [mss](https://github.com/BoboTiG/python-mss) | Lectura del framebuffer a resolución nativa, multimonitor |
| Imagen | [Pillow](https://python-pillow.org/) | Costura de la captura larga, exportación, ícono |
| Atajos globales | [pynput](https://github.com/moses-palmer/pynput) | Teclas que funcionan con la app en segundo plano |
| Integración Windows | [pywin32](https://github.com/mhammond/pywin32) + ctypes | Ventana activa, registro, exclusión de captura |
| Empaquetado | [PyInstaller](https://pyinstaller.org/) | El ejecutable portable único |

Un detalle técnico del que estamos orgullosos. El zoom en vivo funciona porque las ventanas de la aplicación se excluyen de la captura del sistema (`WDA_EXCLUDEFROMCAPTURE`), y eso permite fotografiar la pantalla 25 veces por segundo sin que la app se vea a sí misma.

## Estructura del proyecto

```
screenshot-plus/
├── main.py                     punto de entrada, control de instancia única
├── assets/
│   ├── icons/                  íconos SVG propios de la interfaz
│   └── logo/                   logo de la aplicación
├── docs/manual.md              manual de usuario (se muestra dentro de la app)
├── scripts/build.bat           construcción del ejecutable
└── src/
    ├── config/                 preferencias, rutas seguras y atajos
    ├── core/                   captura, costura de scroll, portapapeles, guardado
    ├── i18n/                   traductor y los 9 idiomas en json
    ├── ui/
    │   ├── overlays/           selección con editor, modo presentación, panel flotante
    │   ├── dialogs/            opciones, acerca de, manual, idioma
    │   ├── widgets/            botones animados, paleta, íconos
    │   └── themes/             tema claro y oscuro (qss)
    └── utils/                  atajos globales, instancia única, autoarranque, updater
```

## Configuración y datos

- Las preferencias se guardan en `%APPDATA%\ScreenshotPlus\settings.json`.
- Las capturas van por defecto a una subcarpeta `Screenshot Plus` dentro de tu carpeta Imágenes real (consultada a Windows, funciona en cualquier idioma del sistema).
- La aplicación no recopila ningún dato ni se conecta a internet, salvo cuando tú pides comprobar actualizaciones (una consulta a la API pública de GitHub).

## Contribuir

Los reportes de errores y las ideas son bienvenidos en los [issues](https://github.com/Cris223511/screenshot-plus/issues). Si quieres aportar código, abre un pull request; el proyecto corre con `python main.py` sin ninguna configuración extra.

## Licencia

MIT © [Cris223511](https://github.com/Cris223511). Úsalo, modifícalo y compártelo con libertad; el texto completo está en [LICENSE](LICENSE).

Si la aplicación te resulta útil, una estrella en el repositorio ayuda a que más personas la encuentren.
