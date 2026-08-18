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

## Lo que NO se decidió todavía

- **Representación interna de la superficie**: ¿malla de triángulos, grilla
  regular, o curvas de nivel? Afecta a `bancos` y a `topo`. Decidir con el caso
  base en la mano, no antes.
- **Algoritmo de trazado de rampa**: helicoidal simple contra búsqueda con
  restricción de radio. Empezar por lo simple y medir contra el archivo 4.
- **Cómo se suavizan las isolíneas** si se acepta ese formato de entrada.
