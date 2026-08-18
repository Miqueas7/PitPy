"""Recorte del diseño contra la topografía.

PENDIENTE DE IMPLEMENTAR.

DOS NIVELES, y Yhonny mismo los ordenó
--------------------------------------
SUFICIENTE (v1): diseñar el pit uno o dos bancos POR ENCIMA de la cota máxima de
la topografía y dejar que el usuario lo recorte después con un booleano en
cualquier software minero. Es lo que hoy hace a mano.
    -> parametros.bancos_sobre_topografia (por omisión 2)

MUCHO MEJOR (objetivo real): entregar el diseño ya limitado por la topografía.
Textual: "si la aplicación pudiera entregar directamente el diseño limitado por
la topografía, sería muchísimo mejor."

Implementar primero el nivel suficiente, que desbloquea todo lo demás, y después
el recorte. No al revés.

CASO BASE
---------
La topografía es una malla de 7,220 caras que cubre 295 ha (mucho más que las
19.6 ha del pit) con el 93 % de las caras bajo 5 grados: terreno suave.
Z entre 313.2 y 366.5 m; el pit diseñado llega a 355.9 m de cresta.

Es un caso benigno. NO asumir que siempre lo será: un pit en ladera empinada
rompe cualquier atajo que dependa de terreno plano.
"""
from __future__ import annotations

from .modelo import Banco, Malla, Rampa


def recortar(bancos: list[Banco], rampa: Rampa | None,
             topografia: Malla) -> tuple[list[Banco], Rampa | None]:
    """Recorta el diseño donde intercepta la superficie del terreno."""
    raise NotImplementedError("Ver el docstring del módulo.")


def cota_en(topografia: Malla, x: float, y: float) -> float | None:
    """Cota del terreno en un punto. None si cae fuera de la malla.

    Es la primitiva de todo lo demás. Hacerla rápida: se llama muchísimo.
    Conviene indexar la malla en una grilla al cargarla.
    """
    raise NotImplementedError
