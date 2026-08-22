"""El callback de progreso, que PitForge consume para su barra de avance.

No es un detalle cosmético: la App tiene los textos mapeados uno a uno contra la
lista del contrato, y reemite cada etapa al navegador por SSE. Si el motor emite
una etapa que no está en el contrato, o manda la fracción para atrás, la barra
salta y el usuario deja de confiar en ella.
"""
import pytest

from pitpy import Parametros, disenar
from pitpy.modelo import Carcaza, Malla
from tests.test_superficie import malla_cono

PARAMETROS = dict(altura_banco=10.0, ancho_berma=6.0, talud_global=45.0,
                  rampa_ancho=12.0, rampa_pendiente=0.10, radio_giro=25.0)

# Las etapas que el motor emite hoy, en orden. Es el contrato con PitForge:
# cambiarla obliga a un REQ-MOT (lo pidieron por escrito en REQ-MOT-004).
ETAPAS = ["detectando talud", "generando bancos", "trazando rampa",
          "recortando topografía"]


def registrar(**kw):
    m = malla_cono(radio=110.0, altura=110.0, lados=360)
    llamadas = []
    disenar(Carcaza(caras=m.caras), Parametros(**{**PARAMETROS, **kw.pop("params", {})}),
            progreso=lambda etapa, fraccion: llamadas.append((etapa, fraccion)), **kw)
    return llamadas


def test_las_etapas_son_las_del_contrato_y_en_orden():
    llamadas = registrar()

    vistas = []
    for etapa, _ in llamadas:
        if etapa not in vistas:
            vistas.append(etapa)

    assert vistas == ETAPAS


def test_la_fraccion_nunca_va_para_atras():
    """Una barra que retrocede es peor que una que no se mueve."""
    llamadas = registrar()

    fracciones = [f for _, f in llamadas]
    assert fracciones == sorted(fracciones), f"la fracción retrocede: {fracciones}"


def test_la_fraccion_termina_en_uno():
    llamadas = registrar()

    assert llamadas[-1][1] == pytest.approx(1.0)


def test_las_etapas_se_emiten_igual_cuando_no_hay_trabajo_que_hacer():
    """Sin rampa y sin topografía la barra tiene que llegar a 1.0 igual, y pasar
    por las mismas etapas: si desaparecen, la barra se cuelga a mitad de camino."""
    llamadas = registrar(params={"trazar_rampa": False})

    vistas = []
    for etapa, _ in llamadas:
        if etapa not in vistas:
            vistas.append(etapa)

    assert vistas == ETAPAS
    assert llamadas[-1][1] == pytest.approx(1.0)


def test_sin_callback_no_falla():
    """`progreso` es opcional: la mayoría de los usuarios de la librería no lo usa."""
    m = malla_cono(radio=110.0, altura=110.0, lados=360)

    disenar(Carcaza(caras=m.caras), Parametros(**PARAMETROS))   # sin progreso=
