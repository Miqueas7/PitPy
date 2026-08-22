"""Recorte del diseño contra la topografía.

QUÉ HACE, Y POR QUÉ ES ASÍ
--------------------------
El diseño (`bancos.superficie_disenada`) se construye a partir de la carcaza sin
conocer el terreno real: es una aproximación de bancos y bermas planos derivada
de la forma agregada de la carcaza. Como el terreno real ondula (aunque sea poco
— ver la advertencia de abajo), esa aproximación puede quedar por ENCIMA del
suelo natural en huecos locales: un banco no puede sobresalir del terreno, ahí no
hay roca que remover.

`recortar()` arregla eso con la operación más simple que existe: donde el
terreno cubre y es más bajo que el diseño, el diseño baja hasta el terreno.
Nunca al revés — el terreno nunca sube el diseño.

DECISIÓN: SE FUE DIRECTO AL "RECORTE DIRECTO", SIN EL "NIVEL SUFICIENTE"
-------------------------------------------------------------------------
El ROADMAP describe dos etapas: primero diseñar 1-2 bancos por encima de la cota
máxima del terreno y dejar que el usuario recorte a mano con un booleano en su
CAD ("nivel suficiente"); después, entregar el diseño ya recortado ("mucho
mejor", en palabras de Yhonny). La primera se pensó como escalón intermedio más
fácil de construir.

Con la grilla ya armada (decisión 6 de ARQUITECTURA) el recorte directo NO es más
difícil que el nivel suficiente — es una resta de arreglos numpy — así que se
implementó directo. Lo que el "nivel suficiente" hubiera evitado (que el diseño
no llegue tan alto como el terreno en algún punto, dejando un escalón entre el
banco más alto y el suelo) se midió en el caso base: como mucho 5.2 m de
diferencia, menos de un banco. Para terrenos benignos como este no hace falta la
etapa intermedia. `Parametros.bancos_sobre_topografia` queda declarado mas no
se usa: si un terreno de verdad empinado necesita ese margen, se retoma acá.

EL RECORTE CAMBIA EL VOLUMEN, Y HAY QUE ENTENDER POR QUÉ
----------------------------------------------------------
Antes de esto, `volumen.calcular()` medía todo contra un plano imaginario a la
altura de la cresta, como si el terreno original fuera plano justo ahí — la
única referencia posible sin datos de terreno. Con topografía real, `volumen`
cambia esa referencia por el terreno de verdad (ver `volumen.py`), y **el volumen
de la carcaza también baja**, aunque la carcaza no se tocó: lo que bajó fue la
calidad de la aproximación, no la roca.

CASO BASE (docs/CASO_BASE.md)
------------------------------
La topografía es una malla de 7,220 caras que cubre 295 ha (mucho más que las
19.6 ha del pit) con el 93 % de las caras bajo 5 grados: terreno suave. Medido:
el diseño protruye por encima del terreno real en 0.74 ha (3.83 % de su huella),
hasta 18 m en el punto más alto, 3 m de mediana donde protruye.

Es un caso benigno. NO asumir que siempre lo será: un pit en ladera empinada
puede protruir mucho más, y en ese caso sí conviene retomar el "nivel suficiente".
"""
from __future__ import annotations

import math

import numpy as np

from .modelo import Malla
from .superficie import Superficie, muestrear_en


def recortar(z_diseno: np.ndarray, superficie: Superficie,
             topografia: Malla) -> np.ndarray:
    """Baja el diseño donde el terreno real está más bajo que él.

    Donde la topografía no cubre, el diseño se deja tal cual: no se inventa
    terreno donde no hay dato (pasa en la práctica — el archivo de topografía
    puede no llegar a toda la huella del pit).
    """
    z_terreno = muestrear_en(topografia, superficie.origen, superficie.paso,
                             z_diseno.shape)
    cubre = ~np.isnan(z_terreno)
    con_diseno_y_terreno = cubre & ~np.isnan(z_diseno)

    resultado = z_diseno.copy()
    resultado[con_diseno_y_terreno] = np.minimum(
        z_diseno[con_diseno_y_terreno], z_terreno[con_diseno_y_terreno])
    return resultado


_TOLERANCIA_M = 1e-6
"""Diferencia mínima para contar una celda como "recortada".

Por debajo de esto es ruido de coma flotante del rasterizado (la interpolación
barrocéntrica de un plano perfectamente horizontal no siempre da el mismo float
en cada celda), no una diferencia real de terreno. Sin este umbral, `recortar()`
y `area_recortada_ha()` no coinciden en el conteo de celdas por unos pocos
femtómetros de diferencia — se midió: 184 celdas de más en el caso sintético.
"""


def area_recortada_ha(z_antes: np.ndarray, z_despues: np.ndarray,
                      paso: float) -> float:
    """Cuánta huella del diseño bajó de cota por el recorte, en hectáreas.

    Es lo que le importa al usuario: no CUÁNTO bajó (eso ya está en el volumen),
    sino DÓNDE — para saber si el recorte tocó una esquina o medio pit.
    """
    afectada = ((z_antes - z_despues) > _TOLERANCIA_M) & ~np.isnan(z_antes)
    return float(np.count_nonzero(afectada)) * paso * paso / 1e4


def cota_en(topografia: Malla, x: float, y: float,
            paso: float = 5.0) -> float | None:
    """Cota del terreno en un punto. None si cae fuera de la malla.

    Rasteriza la malla entera para responder un solo punto: no está pensada para
    un lazo apretado. Si hiciera falta consultar muchos puntos, conviene rasterizar
    una vez con `superficie.muestrear_en()` sobre una grilla propia y leerla
    directamente — es lo mismo que hace esta función, sin repetir el trabajo.
    """
    tris = [t[:3] for t in _triangulos_validos(topografia)]
    if not tris:
        return None
    x0 = min(p[0] for t in tris for p in t)
    y0 = min(p[1] for t in tris for p in t)
    x1 = max(p[0] for t in tris for p in t)
    y1 = max(p[1] for t in tris for p in t)
    if not (x0 <= x <= x1 and y0 <= y <= y1):
        return None

    nx = max(1, math.ceil((x1 - x0) / paso))
    ny = max(1, math.ceil((y1 - y0) / paso))
    z = muestrear_en(topografia, (x0, y0), paso, (ny, nx))
    j = min(nx - 1, int((x - x0) / paso))
    i = min(ny - 1, int((y - y0) / paso))
    valor = z[i, j]
    return None if math.isnan(valor) else float(valor)


def _triangulos_validos(malla: Malla) -> list:
    from .superficie import _triangulos
    return list(_triangulos(malla.caras))
