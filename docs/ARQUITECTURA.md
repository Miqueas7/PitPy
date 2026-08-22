# Arquitectura — PitPy

## Principio

**El motor no sabe nada de interfaces.** Recibe geometría y parámetros, devuelve
geometría y números. PitForge (la app) y una futura CLI son consumidores; ninguno
es parte del motor.

Esto no es purismo: es lo que permite que la idea de Yhonny del *volumen en
tiempo real* (ESPECIFICACION §8) se implemente después sin reescribir nada. Si el
cálculo de volumen vive dentro de un botón, esa función no se puede construir.

## Flujo

```
   carcaza.dxf ────┐
                   ├──▶ dxf.leer() ──▶ Malla
   topografia.dxf ─┘                     │
                                         ▼
                              taludes.detectar() ──▶ TaludDetectado
                                         │           (mediana, por sector)
                                         ▼
   Parametros ────────────────▶ bancos.generar() ──▶ [Banco, Banco, …]
                                         │           (cresta + pie + berma)
                                         ▼
                               rampa.trazar() ──────▶ Rampa
                                         │           (respeta radio de giro)
                                         ▼
                              topo.recortar() ──────▶ Diseno
                                         │
                                         ├──▶ .reporte()  volúmenes, sobre-estéril
                                         └──▶ .a_dxf()    salida
```

## Módulos

| Módulo | Responsabilidad | Estado |
|---|---|---|
| `dxf` | Leer y escribir DXF: mallas 3DFACE y polilíneas | ✅ lectura funcionando |
| `modelo` | Tipos: `Malla`, `Carcaza`, `Parametros`, `Banco`, `Rampa`, `Diseno` | 🚧 esqueleto |
| `taludes` | Ángulo de cada cara; mediana global; segmentación por azimut y cota | 🚧 método validado |
| `bancos` | De la carcaza a la secuencia de bancos con sus bermas | ⬜ |
| `rampa` | Trazado helicoidal respetando ancho, pendiente y radio de giro | ⬜ |
| `topo` | Recorte del diseño contra la superficie topográfica | ⬜ |
| `volumen` | Volúmenes y sobre-estéril; debe poder recalcularse incremental | ⬜ |
| `cli` | Interfaz de línea de comandos (para iterar durante el desarrollo) | ⬜ |

## Decisiones tomadas y por qué

**1. La carcaza suavizada es la entrada principal.**
Recomendación explícita de Yhonny. Las isolíneas son 7 veces más livianas pero
vienen con efecto serrucho y necesitarían suavizado propio. La bruta obliga a
reconstruir el talud desde una escalera de bloques de 5 m.

**2. El talud se detecta, no se pregunta.**
Está demostrado que funciona (CASO_BASE.md). Se detecta y se muestra al usuario
para confirmar o corregir.

**3. El ancho mínimo de fondo es opcional, no una restricción.**
Criterio explícito de Yhonny (ESPECIFICACION §7): prefiere perder bloques antes
que arrastrar estéril. Forzarlo sería imponer un criterio que el experto rechaza.

**4. El volumen se calcula en su propio módulo, no dentro del diseño.**
Para que el flujo interactivo de §8 sea posible más adelante.

**5. Nada de dependencias de CAD pesadas en el núcleo.**
El lector propio de DXF es ~150 líneas y ya funciona sobre los archivos reales.
Meter una librería CAD completa complicaría el empaquetado del ejecutable de
PitForge sin aportar nada que se necesite.

**6. La superficie se representa como una GRILLA REGULAR `z(x, y)`, no como malla
ni como curvas de nivel.** (2026-08-21, decisión L-3, tomada midiendo el caso base.)

El módulo `superficie` rasteriza la malla del DXF a una grilla de celdas cuadradas y
todo lo demás trabaja sobre ella. Por qué:

| Criterio | Grilla | Malla + offset de polígonos |
|---|---|---|
| Área del caso base | 19.05 ha a paso 2 m contra **19.01 ha exactas** (+0.04, dentro del ±0.1 que pide el ROADMAP) | exacta |
| Ensanchar/angostar un contorno | dilatación/erosión sobre celdas, ~15 líneas | offset de polígonos con auto-intersecciones: el problema difícil de la geometría computacional |
| Recorte con topografía (`topo`) | `minimo(z_pit, z_topo)` celda a celda | booleana entre mallas |
| Volumen incremental (ESPECIFICACION §8) | suma de celdas: se puede recalcular solo la zona que cambió | hay que rehacer la malla |
| Dependencias | `numpy`, que ya está | una librería de geometría, contra la decisión 5 |

