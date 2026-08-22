# Contrato público de PitPy

> **Fuente de verdad.** PitForge programa contra este documento.
> Cambiarlo sin avisar rompe la app. Todo cambio se anota en `CHANGELOG.md`.

## Versión

`0.1.0-dev` — nada de esto es estable todavía.

## Tipos

```python
@dataclass(frozen=True)
class Parametros:
    altura_banco: float          # m
    ancho_berma: float           # m
    talud_global: float          # grados; None => se auto-detecta
    rampa_ancho: float           # m
    rampa_pendiente: float       # fracción: 0.10 = 10 %
    radio_giro: float            # m, mínimo
    ancho_fondo_minimo: float | None = None   # None => sin restricción
    forzar_ancho_fondo: bool = False          # ver ESPECIFICACION §7
    bancos_sobre_topografia: int = 2

@dataclass
class TaludDetectado:
    mediana: float               # grados
    p10: float
    p90: float
    es_variable: bool            # True si la dispersión sugiere roseta
    por_sector: dict             # azimut -> grados   (v2, vacío en v1)

@dataclass
class Reporte:
    area_carcaza_ha: float
    area_diseno_ha: float
    sobre_area_ha: float         # el costo de volverla operativa
    volumen_carcaza_m3: float
    volumen_diseno_m3: float
    sobre_esteril_m3: float
    bancos: int
    cota_fondo: float
    cota_cresta: float
    longitud_rampa_m: float
    advertencias: list[str]      # p.ej. "el fondo quedó bajo el ancho mínimo"
```

## Funciones

```python
def leer_carcaza(ruta: str) -> Carcaza: ...
def leer_topografia(ruta: str) -> Malla: ...

class Carcaza:
    def silueta(self, paso: float = 10.0) -> list[Punto]: ...   # REQ-APP-001

# rampa.py
def cabe(carcaza: Carcaza, parametros: Parametros,
         talud_global: float | None = None) -> tuple[bool, str]: ...   # REQ-APP-002

def detectar_talud(carcaza: Carcaza) -> TaludDetectado: ...

def disenar(carcaza: Carcaza,
            parametros: Parametros,
            topografia: Malla | None = None,
            progreso: Callable[[str, float], None] | None = None) -> Diseno: ...

class Diseno:
    def reporte(self) -> Reporte: ...
    def a_dxf(self, ruta: str) -> None: ...
    def bancos(self) -> list[Banco]: ...
    def rampa(self) -> Rampa | None: ...
```

## Estado de implementación — 2026-08-21

El contrato describe la v1 completa; el motor todavía no llegó a toda. Lo que la App
puede usar hoy contra el motor de verdad, y lo que necesita doble de prueba:

| Función | Estado |
|---|---|
| `leer_carcaza`, `leer_topografia`, `leer_malla` | ✅ funciona |
| `detectar_talud` | ✅ funciona |
| `Carcaza.silueta` | ✅ funciona (nuevo, 2026-08-21 — REQ-APP-001) |
| `rampa.cabe` | ✅ funciona (nuevo, 2026-08-21 — REQ-APP-002). El `str` viene siempre |
| `disenar` | 🔨 **parcial**: bancos, rampa y volúmenes. No recorta topografía |
| `Diseno.bancos()` | ✅ devuelve los bancos con su cresta y su pie |
| `Diseno.rampa()` | ✅ funciona (2026-08-21). `Rampa.pendiente` es la **lograda**, no la pedida |
| `disenar(..., topografia=...)` | ✅ funciona (2026-08-21). Recorta volúmenes y reporte; NO recorta las líneas del DXF |
| `Diseno.reporte()` | ✅ funciona (2026-08-21). Sin rampa todavía: ver la nota del sobre-estéril |
| `Diseno.a_dxf()` | 🔨 **parcial** (2026-08-21): escribe las líneas `CRESTA` y `PIE`. Las capas de superficie `BERMA` y `TALUD` todavía no |

### Con topografía, `volumen_carcaza_m3` también cambia — no es un bug

