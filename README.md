<p align="center">
  <img src="assets/logo/logo.jpg" alt="logo de Screenshot Plus" width="140">
</p>

<h1 align="center">Screenshot Plus</h1>

<p align="center">
  Herramienta de capturas de pantalla para Windows, con zoom en vivo, anotaciones y atajos de teclado.
</p>

---

## ¿Qué es Screenshot Plus?

Screenshot Plus es una aplicación de escritorio pensada para que tomar una captura sea cuestión de un atajo y nada más. Presionas la tecla, seleccionas la zona arrastrando el mouse, y con Ctrl+C ya la tienes copiada o con Ctrl+S guardada en tu carpeta de siempre. Sin pasos intermedios ni ventanas que estorben.

Además de capturar, incluye un modo pensado para presentaciones: puedes hacer zoom sobre cualquier parte de la pantalla, señalar con un puntero láser, subrayar, dibujar líneas y trazos libres con la paleta de colores, todo en vivo y controlado por teclado.

Es un único ejecutable. Lo abres y ya está funcionando: no requiere instalación, y si lo cierras sigue activo en la bandeja del sistema, listo para el siguiente atajo.

## Características

- Captura por región, pantalla completa o ventana activa, siempre a resolución nativa.
- Captura con desplazamiento: mantienes el scroll y la app va uniendo el contenido en una sola imagen larga, con vista previa en vivo y sin pérdida de calidad.
- Copiado al portapapeles y guardado a disco con atajos, con notificación de confirmación.
- La carpeta de guardado se recuerda entre sesiones; la última que uses será la próxima en abrirse.
- Modo presentación: zoom sobre la pantalla, puntero láser, subrayado y dibujo a mano alzada.
- Barra de herramientas flotante con bordes redondeados y animaciones, reposicionable en cualquier borde de la pantalla y alternable con una tecla.
- Atajos de teclado personalizables desde las opciones.
- Temas de color personalizables.
- Comprobación de actualizaciones contra las versiones publicadas en este repositorio.
- Manual de usuario y ventana de acerca de integrados en la propia aplicación.
- Preparada para varios idiomas; por ahora disponible en español.

## Requisitos

- Windows 10 u 11. Por el momento la aplicación es exclusiva de Windows.

## Uso

La forma recomendada será descargar el ejecutable desde la sección de versiones (releases) de este repositorio cuando esté publicado. Mientras tanto, se puede ejecutar desde el código fuente:

```
git clone https://github.com/Cris223511/screenshot-plus.git
cd screenshot-plus
pip install -r requirements.txt
python main.py
```

Para generar el ejecutable portable:

```
scripts\build.bat
```

El resultado queda en la carpeta `dist`.

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

## Estado del proyecto

En desarrollo activo. Las funcionalidades descritas arriba corresponden al alcance de la primera versión.

## Licencia

Este proyecto se distribuye bajo la licencia MIT. El texto completo está en el archivo [LICENSE](LICENSE).

Si la aplicación te resulta útil, una estrella en el repositorio siempre ayuda a que más personas la encuentren.
