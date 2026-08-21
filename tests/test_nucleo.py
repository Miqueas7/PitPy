"""El núcleo C++ contra la referencia en Python.

La implementación en Python NO se borra al portar un kernel a C++: queda como
oráculo. Cada kernel tiene que devolver **lo mismo** que ella, y eso se prueba
acá. Sin este test, "lo reescribí en C++ y anda más rápido" es una afirmación sin
respaldo: podría andar más rápido y estar mal.
"""
import math

import numpy as np
import pytest

from pitpy import superficie
from tests.test_superficie import malla_cono, malla_plano_inclinado


def triangulos_de(malla):
    return np.array([t[:3] for t in superficie._triangulos(malla.caras)], dtype=np.float64)


def rejilla_de(malla, paso):
    """Origen y forma que usaría Superficie.desde_malla para esa malla."""
    pts = [p for c in malla.caras for p in c]
    x0 = min(p[0] for p in pts)
    y0 = min(p[1] for p in pts)
    nx = max(1, math.ceil((max(p[0] for p in pts) - x0) / paso))
    ny = max(1, math.ceil((max(p[1] for p in pts) - y0) / paso))
    return (x0, y0), (ny, nx)


def test_el_nucleo_compilado_esta_disponible():
    """Si esto falla, la rueda salió sin extensión y todo corre en Python.

    Es una falla silenciosa peligrosa: la suite pasaría igual, solo que 30 veces
    más lento y nadie se entera hasta que un pit grande tarda minutos.
    """
    assert superficie.NUCLEO_COMPILADO, (
        "el núcleo C++ no está compilado; reinstalar con pip install -e .")


@pytest.mark.parametrize("malla, paso", [
    (malla_plano_inclinado(lado=10.0), 1.0),
    (malla_cono(radio=110.0, altura=110.0, lados=360), 2.0),
    (malla_cono(radio=110.0, altura=110.0, lados=360), 0.5),
    (malla_cono(radio=37.5, altura=90.0, lados=7), 1.0),      # pocos lados, muy oblicuo
])
def test_el_rasterizador_cpp_da_lo_mismo_que_el_de_python(malla, paso):
    tris = triangulos_de(malla)
    origen, forma = rejilla_de(malla, paso)

    z_cpp = superficie._rasterizar_cpp(tris, origen, paso, forma)
    z_py = superficie._rasterizar_python(tris, origen, paso, forma)

    assert z_cpp.shape == z_py.shape
    # Las mismas celdas vacías: si una implementación cubre una celda que la otra
    # no, la línea de cresta sale corrida medio paso justo en el borde.
    assert np.array_equal(np.isnan(z_cpp), np.isnan(z_py))
    llenas = ~np.isnan(z_py)
    assert np.allclose(z_cpp[llenas], z_py[llenas], rtol=0.0, atol=1e-9)


def test_el_rasterizador_cpp_da_lo_mismo_en_el_caso_base(caso_base):
    """La prueba que importa: la malla real, con sus 37,406 triángulos."""
    from pitpy import leer_carcaza

    carcaza = leer_carcaza(caso_base["suavizada"])
    tris = triangulos_de(carcaza)
    origen, forma = rejilla_de(carcaza, 2.0)

    z_cpp = superficie._rasterizar_cpp(tris, origen, 2.0, forma)
    z_py = superficie._rasterizar_python(tris, origen, 2.0, forma)

    assert np.array_equal(np.isnan(z_cpp), np.isnan(z_py))
    llenas = ~np.isnan(z_py)
    assert np.allclose(z_cpp[llenas], z_py[llenas], rtol=0.0, atol=1e-9)


def mascaras_de_prueba():
    """Formas con trampas: un bloque, un anillo, algo disperso y algo vacío."""
    bloque = np.zeros((60, 80), dtype=bool)
    bloque[20:40, 30:50] = True

    anillo = np.zeros((60, 80), dtype=bool)
    anillo[10:50, 15:65] = True
    anillo[20:40, 30:50] = False        # hueco: la distancia entra por adentro

    disperso = np.zeros((40, 40), dtype=bool)
    disperso[::7, ::5] = True           # puntos sueltos

    borde = np.zeros((30, 30), dtype=bool)
    borde[0, :] = True                  # pegado al borde del arreglo

    return {"bloque": bloque, "anillo": anillo, "disperso": disperso,
            "borde": borde, "vacia": np.zeros((20, 20), dtype=bool),
            "llena": np.ones((20, 20), dtype=bool)}


