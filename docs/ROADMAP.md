# Plan de trabajo — PitPy

> Orden sugerido, con criterio de aceptación por etapa. No es un cronograma:
> es una secuencia de dependencias. Cada etapa desbloquea la siguiente.

## Estado actual

| Módulo | Estado |
|---|---|
| `dxf` (lectura) | ✅ funciona, validado |
| `taludes` | ✅ funciona, validado |
| `modelo` | ✅ tipos completos |
| `cli inspeccionar` | ✅ funciona |
| `bancos` | ⬜ **empezar por acá** |
| `volumen` | ⬜ |
| `dxf` (escritura) | ⬜ |
| `rampa` | ⬜ |
| `topo` | ⬜ |
| `cli disenar` | ⬜ |

---

## Etapa 1 — `bancos` ← empezar acá

**Por qué primero:** es donde está la mayor parte del valor. `taludes` ya está
resuelto y lo desbloquea. La rampa se puede aproximar al principio; los bancos no.

**Qué hacer**

De la carcaza (superficie continua al talud global) sacar la secuencia de bancos:
por cada cota, la línea de cresta y la de pie, separadas por la berma.

La cara de banco **no se pide al usuario**: se deriva del talud global y la berma
con `taludes.cara_banco_desde_global()`. Yhonny razona en talud global, no en cara
de banco. Pedirle la cara sería trasladarle una cuenta que la herramienta debe
hacer sola.

**Decisión abierta que hay que tomar acá:** cómo se representa internamente la
superficie — malla de triángulos, grilla regular, o curvas de nivel. Afecta
también a `topo`. Se decide con el caso base en la mano, no antes. Anota en el
CHANGELOG qué elegiste y por qué.

**Criterio de aceptación**

```
pytest tests/test_caso_base.py::test_genera_trece_bancos
```

13 bancos cada 10 m entre las cotas 230 y 350. Quita el `xfail` cuando pase.

---

## Etapa 2 — `volumen`

**Por qué antes que la rampa:** sin volúmenes no se puede medir si un diseño es
bueno. Y con los bancos ya generados se puede comparar contra la carcaza aunque
todavía no haya rampa.

**Qué hacer**

Área proyectada y volumen del diseño y de la carcaza, y la diferencia entre
ambos (el sobre-estéril).

**Mantenerlo recalculable de forma incremental.** No es capricho: la idea que
Yhonny describió en su segundo mensaje —mover la rampa y ver el volumen cambiar
en tiempo real— depende de eso. Si el cálculo solo funciona de una pasada
completa, esa función se vuelve imposible sin reescribir.

**Criterio de aceptación**

`area_proyectada_ha()` debe dar 19.0 ha para la carcaza suavizada y 19.6 ha para
el pit diseñado, ±0.1.

---

## Etapa 3 — escritura de DXF

**Por qué acá:** es cuando Yhonny puede ver algo por primera vez. Aunque no haya
rampa todavía, un DXF con bancos y bermas ya se abre en RecMin y le sirve para
opinar. **Su opinión temprana vale más que cualquier avance en solitario.**

**Qué hacer**

Escribir en capas separadas: `CRESTA`, `PIE`, `BERMA`, `RAMPA`, `TALUD`.

**Criterio de aceptación**

Que Miqueas lo abra en un CAD y las capas se distingan. Y que se lo mande a
Yhonny para que lo compare con el suyo.

**Estado al 2026-08-21:** se escriben `CRESTA` y `PIE`, una polilínea 3D cerrada
por banco, cada una con su color. Falta la malla de superficie (`BERMA`, `TALUD`).

**Por qué falta, para que nadie la dé por trivial:** tejer una cinta de triángulos
entre el pie y la cresta de cada banco parece directo y no lo es. Los dos anillos
salen de una grilla, tienen distinta cantidad de vértices y distinta forma local, y
al parearlos por longitud de arco la cinta se corta en diagonal. Medido sobre el
caso base: la malla sumaba **23.4 ha de caras para un diseño de 19.2 ha** —4 ha de
caras montadas unas sobre otras— y aparecían caras de 85° que en el diseño no
existen. Se probaron dos pareos (avance del atrasado, y remuestreo uniforme) y
ninguno alcanzó. Hacerlo bien pide emparejar por cercanía con restricción de
monotonía, o triangular la superficie completa desde la grilla.

Las líneas alcanzan para el objetivo de la etapa —superponerlas sobre el diseño del
ingeniero y comparar— y es además como se intercambian los diseños en la práctica.

---

## Etapa 4 — `rampa`

