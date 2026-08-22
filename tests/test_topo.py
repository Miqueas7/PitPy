"""Recorte del diseño contra la topografía.

El diseño se construye a partir de la carcaza, sin conocer el terreno real: puede
protuberar por encima de él en cualquier lugar donde la sección local sea más
baja que el plano teórico de una berma o de la cresta. Lo que hace `topo` es
bajar esas celdas a la cota real del terreno — nunca subirlas.

⚠️ La topografía del caso base es benigna (93 % de caras bajo 5 grados): estos
tests con geometría sintética prueban justamente lo que un terreno benigno no
ejercita, terreno que corta el diseño de verdad.
"""
import math

import numpy as np
import pytest

from pitpy import Parametros
from pitpy.modelo import Carcaza, Malla
from tests.test_superficie import malla_cono

PARAMETROS = dict(altura_banco=10.0, ancho_berma=6.0, talud_global=45.0,
                  rampa_ancho=12.0, rampa_pendiente=0.10, radio_giro=25.0,
                  trazar_rampa=False)


def malla_plano(x0, y0, x1, y1, z):
    """Un rectángulo horizontal a la cota `z`, como dos triángulos."""
    p00, p10, p11, p01 = (x0, y0, z), (x1, y0, z), (x1, y1, z), (x0, y1, z)
    return Malla(caras=[[p00, p10, p11], [p00, p11, p01]])


@pytest.fixture(scope="module")
def construccion_del_cono():
    from pitpy.bancos import construir

    m = malla_cono(radio=110.0, altura=110.0, lados=360)
    return construir(Carcaza(caras=m.caras), Parametros(**PARAMETROS), talud_global=45.0)


def test_muestrear_en_pone_una_malla_sobre_una_grilla_ajena(construccion_del_cono):
    """Lo que necesita el recorte: el terreno, en la MISMA grilla que el diseño."""
    from pitpy.superficie import muestrear_en

    s = construccion_del_cono.superficie
    plano = malla_plano(-200, -200, 200, 200, 42.0)

    z = muestrear_en(plano, s.origen, s.paso, s.z.shape)

    assert z.shape == s.z.shape
    assert np.all(z[~np.isnan(z)] == pytest.approx(42.0))


def test_muestrear_en_da_nan_fuera_de_la_huella_del_terreno(construccion_del_cono):
    """Cuando el terreno no cubre toda la grilla, hay que saber dónde no cubre."""
    from pitpy.superficie import muestrear_en

    s = construccion_del_cono.superficie
    parche = malla_plano(0, 0, 20, 20, 42.0)   # una esquina nada más

    z = muestrear_en(parche, s.origen, s.paso, s.z.shape)

    assert np.isnan(z).any()
    assert not np.isnan(z).all()


def test_recortar_no_toca_donde_el_terreno_esta_mas_alto_que_el_diseno(construccion_del_cono):
    """Un terreno que cubre todo por arriba del diseño no debería cambiar nada:
    el pit entero queda por debajo de la superficie natural."""
    from pitpy.bancos import superficie_de_bancos
    from pitpy.topo import recortar

    c = construccion_del_cono
    z = superficie_de_bancos(c)
    terreno = malla_plano(-500, -500, 500, 500, 500.0)   # mucho más alto que la cresta

    recortado = recortar(z, c.superficie, terreno)

    assert np.allclose(recortado[~np.isnan(z)], z[~np.isnan(z)], equal_nan=True)


def test_recortar_baja_el_diseno_donde_el_terreno_es_mas_bajo(construccion_del_cono):
    """El caso que importa: un terreno que corta el diseño a media altura."""
    from pitpy.bancos import superficie_de_bancos
    from pitpy.topo import recortar

    c = construccion_del_cono
    z = superficie_de_bancos(c)
    terreno = malla_plano(-500, -500, 500, 500, 60.0)   # corta el cono a los 60 m

    recortado = recortar(z, c.superficie, terreno)

    con_diseno = ~np.isnan(z)
    assert np.nanmax(recortado[con_diseno]) == pytest.approx(60.0, abs=0.5)
    # Por debajo de 60, nada cambia: ahí el diseño ya estaba bajo el terreno.
    bajo_el_corte = con_diseno & (z <= 60.0)
    assert np.allclose(recortado[bajo_el_corte], z[bajo_el_corte])


