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
