# Historial de cambios

Este documento recoge los cambios importantes de Screenshot Plus, de la versión más reciente a la más antigua. Cada versión publicada tiene además su entrada en las [releases del repositorio](https://github.com/Cris223511/screenshot-plus/releases), donde se anuncian las descargas.

El formato sigue la convención de [Keep a Changelog](https://keepachangelog.com/es/) y el versionado es [semántico](https://semver.org/lang/es/): el primer número indica cambios mayores, el segundo funciones nuevas y el tercero correcciones.

## 1.2.0 (2026-07-13)

El grueso del trabajo se centra en el editor de la captura de región: se añade la selección múltiple, una herramienta de borrador y un pincel de ocultar reconstruido, junto con mejoras de comportamiento y varias correcciones. La pizarra de presentación y los ajustes generales de la aplicación también reciben cambios.

### Editor de captura

- **Selección múltiple**: con la herramienta de selección, Shift + clic añade o quita elementos, y arrastrar sobre una zona vacía traza un recuadro elástico que selecciona todo lo que abarca.
- **Edición conjunta**: con varios elementos seleccionados, los cambios de color, grosor u opacidad se aplican a todos a la vez, y la tecla Suprimir los elimina en bloque. La barra muestra únicamente las opciones comunes a la selección.
- **Herramienta de borrador** (tecla E): elimina las anotaciones que toca, con grosor configurable.
- **Pincel de ocultar reconstruido**: se dibuja como un trazo y, al soltar, la zona queda pixelada o difuminada, con intensidad y grosor a elección. Deja de acumular efecto al repasar la misma área, no se desborda del contorno y prevalece el trazo superior. No es seleccionable ni se puede mover; se elimina solo con el borrador.
- **Desplazamiento del recorte mediante un tirador dedicado**, en lugar de arrastrar su interior, para evitar moverlo sin querer.
- **Redimensionado más robusto**: el recorte se ajusta respecto a un ancla fija, con un tamaño mínimo y con inversión al sobrepasar el lado opuesto, sin bloquearse. La barra de herramientas lo acompaña en tiempo real.
- **Cursores direccionales** en los tiradores de redimensionado y **lupa de aumento** junto al cursor durante la selección, para precisar el borde.
- **Barra de opciones independiente**: los controles de cada herramienta aparecen en un panel flotante bajo la barra, que ya no se ensancha; y cuando el recorte queda pegado al borde inferior, la barra pasa a disposición vertical en un lateral.
- **Atajos de teclado** para cambiar de herramienta (V selección, S formas, L línea, F flecha, B pincel, T texto, P ocultar, E borrador) y **trazo recto** manteniendo Shift en el pincel y el pincel de ocultar.

### Modo presentación

- Incorpora las mismas mejoras del pincel de ocultar y de la edición conjunta con opciones comunes.
- El trazo de ocultar tampoco se puede mover; solo se elimina con el borrador.
- Los atajos del panel se desactivan únicamente ante juegos y aplicaciones a pantalla completa, no ante un navegador a pantalla completa.

### Aplicación y opciones

- Los atajos de captura funcionan en todo momento, incluso sobre juegos y navegadores a pantalla completa.
- El arranque automático con Windows abre la aplicación minimizada en la bandeja, sin mostrar el panel.
- Nueva opción **Restablecer** en la configuración, que devuelve los ajustes generales a su estado inicial sin eliminar ninguna captura ni modificar la carpeta de guardado. Se añade además un botón para restablecer solo los atajos.
- **Nuevo capturador de atajos**, con un indicador de grabación y la posibilidad de cancelar.
- Las opciones de cada herramienta dejan de guardarse en disco y se reinician en cada sesión; la configuración general sí se conserva.
- El anclaje del panel al frente queda desactivado por defecto y se recuerdan las posiciones de los paneles entre sesiones.
- El desplazamiento del selector de idiomas ahora es suave, con resaltado al pasar el cursor.

### Correcciones

- **Pixelado que se acumulaba**: al repasar la misma zona con el pincel de ocultar, el efecto se intensificaba; ahora se mantiene igual y, al variar la intensidad, prevalece el trazo superior.
- **Difuminado fuera del contorno**: el efecto podía pintarse más allá de la selección; ahora queda recortado a ella.
- **Pincel que rellenaba en negro**: un trazo que se cruzaba consigo mismo rellenaba su interior mientras se dibujaba; ahora solo traza la línea.
- **Redimensionado que se bloqueaba**: al reducir mucho el recorte o cruzar el lado opuesto, el ajuste se trababa; ahora fluye e invierte el sentido, respetando un tamaño mínimo.
- **Panel minimizado que reaparecía**: volvía a mostrarse al capturar, copiar o cerrar; ahora permanece oculto hasta que se abre a propósito.
- **Guardado que cerraba el editor**: Ctrl + S cerraba la edición; ahora el diálogo se abre encima y permite continuar.
- **Esc sin efecto sin selección**: no cancelaba la captura hasta interactuar con el ratón; ahora cancela desde el primer momento.
- **Foco perdido tras capturar**: el foco de teclado no regresaba a la ventana anterior; ahora vuelve a la aplicación en la que estabas.

## 1.1.0 (2026-07-09)

El editor de anotaciones y la pizarra de presentación se amplían de forma considerable, y se suman formatos de guardado e idiomas.

- **Editor de anotaciones ampliado**: ocho formas, líneas y flechas con remate configurable en cada extremo y cinco estilos de trazo; texto con todas las tipografías del sistema, además de subrayado, tachado, espaciado, rotación, fondo, sombra y contorno; opacidad e imágenes pegadas. Todo elemento queda seleccionado al dibujarlo y se edita en tiempo real, con Shift para enderezar y proporcionar, Alt para crecer desde el centro y Alt + arrastre para duplicar.
- **Pizarra de presentación por pausa**: el panel lateral permanece flotante y se puede minimizar a un distintivo; la pantalla se congela al activar una herramienta. Incluye el panel de propiedades, puntero láser con estela configurable y atajos globales Alt + letra que siguen activos con el panel minimizado y se desactivan ante juegos a pantalla completa.
- **Catorce formatos de guardado** (incluidos WEBP, AVIF, HEIC e ICO) y **tres idiomas nuevos** (japonés, chino y ruso, nueve en total).
- Selector de color en el idioma de la aplicación, tooltips y manual con diseño propio, tema oscuro homogéneo en los paneles y nuevo logotipo.

## 1.0.0 (2026-07-05)

Reúne todas las funciones previstas para la aplicación: captura, edición, presentación y utilidades del sistema.

- **Captura por región** con editor de anotaciones (formas, líneas y flechas con remates y estilos, pincel, texto y pixelado) y selección desplazable y redimensionable.
- **Captura de pantalla completa** y de **ventana activa**, con el mismo editor.
- **Captura con desplazamiento**, con unión tolerante al ruido visual y editor con desplazamiento al finalizar.
- **Modo presentación** en vivo: panel lateral anclable, zoom en tiempo real, puntero láser con estela y dibujo.
- Interfaz en **seis idiomas** con cambio instantáneo, tema claro y oscuro, panel siempre al frente con anclaje, notificaciones animadas, instancia única, arranque con Windows y comprobación de actualizaciones contra las releases del repositorio.
- Ejecutable portable generado con `scripts/build.bat`.
