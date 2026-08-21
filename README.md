# PitPy

[![Tests](https://img.shields.io/github/actions/workflow/status/Miqueas7/PitPy/tests.yml?branch=master&label=tests)](https://github.com/Miqueas7/PitPy/actions/workflows/tests.yml)
[![Python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-blue)](https://github.com/Miqueas7/PitPy)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](https://github.com/Miqueas7/PitPy/blob/master/LICENSE)

**Motor open source que convierte una carcaza de pit optimizado en un diseño
geométrico operativo**: bancos, bermas y rampa. Con núcleo de cálculo en C++20.

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

🚧 **En construcción, todavía sin publicar en PyPI.** El motor ya convierte una
carcaza real en bancos con berma; falta la rampa, el recorte con topografía y el
reporte de volúmenes.

| Módulo | Estado |
|---|---|
| `dxf` — lectura de mallas 3DFACE y polilíneas | ✅ funciona |
| `taludes` — detección de ángulos desde la carcaza | ✅ funciona |
| `superficie` — la carcaza como grilla regular, contornos | ✅ funciona |
| `_nucleo` — kernels de grilla en C++20 (nanobind) | ✅ funciona |
| `bancos` — generación de banco + berma | ✅ funciona |
| `volumen` — áreas, volúmenes y sobre-estéril | ✅ funciona |
| `dxf` — escritura por capas | 🔨 líneas sí, malla de superficie no |
| `rampa` — trazado con radio de giro | ⬜ especificado |
| `topo` — recorte contra topografía | ⬜ especificado |

Contra el caso base —una carcaza de 18,703 caras y el diseño que el mismo
ingeniero hizo a mano— el motor genera los 13 bancos cada 10 m entre las cotas
230 y 350, con los pies a **2.83 m de mediana** de las líneas dibujadas a mano,
en **0.86 s**. Un pit de 4 km con 58 bancos, a celdas de 2 m, tarda 18 s.

### Rendimiento

Los tres kernels que trabajan sobre la grilla —rasterizar la malla, distancia
euclídea y marching squares— están en C++20 con [nanobind](https://github.com/wjakob/nanobind).
Todo lo demás es Python: la geometría de minas se lee y se discute, no se esconde.

| | Python | con núcleo C++ |
|---|---:|---:|
| Rasterizar la carcaza del caso base | 0.76 s | 0.003 s |
| Rasterizar un pit de 4 km a paso 2 m | 275 s | 0.88 s |
| `disenar()` sobre el caso base | 4.59 s | **0.86 s** |

Cada kernel conserva su implementación de referencia en Python y la suite exige
que las dos den el mismo resultado celda por celda. Es lo que hace verificable la
afirmación de arriba.

## Instalación

Todavía no está en PyPI. Mientras tanto, desde el repositorio:

```bash
git clone https://github.com/Miqueas7/PitPy
cd PitPy
python -m venv .venv
.venv/Scripts/python -m pip install -e ".[dev]"    # Linux/macOS: .venv/bin/python
```

Compilar desde el repositorio necesita un compilador de C++20 (MSVC, gcc o
clang) y CMake. Cuando el paquete esté en PyPI, las ruedas ya vienen compiladas y
no hace falta nada de eso.

Cuando se publique:

```bash
pip install pitpy
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

Lo que ya corre hoy de ese ejemplo es todo menos las dos últimas líneas: los
bancos salen con su cresta y su pie, el reporte y la escritura del DXF todavía
levantan `NotImplementedError`. El estado función por función está en
[docs/API_CONTRACTS.md](docs/API_CONTRACTS.md).

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
| [CHANGELOG.md](CHANGELOG.md) | Registro público de versiones |
| [docs/CHANGELOG.md](docs/CHANGELOG.md) | Bitácora de sesiones, con las decisiones y su porqué |

## Créditos

Especificación funcional: **Ing. Yhonny Ruiz** (instructor oficial de RecMin),
que aportó el caso base y el criterio de diseño.

## Licencia

MIT. Ver [LICENSE](LICENSE).
