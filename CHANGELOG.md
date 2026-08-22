# Registro de cambios

Todas las versiones publicadas de PitPy. El formato sigue
[Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/) y el versionado es
[semántico](https://semver.org/lang/es/).

> Este archivo es el registro **público**: lo que cambia para quien usa la librería.
> La bitácora de trabajo sesión a sesión —con las decisiones y su porqué— está en
> [`docs/CHANGELOG.md`](docs/CHANGELOG.md).

## [No publicado]

Nada publicado todavía en PyPI. La versión `0.1.0` sale cuando el flujo completo
—bancos, rampa, recorte con topografía y reporte de volúmenes— pase el caso base
y el Ing. Yhonny Ruiz valide el diseño generado contra el suyo.

### Agregado

- `bancos.generar()`: de la carcaza a la secuencia de bancos con cresta y pie.
  Trece bancos cada 10 m entre las cotas 230 y 350 en el caso base, con los pies
  a 2.83 m de mediana del diseño hecho a mano por un ingeniero.
- `superficie`: la carcaza como grilla regular `z(x, y)`, con extracción de
  contornos por marching squares. Es la representación interna sobre la que van a
  trabajar también el recorte con topografía y el cálculo de volúmenes.
- `Carcaza.silueta(paso=10.0)`: borde de la carcaza en planta para vistas previas
  livianas. 0.15 s y 281 puntos sobre una carcaza de 18,703 caras.
- `disenar()`: por ahora llega hasta los bancos. `Diseno.rampa()` devuelve `None`
  y `Diseno.reporte()` levanta `NotImplementedError` hasta que existan.
- Núcleo de cálculo en **C++20 con nanobind** (`pitpy._nucleo`): rasterizado de la
  malla, distancia euclídea exacta y marching squares. La API no cambia; cambia el
  reloj. Rasterizar un pit de 4 km pasó de 275 s a 0.88 s, y `disenar()` sobre el
  caso base, a la misma resolución, de 4.59 s a 0.86 s. Cada kernel conserva su gemela en Python como
  referencia verificable y como respaldo si se instala sin compilador.

- `volumen.calcular()` y `Diseno.reporte()`: áreas, volúmenes y sobre-estéril.
  `area_proyectada_ha()` da 19.01 ha para la carcaza del caso base y 19.60 ha para el
  pit diseñado, contra los 19.0 y 19.6 medidos a mano. El reporte trae además las
  advertencias en idioma del oficio, incluida la del fondo más angosto que el mínimo
  pedido —que se avisa, nunca se corrige en silencio—.
- `volumen.area_proyectada_ha()` como función pública.
- `Diseno.a_dxf()`: escribe el diseño a DXF con las líneas de cresta y pie en capas
  separadas y con color. Las capas de superficie (`BERMA`, `TALUD`) quedan para más
  adelante; el porqué está en el ROADMAP.

- `rampa.trazar()`: rampa helicoidal sobre la pared, con radio de giro respetado de
  verdad —lo que RecMin no hace—. En el caso base: 1,256 m entre las cotas 230 y 350,
  radio mínimo 26.2 m para 25 pedidos. La rampa **corta** el diseño y retira lo que
  queda arriba al talud global, así que el sobre-estéril pasa a ser positivo.
- `Parametros.trazar_rampa`, para pedir el diseño de bancos sin rampa.
- `rampa.cabe(carcaza, parametros)`: dice si la rampa entra antes de calcular el diseño
  completo, y por qué no cuando no entra. No estima: traza en borrador sobre una grilla
  gruesa. Coincide con el diseño completo en los seis radios probados sobre el caso base,
  a 0.06-0.92 s contra 2.0-2.7 s.

- `disenar(..., topografia=...)`: recorta el diseño donde quedaba por encima del
  terreno real. Va directo al "recorte directo" (mínimo contra el terreno en la
  grilla), sin la etapa de "nivel suficiente" del ROADMAP: con la grilla ya
  construida, recortar no es más difícil y da más valor. En el caso base:
  0.40 ha recortadas, 2.1 % de la huella, con la rampa puesta.
- `topo.recortar()`, `topo.area_recortada_ha()`, `topo.cota_en()` y
  `superficie.muestrear_en()` como funciones del motor.

### Corregido

- La fracción de `progreso()` **retrocedía**: se emitía `("trazando rampa", 1.0)` y
  después `("recortando topografía", 0.90)`, lo que hacía saltar hacia atrás una
  barra de avance. Ahora es siempre creciente, termina en 1.0, y las cuatro etapas
  se emiten aunque no haya trabajo que hacer.

### Cambiado

- **`volumen_carcaza_m3` cambia de valor con topografía**, aunque la carcaza no se
  toca: antes se medía contra un plano imaginario a la altura de la cresta; con
  terreno real esa referencia se reemplaza por el techo verdadero. En el caso
  base: 11.27 M → 9.93 M m³. El número se vuelve más preciso, no distinto en su
  significado.
- `Rampa.pendiente` informa la pendiente **lograda**, no la pedida. Suelen coincidir;
  cuando respetar el radio obliga a alargar la rampa, la lograda es más tendida y el
  reporte lo dice en una advertencia.

- El paquete pasa de rueda universal a **una rueda por plataforma**. Quien instale
  desde el sdist necesita un compilador de C++20 y CMake.

- `numpy` deja de estar capado a `<2`. La suite pasa igual con 1.26 y con 2.4, y
  el tope obligaba a degradar numpy en el entorno de quien instalara PitPy.

## Antes de PyPI

- `dxf`: lector de mallas `3DFACE` y polilíneas de RecMin, validado contra cinco
  archivos reales.
- `taludes`: detección del talud global desde la geometría de la carcaza.
- `cli inspeccionar`: qué trae un DXF, sin abrir un CAD.
