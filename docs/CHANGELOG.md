# Bitácora — PitPy

Formato: una entrada por sesión, con **Reporte de Cierre** (qué se hizo, qué se
verificó, qué quedó pendiente).

---

## 2026-08-21 — Núcleo C++ (nanobind) para los tres kernels de grilla · REQ-MOT-001

**1. Qué y por qué**

Miqueas preguntó si Python puro iba a aguantar volúmenes grandes. Lo medí antes de opinar:
un pit de 4 km con 58 bancos tardaba 23 s, y solo rasterizar su malla a paso 2 m eran 275 s.
Mi recomendación fue otra —limitar el trabajo a la franja pegada a la pared, que es un
cambio algorítmico con ~130× y sin dependencias—, pero la decisión fue núcleo C++ como
VentPy, y eso se hizo, completo.

**Qué se llevó a C++ y qué NO.** Tres funciones: rasterizar la malla a la grilla, la
distancia euclídea hasta una región, y marching squares. Nada más. Toda la geometría de
minas —qué es un banco, dónde va el fondo, qué se le avisa al usuario, los mensajes de
error— se queda en Python, donde se lee y se discute con el ingeniero.

**La implementación en Python no se borró**, y esa es la decisión de diseño que importa:
cada kernel conserva su gemela legible (`_rasterizar_python`, `_distancia_python`,
`_contornos_python`) y `tests/test_nucleo.py` exige que las dos den el mismo resultado.
Sin ese test, «lo reescribí en C++ y anda más rápido» es una afirmación sin respaldo:
podría andar más rápido y estar mal. También es el respaldo si alguien instala el sdist sin
compilador (`NUCLEO_COMPILADO` dice cuál está corriendo).

Un kernel se pudo mejorar de verdad, no solo traducir: la distancia en Python es fuerza
bruta sobre una ventana, O(celdas × offsets), y por eso necesitaba un tope de radio. En C++
es la transformada de Felzenszwalb & Huttenlocher: **exactamente el mismo resultado** en
O(celdas), sin tope.

**2. Criterio de aceptación → evidencia**

| Criterio | Evidencia |
|---|---|
| El núcleo da lo mismo que la referencia | ✅ 24 tests diferenciales nuevos; en el rasterizado y la distancia la coincidencia es a `atol=1e-9` sobre la carcaza real |
| Nada se rompió | ✅ 72 passed, 3 xfailed. Los tests de geometría de MOT-1 pasan sin tocarles una línea |
| Anda más rápido, medido | ✅ tabla de abajo |
| El paquete sigue publicable | ✅ `build` + `twine check --strict` PASSED en rueda y sdist |

**3. Verificación reproducible**

```
$ .venv/Scripts/python -m pytest -q
72 passed, 3 xfailed in 10.97s        (antes del núcleo: 30.14s)
```

Kernel contra kernel, y en la misma corrida se verifica que dan lo mismo:

```
  caso                            celdas     Python      C++      mejora
  caso base real 750 m             0.47 M     0.76s    0.003s    218.1x  identico
  caso base real, paso 0.5 m       1.92 M     1.94s    0.009s    217.3x  identico
  cono 2 km, paso 4 m              0.25 M     8.86s    0.030s    295.8x  identico
  cono 4 km, paso 2 m              4.00 M   275.40s    0.876s    314.3x  identico
```

De punta a punta, apagando y prendiendo el núcleo sobre el mismo pit y la misma
resolución:

```
  caso base real, 0.55 M celdas, 13 bancos:  Python 4.59s  ->  C++ 0.86s   (5.1x)
```

Y lo que cuesta hoy cada tamaño, a la resolución por omisión:

```
  caso base real   750 m   paso 1.01 m   0.55 M celdas   13 bancos    0.86s
  cono de 2 km    2000 m   paso 1.01 m   3.92 M celdas   38 bancos    9.49s
  cono de 4 km    4000 m   paso 2.00 m   4.00 M celdas   58 bancos   18.42s
```