El costo es discretización: las líneas salen con escalón del tamaño de la celda. Se
compensa extrayendo los contornos con interpolación lineal (marching squares) en vez de
seguir el borde de las celdas. Paso por omisión = `min(avance_cara, ancho_berma) / 4`
(1.0 m en el caso base): cuatro celdas a lo ancho del rasgo más angosto del diseño.

**7. Los bancos se anclan a la carcaza cota por cota, sin acumular.** El pie de cada
banco se apoya en el contorno de la carcaza de su propia cota; la cresta sale de ahí
ensanchando `avance_cara`. No se construye el banco N a partir del banco N-1.

Medido: el diseño del ingeniero (archivo 4) cae sobre el contorno de la carcaza a **+2 m
de mediana en las 14 cotas**, sin deriva — el mismo desvío abajo que arriba. Y la carcaza
avanza 10.0 m de mediana por banco, que es exactamente el avance de un banco de 10 m a
talud global de 45°: la geometría cierra sola.

La alternativa —construir de abajo hacia arriba dilatando el banco anterior 10 m— se
probó y **da 34.5 ha contra las 19.6 del ingeniero**. La dilatación de un contorno
arrugado no es un desplazamiento de pared: se derrama por los rincones, y el error se
acumula banco a banco (+1.2 ha por banco medido). Queda descartada por medición, no por
opinión.

**8. El fondo es el nivel más bajo cuya sección admita un banco completo.** Criterio:
que en la sección quepa un círculo de diámetro igual al avance por banco
(`altura / tan(global)`, 10.04 m en el caso base).

Medido en la carcaza suavizada: a la cota 210 la sección admite 8.0 m — es la punta del
tazón, no un piso; a la 220 admite 30.5 m. El criterio pone el fondo en **220**, que es
exactamente donde lo puso el ingeniero (el archivo 4 no tiene nada bajo la cota 220).
Y la cresta es `floor(z_max / altura) * altura` = 350, también la del archivo 4.

**Esto no es ensanchar el fondo** (ESPECIFICACION §7 lo prohíbe): es no inventar un banco
donde la carcaza no tiene piso. `ancho_fondo_minimo` sigue siendo del usuario, opcional y
desactivado por omisión.

**9. Los kernels de grilla viven en C++ (nanobind), el resto en Python.**
(2026-08-21. Decisión de Miqueas, medida después.)

Lo que está en C++ son tres funciones y nada más: rasterizar la malla a la grilla,
la distancia euclídea hasta una región, y marching squares. Toda la geometría de
minas —qué es un banco, dónde va el fondo, qué se le avisa al usuario— se queda en
Python, donde se lee y se discute con el ingeniero.

| | referencia Python | con núcleo |
|---|---:|---:|
| Rasterizar la carcaza del caso base (0.47 M celdas) | 0.76 s | 0.003 s |
| Rasterizar un pit de 4 km a paso 2 m (4 M celdas) | 275 s | 0.88 s |
| `disenar()` sobre el caso base, misma resolución | 4.59 s | **0.86 s** |

El kernel puntual rinde 200-300×; de punta a punta el diseño rinde **5×**, porque lo
que queda ya era numpy y numpy ya corría en C. Vale decirlo con todas las letras
para que nadie espere 300× en el reloj de pared.

A la resolución por omisión de hoy, con el tope en 2000 celdas por lado:

| Pit | Paso | Celdas | Bancos | `disenar()` |
|---|---:|---:|---:|---:|
| Caso base, 750 m | 1.01 m | 0.55 M | 13 | 0.86 s |
| Cono de 2 km | 1.01 m | 3.92 M | 38 | 9.5 s |
| Cono de 4 km | 2.00 m | 4.00 M | 58 | 18.4 s |

El costo sigue siendo O(celdas × bancos): el núcleo bajó la constante, no el orden.

**La implementación en Python NO se borró.** Cada kernel conserva su gemela legible
(`_rasterizar_python`, `_distancia_python`, `_contornos_python`) y
`tests/test_nucleo.py` exige que las dos den el mismo resultado, celda por celda,
sobre la carcaza real. Sin ese test, «lo reescribí en C++ y anda más rápido» es una
afirmación sin respaldo: podría andar más rápido y estar mal. Además es la red si
alguien instala el sdist sin compilador.

