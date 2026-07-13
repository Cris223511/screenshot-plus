# Historial de cambios

Este documento recoge los cambios importantes de Screenshot Plus, de la versión más reciente a la más antigua. Cada versión publicada tiene además su entrada en las [releases del repositorio](https://github.com/Cris223511/screenshot-plus/releases), donde se anuncian las descargas.

El formato sigue la convención de [Keep a Changelog](https://keepachangelog.com/es/) y el versionado es [semántico](https://semver.org/lang/es/): el primer número indica cambios mayores, el segundo funciones nuevas y el tercero correcciones.

## 1.2.0 (2026-07-13)

La mayor parte de las novedades se concentran en el editor de la captura de región, que incorpora selección múltiple, una herramienta de borrador y un pincel de ocultar reconstruido, además de un manejo del recorte mucho más preciso. La pizarra de presentación hereda las mismas mejoras, y los ajustes de la aplicación suman un capturador de atajos nuevo, la opción de restablecer y un arranque con Windows más discreto. Se corrigen, además, varios errores reportados.

### Selección y edición de elementos

- **Selección múltiple:** con la herramienta de selección, *Shift + clic* añade o quita elementos uno a uno, y arrastrar sobre una zona vacía traza un recuadro elástico que toma todo lo que abarca.
- **Edición conjunta:** con varios elementos seleccionados, los cambios de color, grosor u opacidad se aplican a todos a la vez, y *Suprimir* los elimina en bloque.
- **Opciones comunes:** al tener seleccionados elementos de distinto tipo, la barra muestra únicamente las opciones que aplican a todos. Por ejemplo, un texto y una línea comparten color y opacidad, pero no grosor, porque el texto no lo tiene.
- **Atajos de teclado** para cambiar de herramienta al vuelo: *V* selección, *S* formas, *L* línea, *F* flecha, *B* pincel, *T* texto, *P* ocultar y *E* borrador.

### Herramientas nuevas

- **Borrador** (*E*): elimina las anotaciones que su círculo toca, con grosor configurable.
- **Pincel de ocultar reconstruido:** se dibuja como un trazo (contorno azul) y, al soltar, la zona queda *pixelada* o *difuminada*, a elección, con intensidad y grosor ajustables. No es seleccionable ni se puede mover; se quita únicamente con el borrador.
- **Trazo recto:** manteniendo *Shift* con el pincel o el pincel de ocultar, el trazo sale recto desde el punto de partida.

### Recorte de la captura

- **Tirador para mover el recorte:** un agarre dedicado desplaza la zona seleccionada, en lugar de arrastrar su interior, para no moverla sin querer al ir a copiar.
- **Redimensionado firme:** el recorte se ajusta respecto a un ancla fija, con un tamaño mínimo y con inversión al sobrepasar el lado opuesto, sin bloquearse.
- **Barra que acompaña:** la barra de herramientas se reubica en tiempo real mientras mueves o cambias el tamaño del recorte, sin quedar por encima de él.
- **Cursores direccionales** en cada tirador de redimensionado, y **lupa de aumento** junto al cursor durante la selección, para acertar el borde exacto.
- **Círculo de tamaño** bajo el cursor con el pincel de ocultar y el borrador, para ver el área que van a cubrir.

### Interfaz del editor

- **Barra de opciones independiente:** los controles de cada herramienta pasan a un panel flotante bajo la barra, de modo que la barra de herramientas ya no se ensancha al mostrarlos.
- **Barra vertical:** cuando el recorte queda pegado al borde inferior de la pantalla, la barra se coloca en vertical a un lado.
- **Confirmación al descartar:** al salir con *Esc* habiendo dibujado algo, se pregunta antes de perderlo, con la opción de no volver a preguntar (compartida con la pizarra de presentación).

### Modo presentación

- Incorpora las mismas mejoras del pincel de ocultar y de la edición conjunta con opciones comunes.
- El trazo de ocultar tampoco se puede mover; solo se elimina con el borrador.
- Los atajos del panel se desactivan únicamente ante juegos y aplicaciones a pantalla completa; ante un navegador a pantalla completa siguen funcionando.

### Aplicación y sistema

- **Captura siempre disponible:** los atajos de captura funcionan en todo momento, incluso sobre juegos y navegadores a pantalla completa.
- **Arranque discreto:** cuando Windows abre la aplicación al iniciar sesión, esta se queda minimizada en la bandeja, sin mostrar el panel.
- **Foco devuelto:** al terminar una captura, el teclado vuelve a la ventana en la que estabas (el navegador, un documento).
- **Anclaje del panel** al frente desactivado por defecto, y **posiciones de los paneles** recordadas entre sesiones.

### Opciones

- **Restablecer:** un botón devuelve los ajustes generales a su estado inicial. *No elimina ninguna captura ni modifica la carpeta de guardado.* Se añade, aparte, un botón para restablecer solo los atajos.
- **Capturador de atajos nuevo:** un campo con indicador de grabación que late suave, muestra las teclas conforme se pulsan y permite cancelar.
- **Ajustes de herramienta por sesión:** el color, el grosor, la intensidad del pixelado y demás opciones de las herramientas dejan de guardarse en disco y se reinician en cada sesión; la configuración general sí se conserva.
- **Selector de idiomas** con desplazamiento suave y resaltado al pasar el cursor.

### Correcciones

- **Pixelado que se acumulaba:** al repasar la misma zona con el pincel de ocultar, el efecto se intensificaba. Ahora se mantiene igual y, al variar la intensidad, prevalece el trazo superior.
- **Difuminado fuera del contorno:** el efecto podía pintarse más allá de la selección. Ahora queda recortado a ella.
- **Pincel que rellenaba en negro:** un trazo que se cruzaba consigo mismo rellenaba su interior mientras se dibujaba. Ahora solo traza la línea.
- **Redimensionado que se bloqueaba:** al reducir mucho el recorte o cruzar el lado opuesto, el ajuste se trababa. Ahora fluye e invierte el sentido, respetando un tamaño mínimo.
- **Panel minimizado que reaparecía:** volvía a mostrarse al capturar, copiar o cerrar. Ahora permanece oculto hasta que se abre a propósito.
- **Guardado que cerraba el editor:** *Ctrl + S* cerraba la edición. Ahora el diálogo se abre encima y permite continuar.
- **Esc sin efecto sin selección:** no cancelaba la captura hasta interactuar con el ratón. Ahora cancela desde el primer momento.
- **Foco perdido tras capturar:** el teclado no regresaba a la ventana anterior. Ahora vuelve a la aplicación en la que estabas.

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
