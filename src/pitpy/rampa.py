"""Trazado de la rampa.

PENDIENTE DE IMPLEMENTAR.

ALCANCE v1 — UNA sola rampa
---------------------------
Yhonny fue explícito: "para una primera versión pienso que se podría comenzar
con una sola rampa. Pedirle al algoritmo que determine automáticamente cuántas
rampas son necesarias ya sería bastante más complejo."

PARÁMETROS
    ancho        12 m en el caso base ("porque es un tajo pequeño")
    pendiente    10 % en el caso base ("es un valor que puede variar")
    radio_giro   mínimo, en metros

EL RADIO DE GIRO ES LA VENTAJA COMPETITIVA
------------------------------------------
RecMin NO lo admite como parámetro. Yhonny: "en la práctica, uno va estirando o
acomodando la banqueta para generar suficiente espacio para que el camión pueda
girar. Supongo la aplicación deberá considerarlo."

O sea: hoy eso se resuelve a mano y a ojo. Si PitPy lo respeta de verdad, hace
algo que la herramienta que ellos usan no hace. No lo trates como un detalle.

ENFOQUE SUGERIDO PARA v1
------------------------
Trazado helicoidal simple sobre la pared del pit, subiendo a pendiente constante
y verificando en cada curva que el radio no baje del mínimo. Cuando no cumpla,
ensanchar la banqueta localmente (que es lo que hace el humano).

Empezar por lo simple y medir contra el archivo 4 del caso base. No arrancar con
búsqueda de rutas: puede que no haga falta.

ERRORES
-------
Si no cabe, lanzar RampaImposible CON LA PISTA de qué relajar:
    "no cabe una rampa de 12 m al 10 % en 120 m de desnivel con radio de 25 m:
     necesitarías ~1,200 m de desarrollo y el perímetro disponible es ~900 m.
     Prueba con 12 % de pendiente o reduce el radio a 20 m."

Es el error que el usuario va a ver más seguido. Sin la pista, no sabe qué mover.

v2 — NO IMPLEMENTAR TODAVÍA
---------------------------
· Varias rampas decididas por el algoritmo.
· Un carril desde cierta cota al fondo, dos carriles de ahí a superficie.
· LA FUNCIÓN ESTRELLA (ESPECIFICACION 6.1): que el usuario señale por qué sector
  quiere que la rampa salga a superficie. Yhonny: "eso sería un boom". La
  arquitectura de v1 no debe cerrarle la puerta.
"""
from __future__ import annotations

from .modelo import Banco, Parametros, Rampa


def trazar(bancos: list[Banco], parametros: Parametros) -> Rampa:
    """Traza la rampa que conecta el fondo con la superficie.

    Raises:
        RampaImposible: si no cabe. El mensaje DEBE decir qué parámetro relajar.
    """
    raise NotImplementedError("Ver el docstring del módulo.")


def desarrollo_necesario(desnivel: float, pendiente: float) -> float:
    """Longitud de rampa necesaria para salvar un desnivel, en metros.

    Trivial, pero separado para poder verificar la factibilidad ANTES de trazar
    y así dar un error útil en vez de fallar a mitad del cálculo.
    """
    return desnivel / pendiente