def test_recortar_deja_igual_donde_el_terreno_no_cubre(construccion_del_cono):
    """Si el archivo de topografía no llega a todo el pit —pasa en la práctica—
    lo que no cubre se deja como el diseño lo calculó, no se inventa nada."""
    from pitpy.bancos import superficie_de_bancos
    from pitpy.topo import recortar

    c = construccion_del_cono
    z = superficie_de_bancos(c)
    x0, y0 = c.superficie.origen
    # Un parche que cubre solo un cuarto de la grilla.
    terreno = malla_plano(x0, y0, x0 + 50, y0 + 50, 60.0)

    recortado = recortar(z, c.superficie, terreno)

    ny, nx = z.shape
    lejos = np.isnan(np.full(z.shape, 0.0))
    lejos[ny // 2:, nx // 2:] = True   # cuadrante opuesto al parche
    con_diseno_lejos = ~np.isnan(z) & lejos
    assert con_diseno_lejos.any(), "el cono tiene que llegar también a ese cuadrante"
    assert np.array_equal(recortado[con_diseno_lejos], z[con_diseno_lejos])


def test_area_recortada_ha_mide_lo_que_bajo_el_terreno(construccion_del_cono):
    from pitpy.bancos import superficie_de_bancos
    from pitpy.topo import area_recortada_ha, recortar

    c = construccion_del_cono
    z = superficie_de_bancos(c)
    terreno = malla_plano(-500, -500, 500, 500, 60.0)
    recortado = recortar(z, c.superficie, terreno)

    afectada = area_recortada_ha(z, recortado, c.superficie.paso)

    esperada = np.count_nonzero((z > 60.0) & ~np.isnan(z)) * c.superficie.paso ** 2 / 1e4
    assert afectada == pytest.approx(esperada)
    assert 0 < afectada < 10.0   # sanity: ni cero ni el pit entero


def test_cota_en_da_la_altura_del_terreno_en_un_punto():
    from pitpy.topo import cota_en

    plano = malla_plano(-100, -100, 100, 100, 77.0)

    assert cota_en(plano, 0.0, 0.0) == pytest.approx(77.0, abs=0.1)


def test_cota_en_da_none_fuera_del_terreno():
    from pitpy.topo import cota_en

    plano = malla_plano(0, 0, 10, 10, 77.0)

    assert cota_en(plano, 500.0, 500.0) is None


def test_el_diseno_con_topografia_pasa_por_disenar(construccion_del_cono):
    """El camino completo: disenar(topografia=...) tiene que llegar hasta el
    reporte sin levantar nada, y avisar que recortó."""
    from pitpy import disenar

    m = malla_cono(radio=110.0, altura=110.0, lados=360)
    terreno = malla_plano(-500, -500, 500, 500, 60.0)

    d = disenar(Carcaza(caras=m.caras), Parametros(**PARAMETROS), topografia=terreno)
    r = d.reporte()

    assert r.bancos == 9
    assert any("topograf" in a.lower() for a in r.advertencias)


def test_la_topografia_hace_mas_chico_el_volumen_del_diseno(construccion_del_cono):
    """Antes de MOT-5, el volumen se medía contra un plano imaginario a la altura
    de la cresta, como si el terreno original fuera plano ahí. Con terreno real
    —que acá es mucho más bajo, a 60 m— esa referencia se reemplaza por el techo
    real, y el volumen tiene que bajar: ya no se cuenta como "removido" un rocío
    que nunca existió por encima del suelo natural.
    """
    from pitpy import disenar

    m = malla_cono(radio=110.0, altura=110.0, lados=360)
    p = Parametros(**PARAMETROS)

    sin_topo = disenar(Carcaza(caras=m.caras), p).reporte()
    terreno = malla_plano(-500, -500, 500, 500, 60.0)
    con_topo = disenar(Carcaza(caras=m.caras), p, topografia=terreno).reporte()

    assert con_topo.volumen_diseno_m3 < sin_topo.volumen_diseno_m3
    assert con_topo.volumen_carcaza_m3 < sin_topo.volumen_carcaza_m3
    # El área en planta no cambia: la topografía baja el techo, no borra celdas.
    assert con_topo.area_diseno_ha == pytest.approx(sin_topo.area_diseno_ha)


def test_sin_topografia_el_volumen_es_el_de_siempre(construccion_del_cono):
    """Blindaje de regresión: con topografia=None el resultado tiene que ser
    BIT A BIT el mismo que daban MOT-2/MOT-3/MOT-4, sin este cambio de fórmula."""
    from pitpy import disenar

    m = malla_cono(radio=110.0, altura=110.0, lados=360)
    r = disenar(Carcaza(caras=m.caras), Parametros(**PARAMETROS)).reporte()

    assert r.volumen_carcaza_m3 == pytest.approx(1047145.1, rel=1e-6)
    assert r.volumen_diseno_m3 == pytest.approx(941962.6, rel=1e-6)


def test_sin_topografia_no_hay_advertencia_de_recorte(construccion_del_cono):
    from pitpy import disenar

    m = malla_cono(radio=110.0, altura=110.0, lados=360)
    r = disenar(Carcaza(caras=m.caras), Parametros(**PARAMETROS)).reporte()

    assert not any("topograf" in a.lower() for a in r.advertencias)
