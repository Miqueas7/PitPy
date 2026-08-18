"""Detección del ángulo de talud desde la geometría de la carcaza.

MÉTODO VALIDADO (17-ago-2026) contra el caso base: la carcaza suavizada arroja
mediana 48.2 grados con el 68 % de las caras entre 45 y 50, que es el talud
global de 45 grados que declaró Yhonny. Ver docs/CASO_BASE.md.

Por qué importa: Yhonny preguntó si la app debía pedirle los ángulos otra vez o
si podía deducirlos de la carcaza. Se puede. La decisión de diseño es
auto-detectar Y MOSTRAR el valor, para que confirme o corrija — no decidir en
silencio ni obligarlo a tipear lo que el archivo ya sabe.
"""
from __future__ import annotations

import math

from .modelo import Malla, Punto, TaludDetectado


def angulo_cara(pts: list[Punto]) -> float | None:
    """Ángulo de la cara respecto a la horizontal, en grados.

    0 = horizontal (berma, fondo del pit).
    90 = vertical (pared de la escalera de bloques en la carcaza bruta).

    Devuelve None si la cara es degenerada (área cero).
    """
    (x1, y1, z1), (x2, y2, z2), (x3, y3, z3) = pts[0], pts[1], pts[2]
    ux, uy, uz = x2 - x1, y2 - y1, z2 - z1
    vx, vy, vz = x3 - x1, y3 - y1, z3 - z1
    nx = uy * vz - uz * vy
    ny = uz * vx - ux * vz
    nz = ux * vy - uy * vx
    norma = math.sqrt(nx * nx + ny * ny + nz * nz)
    if norma == 0:
        return None
    return math.degrees(math.acos(min(1.0, abs(nz) / norma)))


def azimut_cara(pts: list[Punto]) -> float | None:
    """Azimut de máxima pendiente de la cara, en grados desde el norte (0-360).

    Necesario para la roseta de taludes por sector (v2). Ver ESPECIFICACION 3.2.
    """
    (x1, y1, z1), (x2, y2, z2), (x3, y3, z3) = pts[0], pts[1], pts[2]
    ux, uy, uz = x2 - x1, y2 - y1, z2 - z1
    vx, vy, vz = x3 - x1, y3 - y1, z3 - z1
    nx = uy * vz - uz * vy
    ny = uz * vx - ux * vz
    if nx == 0 and ny == 0:
        return None
    return math.degrees(math.atan2(nx, ny)) % 360


def detectar_talud(carcaza: Malla, ignorar_planas: bool = True) -> TaludDetectado:
    """Deduce el talud global de la carcaza.

    Args:
        carcaza: la malla leída del DXF.
        ignorar_planas: descarta las caras bajo 5 grados (fondo del pit y techos
            de la carcaza en bruto). Sin esto la mediana se hunde: en la carcaza
            bruta del caso base el 36 % de las caras son planas.

    Returns:
        TaludDetectado con mediana, percentiles y si el talud parece variable.

    Raises:
        GeometriaInvalida: si no hay ninguna cara inclinada.
    """
    angs = [a for a in (angulo_cara(c) for c in carcaza.caras) if a is not None]
    if ignorar_planas:
        angs = [a for a in angs if a >= 5.0]
    if not angs:
        from . import GeometriaInvalida
        raise GeometriaInvalida(
            "la carcaza no tiene caras inclinadas. Puede ser una superficie plana, "
            "o un archivo de isolíneas (que no trae caras: usa la carcaza suavizada)."
        )
    angs.sort()
    n = len(angs)

    def pct(p: float) -> float:
        return angs[min(n - 1, int(n * p))]

    mediana, p10, p90 = pct(0.50), pct(0.10), pct(0.90)
    p25, p75 = pct(0.25), pct(0.75)

    # Criterio de variabilidad: RANGO INTERCUARTIL, no p10-p90.
    #
    # Medido en el caso base (carcaza de talud ÚNICO declarado en 45 grados):
    #     p10 26.6 | p25 45.0 | p50 48.2 | p75 48.2 | p90 56.3
    #     IQR = 3.2 grados,  pero  p90-p10 = 29.7 grados
    #
    # Las colas están contaminadas por artefactos de triangulación: al partir en
    # dos triángulos un cuadrilátero del talud, uno queda más tendido que el
    # otro. Son 3,865 caras entre 25 y 35 grados repartidas por toda la carcaza
    # (no concentradas en el fondo), o sea ruido de malla, no geometría real.
    #
    # El IQR las ignora. Umbral de 8 grados: bien por encima de los 3.2 medidos
    # en un talud único, y bien por debajo de la diferencia que tendría una
    # roseta real (donde los sectores difieren en 10 grados o más).
    es_variable = (p75 - p25) > 8.0

    return TaludDetectado(
        mediana=round(mediana, 1),
        p10=round(p10, 1),
        p90=round(p90, 1),
        es_variable=es_variable,
        por_sector={},   # v2: segmentar por azimut y por rango de cota
    )


def talud_global_desde_banco(altura_banco: float, cara_banco: float,
                             ancho_berma: float) -> float:
    """Talud global que resulta de una configuración banco/berma, en grados.

    VERIFICADO con el caso base:
        banco 10 m, cara 68 grados, berma 6 m  ->  44.9 grados ~ los 45 declarados.
    """
    avance = altura_banco / math.tan(math.radians(cara_banco))
    return math.degrees(math.atan(altura_banco / (avance + ancho_berma)))


def cara_banco_desde_global(altura_banco: float, talud_global: float,
                            ancho_berma: float) -> float:
    """Inverso del anterior: qué cara de banco hace falta para un talud global dado.

    Es lo que necesita el módulo `bancos` para construir la geometría a partir de
    lo que pide el usuario.

    Raises:
        GeometriaInvalida: si la berma sola ya excede el avance permitido. El
            mensaje dice qué parámetro relajar, porque es un error que el usuario
            va a ver seguido al probar combinaciones.
    """
    avance_total = altura_banco / math.tan(math.radians(talud_global))
    avance_cara = avance_total - ancho_berma
    if avance_cara <= 0:
        from . import GeometriaInvalida
        raise GeometriaInvalida(
            f"con banco de {altura_banco} m y berma de {ancho_berma} m no se puede "
            f"alcanzar un talud global de {talud_global} grados: la berma sola ya "
            f"consume todo el avance. Reduce la berma o baja el ángulo global."
        )
    return math.degrees(math.atan(altura_banco / avance_cara))