⚠️ **Ojo con comparar contra los números que anoté antes en esta misma sesión**
(«cono de 2 km: 2.45 s»): esos se midieron con el tope de grilla en 1000 celdas por
lado. Al subirlo a 2000 —que es lo que resuelve la berma— esos pits pasan a
calcularse con **cuatro veces más celdas**, y por eso hoy tardan más. No es una
regresión: es más resolución. La comparación válida es a igual resolución, la de
arriba.

**El kernel rinde 200-300×, el diseño completo 5×.** Vale decirlo con todas las letras:
lo que quedaba fuera de los kernels ya era numpy, y numpy ya corría en C. Quien espere 300×
en el reloj de pared va a quedar decepcionado, y no porque el núcleo esté mal.

Empaquetado:

```
$ .venv/Scripts/python -m build
Successfully built pitpy-0.1.0.dev0.tar.gz and pitpy-0.1.0.dev0-cp312-cp312-win_amd64.whl
$ .venv/Scripts/python -m twine check --strict dist/*
PASSED / PASSED
```

**4. De paso, dos cosas que el núcleo destrabó**

- **El tope de resolución subió de 1000 a 2000 celdas por lado, y hacía falta.** Con 1000, un
  pit de 4 km quedaba con celdas de 4 m: una berma de 6 m no se resuelve con celda y media, y
  la línea de cresta traía más ruido que rasgo. Ahora el paso es 2 m —tres celdas por berma— y
  ese pit se diseña en 17.8 s. Era un problema de calidad geométrica, no de velocidad.
- **Un error real que encontró el port:** el encadenado de anillos en C++ partía el contorno
  de un cono en dos. Causa: dos cuadrados vecinos calculan el punto de su lado compartido con
  las esquinas en orden opuesto (`t` contra `1-t`) y el resultado difiere en el último bit.
  En Python eso lo tapaba el `round(x, 6)` que parecía cosmético. Ahora está replicado en C++
  **con el porqué escrito en el encabezado del archivo**, para que nadie lo «limpie».

**5. Archivos**

Nuevos: `CMakeLists.txt`, `include/pitpy/rasterizar.hpp`, `include/pitpy/distancia.hpp`,
`include/pitpy/contornos.hpp`, `bindings/bindings.cpp`, `tests/test_nucleo.py` (24 tests).
Modificados: `pyproject.toml` (scikit-build-core + cibuildwheel), `src/pitpy/superficie.py`
(despacho núcleo/referencia), `src/pitpy/bancos.py` (tope de grilla), `tests/test_bancos.py`,
`.github/workflows/release.yml` (ruedas por plataforma), `.github/workflows/tests.yml`,
`README.md`, `CHANGELOG.md`, `docs/ARQUITECTURA.md` (decisión 9), `docs/API_CONTRACTS.md`,
`docs/APP_REQUESTS.md` (REQ-MOT-001). Borrado: `MANIFEST.in` (era de setuptools).

**6. Impacto en el otro dominio**

**REQ-MOT-001 abierto, prioridad ALTA.** La API no cambió —ni una firma— pero el paquete sí:
de rueda universal a una rueda por plataforma con un `.pyd` adentro. PyInstaller suele
detectarlo solo, pero cuando no lo hace el `.exe` se arma sin error y revienta al abrirse con
`ModuleNotFoundError: pitpy._nucleo`. Le pedí a la App que lo verifique **abriendo la ventana**
en APP-3, y le di `NUCLEO_COMPILADO` para que sepa si quedó adentro sin esperar a que reviente.

**7. Qué quedó pendiente**

- **La franja angosta sigue disponible y sigue siendo el 130×.** El núcleo bajó la constante;
  el trabajo por banco sigue siendo O(área de la grilla) cuando debería ser O(perímetro). Si
  alguna vez se busca el volumen en tiempo real de ESPECIFICACION §8, ahí está el camino.