Consecuencia de empaquetado: la rueda deja de ser universal y pasa a haber una por
plataforma (`cibuildwheel`, como VentPy), y PitForge tiene que empacar la extensión
en su `.exe` (REQ-MOT-001).

**10. El diseño se entrega como LÍNEAS, no como malla** (2026-08-21, MOT-3).

`CRESTA` y `PIE`, una polilínea 3D cerrada por banco, con su color. La malla de
superficie quedó afuera de v1 por un motivo medido, no por falta de tiempo: ver
`ROADMAP.md` §Etapa 3. Los vértices se remuestrean a un paso fijo (5 m por omisión),
que además saca la ondulación de tamaño de celda que traen los contornos de la
grilla: una línea de diseño con dientes de medio metro no es lo que dibuja un
ingeniero.

**11. La rampa se traza interpolando entre los contornos del diseño** (2026-08-21, MOT-4).

Se probaron dos formas y la primera se descartó con números:

| Trazado | Qué pasó |
|---|---|
| Rayos desde el centro del pit hacia la pared | Anda en un cono. En el caso base, entre dos azimuts vecinos el rayo cruza la pared a radios muy distintos: **saltos de 265 m** en el eje |
| Caminar el contorno de cada nivel | Continuo, pero cambiar de anillo mete un paso lateral del ancho de un banco y el radio de giro se desploma |
| **Interpolar entre el contorno de abajo y el de arriba según la cota** | La rampa se aleja de la pared de a poco mientras sube. Es el que quedó |

El radio se consigue suavizando: promedio móvil **más re-espaciado uniforme** en cada
pasada. El re-espaciado no es cosmético — sin él los puntos se amontonan en las curvas y
el radio medido empeora por más que se suavice: se estanca en 17 m contra los 25 que se
alcanzan con re-espaciado. Suavizar es, físicamente, comerse la esquina: la rampa se mete
en la pared para poder girar, que es lo mismo que hace el humano estirando la banqueta.

Y como el suavizado acorta el desarrollo de forma **no proporcional** (trazar al 8.6 % dio
818 m y trazar al 6.5 % dio 1,219 m), no sirve un solo ajuste de pendiente: se prueba una
escalera de trazas y se toma la primera que alcanza la salida.

**12. La topografía recorta el diseño directamente, sin la etapa intermedia**
(2026-08-21, MOT-5).

El ROADMAP planteaba dos escalones: primero el "nivel suficiente" —diseñar 1-2 bancos
por encima del terreno y que el usuario recorte a mano con un booleano en su CAD— y
después el recorte directo, que es lo que Yhonny realmente quiere. Se fue directo al
segundo, y la razón es la decisión 6: **con la superficie ya en una grilla, recortar es
`minimum(z_diseño, z_terreno)`**, una resta de arreglos. El escalón intermedio existía
para ahorrar trabajo que, con esta representación, no cuesta.

`Parametros.bancos_sobre_topografia` queda declarado pero sin uso. No se borra: si
aparece un pit en ladera empinada donde el margen haga falta, el parámetro ya está en
el contrato y no hay que romper nada para retomarlo.

**El recorte cambia la referencia de los volúmenes, y eso hay que decirlo.** Sin
topografía el motor integra contra un plano imaginario a la altura de la cresta —la
única referencia posible sin datos—. Con terreno real, el techo pasa a ser el terreno, y
**`volumen_carcaza_m3` también baja** aunque la carcaza no se haya tocado: 11.27 M →
9.93 M m³ en el caso base. Lo que bajó es la imprecisión de la aproximación anterior.

**Lo que NO recorta:** las líneas `CRESTA`/`PIE` del DXF. Son contornos a cota fija
(decisión 7) y el recorte produce una curva irregular que no es una línea de banco. El
reporte lo dice en una advertencia en vez de entregar líneas que parecen diseño y no lo
son.

Medido sobre el caso base: el diseño protruía sobre el terreno en **0.40 ha (2.1 % de su
huella)** con la rampa puesta, hasta 18 m en el punto peor. La topografía del caso base
tiene el 93 % de sus caras bajo 5°, o sea que **ni el terreno más benigno es plano**: si
el recorte hiciera falta solo en laderas empinadas, este número sería cero.

## Lo que NO se decidió todavía

- **Algoritmo de trazado de rampa**: helicoidal simple contra búsqueda con
  restricción de radio. Empezar por lo simple y medir contra el archivo 4.
- **Cómo se suavizan las isolíneas** si se acepta ese formato de entrada.