**Enfoque para v1:** trazado helicoidal simple sobre la pared, a pendiente
constante, verificando en cada curva que el radio no baje del mínimo. Cuando no
cumpla, ensanchar la banqueta localmente — que es lo que hace el humano.

Empezar por lo simple y medir contra el archivo 4. **No arrancar con búsqueda de
rutas:** puede que no haga falta, y es un pozo de tiempo.

**El radio de giro es la ventaja competitiva.** RecMin no lo admite como
parámetro; hoy se resuelve a ojo estirando la banqueta. Si PitPy lo respeta de
verdad, hace algo que la herramienta que ellos usan no hace.

**Criterio de aceptación**

Que la rampa exista, respete el radio, y que el sobre-área quede cerca de 0.6 ha.

**Estado al 2026-08-21: cumplido.** Sobre el caso base: 1,256 m de desarrollo entre
las cotas 230 y 350, radio mínimo **26.2 m** para 25 pedidos, pendiente lograda
9.6 %, y **sobre-área 0.409 ha** contra las 0.6 del ingeniero (que incluye su
propio trazado, distinto del nuestro). El sobre-estéril pasa de −618,000 m³ sin
rampa a **+364,710 m³** con ella.

**Lo que quedó fuera, dicho de frente:**

- **La rampa no baja hasta el fondo.** Arranca en el nivel más bajo donde el radio
  de giro entra de verdad — en el caso base, la cota 230 y no la 220 — y se avisa
  por escrito. No es una limitación: es lo que hace Yhonny (ESPECIFICACION §7).
- **El sector de salida no se elige**, arranca en el primer anillo. Elegirlo es v2
  y es, en palabras suyas, «un boom».
- **La pendiente lograda puede ser más tendida que la pedida** (9.6 % contra 10 %):
  respetar el radio obliga a alargar la rampa. La pedida es un máximo, así que
  entregar menos es correcto — pero se informa, no se maquilla.

---

## Etapa 5 — `topo`

Primero el nivel **suficiente**: diseñar 1 o 2 bancos por encima de la cota
máxima del terreno y dejar que el usuario recorte con un booleano. Es lo que hoy
hace a mano y ya le sirve.

Después el recorte directo, que es lo que él querría.

**Cuidado:** la topografía del caso base es benigna —terreno suave, 93 % de las
caras bajo 5°—. No asumas que siempre lo será. Un pit en ladera empinada rompe
cualquier atajo que dependa de terreno plano.

**Estado al 2026-08-21: cumplido, yendo directo al recorte.** Con la grilla ya
construida (decisión 6), recortar es una resta de arreglos, no más difícil que
el "nivel suficiente" — así que se implementó directo, sin la etapa intermedia.
Medido sobre el caso base (con rampa): **0.40 ha recortadas (2.1 % de la
huella)**, donde el diseño quedaba por encima del terreno real. Que el terreno
sea "benigno" no lo hace plano: 93 % de caras bajo 5° no es lo mismo que 0°.

**Consecuencia que hay que conocer:** con topografía, `volumen_carcaza_m3`
**también baja** (11.27 M → 9.93 M m³ en el caso base), aunque la carcaza no se
tocó. Antes se medía contra un plano imaginario a la altura de la cresta; con
terreno real esa aproximación se reemplaza por el techo verdadero, y el número
se vuelve más preciso, no distinto en su significado.

**Lo que sigue sin hacer:** las líneas de cresta y pie exportadas al DXF no se
recortan —son contornos a cota fija (decisión 7), y el recorte real produce una
curva irregular que no encaja en ese modelo—. Solo los volúmenes y el reporte
son topografía-conscientes. Ídem la malla de superficie del DXF, pendiente desde
MOT-3.

---

## Etapa 6 — `cli disenar` y entrega a PitForge

Cerrar el flujo completo por línea de comandos, y recién ahí PitForge tiene contra
qué programar.

Revisar `../PitForge/docs/API_REQUESTS.md`: hay dos pedidos abiertos (silueta
liviana para vista previa, y verificación de si la rampa cabe antes de calcular).

---

## Cuando termine v1

Antes de pensar en v2, **mandarle a Yhonny el diseño generado y su reporte de
volúmenes** y pedirle que lo compare con el suyo. Su respuesta define qué se
construye después.

Lo de v2 está listado en `ESPECIFICACION.md` §10. La que más valor tiene, según
sus propias palabras, es elegir por qué sector sale la rampa a superficie: «eso
sería un boom». Pero no se empieza hasta que la v1 esté validada por él.
