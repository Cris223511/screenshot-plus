<p align="center">
  <img src="assets/logo/logo.jpg" alt="logo de Screenshot Plus" width="140">
</p>

<h1 align="center">Screenshot Plus</h1>

<p align="center">
  Herramienta de capturas de pantalla para Windows: captura, anota, pixela, une páginas largas con scroll
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
| 1.2.0 | [ScreenshotPlus.exe](https://github.com/Cris223511/screenshot-plus/releases/download/v1.2.0/ScreenshotPlus.exe) | Disponible |

Basta con descargar el `.exe` y ejecutarlo. No hay instalador ni pasos adicionales; todas las versiones viven en la sección de [releases](https://github.com/Cris223511/screenshot-plus/releases) y los cambios de cada una están en el [historial de cambios](CHANGELOG.md).

> **Nota sobre el aviso de Windows SmartScreen.** La primera vez que ejecutes el archivo, Windows puede mostrar "Windows protegió su PC" con editor desconocido. Es el comportamiento normal para cualquier ejecutable open source sin certificado de firma de código (que es un servicio de pago); no indica ningún problema con la aplicación, cuyo código completo puedes revisar en este repositorio. Para continuar: **Más información → Ejecutar de todas formas**. El aviso desaparece con el tiempo a medida que más personas usan el mismo archivo.

## Características

### Captura

- **Región** (Alt + A): la pantalla se congela, arrastras sobre la zona y al soltar se abre el editor de anotaciones. La selección se puede mover y redimensionar antes de decidir.
- **Pantalla completa** (Alt + S) y **ventana activa** (Alt + W): el mismo editor, con la zona ya seleccionada automáticamente; anotas si quieres y decides entre copiar o guardar.
- **Captura con desplazamiento** (Alt + D): eliges la zona, el resto de la pantalla queda bloqueado con un velo, y mientras haces scroll la aplicación une el contenido en una sola imagen larga con vista previa en vivo. La costura tolera ruido visual (suavizado de fuentes, cursores parpadeando) y descarta fotogramas repetidos. Al finalizar, la imagen se abre en un editor con scroll.
- Todo se captura a **resolución nativa del monitor**, sin pérdida, incluso con escalado de Windows al 125 o 150 %.
- El panel de la aplicación se aparta solo al capturar: nunca sale en tus fotos.

### Editor de anotaciones

- **Formas** (8): rectángulo, rectángulo redondeado, elipse, triángulo, rombo, pentágono, hexágono y estrella.
- **Líneas y flechas** con remate configurable en cada extremo por separado (nada, flecha, flecha rellena, punto, cuadrado, rombo) y cinco estilos de trazo (continuo, discontinuo, punteado, guion-punto, guion-punto-punto).
- **Pincel** de trazo libre con grosor ajustable; con Shift el trazo sale recto.
- **Texto** con todas las tipografías del sistema, tamaño, negrita, cursiva, subrayado, tachado, espaciado de letras, rotación, fondo (sólido o redondeado con su color), sombra y contorno. Un clic lo selecciona, doble clic reedita su contenido.
- **Pincel de ocultar** para tapar correos, números o cualquier dato sensible: se pinta como un trazo y al soltar queda **pixelado o difuminado**, con intensidad y grosor a elección. También **opacidad** para cualquier elemento e **imágenes** pegadas con Ctrl + V.
- **Borrador** para quitar anotaciones tocándolas, con grosor configurable.
- **Selección múltiple**: Shift + clic suma o quita elementos, o los rodeas con un recuadro elástico, y los editas o borras a todos a la vez. La barra muestra solo las opciones comunes a lo seleccionado.
- **Edición posterior**: cualquier elemento ya dibujado se selecciona, se mueve, se redimensiona por sus tiradores y se le cambia color, grosor o estilo desde la misma barra, en vivo. Al terminar de dibujar queda seleccionado, listo para acomodar.
- **Modificadores estilo diseño**: Shift endereza líneas (pasos de 15°), hace formas proporcionadas, conserva la proporción al estirar y mueve en recto; Alt crece desde el centro; Alt + arrastre duplica el elemento.
- **Atajos de letra** para cambiar de herramienta al vuelo (V selección, S formas, L línea, F flecha, B pincel, T texto, P ocultar, E borrador).
- Deshacer (Ctrl + Z, movimientos incluidos), rehacer (Ctrl + Y), borrar elemento (Supr), restaurar todo, copiar (Ctrl + C) y guardar (Ctrl + S).

### Pizarra de presentación

Pensada para clases y reuniones: un panel lateral flotante que pausa la pantalla cuando lo necesitas, la convierte en pizarra y la devuelve intacta al salir.

- **Panel lateral** con letras de atajo visibles (y configurables), arrastrable a cualquier borde y con minimizar a un chip flotante.
- **Herramientas**: zoom con la rueda (Z), selección con recuadro elástico y edición por tiradores (V), mano (H), borrador (E), pincel (P), línea (I), flecha (F), formas (S, repetir rota entre las ocho), texto (T), resaltador (R) y puntero láser con estela configurable (L).
- **Ventanita de propiedades** al costado: colores con recientes y código hex, grosor, estilos de trazo, extremos de flecha, opacidad y las opciones completas de texto; con algo seleccionado carga sus valores y lo edita en vivo, incluso varios a la vez.
- **Imágenes insertadas** desde archivo o pegadas con Ctrl + V, movibles y estirables.
- **Con el panel minimizado**, cada herramienta responde con Alt + su letra desde cualquier ventana.
- **Deshacer y rehacer por acciones**: también reviven lo borrado y lo limpiado.
- **Captura integrada**: Ctrl + C copia toda la pizarra con los dibujos, Ctrl + S la guarda, y Ctrl + A recorta solo un pedazo.

### Aplicación

- **Atajos globales** funcionando en todo momento, incluso sobre juegos y navegadores a pantalla completa; todos personalizables. Solo la pizarra de presentación se calla ante un juego o app a pantalla completa (no ante un navegador).
- **9 idiomas**: español (por defecto), inglés, portugués, francés, alemán, italiano, japonés, chino y ruso. El cambio se aplica al instante, sin reiniciar.
- **14 formatos de guardado**: PNG, JPG, JPEG, JFIF, WEBP, GIF, AVIF, BMP, TIFF, TIF, HEIC, HEIF, ICO y TGA, con calidad ajustable donde aplica y opción de abrir la carpeta al guardar.
- **Tema claro y oscuro**, panel siempre adelante con pin, notificaciones y tooltips animados propios.
- **Instancia única**: ejecutar el `.exe` dos veces no duplica la app, trae la que ya corre.
- **Arranque con Windows** (que abre minimizado en la bandeja) y arranque directo a la bandeja, opcionales.
- **Restablecer la configuración** desde Opciones, sin borrar ninguna captura ni cambiar tu carpeta de guardado.
- **Comprobación de actualizaciones** contra las releases de este repositorio, sin servidores propios ni telemetría.
- **Manual de usuario y acerca de integrados**: nada te redirige fuera de la aplicación.
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

Todos los atajos globales se cambian desde Opciones → Acceso rápido, presionando la combinación nueva.

## Uso en 20 segundos

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

Un detalle técnico del que estamos orgullosos: el zoom en vivo funciona porque las ventanas de la aplicación se excluyen de la captura del sistema (`WDA_EXCLUDEFROMCAPTURE`), lo que permite fotografiar la pantalla 25 veces por segundo sin que la app se vea a sí misma.

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