- **No hay tests de C++** (VentPy tiene GoogleTest). Hoy la red son los 24 diferenciales desde
  Python, que prueban el kernel contra su referencia sobre datos reales. Es suficiente
  mientras los kernels sean tres funciones puras; si el núcleo crece, hace falta gtest.
- **El trusted publisher de PyPI y el environment `pypi` siguen sin configurar** — es manual,
  de Miqueas. Y no se publica hasta que cierre MOT-6 y Yhonny valide.
- Los tres `xfail` siguen igual: MOT-2 (volúmenes) y MOT-4 (rampa). El próximo objetivo del
  motor no cambió.

---

## 2026-08-21 — Empaquetado listo para PyPI, al estándar de VentPy

**1. Qué y por qué**

Miqueas avisó que PitPy se va a publicar en PyPI igual que VentPy. Fui a ver cómo está
armado VentPy y traje su estándar acá. Es trabajo de infraestructura, no de motor: no
cambia una línea de geometría.

Lo que se copió de VentPy: metadatos completos en el `pyproject`, licencia como expresión
PEP 639, `[project.urls]`, badges en el README, registro de cambios público en formato
Keep a Changelog, workflow de tests y workflow de publicación por **trusted publishing**
(sin token en secrets, con `environment: pypi`). Lo que **no** se copió: `cibuildwheel` y
la matriz de ruedas por plataforma — VentPy las necesita porque su núcleo es C++; PitPy es
Python puro y le alcanza una rueda universal.

**2. Decisión: se levanta el tope `numpy<2`**

El `pyproject` capaba numpy a `<2` con el comentario «hay VPS sin soporte x86-64-v2».
Verificado hoy: **la misma suite pasa con numpy 1.26.4 y con 2.4.6** (41 passed, 3 xfailed
en las dos). Un tope superior en una librería publicada obliga a degradar numpy en el
entorno de quien la instale, y el motivo original es de despliegue, no de la librería: ese
pin va en el VPS, no en el paquete. Queda `numpy>=1.24`, y el workflow de tests corre la
suite contra la versión mínima declarada y contra la última, para que el rango publicado no
sea una promesa sin probar.

**3. Verificación reproducible**

```
$ .venv/Scripts/python -m build
Successfully built pitpy-0.1.0.dev0.tar.gz and pitpy-0.1.0.dev0-py3-none-any.whl

$ .venv/Scripts/python -m twine check --strict dist/*
Checking dist/pitpy-0.1.0.dev0-py3-none-any.whl: PASSED
Checking dist/pitpy-0.1.0.dev0.tar.gz: PASSED
```

Instalación limpia de la rueda en un venv vacío, sin el repositorio a la vista:

```
pitpy 0.1.0.dev0 | numpy 2.5.2
bancos: 9 | cotas 20.0 .. 100.0
silueta: 177 puntos
$ pitpy --help
usage: pitpy [-h] {inspeccionar,disenar} ...
```

La rueda lleva `py.typed` y el `LICENSE`; los metadatos salen como
`Metadata-Version: 2.4` con `License-Expression: MIT`.

El nombre **`pitpy` está libre en PyPI** (`https://pypi.org/pypi/pitpy/json` → 404).

**4. Archivos**

Nuevos: `.github/workflows/tests.yml`, `.github/workflows/release.yml`, `CHANGELOG.md`
(registro público, distinto de esta bitácora), `MANIFEST.in`, `src/pitpy/py.typed`.
Modificados: `pyproject.toml`, `README.md` (badges, estado real después de MOT-1,
instalación).

**5. Commits**

`chore: empaquetado listo para publicar en PyPI`.

**6. Impacto en el otro dominio**

Ninguno en el contrato. Sí importa para PitForge: la rueda incluye `py.typed`, así que el
editor de la App ve los tipos del motor sin stubs. Y cuando PitPy esté en PyPI, PitForge
puede depender de una versión publicada en vez de una ruta local — pero eso recién cuando
salga 0.1.0.

**7. Qué quedó pendiente**

