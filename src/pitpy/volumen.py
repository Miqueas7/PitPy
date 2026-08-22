"""Volúmenes y sobre-estéril.

Implementado en MOT-2 (2026-08-21); el recorte con topografía cambia la referencia
de los volúmenes y eso está explicado en `calcular()` y en `topo.py`.

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

    El volumen se integra contra un TECHO: la cota por encima de la cual se
    considera que no había nada que remover. Sin topografía, el único techo
    posible es un plano imaginario a la altura de la cresta —como si el terreno
    original fuera plano justo ahí—, que es una aproximación gruesa pero es la
    única disponible. **Con topografía, el techo pasa a ser el terreno real**
    donde cubre (y la cresta donde no), y con eso **los dos volúmenes bajan**
    —también `volumen_carcaza_m3`, aunque la carcaza no se tocó—: lo que baja es
    la calidad de la aproximación, no la roca. Ver `topo.py`.
    """
    from .bancos import construir, superficie_antes_de_topo
    from .superficie import muestrear_en

    construccion = getattr(diseno, "construccion_", None)
    if construccion is None:
        construccion = construir(diseno.carcaza, diseno.parametros,
                                 diseno.parametros.talud_global
                                 or diseno.carcaza.talud_detectado())

    superficie = construccion.superficie
    celda = superficie.paso * superficie.paso
    cresta = construccion.cotas[-1] if construccion.cotas else construccion.fondo

    techo = np.full(superficie.z.shape, cresta)
    if construccion.topografia is not None:
        terreno = muestrear_en(construccion.topografia, superficie.origen,
                               superficie.paso, superficie.z.shape)
        cubre = ~np.isnan(terreno)
        techo[cubre] = terreno[cubre]

    z_carcaza = superficie.z
    hay_carcaza = ~np.isnan(z_carcaza)
    volumen_carcaza = float(np.sum(
        np.clip(techo[hay_carcaza] - z_carcaza[hay_carcaza], 0.0, None))) * celda

    z_antes_topo = superficie_antes_de_topo(construccion)
    if construccion.topografia is not None:
        from .topo import recortar
        z_diseno = recortar(z_antes_topo, superficie, construccion.topografia)
    else:
        z_diseno = z_antes_topo
    hay_diseno = ~np.isnan(z_diseno)
    volumen_diseno = float(np.sum(
        np.clip(techo[hay_diseno] - z_diseno[hay_diseno], 0.0, None))) * celda

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
        advertencias=_advertencias(diseno, construccion, z_antes_topo, z_diseno),
    )


def _advertencias(diseno: Diseno, construccion, z_antes_topo: np.ndarray,
                  z_diseno: np.ndarray) -> list[str]:
    """Lo que el usuario tiene que saber sin tener que mirar la geometría.

    Redactadas en el idioma del oficio: PitForge las muestra tal cual.
    """
    from .superficie import ancho_inscrito

    avisos = []
    parametros = diseno.parametros

    if diseno.rampa_ is not None and diseno.rampa_.eje:
        arranque = diseno.rampa_.eje[0][2]
        if arranque > construccion.fondo + 0.5:
            avisos.append(
                f"La rampa baja hasta la cota {arranque:.0f}, no hasta el fondo "
                f"({construccion.fondo:.0f}): más abajo el pit es demasiado angosto "
                f"para un radio de giro de {parametros.radio_giro:.0f} m. Los "
                f"últimos bancos quedan sin acceso directo de camión.")
        if diseno.rampa_.pendiente < parametros.rampa_pendiente - 0.002:
            avisos.append(
                f"La rampa quedó al {100 * diseno.rampa_.pendiente:.1f} %, más "
                f"tendida que el {100 * parametros.rampa_pendiente:.0f} % pedido: "
                f"respetar el radio de giro obligó a alargarla.")

    if diseno.rampa_ is None:
        avisos.append(
            "El diseño todavía no incluye rampa: el sobre-estéril informado es solo "
            "el costo de los bancos y las bermas.")

    if construccion.topografia is not None:
        from .topo import area_recortada_ha

        afectada = area_recortada_ha(z_antes_topo, z_diseno,
                                     construccion.superficie.paso)
        if afectada > 0:
            huella_ha = (float(np.count_nonzero(~np.isnan(z_antes_topo)))
                        * construccion.superficie.paso ** 2 / 1e4)
            avisos.append(
                f"El diseño se recortó contra la topografía en {afectada:.2f} ha "
                f"({100 * afectada / huella_ha:.1f} % de su huella): ahí el "
                f"diseño quedaba por encima del terreno real. Los volúmenes ya "
                f"reflejan el recorte; las líneas de cresta y pie exportadas al "
                f"DXF todavía no —son la geometría teórica de banco, no una "
                f"malla.")

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
