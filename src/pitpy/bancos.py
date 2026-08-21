"""Generación de bancos y bermas a partir de la carcaza.

PENDIENTE DE IMPLEMENTAR. Es el corazón del motor.

QUÉ TIENE QUE HACER
-------------------
Dada una carcaza (superficie continua al talud global) y los parámetros,
producir la secuencia de bancos: para cada cota, la línea de CRESTA y la de PIE,
separadas por la berma.

    cota 350  ─── cresta ─────╮
                              │ cara de banco (ver taludes.cara_banco_desde_global)
    cota 340  ─── pie ────────╯
              ─── berma ───────────  (ancho_berma, horizontal)
              ─── cresta ──────────╮
    cota 330  ─── pie ─────────────╯

GEOMETRÍA VERIFICADA (docs/CASO_BASE.md)
    banco 10 m + cara 68 grados + berma 6 m = talud global 44.9 grados
    avance de la cara = altura / tan(cara) = 4.04 m
    avance total por banco = 4.04 + 6.00 = 10.04 m

La cara de banco NO se pide al usuario: se deriva del talud global y la berma
con taludes.cara_banco_desde_global(). Yhonny piensa en talud global, no en cara
de banco — pedirle la cara sería trasladarle una cuenta que la herramienta debe
hacer sola.

ANCHO MÍNIMO DE FONDO — leer ESPECIFICACION 7 antes de tocar esto
------------------------------------------------------------------
Criterio explícito de Yhonny: prefiere PERDER BLOQUES antes que ensanchar
artificialmente el pit. Forzar el ancho desplaza las paredes finales y arrastra
estéril adicional.

Por lo tanto:
  · `ancho_fondo_minimo=None`  -> sin restricción (por omisión)
  · `forzar_ancho_fondo=False` -> se AVISA en Reporte.advertencias, no se corrige
  · `forzar_ancho_fondo=True`  -> se ensancha, y se reporta cuánto estéril costó

Nunca ensanchar en silencio.

CÓMO VALIDAR
------------
Comparar contra `4_Pit Geometric Diseñado.dxf`: debe dar 13 bancos cada 10 m
entre las cotas 230 y 350, con distribución de ángulos bimodal (caras de banco
alrededor de 65-70 grados y bermas bajo 5).
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from .modelo import Banco, Carcaza, Parametros
from .superficie import Superficie, cabe_circulo, distancia_hasta
from .taludes import cara_banco_desde_global


@dataclass
class Construccion:
    """Todo lo que sale de recorrer la carcaza banco por banco.

    Se separa de `generar()` porque `volumen` y, más adelante, la escritura de DXF
    y el recorte con topografía necesitan la misma grilla. Reconstruirla en cada
    módulo sería recalcular la carcaza entera tres veces.
    """
    superficie: Superficie
    cotas: list[float]
    fondo: float
    altura: float
    avance_cara: float
    avance_total: float
    cara: float


def construir(carcaza: Carcaza, parametros: Parametros, talud_global: float,
              paso: float | None = None) -> Construccion:
    """Prepara la grilla y decide las cotas. No extrae ninguna línea todavía."""
    altura = parametros.altura_banco
    berma = parametros.ancho_berma
    cara = cara_banco_desde_global(altura, talud_global, berma)
    avance_cara = altura / math.tan(math.radians(cara))
    avance_total = altura / math.tan(math.radians(talud_global))
    if paso is None:
        ancho, largo = carcaza.extension()
        paso = paso_por_omision(avance_cara, berma, max(ancho, largo))

    superficie = Superficie.desde_malla(carcaza, paso)
    z_min, z_max = superficie.rango_z()
    cresta = math.floor(z_max / altura) * altura

    fondo = _cota_de_fondo(superficie, cresta, altura, avance_total, z_min, paso)
    if fondo is None or fondo >= cresta:
        from . import GeometriaInvalida
        raise GeometriaInvalida(
            f"la carcaza no da para un solo banco de {altura} m: entre la cota "
            f"{z_min:.1f} y la {z_max:.1f} no hay ningún nivel donde quepa un piso "
            f"de {avance_total:.1f} m de ancho. Revisa que sea una carcaza de pit "
            f"y no una superficie suelta, o baja la altura de banco."
        )

    return Construccion(
        superficie=superficie,
        cotas=cotas_de_banco(fondo + altura, cresta, altura),
        fondo=fondo, altura=altura, avance_cara=avance_cara,
        avance_total=avance_total, cara=cara,
    )


def generar(carcaza: Carcaza, parametros: Parametros,
            talud_global: float, paso: float | None = None) -> list[Banco]:
    """Construye los bancos desde la cota de fondo hasta la cresta.

    Args:
        carcaza: la carcaza optimizada, ya leída.
        parametros: altura de banco, ancho de berma, ancho de fondo...
        talud_global: en grados. Viene de taludes.detectar_talud() o del usuario.
        paso: tamaño de celda de la grilla, en metros. Por omisión, un cuarto del
            rasgo más angosto del diseño (ver ARQUITECTURA, decisión 6).

    Returns:
        Lista de Banco ordenada de la cota más baja a la más alta. La cota de
        cada banco es la de su CRESTA; el pie está una altura de banco más abajo.
    """
    return lineas(construir(carcaza, parametros, talud_global, paso))


def lineas(c: Construccion) -> list[Banco]:
    """Extrae la cresta y el pie de cada banco de una construcción ya hecha."""
    bancos = []
    for cota in c.cotas:
        z_pie = cota - c.altura
        seccion = c.superficie.seccion(z_pie)
        anillos_pie = c.superficie.contorno(z_pie)
        # La cresta es el pie corrido hacia afuera el avance de la cara: el ángulo
        # de cara es dato geotécnico, la berma es la que absorbe la diferencia.
        campo = distancia_hasta(seccion, c.superficie.paso, c.avance_cara * 1.25)
        anillos_cresta = c.superficie.contorno_de(campo, c.avance_cara, cota)
        bancos.append(Banco(
            cota=cota,
            pie=anillos_pie[0] if anillos_pie else [],
            cresta=anillos_cresta[0] if anillos_cresta else [],
        ))
    return bancos


def superficie_disenada(c: Construccion) -> np.ndarray:
    """La cota del DISEÑO en cada celda: el tazón escalonado que reemplaza la carcaza.

    Se arma de abajo hacia arriba y cada celda se escribe una sola vez, la primera:

        piso del pit          -> la cota de fondo
        cara de banco         -> interpola entre el pie y la cresta según la distancia
        berma                 -> la cota del banco, plana

    NaN donde el diseño no llega. Es lo que `volumen` integra y lo que `topo` va a
    recortar; también es de donde sale la superficie a escribir en el DXF.
    """
    z = np.full(c.superficie.z.shape, np.nan)
    piso = c.superficie.seccion(c.fondo)
    z[piso] = c.fondo

    for cota in c.cotas:
        pie = c.superficie.seccion(cota - c.altura)
        d = distancia_hasta(pie, c.superficie.paso, c.avance_cara * 1.25)
        cara = np.isnan(z) & (d <= c.avance_cara)
        z[cara] = (cota - c.altura) + c.altura * (d[cara] / c.avance_cara)
        berma = np.isnan(z) & c.superficie.seccion(cota)
        z[berma] = cota
    return z


CELDAS_POR_LADO = 2000
"""Tope de resolución de la grilla.

