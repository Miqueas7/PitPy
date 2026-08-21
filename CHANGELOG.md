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

### Cambiado

- El paquete pasa de rueda universal a **una rueda por plataforma**. Quien instale
  desde el sdist necesita un compilador de C++20 y CMake.

- `numpy` deja de estar capado a `<2`. La suite pasa igual con 1.26 y con 2.4, y
  el tope obligaba a degradar numpy en el entorno de quien instalara PitPy.

## Antes de PyPI

- `dxf`: lector de mallas `3DFACE` y polilíneas de RecMin, validado contra cinco
  archivos reales.
- `taludes`: detección del talud global desde la geometría de la carcaza.
- `cli inspeccionar`: qué trae un DXF, sin abrir un CAD.
