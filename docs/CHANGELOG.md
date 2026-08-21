# Bitácora — PitPy

Formato: una entrada por sesión, con **Reporte de Cierre** (qué se hizo, qué se
verificó, qué quedó pendiente).

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