- **Publicar no se puede todavía y no debería:** `disenar()` está a medias (sin rampa, sin
  topografía, sin reporte). Publicar un paquete cuyo ejemplo del README levanta
  `NotImplementedError` quema el nombre. La 0.1.0 sale cuando cierre MOT-6 y Yhonny valide.
- **Falta configurar en GitHub, y es manual:** el *trusted publisher* en PyPI (proyecto
  `pitpy`, repo `Miqueas7/PitPy`, workflow `release.yml`, environment `pypi`) y el
  environment `pypi` en el repositorio. Sin eso el workflow de publicación falla al llegar.
- **El repositorio remoto todavía no existe** (`git remote -v` vacío): los badges y las URLs
  del `pyproject` apuntan a `github.com/Miqueas7/PitPy`, que hay que crear.
- VentPy tiene además `CONTRIBUTING.md`, README bilingüe y sitio de documentación
  (`miqueas.dev/ventpy`). No los inventé acá: son decisión de Miqueas y valen la pena
  recién cuando el motor esté completo.
- **Este trabajo no tiene fila en el tablero.** La ronda lo va a marcar como objetivo
  huérfano. Corresponde que el Orquestador le abra su fila (¿MOT-7, publicación?).

---

## 2026-08-21 — MOT-1: bancos, y respuesta a REQ-APP-001 y REQ-APP-002

**1. Qué y por qué**

Etapa 1 del ROADMAP: de la carcaza a bancos con berma. Con ella se cierran también las
tres decisiones que estaban abiertas y bloqueando (L-3 del tablero), y de yapa sale
`Carcaza.silueta()`, que era el REQ-APP-001 de la App.

**Decisiones tomadas** (van completas en `ARQUITECTURA.md` §6-8):

- **6. La superficie se representa como grilla regular `z(x, y)`**, no como malla ni como
  curvas de nivel. Lo que la inclinó no fue la elegancia sino tres cosas que se vuelven
  triviales: ensanchar un contorno (dilatación de celdas contra offset de polígonos, que es
  el problema difícil de la geometría computacional), recortar con topografía (`min` celda a
  celda) y el volumen incremental que pide ESPECIFICACION §8. Costo: discretización, que se
  compensa extrayendo las líneas con marching squares en vez de seguir el borde de las celdas.
- **7. Los bancos se anclan a la carcaza cota por cota, sin acumular.** El pie de cada banco
  se apoya en el contorno de la carcaza de su cota; la cresta sale ensanchando el avance de
  cara. **La alternativa la probé y la descarté con números:** construir de abajo hacia arriba
  dilatando el banco anterior da **34.5 ha contra las 19.6 del ingeniero** — la dilatación de
  un contorno arrugado se derrama por los rincones y el error se acumula (+1.2 ha por banco).
- **8. El fondo es el nivel más bajo cuya sección admita un círculo del ancho de un banco**
  (10.04 m acá). Medido: a la cota 210 la sección de la carcaza admite 8.0 m — es la punta
  del tazón, no un piso; a la 220, 30.5 m. El criterio pone el fondo en 220, que es
  **exactamente donde lo puso el ingeniero**. No es ensanchar el fondo (ESPECIFICACION §7 lo
  prohíbe): es no inventar un banco donde la carcaza no tiene piso.

**2. Criterio de aceptación → evidencia**

| Criterio (ROADMAP §Etapa 1) | Evidencia |
|---|---|
| `pytest tests/test_caso_base.py::test_genera_trece_bancos` | ✅ pasa. `xfail` quitado |
| 13 bancos cada 10 m entre 230 y 350 | ✅ 13 bancos, cotas 230..350, pie del más bajo en la 220 |
| Comparar contra el diseño de referencia (CLAUDE.md, regla 1) | ✅ test nuevo `test_los_bancos_caen_sobre_el_diseno_que_hizo_el_ingeniero`: **mediana 2.83 m** sobre 19,292 puntos de pie contra el archivo 4 |
| Decisión de representación anotada con su porqué | ✅ `ARQUITECTURA.md` §6-8 |

