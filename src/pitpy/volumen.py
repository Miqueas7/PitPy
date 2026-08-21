"""Volúmenes y sobre-estéril.

PENDIENTE DE IMPLEMENTAR.

POR QUÉ ESTE MÓDULO EXISTE APARTE
---------------------------------
Podría vivir dentro de Diseno, pero está separado a propósito. La idea que
Yhonny describió en su segundo mensaje (ESPECIFICACION 8) es un flujo donde el
usuario mueve la rampa y ve EN TIEMPO REAL cuánto volumen agrega:

    "el algoritmo con esa guía de rampa entienda y desplace las paredes
     dinámicamente y me vaya informando en tiempo real cuánto volumen está
     aumentando el Pit... y en el proceso uno se detenga y diga: esto quiero."

Eso exige recálculo incremental. Si el cálculo vive dentro de un botón de la
interfaz, esa función no se puede construir nunca. Por eso vive acá.

EL NÚMERO QUE IMPORTA
---------------------
Del caso base: el pit DISEÑADO ocupa 19.6 ha contra 19.0 ha de la carcaza
suavizada. Esas 0.6 ha son el costo geométrico de volver operativa la carcaza —
bermas y rampa empujan las paredes hacia afuera.

Ese es exactamente el número que hoy NO se puede comparar entre diseños, y es la
razón de ser de la herramienta. Reportarlo bien vale más que cualquier otra
métrica.
"""
from __future__ import annotations

import numpy as np

from .modelo import Diseno, Reporte


def calcular(diseno: Diseno) -> Reporte:
    """Volúmenes del diseño y sobre-estéril respecto de la carcaza.

    El volumen se mide **desde el plano de la cresta hacia abajo**: es la única
    referencia que el motor tiene mientras no exista el recorte con topografía
    (MOT-5). Con topografía, la referencia pasa a ser el terreno y los dos números
    cambian de magnitud —no de significado—, porque lo que importa es la RESTA.
    """
    from .bancos import construir, superficie_disenada

    construccion = getattr(diseno, "construccion_", None)
    if construccion is None:
        construccion = construir(diseno.carcaza, diseno.parametros,
                                 diseno.parametros.talud_global
                                 or diseno.carcaza.talud_detectado())

    superficie = construccion.superficie
    celda = superficie.paso * superficie.paso
    cresta = construccion.cotas[-1] if construccion.cotas else construccion.fondo

    z_carcaza = superficie.z
    bajo_la_cresta = ~np.isnan(z_carcaza) & (z_carcaza <= cresta)
    volumen_carcaza = float(np.sum(cresta - z_carcaza[bajo_la_cresta])) * celda

    z_diseno = superficie_disenada(construccion)
    hay_diseno = ~np.isnan(z_diseno)
    volumen_diseno = float(np.sum(cresta - z_diseno[hay_diseno])) * celda

    area_carcaza = area_proyectada_ha(diseno.carcaza.caras)
    area_diseno = float(np.count_nonzero(hay_diseno)) * celda / 1e4

    return Reporte(
        area_carcaza_ha=round(area_carcaza, 3),
        area_diseno_ha=round(area_diseno, 3),
        sobre_area_ha=round(area_diseno - area_carcaza, 3),
        volumen_carcaza_m3=round(volumen_carcaza, 1),
        volumen_diseno_m3=round(volumen_diseno, 1),
        sobre_esteril_m3=round(volumen_diseno - volumen_carcaza, 1),
        bancos=len(construccion.cotas),
        cota_fondo=construccion.fondo,
        cota_cresta=cresta,
        longitud_rampa_m=diseno.rampa_.longitud if diseno.rampa_ else 0.0,
        advertencias=_advertencias(diseno, construccion),
    )


def _advertencias(diseno: Diseno, construccion) -> list[str]:
    """Lo que el usuario tiene que saber sin tener que mirar la geometría.

    Redactadas en el idioma del oficio: PitForge las muestra tal cual.
    """
    from .superficie import ancho_inscrito

    avisos = []
    parametros = diseno.parametros

    if diseno.rampa_ is None:
        avisos.append(
            "El diseño todavía no incluye rampa: el sobre-estéril informado es solo "
            "el costo de los bancos y las bermas.")

    minimo = parametros.ancho_fondo_minimo
    if minimo is not None:
        piso = construccion.superficie.seccion(construccion.fondo)
        ancho = ancho_inscrito(piso, construccion.superficie.paso)
        if ancho < minimo:
            avisos.append(
                f"El fondo quedó en {ancho:.0f} m de ancho, por debajo del mínimo "
                f"de {minimo:.0f} m que pediste, a la cota {construccion.fondo:.0f}. "
                f"No se ensanchó: ensanchar el fondo desplaza las paredes finales y "
                f"arrastra estéril adicional.")
            if parametros.forzar_ancho_fondo:
                avisos.append(
                    "Pediste forzar el ancho mínimo de fondo, pero el motor todavía "
                    "no lo hace: el fondo quedó como salió de la carcaza.")
    return avisos


def area_proyectada_ha(caras: list) -> float:
    """Área proyectada en planta de una malla, en hectáreas.

    Fórmula del zapato (shoelace) por cara. Validado contra el caso base:
    carcaza suavizada = 19.0 ha, pit diseñado = 19.6 ha.
    """
    total = 0.0
    for cara in caras:
        area = 0.0
        for (x1, y1, _), (x2, y2, _) in zip(cara, cara[1:] + cara[:1]):
            area += x1 * y2 - x2 * y1
        total += abs(area) / 2.0
    return total / 1e4
