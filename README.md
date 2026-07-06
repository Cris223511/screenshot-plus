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
| 1.0.0 | [ScreenshotPlus.exe](https://github.com/Cris223511/screenshot-plus/releases/download/v1.0.0/ScreenshotPlus.exe) | Disponible |

Basta con descargar el `.exe` y ejecutarlo. No hay instalador ni pasos adicionales; todas las versiones viven en la sección de [releases](https://github.com/Cris223511/screenshot-plus/releases).

> **Nota sobre el aviso de Windows SmartScreen.** La primera vez que ejecutes el archivo, Windows puede mostrar "Windows protegió su PC" con editor desconocido. Es el comportamiento normal para cualquier ejecutable open source sin certificado de firma de código (que es un servicio de pago); no indica ningún problema con la aplicación, cuyo código completo puedes revisar en este repositorio. Para continuar: **Más información → Ejecutar de todas formas**. El aviso desaparece con el tiempo a medida que más personas usan el mismo archivo.

## Características

### Captura

- **Región** (Alt + A): la pantalla se congela, arrastras sobre la zona y al soltar se abre el editor de anotaciones. La selección se puede mover y redimensionar antes de decidir.
- **Pantalla completa** (Alt + S) y **ventana activa** (Alt + W): directo al portapapeles, con notificación.
- **Captura con desplazamiento** (Alt + D): eliges la zona, el resto de la pantalla queda bloqueado con un velo, y mientras haces scroll la aplicación une el contenido en una sola imagen larga con vista previa en vivo. La costura tolera ruido visual (suavizado de fuentes, cursores parpadeando) y descarta fotogramas repetidos. Al finalizar, la imagen se abre en un editor con scroll.
- Todo se captura a **resolución nativa del monitor**, sin pérdida, incluso con escalado de Windows al 125 o 150 %.
- El panel de la aplicación se aparta solo al capturar: nunca sale en tus fotos.

### Editor de anotaciones

- **Formas** (8): rectángulo, rectángulo redondeado, elipse, triángulo, rombo, pentágono, hexágono y estrella.
- **Líneas y flechas** con remate configurable en cada extremo por separado (nada, flecha, flecha rellena, punto, cuadrado, rombo) y trazo continuo, discontinuo o punteado.
- **Pincel** de trazo libre con grosor ajustable.
- **Texto** con más de 25 tipografías en desplegable, tamaño, negrita, cursiva y color. Se escribe directo sobre la imagen; doble clic reabre un texto existente.
- **Pixelado** para ocultar correos, números o cualquier dato sensible.
- **Edición posterior**: cualquier elemento ya dibujado se selecciona, se mueve, se redimensiona por sus tiradores y se le cambia color, grosor o estilo desde la misma barra, en vivo.
- Deshacer (Ctrl + Z), borrar elemento (Supr), restaurar todo, copiar (Ctrl + C) y guardar (Ctrl + S).

### Modo presentación

Pensado para clases y reuniones, con la pantalla **en vivo**: nada se congela, los videos siguen corriendo.

- **Panel lateral flotante** con bordes redondeados, arrastrable a cualquier borde y fijable siempre adelante con su pin.
- **Zoom en vivo** (Z): amplía lo que está pasando alrededor del cursor, con la rueda o las teclas + y -.
- **Puntero láser** (L) con estela que se desvanece; color, tamaño y estela configurables en Opciones.
- **Pincel** (P), **resaltador** (R), **línea** (I) y **flecha** (F) para marcar sobre la pantalla; C limpia todo.

### Aplicación

- **Atajos globales** funcionando aunque la app esté en la bandeja, todos personalizables.
- **6 idiomas**: español (por defecto), inglés, portugués, francés, alemán e italiano. El cambio se aplica al instante, sin reiniciar.
- **Tema claro y oscuro**, panel siempre adelante con pin, notificaciones animadas propias.
- **Instancia única**: ejecutar el `.exe` dos veces no duplica la app, trae la que ya corre.
- **Arranque con Windows** y arranque minimizado en la bandeja, opcionales.
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
    ├── i18n/                   traductor y los 6 idiomas en json
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
