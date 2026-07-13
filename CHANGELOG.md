# Historial de cambios

Todos los cambios importantes de Screenshot Plus quedan anotados aquí, de la versión más reciente a la más antigua. Cada versión publicada tiene además su nota en las [releases del repositorio](https://github.com/Cris223511/screenshot-plus/releases), que es donde se anuncian las descargas.

El formato sigue la idea de [Keep a Changelog](https://keepachangelog.com/es/) y el versionado es [semántico](https://semver.org/lang/es/): el primer número marca cambios grandes, el segundo funciones nuevas y el tercero correcciones.

## 1.2.0 — 2026-07-13

Una tanda grande, centrada sobre todo en el editor de la captura de región: selección múltiple, un borrador de verdad, el pincel de ocultar rehecho y un montón de detalles que se sentían toscos.

### Editor de captura

- **Selección múltiple**: con la herramienta de selección, **Shift + clic** suma o quita elementos, y arrastrar en el vacío traza un **recuadro elástico** que toma todo lo que abarca.
- **Edición en conjunto**: con varios elementos tomados, cambiar color, grosor u opacidad los afecta a todos a la vez, y Suprimir los borra juntos. La barra muestra **solo las opciones comunes** a lo seleccionado (por ejemplo, texto más línea no ofrece grosor, porque el texto no lo tiene).
- **Borrador** (tecla E): una herramienta nueva que quita las anotaciones que su círculo toca, con grosor configurable.
- **Pincel de ocultar rehecho**: ahora se pinta como el pincel (un trazo azul mientras arrastras) y al soltar queda pixelado o difuminado. Elige entre **pixelar o difuminar**, su intensidad y su grosor. No se puede mover ni seleccionar: solo se quita con el borrador.
- **Botón para mover el recorte**: un agarre propio en la esquina superior; arrastrar el interior del recorte ya no lo mueve sin querer.
- **Redimensión mejorada**: la selección se estira contra un ancla fija, con un tamaño mínimo y volteo al pasarse del lado opuesto, sin trabarse. La barra de herramientas la acompaña en vivo mientras la cambias.
- **Cursores direccionales** en los tiradores de redimensión, y una **lupa de zoom** junto al cursor mientras eliges la zona, para acertar el borde exacto.
- **Barra de opciones flotante**: los controles de cada herramienta salen en una ventanita aparte debajo de la barra, que ya no se estira; y cuando el recorte se pega abajo, la barra pasa a vertical al costado.
- **Atajos de letra**: V vuelve a selección, y también S, L, F, B, T, P y E para el resto de herramientas.
- **Trazo recto con Shift** en el pincel y el pincel de ocultar.

### Modo presentación

- Las mismas mejoras del pincel de ocultar (pixelar o difuminar, no acumula, no se sale del recorte) y de la edición en conjunto con opciones comunes.
- El trazo de ocultar tampoco se mueve; solo se borra.
- Los atajos del panel **se desactivan solo ante juegos y apps a pantalla completa**, pero **siguen funcionando en navegadores a pantalla completa**.

### Aplicación y opciones

- **La captura funciona en todo momento**, incluso sobre juegos y navegadores a pantalla completa.
- **Arranque con Windows minimizado**: si la app se abre sola al encender la PC, se queda en la bandeja sin mostrar el panel.
- **Botón "Restablecer todo"** en Opciones: devuelve la configuración general a su estado inicial sin borrar ninguna captura ni cambiar tu carpeta de guardado. Aparte, un botón para restablecer solo los atajos.
- **Capturador de atajos nuevo**: un campo con indicador de grabación que late suave, muestra las teclas que pulsas y se puede cancelar.
- Las **opciones de cada herramienta** (color, grosor, intensidad del pixelado, etc.) ya no se guardan a disco: se reinician en cada sesión. La configuración general sí se conserva.
- El **pin del panel arranca apagado** y se recuerdan las posiciones de los paneles entre sesiones.
- El **scroll del selector de idiomas** ahora es suave, con hover y una barra fina.

### Correcciones

- El pixelado ya no se acumula al pasar el pincel varias veces por el mismo lugar; y si cambias la intensidad, manda el trazo de encima.
- El difuminado ya no se veía fuera del contorno de la selección.
- El pincel normal ya no rellenaba con negro los trazos que se cruzaban.
- El panel minimizado ya no reaparece al capturar, copiar o cerrar.
- Al guardar con Ctrl + S ya no se cierra el editor; el diálogo aparece encima y puedes seguir.
- Esc cancela la captura desde el primer momento, aunque no hayas seleccionado nada.
- El foco vuelve a la ventana anterior (tu navegador, un documento) al terminar con la captura.

## 1.1.0 — 2026-07-09

El editor de anotaciones y la pizarra de presentación dieron un salto grande.

- **Editor mucho más completo**: ocho formas, líneas y flechas con remate configurable en cada extremo y cinco estilos de trazo; texto con todas las tipografías del sistema más subrayado, tachado, espaciado, rotación, fondo, sombra y contorno; opacidad e imágenes pegadas. Todo queda seleccionado al dibujarlo y se edita en vivo, con Shift para enderezar y proporcionar, Alt para crecer desde el centro y Alt + arrastre para duplicar.
- **Pizarra de presentación por pausa**: el panel lateral flota siempre y es minimizable a un chip; la pantalla se congela al activar una herramienta. Trae la ventanita de propiedades, láser con estela suave y configurable, y atajos globales Alt + letra que siguen con el panel minimizado y se callan en juegos a pantalla completa.
- **Catorce formatos de guardado** (incluidos WEBP, AVIF, HEIC e ICO) y **tres idiomas nuevos** (japonés, chino y ruso, nueve en total).
- El selector de color en el idioma de la app, tooltips y manual con diseño propio, tema oscuro parejo en los paneles y el logo nuevo.

## 1.0.0 — 2026-07-05

Primera versión funcional completa, cubriendo todo el alcance planeado.

- **Captura por región** con editor de anotaciones (formas, líneas y flechas con remates y estilos, pincel, texto, pixelado), selección movible y redimensionable.
- **Pantalla completa** y **ventana activa** con el mismo editor.
- **Captura con desplazamiento**, con costura tolerante al ruido visual y editor con scroll al finalizar.
- **Modo presentación** en vivo: panel lateral fijable, zoom en vivo, láser con estela y dibujo.
- Interfaz en **seis idiomas** con cambio instantáneo, tema claro y oscuro, panel siempre adelante con pin, notificaciones animadas, instancia única, arranque con Windows y comprobación de actualizaciones contra las releases del repositorio.
- Ejecutable portable generado con `scripts/build.bat`.
