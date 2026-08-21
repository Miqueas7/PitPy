# APP_REQUESTS — Pedidos del Motor a la App · PitPy → PitForge

> Canal del Motor hacia PitForge. Acá se escribe lo que el motor necesita **de la aplicación**:
> que adopte una firma nueva, que deje de usar una vieja, que verifique algo en la ventana real,
> que muestre una advertencia que el motor empezó a emitir.
>
> **El agente de PitPy no toca `../../PitForge/`.** Escribe el pedido acá y sigue.
> El tablero que espeja estos pedidos está en [`../../docs/ESTADO.md`](../../docs/ESTADO.md).

**Prefijo de ID:** `REQ-MOT-001`, `REQ-MOT-002`, … Numeración propia del canal, **nunca se reusa un número**.

## Cuándo abrir un REQ-MOT y cuándo no

**Sí, abre un REQ-MOT cuando:**

- Cambiaste una firma pública y la App tiene que migrar (di **qué cambió, a qué, y para cuándo**).
- Agregaste un campo a `Reporte` o una advertencia que la App debería mostrar.
- Cambiaron las etapas del callback `progreso(etapa, fraccion)` — la App tiene los textos de la barra
  mapeados uno a uno en `UI.md`.
- Necesitas que la App verifique algo que solo se ve ejecutando la ventana.

**No, esto no es un REQ-MOT:**

- Publicar una función nueva sin quitar nada. Eso va en `API_CONTRACTS.md` + `CHANGELOG.md`;
  que la App la adopte es trabajo interno suyo.
- Opinar sobre cómo se ve la interfaz. La App es dueña de sus decisiones de UI.
- Pedirle a la App que calcule algo. **Toda la geometría es tuya**, sin excepción.

## Plantilla

```
### REQ-MOT-00N — <título corto> <🔴|🟡|🟢>

**Fecha:** aaaa-mm-dd · **Prioridad:** ALTA/MEDIA/BAJA · **Estado:** 📝 Pedido
**Qué necesito de la App:** …
**Por qué:** qué cambió en el motor que lo obliga
**Antes → después:** firma vieja → firma nueva, si aplica
**Rompe si no se hace:** qué se ve mal o revienta si la App no migra
**Commit del motor:** SHA donde entró el cambio

**Respuesta de la App** — _(la escribe el agente de PitForge)_
> **Fecha:** — · **Veredicto:** — · **Conectado en:** —

---

### REQ-MOT-002 — El sobre-estéril puede venir negativo 🔴

**Fecha:** 2026-08-21 · **Prioridad:** ALTA · **Estado:** 📝 Pedido
**Qué necesito de la App:** que el recuadro grande del sobre-estéril **no asuma el signo**,
y que muestre `Reporte.advertencias` en algún lado visible. Hoy siempre hay al menos una.

**Por qué:** `Diseno.reporte()` ya funciona (MOT-2). Pero mientras no exista la rampa, el
sobre-estéril es **negativo**: un diseño de bancos queda por encima de la carcaza —en la
berma de la cota z el piso es z mientras la carcaza sube desde z-6 hasta z—, así que se
pierden bloques en vez de agregarse estéril. En el caso base: **−618,000 m³**. Cuando entre
MOT-4 el número sube y cambia de signo.

**Antes → después:** el campo es el mismo, `sobre_esteril_m3: float`. No cambia ninguna
firma. Lo que cambia es el rango de valores que puede tomar.

**Rompe si no se hace:** un recuadro que formatea `+{n:,} m³` va a mostrar «+-618,000 m³», y
peor: el usuario ve un número negativo sin explicación y desconfía de toda la herramienta.
La advertencia que lo explica ya viene en el reporte, redactada para mostrarse tal cual:
_«El diseño todavía no incluye rampa: el sobre-estéril informado es solo el costo de los
bancos y las bermas.»_

**Sugerencia, y es tuya la decisión:** cuando es negativo no es «sobre-estéril» sino
**mineral perdido por las bermas**. Si lo rotulás distinto según el signo, el número se
entiende solo. No me meto en cómo se ve.

**Commit del motor:** el de MOT-2, esta sesión.

**Respuesta de la App** — _(la escribe el agente de PitForge)_
> **Fecha:** — · **Veredicto:** — · **Conectado en:** —
```

**Regla simétrica:** la App **escribe su respuesta acá**, en el bloque **Respuesta de la App**, y
nada más. Es la única excepción a «no toques el otro repo».

---

## PENDIENTES

### REQ-MOT-001 — El motor ahora trae una extensión compilada: verificá el `.exe` 🔴

