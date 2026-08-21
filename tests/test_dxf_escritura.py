"""Escritura del diseño a DXF por capas.

El criterio de aceptación de la etapa 3 es que Miqueas lo abra en un CAD y las
capas se distingan. Eso no se puede automatizar; lo que sí se puede es exigir que
el archivo se relea con nuestro propio lector y traiga lo que tiene que traer.
"""
import math

import pytest

from pitpy import Parametros, disenar
from pitpy.modelo import Carcaza
from tests.test_superficie import malla_cono

PARAMETROS = dict(altura_banco=10.0, ancho_berma=6.0, talud_global=45.0,
                  rampa_ancho=12.0, rampa_pendiente=0.10, radio_giro=25.0)


@pytest.fixture(scope="module")
def diseno_del_cono():
    """Sin rampa a propósito: estos tests son sobre las líneas de banco.

    La rampa en el DXF tiene su propio test, en test_rampa.py, porque su línea
    cruza cotas y no cumple —ni tiene por qué— las reglas de una línea de banco.
    """
    m = malla_cono(radio=110.0, altura=110.0, lados=360)
    return disenar(Carcaza(caras=m.caras),
                   Parametros(**{**PARAMETROS, "trazar_rampa": False}))


@pytest.fixture(scope="module")
def dxf_escrito(diseno_del_cono, tmp_path_factory):
    ruta = tmp_path_factory.mktemp("dxf") / "cono.dxf"
    diseno_del_cono.a_dxf(str(ruta))
    return str(ruta)


def test_el_dxf_escrito_lo_lee_nuestro_propio_lector(dxf_escrito):
    """Round-trip. Si nuestro lector no lo lee, ningún CAD lo va a leer mejor."""
    from pitpy import leer_malla

    m = leer_malla(dxf_escrito)

    assert len(m.polilineas) == 2 * 9, "una polilínea de pie y una de cresta por banco"


def test_estan_las_capas_de_lineas_con_su_color(dxf_escrito):
    """BERMA y TALUD no se escriben todavía: ver la nota de escribir_diseno()."""
    from pitpy import leer_malla

    capas = leer_malla(dxf_escrito).capas

    assert {"CRESTA", "PIE"} <= set(capas)
    assert "BERMA" not in capas and "TALUD" not in capas


def test_las_lineas_escritas_cubren_las_cotas_del_diseno(diseno_del_cono, dxf_escrito):
    from pitpy import leer_malla

    z_min, z_max = leer_malla(dxf_escrito).rango_z()
    r = diseno_del_cono.reporte()

    assert z_min == pytest.approx(r.cota_fondo, abs=1.0)
    assert z_max == pytest.approx(r.cota_cresta, abs=1.0)


def test_cada_linea_escrita_esta_a_la_cota_de_su_banco(dxf_escrito):
    """Una línea de diseño con vértices a distinta cota no es una línea de banco."""
    from pitpy import leer_malla

    for anillo in leer_malla(dxf_escrito).polilineas:
        cotas = {round(p[2], 3) for p in anillo}
        assert len(cotas) == 1, "cada polilínea vive en una sola cota"


def test_la_linea_mas_alta_encierra_el_area_del_diseno(diseno_del_cono, dxf_escrito):
    """La cresta del banco más alto es el borde del diseño: tiene que encerrar la
    misma área que informa el reporte."""
    from pitpy import leer_malla

    from tests.test_superficie import area_encerrada

    anillos = leer_malla(dxf_escrito).polilineas
    mayor = max(area_encerrada(a) for a in anillos)

    assert mayor / 1e4 == pytest.approx(diseno_del_cono.reporte().area_diseno_ha, rel=0.02)


def test_el_remuestreo_no_deforma_la_linea(diseno_del_cono, dxf_escrito):
    """Guardar un vértice cada 5 m en vez de cada metro tiene que cambiar el área
    encerrada en menos de lo que mide una celda."""
    from pitpy import leer_malla

    from tests.test_superficie import area_encerrada

    mayor = max(area_encerrada(a) for a in leer_malla(dxf_escrito).polilineas)
    original = max(area_encerrada(b.cresta) for b in diseno_del_cono.bancos())

    assert mayor == pytest.approx(original, rel=0.01)


def test_no_se_escribe_una_rampa_que_no_existe(dxf_escrito):
    """Una capa RAMPA vacía en el CAD hace pensar que la rampa se calculó y dio
    cero. Mientras no haya rampa, no se escribe la capa."""
    from pitpy import leer_malla

    assert "RAMPA" not in leer_malla(dxf_escrito).capas
