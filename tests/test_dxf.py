"""El lector de DXF contra los archivos reales.

Estas cifras salieron de medir los archivos que mandó Yhonny el 17-ago-2026.
Si un cambio las mueve, o el cambio está mal o los archivos cambiaron. Cualquiera
de las dos cosas hay que mirarla, no ajustar el número para que pase.
"""
import pytest

from pitpy.dxf import leer_malla


@pytest.mark.parametrize("clave,caras,polilineas", [
    ("bruta", 20876, 408),
    ("suavizada", 18703, 408),
    ("isolineas", 0, 21),
    ("disenado", 5923, 295),
    # La topografía declara 1 POLYLINE pero sin ningún VERTEX: el lector
    # la descarta en vez de devolver una polilínea vacía.
    ("topografia", 7220, 0),
])
def test_conteo_de_entidades(caso_base, clave, caras, polilineas):
    m = leer_malla(caso_base[clave])
    assert len(m.caras) == caras
    assert len(m.polilineas) == polilineas


@pytest.mark.parametrize("clave,zmin,zmax", [
    ("bruta", 210.0, 355.0),
    ("suavizada", 210.0, 352.5),
    ("isolineas", 219.0, 349.0),
    ("disenado", 220.0, 355.9),
    ("topografia", 313.2, 366.5),
])
def test_rango_de_cotas(caso_base, clave, zmin, zmax):
    a, b = leer_malla(caso_base[clave]).rango_z()
    assert a == pytest.approx(zmin, abs=0.1)
    assert b == pytest.approx(zmax, abs=0.1)


def test_las_isolineas_no_traen_caras(caso_base):
    """Son POLYLINE/VERTEX puras: 21 polilíneas, 7,244 vértices.

    Importa porque detectar_talud() necesita caras: con isolíneas debe fallar
    con un mensaje claro, no devolver un número inventado.
    """
    m = leer_malla(caso_base["isolineas"])
    assert not m.caras
    assert sum(len(p) for p in m.polilineas) == 7244


def test_archivo_ilegible_da_error_claro(tmp_path):
    from pitpy import DXFIlegible
    f = tmp_path / "vacio.dxf"
    f.write_text("no soy un dxf")
    with pytest.raises(DXFIlegible):
        leer_malla(str(f))
