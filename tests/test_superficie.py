"""Tests de la representación interna: la superficie como grilla regular.

Decisión 6 de docs/ARQUITECTURA.md. Todo se prueba con geometría sintética de
respuesta conocida a mano; el caso base se prueba en test_caso_base.py.
"""
import math

import pytest

from pitpy.modelo import Malla


def malla_plano_inclinado(lado=10.0, pendiente=1.0):
    """Cuadrado de `lado` metros donde z = pendiente * x. Dos triángulos."""
    p00 = (0.0, 0.0, 0.0)
    p10 = (lado, 0.0, pendiente * lado)
    p11 = (lado, lado, pendiente * lado)
    p01 = (0.0, lado, 0.0)
    return Malla(caras=[[p00, p10, p11], [p00, p11, p01]])


def test_rasteriza_un_plano_inclinado_a_su_cota_real():
    from pitpy.superficie import Superficie

    s = Superficie.desde_malla(malla_plano_inclinado(lado=10.0), paso=1.0)

    # 10 celdas de 1 m: los centros caen en x = 0.5, 1.5, ... 9.5 y z = x.
    assert s.z.shape == (10, 10)
    assert s.z[0][0] == pytest.approx(0.5)
    assert s.z[5][9] == pytest.approx(9.5)


def test_el_area_de_la_grilla_es_la_del_terreno():
    from pitpy.superficie import Superficie

    s = Superficie.desde_malla(malla_plano_inclinado(lado=10.0), paso=1.0)

    assert s.area_m2() == pytest.approx(100.0)


def malla_cono(radio=100.0, altura=100.0, lados=180):
    """Cono invertido (un pit de juguete): vértice abajo, talud de 45 grados.

    z(r) = altura * r / radio. Con radio == altura el talud es de 45 grados.
    """
    caras = []
    vertice = (0.0, 0.0, 0.0)
    for k in range(lados):
        a1 = 2 * math.pi * k / lados
        a2 = 2 * math.pi * (k + 1) / lados
        p1 = (radio * math.cos(a1), radio * math.sin(a1), altura)
        p2 = (radio * math.cos(a2), radio * math.sin(a2), altura)
        caras.append([vertice, p1, p2])
    return Malla(caras=caras)


def test_la_seccion_a_una_cota_es_el_area_bajo_esa_cota():
    from pitpy.superficie import Superficie

    s = Superficie.desde_malla(malla_cono(radio=100.0, altura=100.0), paso=1.0)

    # En un cono a 45 grados, la sección a la cota z es un círculo de radio z.
    area = s.area_seccion_m2(s.seccion(50.0))
    assert area == pytest.approx(math.pi * 50.0 ** 2, rel=0.02)


def test_dilatar_ensancha_el_contorno_la_distancia_pedida():
    from pitpy.superficie import Superficie, dilatar

    s = Superficie.desde_malla(malla_cono(radio=100.0, altura=100.0), paso=1.0)
    sec = s.seccion(50.0)

    ancha = dilatar(sec, radio=10.0, paso=1.0)

    # Círculo de radio 50 ensanchado 10 m -> círculo de radio 60.
    assert s.area_seccion_m2(ancha) == pytest.approx(math.pi * 60.0 ** 2, rel=0.02)


def test_erosionar_angosta_el_contorno_la_distancia_pedida():
    from pitpy.superficie import Superficie, erosionar

    s = Superficie.desde_malla(malla_cono(radio=100.0, altura=100.0), paso=1.0)

    angosta = erosionar(s.seccion(50.0), radio=10.0, paso=1.0)

    assert s.area_seccion_m2(angosta) == pytest.approx(math.pi * 40.0 ** 2, rel=0.02)


def test_cabe_circulo_distingue_la_punta_del_tazon_de_un_piso_de_verdad():
    """El criterio del fondo (decisión 8): que quepa un banco completo."""
    from pitpy.superficie import Superficie, cabe_circulo

    s = Superficie.desde_malla(malla_cono(radio=100.0, altura=100.0), paso=1.0)

    assert cabe_circulo(s.seccion(30.0), diametro=20.0, paso=1.0)      # r=30 -> sí
    assert not cabe_circulo(s.seccion(5.0), diametro=20.0, paso=1.0)   # r=5  -> no


def area_encerrada(anillo):
    """Fórmula del zapato sobre un anillo cerrado, en m2."""
    a = 0.0
    for (x1, y1, _), (x2, y2, _) in zip(anillo, anillo[1:]):
        a += x1 * y2 - x2 * y1
    return abs(a) / 2.0


def test_el_contorno_de_una_seccion_es_un_anillo_cerrado_con_su_area():
    from pitpy.superficie import Superficie

    s = Superficie.desde_malla(malla_cono(radio=100.0, altura=100.0), paso=1.0)

    anillos = s.contorno(50.0)

    assert len(anillos) == 1, "un cono tiene un solo borde a cada cota"
    anillo = anillos[0]
    assert anillo[0] == anillo[-1], "el anillo tiene que cerrar"
    assert area_encerrada(anillo) == pytest.approx(math.pi * 50.0 ** 2, rel=0.01)


def test_el_contorno_lleva_la_cota_pedida_en_z():
    from pitpy.superficie import Superficie

    s = Superficie.desde_malla(malla_cono(radio=100.0, altura=100.0), paso=1.0)

    anillo = s.contorno(50.0)[0]

    assert all(p[2] == pytest.approx(50.0) for p in anillo)


def test_el_contorno_de_un_ensanche_queda_a_la_distancia_pedida():
    """Así se saca la cresta: el pie ensanchado el avance de la cara."""
    from pitpy.superficie import Superficie, distancia_hasta

    s = Superficie.desde_malla(malla_cono(radio=100.0, altura=100.0), paso=1.0)
    campo = distancia_hasta(s.seccion(50.0), paso=1.0, radio_max=15.0)

    anillo = s.contorno_de(campo, valor=10.0, z=60.0)[0]

    assert area_encerrada(anillo) == pytest.approx(math.pi * 60.0 ** 2, rel=0.01)


def test_la_silueta_es_el_borde_de_la_carcaza_en_planta():
    """REQ-APP-001: miniatura para PitForge sin dibujar 20,000 caras."""
    from pitpy.modelo import Carcaza

    c = Carcaza(caras=malla_cono(radio=110.0, altura=110.0, lados=360).caras)

    silueta = c.silueta(paso=5.0)

    assert silueta[0] == silueta[-1], "la silueta cierra"
    assert area_encerrada(silueta) == pytest.approx(math.pi * 110.0 ** 2, rel=0.03)


def test_la_silueta_trae_la_cota_del_borde_y_no_cero():
    from pitpy.modelo import Carcaza

    c = Carcaza(caras=malla_cono(radio=110.0, altura=110.0, lados=360).caras)

    silueta = c.silueta(paso=5.0)

    assert all(p[2] > 100.0 for p in silueta), "el borde del cono está arriba de 100"