Sin `topografia`, los volúmenes se miden contra un plano imaginario a la altura de
la cresta (como si el terreno original fuera plano ahí). **Con topografía real la
referencia pasa a ser el terreno**, y eso hace bajar tanto `volumen_diseno_m3`
como `volumen_carcaza_m3` — la carcaza no se tocó; lo que bajó fue la imprecisión
de la aproximación anterior. En el caso base: 11.27 M → 9.93 M m³.
`sobre_esteril_m3` sigue siendo la resta de los dos, ahora más precisa.

`Reporte.advertencias` trae cuánta huella se recortó (en ha y en % de la huella)
cuando el recorte hizo algo. **Las líneas `CRESTA`/`PIE` del DXF no se recortan**:
siguen siendo la geometría teórica de cada banco a su cota fija.

### `Parametros.trazar_rampa: bool = True`

Campo nuevo (2026-08-21). En `False`, `disenar()` devuelve el diseño de bancos sin
rampa. Es la primera etapa del flujo que describe ESPECIFICACION §8 —suavizar la
carcaza sin rampa y recién después decidir por dónde sube— y sirve para comparar
cuánto cuesta la rampa: es la resta de los dos reportes.

### El sobre-estéril puede venir NEGATIVO, y no es un error

`sobre_esteril_m3` es `volumen_diseno - volumen_carcaza`. Mientras no exista la rampa
(MOT-4) ese número es **negativo**: un diseño de bancos queda por encima de la carcaza
—en la berma de la cota z el piso es z mientras la carcaza sube desde z-6 hasta z—, así
que se **pierden bloques** en vez de agregarse estéril. En el caso base da −618,000 m³.

**Con rampa el número es positivo** (caso base: +364,710 m³) y **sin rampa es negativo**
(−618,000 m³), y las dos cosas son ciertas: los bancos solos dejan bloques sin minar, y la
rampa empuja las paredes. Como `trazar_rampa` es del usuario, **la App no puede asumir el
signo**: hay que mostrarlo como viene, y mostrar también `advertencias`. Ver REQ-MOT-002.

Mientras `topo` no exista, el volumen se mide **desde el plano de la cresta hacia abajo**.
Con topografía la referencia pasa a ser el terreno: los dos volúmenes cambian de
magnitud, no de significado, porque lo que importa es la resta.

**Desde el 2026-08-21 el motor trae un núcleo compilado en C++** (`pitpy._nucleo`).
La API no cambia en nada — ninguna firma, ningún tipo de retorno—; lo que cambia es
el empaquetado: hay una rueda por plataforma en vez de una universal. Ver REQ-MOT-001.

Etapas de `progreso()` que se emiten hoy: `"detectando talud"`, `"generando
bancos"`, `"trazando rampa"` y `"recortando topografía"` — las cuatro se emiten
siempre, aunque no haya trabajo que hacer (sin rampa o sin topografía), con la
fracción llegando a 1.0 igual. Falta `"calculando volúmenes"`: ese trabajo sucede
dentro de `Diseno.reporte()`, que todavía no recibe callback de progreso.

## Errores

```python
class PitPyError(Exception): ...
class DXFIlegible(PitPyError): ...          # el archivo no se pudo interpretar
class GeometriaInvalida(PitPyError): ...    # la carcaza no forma un pit cerrado
class RampaImposible(PitPyError): ...       # no cabe con esos parámetros
```

`RampaImposible` debe traer en el mensaje **qué parámetro relajar** — es el error
que más va a ver el usuario.

## Contrato de progreso

`disenar()` acepta un callback `progreso(etapa: str, fraccion: float)`. PitForge
lo usa para la barra de avance. Etapas previstas:

`"leyendo"` → `"detectando talud"` → `"generando bancos"` → `"trazando rampa"` →
`"recortando topografía"` → `"calculando volúmenes"`

## Pendientes de contrato

- [ ] Cómo se entregan los taludes por roseta (v2)
- [ ] Firma de la API incremental para el volumen en tiempo real (ESPECIFICACION §8)
