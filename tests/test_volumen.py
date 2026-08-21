"""Áreas, volúmenes y sobre-estéril.

El criterio de aceptación de la etapa 2 son dos números medidos sobre los
archivos reales: 19.0 ha la carcaza suavizada y 19.6 ha el pit diseñado, ±0.1.
Todo lo demás se prueba con geometría sintética de respuesta conocida.
"""
import math

import pytest

from pitpy.modelo import Carcaza, Malla, Parametros
from tests.test_superficie import malla_cono

PARAMETROS = dict(altura_banco=10.0, ancho_berma=6.0, talud_global=45.0,
                  rampa_ancho=12.0, rampa_pendiente=0.10, radio_giro=25.0)


def test_el_area_proyectada_de_un_cuadrado_es_su_area():
    from pitpy.volumen import area_proyectada_ha

    lado = 100.0
    cuadrado = Malla(caras=[[(0.0, 0.0, 5.0), (lado, 0.0, 5.0),
                             (lado, lado, 5.0), (0.0, lado, 5.0)]])

    assert area_proyectada_ha(cuadrado.caras) == pytest.approx(1.0)   # 10,000 m2


def test_el_area_no_cambia_si_la_superficie_esta_inclinada():
    """Es área EN PLANTA: la proyección, no la superficie desarrollada."""
    from pitpy.volumen import area_proyectada_ha

    plano = Malla(caras=[[(0.0, 0.0, 0.0), (100.0, 0.0, 100.0),
                          (100.0, 100.0, 100.0), (0.0, 100.0, 0.0)]])

    assert area_proyectada_ha(plano.caras) == pytest.approx(1.0)


def test_el_area_de_la_carcaza_del_caso_base(caso_base):
    """Criterio de aceptación de la etapa 2 (ROADMAP)."""
    from pitpy import leer_carcaza
    from pitpy.volumen import area_proyectada_ha

    carcaza = leer_carcaza(caso_base["suavizada"])

    assert area_proyectada_ha(carcaza.caras) == pytest.approx(19.0, abs=0.1)


def test_el_area_del_pit_disenado_del_caso_base(caso_base):
    """La otra mitad del criterio: el diseño del ingeniero ocupa 19.6 ha."""
    from pitpy import leer_malla
    from pitpy.volumen import area_proyectada_ha

    diseno = leer_malla(caso_base["disenado"])

    assert area_proyectada_ha(diseno.caras) == pytest.approx(19.6, abs=0.1)


@pytest.fixture
def diseno_del_cono():
    """Sin rampa: estos tests miden lo que cuestan los bancos y las bermas solos.

    Con rampa el signo del sobre-estéril se da vuelta, y eso tiene su propio test
    en test_rampa.py.
    """
    from pitpy import disenar
    m = malla_cono(radio=110.0, altura=110.0, lados=360)
    return disenar(Carcaza(caras=m.caras),
                   Parametros(**{**PARAMETROS, "trazar_rampa": False}))


def test_el_reporte_trae_los_bancos_y_las_cotas_del_diseno(diseno_del_cono):
    r = diseno_del_cono.reporte()

    assert r.bancos == 9
    assert r.cota_fondo == pytest.approx(10.0)
    assert r.cota_cresta == pytest.approx(100.0)


def test_el_volumen_del_pit_es_el_del_cono_que_lo_contiene(diseno_del_cono):
    """El volumen excavado de un cono de radio 100 y 100 de alto es pi*r^2*h/3.

    Se mide desde el plano de la cresta hacia abajo, que es la única referencia
    que el motor tiene mientras no exista el recorte con topografía.
    """
    r = diseno_del_cono.reporte()

    esperado = math.pi * 100.0 ** 2 * 100.0 / 3.0
    assert r.volumen_carcaza_m3 == pytest.approx(esperado, rel=0.03)


def test_el_sobre_esteril_es_la_diferencia_entre_el_diseno_y_la_carcaza(diseno_del_cono):
    r = diseno_del_cono.reporte()

    assert r.sobre_esteril_m3 == pytest.approx(r.volumen_diseno_m3 - r.volumen_carcaza_m3)
    assert r.sobre_area_ha == pytest.approx(r.area_diseno_ha - r.area_carcaza_ha)


def test_sin_rampa_el_diseno_pierde_bloques_en_vez_de_agregar_esteril(diseno_del_cono):
    """El signo del sobre-estéril dice qué está pasando, y hay que entenderlo.

    Un diseño de bancos sobre una carcaza lisa queda POR ENCIMA de ella: en la
    berma de la cota z el piso es z mientras la carcaza sube desde z-6 hasta z, y
    en la cara pasa lo mismo. Es decir, se dejan bloques sin minar; no se agrega
    estéril. Eso llega recién con la rampa (MOT-4), que sí empuja las paredes.

    El desnivel medio esperado es la mitad de lo que la berma le come al avance:

        altura * berma / (2 * avance_total) = 10 * 6 / (2 * 10.04) = 2.99 m

    Se reparte sobre la huella de la CARCAZA, no sobre la del diseño: parte de lo
    que se deja sin minar es el anillo del borde, entre la cresta del banco más
    alto y donde llegaba la carcaza, adonde el diseño directamente no llega.
    Medido: 3.35 m en el cono, 3.25 m en el caso base.
    """
    r = diseno_del_cono.reporte()

    assert r.sobre_esteril_m3 < 0, "sin rampa no se puede agregar estéril"

    desnivel_medio = -r.sobre_esteril_m3 / (r.area_carcaza_ha * 1e4)
    teorico = 10.0 * 6.0 / (2 * 10.0 / math.tan(math.radians(45.0)))
    assert desnivel_medio == pytest.approx(teorico, rel=0.25)


def test_el_reporte_avisa_que_todavia_no_hay_rampa(diseno_del_cono):
    """PitForge muestra las advertencias tal cual: no puede informar un
    sobre-estéril incompleto sin decir que le falta la rampa."""
    r = diseno_del_cono.reporte()

    assert any("rampa" in a.lower() for a in r.advertencias)
