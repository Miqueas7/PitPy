# Caso base — pit convencional pequeño

Aportado por el Ing. Yhonny Ruiz el 17-ago-2026. Es el **test de regresión** del
proyecto: el archivo 4 es un diseño hecho por un ingeniero y es contra él que se
compara toda salida del motor.

## Dónde están los archivos

```
C:\Users\mique\OneDrive\TRABAJOS\Yhonny Ruiz - Recmin\
```

No se versionan en el repo (10 MB). Los tests los buscan en la ruta del entorno
`PITPY_CASO_BASE` y se saltan si no está definida:

```bash
set PITPY_CASO_BASE=C:\Users\mique\OneDrive\TRABAJOS\Yhonny Ruiz - Recmin
```

## Parámetros declarados por Yhonny

| Parámetro | Valor |
|---|---|
| Ángulo de talud global | 45° (la carcaza también se optimizó con ese ángulo) |
| Altura de banco | 10 m |
| Ancho de berma | 6 m |
| Ancho de rampa | 12 m (tajo pequeño) |
| Pendiente de rampa | 10 % |
| Radio de giro | no parametrizable en RecMin; se acomoda la banqueta a mano |

## Lo que midió el parser

⚠️ **Los DXF de RecMin son mallas de `3DFACE`** (4 esquinas: códigos 10/20/30,
11/21/31, 12/22/32, 13/23/33). Las isolíneas sí son `POLYLINE`/`VERTEX`. Un
parser que asuma solo polilíneas devuelve datos sin sentido **sin lanzar error**.

| Archivo | 3DFACE | Extensión | Z | Área proyectada |
|---|---:|---|---|---:|
| 1 · Carcaza bruta | 20,876 | 640 × 750 m | 210.0 – 355.0 | 18.9 ha |
| 2 · Carcaza suavizada | 18,703 | 640 × 750 m | 210.0 – 352.5 | 19.0 ha |
| 3 · Isolíneas | 0 (21 polilíneas, 7,244 vértices) | 623 × 741 m | 219 – 349 | — |
| 4 · **Pit diseñado** | 5,923 | 656 × 762 m | 220.0 – 355.9 | **19.6 ha** |
| 5 · Topografía | 7,220 | 1,853 × 1,605 m | 313.2 – 366.5 | 295.4 ha |

### Distribución de ángulos de cara

| Archivo | Mediana | Interpretación |
|---|---|---|
| 1 · Bruta | 90.0° | 63 % verticales + 36 % planas → escalera de bloques. **Saltos de cota de 5 m: el modelo de bloques tiene bloques de 5 m** |
| 2 · Suavizada | **48.2°** | 68 % entre 45-50°, cero caras planas → el talud global de 45° declarado |
| 4 · Diseñado | 36.1° | **Bimodal: 46 % entre 65-70° y 45 % planas** → cara de banco + berma |
| 5 · Topografía | 2.7° | 93 % bajo 5° → terreno suave |

### Isolíneas y bancos

Archivo 3: 14 cotas exactas cada 10 m (219, 229, … 349).
Archivo 4: 13 cotas dominantes cada 10 m (230, 240, … 350).

Confirma la altura de banco de 10 m.

## La geometría cierra

Con banco de 10 m, cara de banco a 68° y berma de 6 m:

```
avance horizontal de la cara = 10 / tan(68°) = 4.04 m
4.04 + 6.00 = 10.04 m horizontales por cada 10 m verticales
talud global = atan(10 / 10.04) = 44.9° ≈ 45°   ✔
```

Yhonny declaró el global de 45° y la berma de 6 m, pero **no** la cara de banco.
Que el ángulo medido cierre exactamente confirma que el caso es coherente.

## El número que importa

El pit diseñado ocupa **19.6 ha** contra **19.0 ha** de la carcaza suavizada.

Esas **0.6 ha** son el costo geométrico de volver operativa la carcaza: bermas y
rampa empujan las paredes hacia afuera. Ese es exactamente el número que la
herramienta debe reportar en cada decisión, porque es lo que hoy no se puede
comparar entre diseños.

## Aserciones para los tests

```python
CASO_BASE = {
    "suavizada": {"caras": 18703, "talud_mediana": 48.2, "z_min": 210.0, "z_max": 352.5},
    "disenado":  {"caras": 5923,  "cotas": 13, "altura_banco": 10.0, "area_ha": 19.6},
    "isolineas": {"polilineas": 21, "vertices": 7244, "paso_cota": 10.0},
    "topografia": {"caras": 7220, "z_min": 313.2, "z_max": 366.5},
}
```