**3. Verificación reproducible**

```
$ PITPY_CASO_BASE="C:/Users/mique/OneDrive/TRABAJOS/Yhonny Ruiz - Recmin" .venv/Scripts/python -m pytest -q
41 passed, 3 xfailed in 25.21s
```

Los 3 `xfail` que quedan son MOT-2 (reporte de volúmenes) y MOT-4 (rampa), cada uno con su
razón declarada. Antes de esta sesión el suite ni siquiera corría: `ModuleNotFoundError: No
module named 'pitpy'` — no había venv ni instalación editable.

```
$ .venv/Scripts/python -c "... disenar(carcaza_suavizada, parametros_de_yhonny) ..."
leer_carcaza: 0.1s  (18703 caras)
disenar: 3.7s -> 13 bancos, etapas [('detectando talud', 0.05), ('generando bancos', 0.2), ('generando bancos', 1.0)]
cotas: 230 .. 350
  banco 230: pie 219 pts (z=220), cresta 296 pts (z=230)
  banco 290: pie 1957 pts (z=280), cresta 1948 pts (z=290)
  banco 350: pie 1432 pts (z=340), cresta 1405 pts (z=350)
```

```
$ .venv/Scripts/python -c "... carcaza.silueta(paso) ..."
silueta paso=10.0 m:   281 puntos, 0.15s, area encerrada 19.25 ha, z 325.0..352.5
silueta paso= 5.0 m:   559 puntos, 0.10s, area encerrada 19.01 ha, z 325.0..352.5
```

**Mediciones que respaldan las decisiones** (grilla de 2 m sobre el caso base):

```
area de la grilla contra el calculo exacto por triangulo:
  paso 5.0 m -> 19.24 ha (+0.23)   paso 2.0 m -> 19.05 ha (+0.04)   exacto 19.01 ha

avance horizontal del contorno por banco (mediana), carcaza suavizada:
  240->250  10.20 | 250->260  10.00 | ... | 320->330   8.94        (= 45 grados, cierra)

el diseno del ingeniero contra la carcaza, cota a cota (offset mediano del contorno):
  220: -4.00 | 230: +2.00 | 240: -2.00 | ... | 350: +2.00          (sin deriva: no acumula)

ancho inscrito de la seccion de la carcaza:
  cota 210 -> 8.0 m | cota 220 -> 30.5 m | cota 230 -> 54.4 m      (el fondo va en 220)
```

**4. Archivos**

Nuevos: `src/pitpy/superficie.py`, `tests/test_superficie.py` (11 tests),
`tests/test_bancos.py` (8 tests), `.venv/` (ignorado).
Modificados: `src/pitpy/bancos.py` (implementado), `src/pitpy/__init__.py` (`disenar` parcial),
`src/pitpy/modelo.py` (`Carcaza.silueta`), `tests/test_caso_base.py` (se quitó el `xfail` del
criterio de aceptación y se agregó el test contra el archivo 4), `docs/ARQUITECTURA.md`
(decisiones 6-8), `docs/API_CONTRACTS.md` (silueta + tabla de estado de implementación),
`../PitForge/docs/API_REQUESTS.md` (solo los bloques *Respuesta del Motor*).

**5. Commits**

Ninguno todavía: el árbol venía sucio con los cambios de la instalación de la orquestación
(L-6 del tablero, decisión pendiente de Miqueas). Propuesta: dos commits separados — uno con
lo de la instalación (`.gitignore`, `CLAUDE.md`, `docs/APP_REQUESTS.md`) y otro con MOT-1.

**6. Impacto en el otro dominio**

- **REQ-APP-001 (silueta): respondido, aceptado sin cambios de firma, e implementado.** Queda
  en 🧪 verificado motor; lo cierra la App cuando conecte.
