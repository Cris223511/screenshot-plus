# Historial de cambios

Este documento recoge los cambios importantes de Screenshot Plus, de la versión más reciente a la más antigua. Cada versión publicada tiene además su entrada en las [releases del repositorio](https://github.com/Cris223511/screenshot-plus/releases), donde están las descargas.

El formato sigue la convención de [Keep a Changelog](https://keepachangelog.com/es/) y el versionado es [semántico](https://semver.org/lang/es/). El primer número marca los cambios mayores, el segundo las funciones nuevas y el tercero las correcciones.

## 1.2.2 (2026-07-16)

Esta versión corrige cinco molestias del uso diario. Tocan el arranque junto a Windows, el cierre de la captura de región al guardar, la tecla Escape, la exactitud de los atajos globales y la captura con desplazamiento.

- El arranque junto a Windows ahora sí ocurre al encender el equipo. Antes se apuntaba solo a la clave de inicio del registro y, con un ejecutable portable y sin firma, muchas veces no corría. Ahora se registra por dos caminos a la vez, la clave del registro y un acceso directo en la carpeta de Inicio, y encima se quita del propio `.exe` la marca de "descargado de internet", que era la que hacía que SmartScreen bloqueara el arranque automático. La aplicación se levanta minimizada en la bandeja y no abre la ventana.
- Guardar una captura de región cierra el recorte. Antes, al guardar una zona con Ctrl + S, se cerraba el diálogo de archivo pero el recorte y su capa oscura se quedaban en pantalla y tocaba cerrarlos a mano. Ahora, apenas se confirma el guardado, se cierra todo y la aplicación vuelve a donde estaba, la bandeja o el panel. El editor de captura larga y la pizarra se quedan abiertos, que ahí sí conviene continuar el trabajo.
- Escape cancela al primer toque. Cuando la captura de región saltaba con el atajo desde otra aplicación, la superposición no siempre se quedaba con el foco del teclado, así que el primer Escape se perdía y había que darle varias veces. Ahora la superposición toma el foco por su cuenta apenas aparece y Escape cancela a la primera, sin excepción.
- Los atajos globales responden solo a la combinación exacta. Si el atajo es Alt + A, pulsar Ctrl + Alt + A ya no lo dispara, y tampoco lo hace si traías otra tecla pulsada de antes. Vale igual para cualquier atajo que tengas configurado.
- La captura con desplazamiento quedó rehecha por dentro. La vista previa mostraba a veces una zona que no tenía nada que ver con lo seleccionado. El problema estaba en la máscara de recorte de la capa oscura, que en pantallas con escalado quedaba corrida, de modo que uno desplazaba un sitio y se capturaba otro. Se reemplazó por una capa que deja pasar el ratón entero, sin máscara, así lo que ves moverse es justo lo que se captura. La unión de los fotogramas trabaja en los dos sentidos, hacia arriba acumula por encima y hacia abajo por debajo, sin repetir ni recortar, y descarta los fotogramas casi vacíos que ensuciaban el resultado.

## 1.2.1 (2026-07-13)

Arregla un fallo de arranque del ejecutable. No cambia ninguna función respecto a la 1.2.0.

- El ejecutable podía cerrarse nada más abrirse, unas veces sí y otras no. El origen era un choque entre pynput y PySide6 durante la importación. pynput trae dentro la librería six, y su importador especial hacía que el sistema de inspección de módulos de PySide6 (shiboken) fallara con un error raro al armar la representación textual de ese módulo, y eso tumbaba el arranque antes de que apareciera la ventana.
- La corrección refuerza esa inspección para que trate el caso como un módulo sin archivo fuente y esquive la representación que reventaba. El arranque quedó estable.
- Aparte, el empaquetado limpia la caché de PyInstaller en cada compilación, para descartar paquetes a medio generar que también podían dar un ejecutable defectuoso.

## 1.2.0 (2026-07-13)

La mayor parte de las novedades se concentran en el editor de la captura de región, que incorpora selección múltiple, una herramienta de borrador y un pincel de ocultar reconstruido, además de un manejo del recorte mucho más preciso. La pizarra de presentación hereda las mismas mejoras, y los ajustes de la aplicación suman un capturador de atajos nuevo, la opción de restablecer y un arranque con Windows más discreto. Se corrigen, aparte, varios errores reportados.

### Selección y edición de elementos

- Con la herramienta de selección, Shift + clic añade o quita elementos uno a uno, y si arrastras sobre una zona vacía trazas un recuadro elástico que atrapa todo lo que abarca.
- Con varios elementos seleccionados, los cambios de color, grosor u opacidad se aplican a todos a la vez, y Suprimir los borra en bloque.
- Cuando seleccionas elementos de distinto tipo, la barra muestra solo las opciones que valen para todos. Un texto y una línea, por ejemplo, comparten color y opacidad, pero no grosor, porque el texto no lo tiene.
- Atajos de letra para cambiar de herramienta al vuelo. V selección, S formas, L línea, F flecha, B pincel, T texto, P ocultar y E borrador.

### Herramientas nuevas

- El borrador (E) quita las anotaciones que su círculo toca, con grosor ajustable.
- El pincel de ocultar se rehízo. Ahora se traza con contorno azul y, al soltar, la zona queda pixelada o difuminada, a tu elección, con intensidad y grosor ajustables. No se selecciona ni se mueve, y solo el borrador lo quita.
- Con Shift, tanto el pincel como el pincel de ocultar sacan el trazo recto desde el punto de partida.

### Recorte de la captura

- Un tirador dedicado desplaza la zona seleccionada, en lugar de arrastrarla por dentro, para no moverla sin querer cuando vas a copiar.
- El recorte se ajusta contra un ancla fija, con un tamaño mínimo, y se invierte si cruzas el lado opuesto, sin trabarse.
- La barra de herramientas se recoloca en tiempo real mientras mueves o redimensionas el recorte, y nunca queda por encima de él.
- Cada tirador de redimensionado muestra su cursor direccional, y una lupa de aumento acompaña al cursor durante la selección para acertar el borde exacto.
- Un círculo bajo el cursor marca el área que van a cubrir el pincel de ocultar y el borrador.

### Interfaz del editor

- Los controles de cada herramienta pasaron a un panel flotante bajo la barra, así la barra de herramientas ya no se ensancha cuando aparecen.
- Cuando el recorte queda pegado al borde inferior de la pantalla, la barra se pone vertical a un lado.
- Si sales con Esc después de haber dibujado algo, la aplicación pregunta antes de perderlo, con la opción de no volver a preguntar, que comparte con la pizarra de presentación.

### Modo presentación

- Hereda las mismas mejoras del pincel de ocultar y de la edición conjunta con opciones comunes.
- El trazo de ocultar tampoco se puede mover, solo se quita con el borrador.
- Los atajos del panel se apagan únicamente ante juegos y aplicaciones a pantalla completa. Ante un navegador a pantalla completa siguen activos.

### Aplicación y sistema

- Los atajos de captura responden en todo momento, incluso sobre juegos y navegadores a pantalla completa.
- Cuando Windows abre la aplicación al iniciar sesión, se queda minimizada en la bandeja y no muestra el panel.
- Al terminar una captura, el teclado vuelve a la ventana en la que estabas, el navegador o un documento.
- El anclaje del panel al frente viene desactivado por defecto, y las posiciones de los paneles se recuerdan entre sesiones.

### Opciones

- Un botón devuelve los ajustes generales a su estado inicial. No borra ninguna captura ni cambia la carpeta de guardado. Hay, aparte, otro botón que restablece solo los atajos.
- El campo para capturar atajos es nuevo, con un indicador de grabación que late suave, muestra las teclas conforme las pulsas y deja cancelar.
- El color, el grosor, la intensidad del pixelado y las demás opciones de las herramientas ya no se guardan en disco, se reinician en cada sesión. La configuración general sí se conserva.
- El selector de idiomas se desplaza suave y resalta la opción al pasar el cursor.

### Correcciones

- El pixelado ya no se acumula. Al repasar la misma zona con el pincel de ocultar el efecto se intensificaba; ahora se mantiene igual y, cuando cambias la intensidad, prevalece el trazo de encima.
- El difuminado ya no se sale del contorno. Antes podía pintarse más allá de la selección; ahora queda recortado a ella.
- El pincel ya no rellena en negro. Un trazo que se cruzaba consigo mismo rellenaba su interior mientras lo dibujabas; ahora solo traza la línea.
- El redimensionado ya no se bloquea. Al reducir mucho el recorte o cruzar el lado opuesto se trababa; ahora fluye e invierte el sentido, con un tamaño mínimo respetado.
- El panel minimizado ya no reaparece solo. Volvía a mostrarse al capturar, copiar o cerrar; ahora se queda oculto hasta que lo abres a propósito.
- Guardar ya no cierra el editor. Ctrl + S cerraba la edición; ahora el diálogo se abre encima y puedes seguir.
- Esc funciona sin selección previa. Antes no cancelaba la captura hasta tocar el ratón; ahora cancela desde el primer momento.
- El foco vuelve tras capturar. El teclado no regresaba a la ventana anterior; ahora vuelve a la aplicación en la que estabas.

## 1.1.0 (2026-07-09)

El editor de anotaciones y la pizarra de presentación crecen bastante, y se suman formatos de guardado e idiomas.

- El editor de anotaciones creció mucho. Trae ocho formas, líneas y flechas con remate configurable en cada extremo y cinco estilos de trazo, texto con todas las tipografías del sistema más subrayado, tachado, espaciado, rotación, fondo, sombra y contorno, opacidad e imágenes pegadas. Todo elemento queda seleccionado al dibujarlo y se edita en vivo, con Shift para enderezar y proporcionar, Alt para crecer desde el centro y Alt + arrastre para duplicar.
- La pizarra de presentación funciona por pausa. El panel lateral queda flotante y se minimiza a un distintivo, y la pantalla se congela al activar una herramienta. Incluye panel de propiedades, puntero láser con estela configurable y atajos globales Alt + letra que siguen activos con el panel minimizado y se apagan ante juegos a pantalla completa.
- Catorce formatos de guardado, con WEBP, AVIF, HEIC e ICO entre ellos, y tres idiomas nuevos, el japonés, el chino y el ruso, para un total de nueve.
- Selector de color en el idioma de la aplicación, tooltips y manual con diseño propio, tema oscuro homogéneo en los paneles y logotipo nuevo.

## 1.0.0 (2026-07-05)

Reúne todas las funciones previstas para la aplicación. Captura, edición, presentación y utilidades del sistema.

- Captura por región con editor de anotaciones (formas, líneas y flechas con remates y estilos, pincel, texto y pixelado) y una selección que se mueve y se redimensiona.
- Captura de pantalla completa y de ventana activa, con el mismo editor.
- Captura con desplazamiento, con una unión que tolera el ruido visual y un editor con scroll al terminar.
- Modo presentación en vivo, con panel lateral anclable, zoom en tiempo real, puntero láser con estela y dibujo.
- Interfaz en seis idiomas con cambio instantáneo, tema claro y oscuro, panel siempre al frente con anclaje, notificaciones animadas, instancia única, arranque con Windows y comprobación de actualizaciones contra las releases del repositorio.
- Ejecutable portable, generado con `scripts/build.bat`.
