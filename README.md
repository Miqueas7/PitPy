# PitPy

**Motor open source que convierte una carcaza de pit optimizado en un diseño
geométrico operativo**: bancos, bermas y rampa.

```
carcaza optimizada  ──▶  PitPy  ──▶  pit operativo (DXF)
   (mesh / isolíneas)              + reporte de volúmenes
```

## El problema

Optimizar un pit ya está resuelto y es rápido. El cuello de botella viene
después: convertir esa carcaza en un diseño con bancos, bermas y rampas reales
toma horas de trabajo manual banco a banco. Tanto, que en la práctica solo se
alcanza a evaluar **uno o dos diseños** cuando deberían compararse muchos.

PitPy automatiza ese paso. No para ahorrar un rato: para que se puedan probar
diez alternativas en vez de una.

## Estado

🚧 **En construcción.** El lector de DXF funciona y está validado contra un caso
real. El resto del motor está especificado y pendiente de implementar.

| Módulo | Estado |
|---|---|
| `dxf` — lectura de mallas 3DFACE y polilíneas | ✅ funciona |
| `taludes` — detección de ángulos desde la carcaza | 🚧 método probado, falta empaquetar |
| `bancos` — generación de banco + berma | ⬜ especificado |
| `rampa` — trazado con radio de giro | ⬜ especificado |
| `topo` — recorte contra topografía | ⬜ especificado |

## Instalación

```bash
pip install -e ".[dev]"
```

## Uso previsto

```python
from pitpy import Carcaza, Parametros, disenar

carcaza = Carcaza.desde_dxf("suavizada.dxf")
print(carcaza.talud_detectado())        # 48.2°

diseno = disenar(carcaza, Parametros(
    altura_banco=10.0,
    ancho_berma=6.0,
    talud_global=45.0,
    rampa_ancho=12.0,
    rampa_pendiente=0.10,
    radio_giro=25.0,
))
print(diseno.reporte())                 # volúmenes y sobre-estéril
diseno.a_dxf("pit_operativo.dxf")
```

## Documentación

> **¿Recién llegas al proyecto?** Empieza por
> **[docs/EMPEZAR_AQUI.md](docs/EMPEZAR_AQUI.md)**.

| Documento | Qué contiene |
|---|---|
| [docs/EMPEZAR_AQUI.md](docs/EMPEZAR_AQUI.md) | **Arranque**: contexto, entorno, trampas conocidas |
| [docs/ROADMAP.md](docs/ROADMAP.md) | Qué hacer, en qué orden, y cómo saber que está bien |
| [docs/ESPECIFICACION.md](docs/ESPECIFICACION.md) | Los requisitos, en palabras del usuario experto |
| [docs/CASO_BASE.md](docs/CASO_BASE.md) | El caso real medido, con sus números |
| [docs/ARQUITECTURA.md](docs/ARQUITECTURA.md) | Cómo está pensado el motor y por qué |
| [docs/API_CONTRACTS.md](docs/API_CONTRACTS.md) | Lo que PitForge consume — **fuente de verdad** |
| [docs/CHANGELOG.md](docs/CHANGELOG.md) | Bitácora de sesiones |

## Créditos

Especificación funcional: **Ing. Yhonny Ruiz** (instructor oficial de RecMin),
que aportó el caso base y el criterio de diseño.

## Licencia

MIT. Ver [LICENSE](LICENSE).
