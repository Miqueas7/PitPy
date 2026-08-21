"""Tests de la generación de bancos.

La geometría se prueba contra un cono de talud conocido, donde la respuesta se
calcula a mano. El caso base real (13 bancos del archivo 4) está en
test_caso_base.py: acá se prueba el mecanismo, allá el resultado.
"""
import math

import pytest

from pitpy.modelo import Carcaza, Parametros
from tests.test_superficie import area_encerrada, malla_cono

PARAMETROS = dict(altura_banco=10.0, ancho_berma=6.0, talud_global=45.0,
                  rampa_ancho=12.0, rampa_pendiente=0.10, radio_giro=25.0)


@pytest.fixture
def cono():
    """Pit de juguete: cono invertido de talud 45 grados.

    110 m de alto y no 100 a propósito: así la cota máxima de la carcaza (109.x
    en los centros de celda) queda lejos del múltiplo de la altura de banco y la
    cresta cae sin ambigüedad en la 100.
    """
    m = malla_cono(radio=110.0, altura=110.0, lados=360)
    return Carcaza(caras=m.caras)


def test_las_cotas_del_caso_base_son_trece():
    from pitpy.bancos import cotas_de_banco

    cotas = cotas_de_banco(230.0, 350.0, 10.0)

    assert len(cotas) == 13
    assert cotas[0] == 230.0 and cotas[-1] == 350.0


def test_la_ultima_cota_nunca_pasa_la_cresta():
    from pitpy.bancos import cotas_de_banco

    assert cotas_de_banco(230.0, 355.0, 10.0)[-1] == 350.0


def test_el_fondo_no_baja_hasta_la_punta_del_tazon(cono):
    """Decisión 8: donde no cabe un banco completo no hay piso, hay punta."""
    from pitpy.bancos import generar

    bancos = generar(cono, Parametros(**PARAMETROS), talud_global=45.0, paso=1.0)

    # Cresta a la cota 100. El avance por banco es 10 m, y la sección del cono a
    # la cota z es un círculo de radio z: el primer nivel donde cabe es el 10.
    assert bancos[0].cota == 20.0
    assert bancos[-1].cota == 100.0
    assert len(bancos) == 9


def test_el_pie_de_cada_banco_se_apoya_en_la_carcaza(cono):
    """Decisión 7: el pie es el contorno de la carcaza de su propia cota."""
    from pitpy.bancos import generar

    banco = [b for b in generar(cono, Parametros(**PARAMETROS),
                                talud_global=45.0, paso=1.0) if b.cota == 60.0][0]

    assert all(p[2] == pytest.approx(50.0) for p in banco.pie)
    assert area_encerrada(banco.pie) == pytest.approx(math.pi * 50.0 ** 2, rel=0.02)


def test_la_cresta_avanza_lo_que_dice_la_cara_de_banco(cono):
    """Talud global 45 y berma 6 => avance de cara 4 m. La cresta va 4 m afuera."""
    from pitpy.bancos import generar

    banco = [b for b in generar(cono, Parametros(**PARAMETROS),
                                talud_global=45.0, paso=1.0) if b.cota == 60.0][0]

    assert all(p[2] == pytest.approx(60.0) for p in banco.cresta)
    assert area_encerrada(banco.cresta) == pytest.approx(math.pi * 54.0 ** 2, rel=0.02)


def test_entre_la_cresta_de_un_banco_y_el_pie_del_siguiente_queda_la_berma(cono):
    """El ancho de berma pedido tiene que aparecer en la geometría, no en un papel."""
    from pitpy.bancos import generar

    bancos = {b.cota: b for b in generar(cono, Parametros(**PARAMETROS),
                                         talud_global=45.0, paso=1.0)}

    r_cresta = math.sqrt(area_encerrada(bancos[60.0].cresta) / math.pi)
    r_pie_siguiente = math.sqrt(area_encerrada(bancos[70.0].pie) / math.pi)

    assert r_pie_siguiente - r_cresta == pytest.approx(6.0, abs=0.5)


def test_el_paso_no_se_hace_infinitamente_chico_con_bermas_anchas():
    """Con banco 7 m y berma 6 m el avance de cara es 1 m: el paso ideal sería
    0.25 m y la grilla de un pit de 750 m se iría a 9 millones de celdas.

    Eso en PitForge no es "lento": es la ventana colgada. La grilla se topea.
    """
    from pitpy.bancos import paso_por_omision

    fino = paso_por_omision(avance_cara=1.0, ancho_berma=6.0, extension=750.0)

    assert fino >= 750.0 / 1000.0
    assert 750.0 / fino <= 1000


def test_el_paso_por_omision_resuelve_el_rasgo_mas_angosto():
    """Mientras la grilla no se dispare, manda la geometría: cuatro celdas a lo
    ancho del rasgo más angosto del diseño (ARQUITECTURA, decisión 6)."""
    from pitpy.bancos import paso_por_omision

    assert paso_por_omision(avance_cara=4.04, ancho_berma=6.0,
                            extension=750.0) == pytest.approx(1.01)
