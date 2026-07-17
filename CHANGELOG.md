# Historial de cambios

Este documento recoge los cambios importantes de Screenshot Plus, de la versión más reciente a la más antigua. Cada versión publicada tiene además su entrada en las [releases del repositorio](https://github.com/Cris223511/screenshot-plus/releases), donde están las descargas.

El formato sigue la convención de [Keep a Changelog](https://keepachangelog.com/es/) y el versionado es [semántico](https://semver.org/lang/es/). El primer número marca los cambios mayores, el segundo las funciones nuevas y el tercero las correcciones.

## 1.2.3 (2026-07-16)

Correcciones sobre la captura con desplazamiento, que arrastraba varios fallos serios, y un cierre más corto para lo capturado.

- El velo de la captura con desplazamiento dejaba pasar el ratón por completo, así que un clic podía colarse en la ventana de atrás y sacarte de la captura. Ahora un filtro bloquea los clics mientras la captura está activa, salvo los que caen sobre el panel de control, y solo Esc cancela.
- El scroll lento podía disparar el uso del procesador y dejar el equipo casi bloqueado. Para frenar la rueda se reinyectaba una versión más corta, y cuando el sistema no reconocía esa inyección propia el filtro la tomaba como un giro nuevo y la reinyectaba sin fin. Ahora cada rueda inyectada queda contabilizada por la propia aplicación, así se reconoce al volver por el hook y nunca puede realimentarse.
- La unión de los fotogramas producía imágenes de una altura imposible y con partes repetidas. El desplazamiento se medía con el signo invertido, de modo que al scrollear hacia abajo se pegaba como si fuera hacia arriba y el contenido se duplicaba sin parar. Se corrigió el signo, se añadieron límites que descartan los saltos sin solape y un tope de altura, y la medición del calce quedó más liviana para no cargar el equipo en cada captura.
- La vista previa muestra ahora el extremo recién cosido, abajo cuando se scrollea hacia abajo y arriba cuando es hacia arriba.
- El cierre de lo capturado es más corto. Durante la captura, Ctrl + C copia y termina, Ctrl + S guarda y termina, y Enter abre el editor para anotar antes de decidir. En ese editor, copiar o guardar también cierra y da el flujo por concluido.

## 1.2.2 (2026-07-16)

Esta versión corrige cinco errores que afectaban al funcionamiento habitual de la aplicación. Se resuelven problemas en el arranque junto a Windows, en el cierre de la captura de región al guardar, en el comportamiento de la tecla Escape, en la exactitud de los atajos globales y en la captura con desplazamiento.

- Se corrige el arranque junto a Windows, que en muchos equipos no se producía al iniciar sesión. Hasta ahora solo se registraba una entrada en la clave de inicio del registro y, con un ejecutable portable y sin firma, esa vía no siempre bastaba. La aplicación pasa a registrarse por dos medios a la vez, la clave del registro y un acceso directo en la carpeta de Inicio, y además retira del propio `.exe` la marca de "descargado de internet", que era la que provocaba que SmartScreen bloqueara el inicio automático. La aplicación arranca minimizada en la bandeja del sistema, sin abrir la ventana.
- Al guardar una captura de región, la superposición ahora se cierra por completo. Antes, tras guardar una zona con Ctrl + S, se cerraba el diálogo de archivo pero el recorte y su capa oscura permanecían en pantalla y había que cerrarlos de forma manual. En cuanto se confirma el guardado, se cierra toda la superposición y la aplicación regresa a su estado anterior, la bandeja o el panel. El editor de captura larga y la pizarra permanecen abiertos, ya que en ellos sí resulta útil continuar el trabajo.
- La tecla Escape vuelve a cancelar a la primera pulsación. Cuando la captura de región se activaba con el atajo desde otra aplicación, la superposición no siempre recibía el foco del teclado, de modo que el primer Escape se perdía y era necesario pulsarlo varias veces. La superposición reclama ahora el foco de forma activa en cuanto aparece, con lo que Escape cancela al primer intento en todos los casos.
- Los atajos globales pasan a responder únicamente a la combinación exacta. Si el atajo configurado es Alt + A, la pulsación de Ctrl + Alt + A ya no lo activa, y tampoco lo hace si había otra tecla pulsada con anterioridad. El criterio se aplica a cualquier atajo definido.
- La captura con desplazamiento se rehízo por completo. La vista previa mostraba en ocasiones una zona distinta de la seleccionada, porque la máscara de recorte de la capa oscura quedaba desplazada en pantallas con escalado y el área que se movía no coincidía con la que se capturaba. En su lugar se emplea una capa que deja pasar el ratón en su totalidad, sin máscara, de manera que lo que se ve desplazarse coincide con exactitud con lo que se captura. La unión de los fotogramas funciona ahora en ambos sentidos, con acumulación por encima al subir y por debajo al bajar, sin repetición ni recorte, y descarta los fotogramas casi vacíos que deterioraban el resultado.

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
- El pincel de ocultar se rehízo. Ahora se traza con contorno azul y, al soltar, la zona queda pixelada o difuminada, según se prefiera, con intensidad y grosor ajustables. No se selecciona ni se mueve, y solo el borrador lo elimina.
- Con Shift, tanto el pincel como el pincel de ocultar sacan el trazo recto desde el punto de partida.

### Recorte de la captura

- Un tirador dedicado desplaza la zona seleccionada, en lugar de arrastrarla por su interior, para evitar moverla de forma accidental al copiar.
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
- Guardar ya no cierra el editor. Ctrl + S cerraba la edición; ahora el diálogo se abre encima y permite continuar.
- Esc funciona sin selección previa. Antes no cancelaba la captura hasta tocar el ratón; ahora cancela desde el primer momento.
- El foco vuelve tras capturar. El teclado no regresaba a la ventana anterior; ahora vuelve a la aplicación en la que estabas.

## 1.1.0 (2026-07-09)

El editor de anotaciones y la pizarra de presentación se amplían de forma considerable, y se suman formatos de guardado e idiomas.

- El editor de anotaciones se amplía de forma considerable. Incorpora ocho formas, líneas y flechas con remate configurable en cada extremo y cinco estilos de trazo, texto con todas las tipografías del sistema más subrayado, tachado, espaciado, rotación, fondo, sombra y contorno, opacidad e imágenes pegadas. Todo elemento queda seleccionado al dibujarlo y se edita en vivo, con Shift para enderezar y proporcionar, Alt para crecer desde el centro y Alt + arrastre para duplicar.
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