@pytest.mark.parametrize("nombre", list(mascaras_de_prueba()))
@pytest.mark.parametrize("paso, radio", [(1.0, 5.05), (2.0, 8.0), (0.5, 3.0)])
def test_la_distancia_cpp_da_lo_mismo_que_la_de_python(nombre, paso, radio):
    mascara = mascaras_de_prueba()[nombre]

    d_cpp = superficie._distancia_cpp(mascara, paso, radio)
    d_py = superficie._distancia_python(mascara, paso, radio)

    # El infinito marca "más lejos que el radio pedido" y tiene que caer en las
    # mismas celdas: es lo que decide dónde termina la línea de cresta.
    assert np.array_equal(np.isinf(d_cpp), np.isinf(d_py))
    finitas = np.isfinite(d_py)
    assert np.allclose(d_cpp[finitas], d_py[finitas], rtol=0.0, atol=1e-9)


def test_la_distancia_cpp_da_lo_mismo_sobre_una_seccion_real(caso_base):
    from pitpy import leer_carcaza
    from pitpy.superficie import Superficie

    s = Superficie.desde_malla(leer_carcaza(caso_base["suavizada"]), 2.0)
    seccion = s.seccion(300.0)

    d_cpp = superficie._distancia_cpp(seccion, 2.0, 8.08)
    d_py = superficie._distancia_python(seccion, 2.0, 8.08)

    assert np.array_equal(np.isinf(d_cpp), np.isinf(d_py))
    finitas = np.isfinite(d_py)
    assert np.allclose(d_cpp[finitas], d_py[finitas], rtol=0.0, atol=1e-9)


def iguales_los_anillos(a, b, tol=1e-6):
    if len(a) != len(b):
        return False
    for anillo_a, anillo_b in zip(a, b):
        if len(anillo_a) != len(anillo_b):
            return False
        if not np.allclose(np.array(anillo_a), np.array(anillo_b), rtol=0.0, atol=tol):
            return False
    return True


@pytest.mark.parametrize("cota", [10.0, 50.0, 95.0])
def test_los_contornos_cpp_dan_lo_mismo_que_los_de_python(cota):
    from pitpy.superficie import Superficie

    s = Superficie.desde_malla(malla_cono(radio=110.0, altura=110.0, lados=360), 1.0)
    campo = np.nan_to_num(s.z, nan=np.inf)

    a_cpp = superficie._contornos_cpp(campo, cota, 1.0, s.origen, cota)
    a_py = superficie._contornos_python(campo, cota, 1.0, s.origen, cota)

    assert iguales_los_anillos(a_cpp, a_py)


def test_los_contornos_cpp_dan_lo_mismo_sobre_la_carcaza_real(caso_base):
    """Con 2,200 puntos por anillo, un solo punto fuera de lugar parte la línea."""
    from pitpy import leer_carcaza
    from pitpy.superficie import Superficie

    s = Superficie.desde_malla(leer_carcaza(caso_base["suavizada"]), 2.0)
    campo = np.nan_to_num(s.z, nan=np.inf)

    a_cpp = superficie._contornos_cpp(campo, 300.0, 2.0, s.origen, 300.0)
    a_py = superficie._contornos_python(campo, 300.0, 2.0, s.origen, 300.0)

    assert len(a_cpp) == len(a_py) and len(a_cpp[0]) > 1000
    assert iguales_los_anillos(a_cpp, a_py)


def test_el_contorno_de_un_campo_de_distancia_tambien_coincide(caso_base):
    """El camino real de la cresta: contorno sobre el campo de distancia."""
    from pitpy import leer_carcaza
    from pitpy.superficie import Superficie, distancia_hasta

    s = Superficie.desde_malla(leer_carcaza(caso_base["suavizada"]), 2.0)
    campo = distancia_hasta(s.seccion(300.0), 2.0, 5.05)

    a_cpp = superficie._contornos_cpp(campo, 4.04, 2.0, s.origen, 310.0)
    a_py = superficie._contornos_python(campo, 4.04, 2.0, s.origen, 310.0)

    assert iguales_los_anillos(a_cpp, a_py)