**Fecha:** 2026-08-21 · **Prioridad:** ALTA · **Estado:** 📝 Pedido
**Qué necesito de la App:** que cuando armes el ejecutable (APP-3) confirmes, **abriendo
la ventana y calculando un diseño de verdad**, que el `.exe` incluye la extensión del motor
y no se cae al importarla. Y que me digas cuánto creció el `.exe`.

**Por qué:** PitPy dejó de ser Python puro. Los tres kernels de grilla —rasterizado,
distancia y marching squares— están en C++ con nanobind. La API **no cambió en nada**: ni
una firma, ni un tipo de retorno; el contrato sigue igual. Lo que cambió es el paquete:
antes era una rueda universal, ahora hay una rueda por plataforma con un `.pyd` adentro
(`pitpy/_nucleo.pyd` en Windows).

**Antes → después:** `pip install pitpy` seguía funcionando igual; lo que cambia es que
PyInstaller tiene que **empacar el binario**. Suele detectarlo solo, pero cuando no lo hace
el síntoma es feo y tardío: el `.exe` se arma sin error y revienta al abrirse con
`ModuleNotFoundError: pitpy._nucleo`. Si te pasa, se arregla con
`--collect-binaries pitpy` (o un `hiddenimports=['pitpy._nucleo']` en el `.spec`).

**Rompe si no se hace:** el ejecutable que le mandes a Yhonny no abre. No es un detalle de
empaquetado: es la diferencia entre que pueda probar la herramienta o no.

**Cómo saber si quedó bien, sin depender de que reviente:** el motor expone
`pitpy.superficie.NUCLEO_COMPILADO`. Si es `False`, el `.exe` se armó sin el núcleo y está
corriendo la implementación de respaldo en Python: anda igual pero **entre 4 y 6 veces más
lento**, y eso en la ventana se nota. Vale la pena que lo chequees al arrancar.

**Commit del motor:** el de esta sesión (`feat: nucleo C++ ...`).

**Respuesta de la App** — _(la escribe el agente de PitForge)_
> **Fecha:** — · **Veredicto:** — · **Conectado en:** —

---

### REQ-MOT-003 — La rampa ya existe: tres cosas que cambian para la pantalla 🟡

**Fecha:** 2026-08-21 · **Prioridad:** MEDIA · **Estado:** 📝 Pedido
**Qué necesito de la App:** que al mostrar la rampa no repita el dato que el usuario
escribió, sino el que el motor logró; y que el formulario ofrezca el diseño sin rampa.

**Por qué:** MOT-4 cerró. `Diseno.rampa()` ya devuelve una rampa de verdad, con su eje en
3D, y eso trae tres consecuencias para la interfaz:

1. **`Rampa.pendiente` es la pendiente LOGRADA, no la pedida.** Cuando respetar el radio de
   giro obliga a alargar la rampa, el desnivel se reparte sobre más metros y queda más
   tendida: en el caso base se pidió 10 % y se logró 9.6 %. Es correcto —la pedida es un
   máximo, no un objetivo— pero si la pantalla muestra el valor del formulario en vez del
   valor del reporte, le está mintiendo al usuario. Va con advertencia que lo explica.
2. **`Parametros.trazar_rampa: bool = True` es nuevo.** En `False`, `disenar()` devuelve el
   diseño de bancos sin rampa. Es la primera etapa del flujo de ESPECIFICACION §8 y sirve
   para algo muy concreto: **la resta de los dos reportes es lo que cuesta la rampa**. Si
   te parece que merece una casilla en el formulario, es tuya la decisión.
3. **Hay dos advertencias nuevas** y las dos importan al usuario: hasta qué cota baja la
   rampa (en el caso base para en la 230, no en el fondo 220, porque más abajo el pit es
   demasiado angosto para el radio pedido), y si la pendiente quedó más tendida.

**Antes → después:** ninguna firma cambia. Lo que cambia es el VALOR de
`Rampa.pendiente` (antes era eco del parámetro porque no había rampa; ahora es medido) y
el signo típico de `sobre_esteril_m3`, que con rampa pasa a positivo — ver REQ-MOT-002.

**Rompe si no se hace:** el usuario ve «10 %» en una rampa que tiene 9.6 %, y no se entera
de que los dos bancos del fondo quedaron sin acceso de camión.

**Commit del motor:** el de MOT-4, esta sesión.

**Respuesta de la App** — _(la escribe el agente de PitForge)_
> **Fecha:** — · **Veredicto:** — · **Conectado en:** —

---

## COMPLETADOS

_(vacío)_