No sale de la geometría sino del reloj: es la red para que un rasgo diminuto —una
berma que casi consume el avance de cara— no dispare la grilla a decenas de
millones de celdas.

Estaba en 1000 mientras el rasterizado corría en Python. Con el núcleo C++ el
mismo trabajo cuesta dos órdenes de magnitud menos y el tope se pudo subir, que
hacía falta: **a 1000 celdas por lado un pit de 4 km quedaba con celdas de 4 m, y
una berma de 6 m no se resuelve con celda y media**. A 2000 el paso es 2 m —tres
celdas por berma— y ese pit, con 58 bancos, se diseña en 17.8 s medidos.
"""


def paso_por_omision(avance_cara: float, ancho_berma: float,
                     extension: float) -> float:
    """Tamaño de celda: cuatro celdas a lo ancho del rasgo más angosto.

    Con el tope de CELDAS_POR_LADO, porque el rasgo más angosto puede ser
    diminuto: banco de 7 m con berma de 6 m deja un avance de cara de 1 m, y sin
    tope la grilla de un pit chico se va a nueve millones de celdas.
    """
    ideal = min(avance_cara, ancho_berma) / 4.0
    return max(ideal, extension / CELDAS_POR_LADO)


def _cota_de_fondo(superficie: Superficie, cresta: float, altura: float,
                   avance_total: float, z_min: float, paso: float) -> float | None:
    """El nivel más bajo donde la carcaza todavía tiene piso, no punta de tazón.

    Baja de a un banco desde la cresta mientras la sección admita un círculo del
    ancho de un banco completo. Ver ARQUITECTURA, decisión 8: no es ensanchar el
    fondo (eso lo prohíbe ESPECIFICACION 7), es no inventar un banco donde la
    carcaza no da.
    """
    fondo = None
    cota = cresta
    while cota > z_min - altura:
        seccion = superficie.seccion(cota)
        if not seccion.any() or not cabe_circulo(seccion, avance_total, paso):
            break
        fondo = cota
        cota -= altura
    return fondo


def cotas_de_banco(z_fondo: float, z_cresta: float, altura: float) -> list[float]:
    """Cotas de banco entre el fondo y la cresta, de a `altura`.

    `z_fondo` es la cota del banco más bajo (la berma que se apoya sobre el piso
    del pit), no la del piso. Separado para poder testearlo sin geometría. En el
    caso base:
        cotas_de_banco(230, 350, 10) -> 13 cotas
    """
    if altura <= 0:
        raise ValueError("la altura de banco debe ser positiva")
    n = int(math.floor((z_cresta - z_fondo) / altura + 1e-9)) + 1
    return [z_fondo + k * altura for k in range(max(0, n))]
