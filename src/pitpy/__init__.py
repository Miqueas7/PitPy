"""PitPy — de una carcaza de pit optimizado a un diseño geométrico operativo.

Ver docs/ARQUITECTURA.md para el flujo y docs/API_CONTRACTS.md para el contrato
público (PitForge programa contra él).
"""
from .modelo import Banco, Carcaza, Diseno, Malla, Parametros, Rampa, Reporte, TaludDetectado
from .dxf import leer_carcaza, leer_malla, leer_topografia
from .taludes import detectar_talud

__version__ = "0.1.0.dev0"

__all__ = [
    "Banco", "Carcaza", "Diseno", "Malla", "Parametros", "Rampa", "Reporte",
    "TaludDetectado", "leer_carcaza", "leer_malla", "leer_topografia",
    "detectar_talud", "disenar",
    "PitPyError", "DXFIlegible", "GeometriaInvalida", "RampaImposible",
]


class PitPyError(Exception):
    """Base de todos los errores de PitPy."""


class DXFIlegible(PitPyError):
    """El archivo DXF no se pudo interpretar."""


class GeometriaInvalida(PitPyError):
    """La carcaza no forma un pit cerrado y utilizable."""


class RampaImposible(PitPyError):
    """No se puede trazar la rampa con esos parámetros.

    El mensaje DEBE indicar qué parámetro relajar: es el error que más va a ver
    el usuario y, sin esa pista, no sabe qué hacer.
    """


def disenar(carcaza, parametros, topografia=None, progreso=None):
    """Genera el diseño operativo. Ver docs/API_CONTRACTS.md.

    Args:
        carcaza: Carcaza leída con leer_carcaza().
        parametros: Parametros con la geometría deseada.
        topografia: Malla opcional para recortar el diseño.
        progreso: callback(etapa: str, fraccion: float) para la barra de PitForge.

    Returns:
        Diseno

    Raises:
        GeometriaInvalida, RampaImposible

    ESTADO: v0.1.0-dev. Hoy llega hasta los bancos (MOT-1). La rampa (MOT-4), el
    recorte con topografía (MOT-5) y el reporte de volúmenes (MOT-2) todavía no
    están: `Diseno.rampa()` devuelve None y `Diseno.reporte()` levanta
    NotImplementedError. Las etapas de progreso que faltan tampoco se emiten.
    """
    from .modelo import Diseno

    def avisar(etapa, fraccion):
        if progreso is not None:
            progreso(etapa, fraccion)

    avisar("detectando talud", 0.05)
    talud = parametros.talud_global
    if talud is None:
        talud = detectar_talud(carcaza).mediana

    avisar("generando bancos", 0.20)
    from .bancos import generar
    bancos = generar(carcaza, parametros, talud_global=talud)
    avisar("generando bancos", 1.0)

    return Diseno(bancos_=bancos, rampa_=None, carcaza=carcaza,
                  parametros=parametros)
