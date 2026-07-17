<p align="center">
  <img src="assets/logo/logo.jpg" alt="logo de Screenshot Plus" width="140">
</p>

<h1 align="center">Screenshot Plus</h1>

<p align="center">
  Herramienta de capturas de pantalla para Windows. Captura, anota, oculta información,
  une páginas largas mediante scroll y presenta con zoom en vivo y puntero láser.
  Un solo ejecutable portable, gratuito y de código abierto.
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

Tomar una captura, marcarla con una flecha y enviarla no debería exigir tres programas ni una suscripción. Las herramientas que resuelven bien esta tarea suelen ser de pago, añaden una marca de agua o están cargadas de anuncios. Las gratuitas se quedan cortas al momento de anotar, de capturar una página completa con scroll o de presentar en vivo. Screenshot Plus reúne todo ese flujo en un único ejecutable portable, sin instalación, sin cuenta de usuario y sin funciones de pago.

## Descargas

| Versión | Archivo | Estado |
| ------- | ------- | ------ |
| 1.2.6 | [ScreenshotPlus.exe](https://github.com/Cris223511/screenshot-plus/releases/download/v1.2.6/ScreenshotPlus.exe) | Disponible |

Solo hay que descargar el `.exe` y ejecutarlo. No existe instalador ni pasos adicionales. Todas las versiones están en la sección de [releases](https://github.com/Cris223511/screenshot-plus/releases) y los cambios de cada una se detallan en el [historial de cambios](CHANGELOG.md).

> **Sobre el aviso de Windows SmartScreen.** La primera vez que ejecutes el archivo, Windows puede mostrar el mensaje "Windows protegió su PC" e indicar un editor desconocido. Es el comportamiento normal ante cualquier programa cuyo autor no ha pagado un certificado de firma de código, un servicio de pago que sirve para que Windows reconozca al desarrollador. No significa que el archivo tenga algún problema, y su código fuente completo está disponible en este repositorio para quien quiera revisarlo. Para abrirlo, pulsa **Más información** y luego **Ejecutar de todas formas**. El aviso deja de aparecer con el tiempo, a medida que más personas descargan y ejecutan el mismo archivo.

## Características

### Captura

- **Región (Alt + A):** la pantalla se congela y arrastras el cursor para dibujar un rectángulo sobre la zona que quieres capturar. Al soltar, se abre el editor de anotaciones. Antes de continuar, ese rectángulo se puede desplazar y cambiar de tamaño para ajustar la selección con precisión.
- **Pantalla completa (Alt + S) y ventana activa (Alt + W):** abren el mismo editor con la zona ya seleccionada, la pantalla entera en un caso y la ventana que tenías en primer plano en el otro. Anotas si lo necesitas y luego eliges entre copiar o guardar.
- **Captura con desplazamiento (Alt + D):** sirve para capturar contenido que no cabe en pantalla, como una página web o un documento largo. Eliges la zona, el resto de la pantalla queda cubierto por una capa oscura, y a medida que desplazas el contenido con la rueda del ratón la aplicación une cada porción visible en una sola imagen larga, con una vista previa que se actualiza en tiempo real. La unión tolera el ruido visual habitual, como el suavizado de las letras o el parpadeo del cursor, y descarta las porciones repetidas para no duplicar contenido. Al terminar, la imagen se abre en un editor con scroll.
- **Resolución nativa:** toda captura se toma a la resolución nativa del monitor, sin pérdida de calidad, incluso cuando Windows aplica un escalado del 125 o 150 %.
- **Panel fuera de la imagen:** la ventana de la propia aplicación queda excluida de la captura a nivel del sistema operativo. Aunque el panel esté visible en pantalla en el momento de capturar, no aparece en la imagen resultante, así que no hace falta apartarlo ni cerrarlo antes.

### Editor de anotaciones

- **Ocho formas:** rectángulo, rectángulo redondeado, elipse, triángulo, rombo, pentágono, hexágono y estrella.
- **Líneas y flechas:** con el remate de cada extremo configurable por separado (sin remate, flecha, flecha rellena, punto, cuadrado o rombo) y cinco estilos de trazo (continuo, discontinuo, punteado, guion-punto y guion-punto-punto).
- **Pincel:** de trazo libre con grosor ajustable. Al mantener Shift, el trazo sale recto.
- **Texto:** con todas las tipografías instaladas en el sistema, más tamaño, negrita, cursiva, subrayado, tachado, espaciado entre letras, rotación, color de fondo (sólido o con esquinas redondeadas), sombra y contorno. Un clic selecciona el texto y un doble clic vuelve a abrirlo para editar su contenido.
- **Herramienta de ocultar:** cubre cualquier parte de la imagen. Se pinta sobre la zona y, al soltar, esa zona queda pixelada o difuminada, con la intensidad y el grosor que elijas.
- **Opacidad e imágenes:** opacidad regulable en cualquier elemento e imágenes pegadas desde el portapapeles con Ctrl + V.
- **Borrador:** elimina las anotaciones que toca, con grosor configurable.
- **Selección múltiple:** con Shift y un clic se añaden o se quitan elementos uno a uno, y también se pueden encerrar varios al trazar un rectángulo de selección con el ratón. Los elementos seleccionados se editan o se borran en conjunto, y la barra de herramientas muestra solo las opciones que tienen en común.
- **Edición posterior:** cualquier elemento ya dibujado se puede volver a seleccionar para moverlo, cambiarle el tamaño desde sus tiradores o modificar su color, grosor y estilo desde la misma barra, con el cambio reflejado al instante. Al terminar de dibujar un elemento queda seleccionado, listo para reubicarlo.
- **Modificadores al estilo de un editor de diseño:** Shift endereza las líneas en pasos de 15 grados, mantiene las proporciones de las formas y de los elementos al redimensionar, y restringe el movimiento a la horizontal o la vertical. Alt hace crecer la forma desde su centro. Alt junto con arrastrar duplica el elemento.
- **Atajos de una letra:** cambian de herramienta sin ir a la barra (V selección, S formas, L línea, F flecha, B pincel, T texto, P ocultar, E borrador).
- **Deshacer, rehacer y edición:** deshacer (Ctrl + Z, que incluye los movimientos), rehacer (Ctrl + Y), borrar el elemento seleccionado (Supr), restaurar todo, copiar (Ctrl + C) y guardar (Ctrl + S).

### Pizarra de presentación

Pensada para clases y reuniones. Es un panel lateral que permanece flotante sobre las demás ventanas. Cuando activas una herramienta, congela la imagen de la pantalla y la convierte en una pizarra sobre la que dibujar. Al salir, la pantalla vuelve a su estado normal, sin ninguna marca.

- **Panel lateral:** muestra la letra de atajo de cada herramienta (letras que se pueden reasignar). Se arrastra a cualquier borde de la pantalla y se reduce a un pequeño botón flotante cuando no lo usas.
- **Herramientas:** zoom con la rueda del ratón (Z), selección y edición por tiradores (V), mano para desplazar la vista (H), borrador (E), pincel (P), línea (I), flecha (F), formas (T para texto y S para las formas geométricas; cada pulsación de S pasa a la siguiente de las ocho formas disponibles), resaltador (R) y puntero láser con estela de longitud configurable (L).
- **Panel de propiedades:** junto a la barra, con los colores usados hace poco y un campo para el código hexadecimal, el grosor, los estilos de trazo, los remates de flecha, la opacidad y todas las opciones de texto. Si hay algo seleccionado, el panel carga sus valores y los cambios se aplican en vivo, incluso sobre varios elementos a la vez.
- **Imágenes:** insertadas desde un archivo o pegadas con Ctrl + V, que después se mueven y se redimensionan.
- **Atajos con el panel reducido:** aunque el panel esté convertido en su botón flotante, cada herramienta responde igual con Alt más su letra desde cualquier ventana.
- **Deshacer y rehacer:** por acciones, con la posibilidad de recuperar lo borrado y lo que se limpió de golpe.
- **Captura integrada:** Ctrl + C copia la pizarra completa con los dibujos, Ctrl + S la guarda y Ctrl + A recorta y guarda solo la parte que selecciones.

### Aplicación

- **Atajos globales:** activos en todo momento, incluso sobre juegos y navegadores a pantalla completa, y todos personalizables. Solo la pizarra de presentación se desactiva ante un juego o una aplicación a pantalla completa; ante un navegador a pantalla completa sigue disponible.
- **Nueve idiomas:** español (predeterminado), inglés, portugués, francés, alemán, italiano, japonés, chino y ruso. El cambio se aplica al instante, sin reiniciar la aplicación.
- **Catorce formatos de guardado:** PNG, JPG, JPEG, JFIF, WEBP, GIF, AVIF, BMP, TIFF, TIF, HEIC, HEIF, ICO y TGA, con calidad ajustable en los que lo permiten y la opción de abrir la carpeta al terminar de guardar.
- **Apariencia:** tema claro y oscuro, un botón para mantener el panel siempre por encima de las demás ventanas, y notificaciones y descripciones emergentes con animación propia.
- **Instancia única:** ejecutar el `.exe` una segunda vez no abre otra copia, sino que trae al frente la que ya está en marcha.
- **Arranque con Windows:** abre la aplicación minimizada en la bandeja del sistema. Existe además un arranque directo a la bandeja. Ambas opciones se activan a voluntad.
- **Restablecer la configuración:** desde Opciones, sin borrar ninguna captura ni cambiar la carpeta de guardado.
- **Actualizaciones desde la propia aplicación:** comprueba si hay una versión nueva en las releases de este repositorio y, cuando la hay, la descarga e instala sin salir de la aplicación, que se reinicia ya actualizada. Sin servidores propios ni recopilación de datos.
- **Historial de versiones integrado:** una ventana lista todas las versiones publicadas, con su fecha y sus notas, obtenidas de la API pública de GitHub.
- **Manual e información integrados:** manual de usuario y ventana de información dentro de la propia aplicación. Ningún enlace te lleva fuera, salvo el que abre el repositorio.
- **Carpeta recordada:** la carpeta de guardado se conserva entre sesiones. La última que uses será la que se ofrezca la próxima vez.

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

1. Abre `ScreenshotPlus.exe`. Aparece el panel y la aplicación queda activa en la bandeja del sistema.
2. Pulsa Alt + A, arrastra sobre la zona y anota lo que necesites con la barra de herramientas.
3. Usa Ctrl + C para copiar o Ctrl + S para guardar. Una notificación confirma la acción. Esc cancela en cualquier momento.

## Ejecutar desde el código fuente

Solo hace falta Python 3.10 o superior en Windows.

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

| Componente | Librería | Para qué se usa |
| ---------- | -------- | --------------- |
| Interfaz | [PySide6](https://doc.qt.io/qtforpython-6/) (Qt) | Ventanas, capas superpuestas, animaciones, temas y bandeja |
| Captura | [mss](https://github.com/BoboTiG/python-mss) | Lectura de la pantalla a resolución nativa, con varios monitores |
| Imagen | [Pillow](https://python-pillow.org/) | Unión de la captura larga, exportación y creación del ícono |
| Atajos globales | [pynput](https://github.com/moses-palmer/pynput) | Teclas que responden con la aplicación en segundo plano |
| Integración con Windows | [pywin32](https://github.com/mhammond/pywin32) y ctypes | Ventana activa, registro y exclusión de captura |
| Empaquetado | [PyInstaller](https://pyinstaller.org/) | El ejecutable portable único |

Un detalle técnico que vale la pena mencionar. El zoom en vivo es posible porque las ventanas de la aplicación se excluyen de la captura del sistema con `WDA_EXCLUDEFROMCAPTURE`. Gracias a eso, la aplicación puede fotografiar la pantalla unas 25 veces por segundo sin capturarse a sí misma en el proceso.

## Estructura del proyecto

```
screenshot-plus/
├── main.py                     punto de entrada y control de instancia única
├── assets/
│   ├── icons/                  íconos SVG propios de la interfaz
│   └── logo/                   logo de la aplicación
├── docs/manual.md              manual de usuario (se muestra dentro de la app)
├── scripts/build.bat           construcción del ejecutable
└── src/
    ├── config/                 preferencias, rutas seguras y atajos
    ├── core/                   captura, unión de scroll, portapapeles y guardado
    ├── i18n/                   traductor y los 9 idiomas en json
    ├── ui/
    │   ├── overlays/           selección con editor, modo presentación y panel flotante
    │   ├── dialogs/            opciones, información, manual e idioma
    │   ├── widgets/            botones animados, paleta e íconos
    │   └── themes/             tema claro y oscuro (qss)
    └── utils/                  atajos globales, instancia única, autoarranque y actualizaciones
```

## Configuración y datos

- **Preferencias:** se guardan en `%APPDATA%\ScreenshotPlus\settings.json`.
- **Capturas:** van por defecto a una subcarpeta `Screenshot Plus` dentro de tu carpeta de Imágenes real, que se consulta a Windows y funciona en cualquier idioma del sistema.
- **Privacidad:** la aplicación no recopila ningún dato ni se conecta a internet, salvo cuando pides comprobar actualizaciones, instalar una versión nueva o ver el historial de versiones, casos en los que consulta la API pública de GitHub.

## Contribuir

Los reportes de errores y las ideas son bienvenidos en los [issues](https://github.com/Cris223511/screenshot-plus/issues). Para aportar código, abre un pull request. El proyecto se ejecuta con `python main.py` sin ninguna configuración adicional.

## Licencia

MIT © [Cris223511](https://github.com/Cris223511). Puedes usarlo, modificarlo y compartirlo con libertad. El texto completo está en el archivo [LICENSE](LICENSE).

Si la aplicación te resulta útil, una estrella en el repositorio ayuda a que más personas la encuentren.
