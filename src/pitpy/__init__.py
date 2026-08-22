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

    ESTADO: v0.1.0-dev. Bancos (MOT-1), volúmenes (MOT-2), líneas de DXF (MOT-3),
    rampa (MOT-4) y recorte con topografía (MOT-5) ya funcionan. Falta cerrar el
    flujo por CLI (MOT-6). La malla de superficie del DXF sigue sin escribirse
    (ver docs/ROADMAP.md §Etapa 3), y la topografía solo recorta el techo de
    volúmenes/DXF — las líneas de banco exportadas siguen siendo la geometría
    teórica, sin recortar (mismo motivo: son contornos a cota fija, no una
    malla).
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
    from .bancos import construir, lineas
    construccion = construir(carcaza, parametros, talud_global=talud)
    bancos = lineas(construccion)

    # Las cuatro etapas se emiten SIEMPRE, aunque no haya trabajo que hacer, y con
    # la fracción siempre creciendo. PitForge tiene los textos mapeados uno a uno y
    # reemite cada uno al navegador: una etapa que desaparece deja la barra colgada
    # a mitad de camino, y una fracción que retrocede la hace saltar hacia atrás.
    avisar("trazando rampa", 0.60)
    rampa = None
    if parametros.trazar_rampa:
        from .rampa import trazar
        rampa = trazar(construccion, parametros)
        construccion.rampa = rampa

    avisar("recortando topografía", 0.90)
    if topografia is not None:
        construccion.topografia = topografia
    avisar("recortando topografía", 1.0)

    return Diseno(bancos_=bancos, rampa_=rampa, carcaza=carcaza,
                  parametros=parametros, construccion_=construccion)
