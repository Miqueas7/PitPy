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

from .modelo import Diseno, Reporte


def calcular(diseno: Diseno) -> Reporte:
    """Volúmenes del diseño y sobre-estéril respecto de la carcaza."""
    raise NotImplementedError("Ver el docstring del módulo.")


def area_proyectada_ha(caras: list) -> float:
    """Área proyectada en planta de una malla, en hectáreas.

    Fórmula del zapato (shoelace) por cara. Validado contra el caso base:
    carcaza suavizada = 19.0 ha, pit diseñado = 19.6 ha.
    """
    raise NotImplementedError
