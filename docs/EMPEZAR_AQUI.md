# Empezar aquí

> Para el agente que tome este proyecto sin haber estado en la conversación
> original. Lee esto completo antes de escribir una línea.

## En una frase

Convertir una **carcaza de pit optimizado** (una superficie 3D que sale de un
optimizador) en un **diseño operativo**: bancos, bermas y una rampa. Y reportar
cuánto estéril adicional costó volverla operativa.

## Por qué existe

Optimizar un pit ya está resuelto y es rápido. Convertir esa carcaza en un
diseño con geometría real toma **horas de trabajo manual banco a banco**. Tanto,
que en la práctica solo se alcanza a evaluar uno o dos diseños cuando deberían
compararse muchos.

El valor no es ahorrar un rato. Es **poder comparar diez alternativas en vez de
una**.

## Quién define los requisitos

El **Ing. Yhonny Ruiz**, instructor oficial de RecMin (el software minero
gratuito del Dr. César Castañón). Es el experto de dominio, aportó el caso base
y va a ser el primer usuario y validador.

**No programa.** Eso condiciona todo: por eso existe PitForge, y por eso los
mensajes de error tienen que estar escritos para un ingeniero de minas, no para
un desarrollador.

## Orden de lectura

1. **`ESPECIFICACION.md`** — los requisitos, con las citas textuales de Yhonny.
   Es la fuente. Cuando dudes de un criterio, está ahí.
2. **`CASO_BASE.md`** — los cinco archivos reales, medidos. Incluye la
   verificación geométrica y las cifras que usan los tests.
3. **`ARQUITECTURA.md`** — el flujo, las decisiones tomadas **y las que se
   dejaron abiertas a propósito**.
4. **`API_CONTRACTS.md`** — el contrato que consume PitForge. Cambiarlo sin
   avisar rompe la app.
5. **`ROADMAP.md`** — qué hacer, en qué orden, y cómo saber que está bien.
6. **`../CLAUDE.md`** — las reglas de tu dominio.

## Preparar el entorno

```powershell
cd "D:\Repositorios\Yhonny Ruiz\PitPy"
pip install -e ".[dev]"
$env:PITPY_CASO_BASE = "C:\Users\mique\OneDrive\TRABAJOS\Yhonny Ruiz - Recmin"
pytest -q
```

Debe dar **20 passed, 4 xfailed**. Si los 20 no pasan, algo se rompió antes de
que llegaras: arréglalo antes de avanzar.

Los cinco archivos DXF del caso base **no están en el repo** (pesan 10 MB). Viven
en OneDrive y se localizan por esa variable de entorno. Sin ella los tests que
los usan se saltan en vez de fallar.

## Lo que ya funciona

```powershell
python -m pitpy.cli inspeccionar "<ruta>\Miqueas 2_Carcaza suavizada.dxf"
```

```
caras 3DFACE : 18,703
polilíneas   : 408
extensión    : 640 x 750 m
cotas        : 210.0 a 352.5  (desnivel 142 m)
talud        : mediana 48.2 grados  [p10 26.6 - p90 56.3]
```

- `dxf.py` — lee mallas 3DFACE y polilíneas. Validado contra los 5 archivos.
- `taludes.py` — detecta el talud y convierte entre cara de banco y talud global.
- `modelo.py` — los tipos del dominio.
- `cli.py` — solo el subcomando `inspeccionar`.

## Lo que falta

`bancos.py`, `rampa.py`, `topo.py`, `volumen.py`, la escritura de DXF y el
subcomando `disenar`. Cada uno tiene su especificación completa en el docstring
del módulo. **Léelos: no son esqueletos vacíos, traen el criterio de diseño.**

## Tres trampas ya documentadas

**1. Los DXF de RecMin son mallas de `3DFACE`, no polilíneas.**
Un parser que asuma polilíneas devuelve datos sin sentido y **no lanza ningún
error**. En el caso base leía 816 vértices todos a la misma cota en vez de 84,320
repartidos en 145 m de altura. Ya pasó una vez. Está en grande al inicio de
`dxf.py`.

**2. Las colas de la distribución de ángulos son ruido de triangulación.**
La carcaza suavizada da `p10 = 26.6°` y `p90 = 56.3°` para un talud único de 45°.
Son 3,865 caras entre 25 y 35 grados repartidas por toda la malla: al partir un
cuadrilátero del talud en dos triángulos, uno queda más tendido. **Usa el rango
intercuartil (3.2° en ese mismo archivo), nunca p10-p90.**

**3. El ancho mínimo de fondo NO es una restricción obligatoria.**
Yhonny prefiere perder bloques económicos antes que ensanchar el pit y arrastrar
estéril. Ver `ESPECIFICACION.md` §7. Ensanchar en silencio sería imponerle un
criterio que él rechaza explícitamente.

## Cómo saber que un cambio está bien

El archivo `4_Pit Geometric Diseñado.dxf` **lo diseñó un ingeniero**. Es la
referencia, no una sugerencia. Todo resultado se compara contra él:

- 13 bancos cada 10 m, entre las cotas 230 y 350
- Distribución de ángulos bimodal: caras de banco en 65-70°, bermas bajo 5°
- 19.6 ha proyectadas, contra 19.0 de la carcaza suavizada

Esas **0.6 ha de diferencia** son el número por el que existe la herramienta.

Si un test del caso base falla, **no ajustes el número esperado para que pase.**
O el cambio está mal, o los archivos cambiaron. Las dos cosas hay que mirarlas.

## El estándar de calidad

Yhonny dijo que sus diseños son para **etapas preliminares o informes tipo PEA**,
no ingeniería de detalle. La vara es «sirve para un PEA», no «reemplaza a un
ingeniero de diseño».

No sobre-construyas. Y no metas nada de la lista v2 sin preguntar antes.
