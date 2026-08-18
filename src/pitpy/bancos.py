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

from .modelo import Banco, Carcaza, Parametros


def generar(carcaza: Carcaza, parametros: Parametros,
            talud_global: float) -> list[Banco]:
    """Construye los bancos desde la cota de fondo hasta la cresta.

    Args:
        carcaza: la carcaza optimizada, ya leída.
        parametros: altura de banco, ancho de berma, ancho de fondo...
        talud_global: en grados. Viene de taludes.detectar_talud() o del usuario.

    Returns:
        Lista de Banco ordenada de la cota más baja a la más alta.
    """
    raise NotImplementedError("Ver el docstring del módulo.")


def cotas_de_banco(z_fondo: float, z_cresta: float, altura: float) -> list[float]:
    """Cotas de banco entre el fondo y la cresta.

    Separado para poder testearlo sin geometría. En el caso base:
        cotas_de_banco(230, 350, 10) -> 13 cotas
    """
    raise NotImplementedError