- **REQ-APP-002 (`rampa.cabe`): respondido, aceptado con una corrección** — el `str` viene
  siempre, no solo cuando no cabe. Se entrega después de MOT-4, y el porqué quedó por escrito:
  una estimación barata miente justo en los pits raros, y un validador que dice «cabe» y
  después falla es peor que no tenerlo. Le pedí a la App que `cabe()` **avise pero no bloquee**
  el botón de calcular.
- **Contrato:** se agregó `Carcaza.silueta` y una tabla de estado de implementación. Nada se
  rompió, ninguna firma cambió → **no hace falta ningún REQ-MOT**.

**7. Qué quedó pendiente**

- **MOT-2 (`volumen`)** es lo que sigue, y ahora es barato: el área de una sección es contar
  celdas. Con eso se cierra el número que justifica la herramienta (las 0.6 ha).
- **La cresta contra el archivo 4 no quedó cubierta por un test automático.** Lo intenté y el
  instrumento no da: las crestas del archivo 4 no vienen rotuladas, y muestrear cotas en el
  borde de una berma es ambiguo a escala de celda (una celda adentro y ya estás en la cara de
  banco, 6 m más abajo). Medido a mano: la cresta generada cae a **3.61 m de mediana** de la
  franja de berma del ingeniero, coherente con los 2.83 m de los pies — este diseño va ~3 m
  por dentro del suyo porque todavía no lleva rampa. La verificación de la cresta es visual y
  es justamente el criterio de aceptación de MOT-3 (abrirlo en un CAD).
- **L-4 se puede cerrar:** `.pytest_cache/` y `.venv/` ya están gitignoreados, verificado.
- **L-2 sigue vivo y ahora muerde más:** sin `PITPY_CASO_BASE` los tests del caso base se
  saltan en vez de fallar. Ahora que hay tests que sí prueban geometría, un verde sin esa
  variable es un falso verde. Vale la pena que la ronda del Orquestador lo mire.
- El `paso` por omisión quedó topeado a 1000 celdas por lado. Salió de un experimento: con
  banco de 7 m y berma de 6 m el avance de cara es 1 m, el paso ideal 0.25 m y la grilla se
  iba a 9 millones de celdas — en PitForge eso no es «lento», es la ventana colgada.

**Nota para quien siga**

`superficie.py` es la pieza central ahora: `bancos`, `topo` y `volumen` trabajan todos sobre
la misma grilla. Antes de escribir `volumen`, leer `contorno_de` y `seccion` — el área de una
sección ya sale de ahí, y el recálculo incremental de ESPECIFICACION §8 depende de no romper
esa forma.

---

## 2026-08-17 — Andamiaje inicial

**Qué se hizo**
- Se creó el repositorio con su estructura y documentación completa.
- Se documentó la especificación funcional a partir de la conversación con el
  Ing. Yhonny Ruiz (`docs/ESPECIFICACION.md`), con citas textuales.
- Se analizaron los 5 archivos DXF del caso base y se midió su geometría
  (`docs/CASO_BASE.md`).
- Se implementó `pitpy.dxf`: lector de mallas 3DFACE y de polilíneas.

**Qué se verificó**
- El lector se probó contra los 5 archivos reales: 20,876 / 18,703 / 21 / 5,923
  / 7,220 entidades respectivamente.
- Se confirmó que el talud global de 45° declarado por Yhonny es detectable desde
  la malla: mediana 48.2°, con 68 % de caras entre 45° y 50°.
- Se verificó la consistencia geométrica del caso base: banco 10 m + cara 68° +
  berma 6 m = 44.9° global ≈ los 45° declarados.

**Qué quedó pendiente**
- Todo el motor salvo la lectura: `taludes`, `bancos`, `rampa`, `topo`, `volumen`.
- Decidir la representación interna de la superficie (ver ARQUITECTURA).
- Los tests del caso base están escritos pero la mayoría marcados `xfail`.

**Nota para quien siga**
Empezar por `taludes` — el método ya está validado, solo falta empaquetarlo. Es
la victoria más rápida y desbloquea `bancos`.
