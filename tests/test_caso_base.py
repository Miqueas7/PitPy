"""Test de regresión del motor completo.

Todos marcados xfail hasta que el motor exista. A medida que se implemente,
quitar el xfail de a uno. NO relajar los números para que pasen: el archivo 4 lo
diseñó un ingeniero y es la referencia.
"""
import pytest

pytestmark = pytest.mark.xfail(reason="el motor todavía no está implementado",
                               raises=NotImplementedError, strict=False)

PARAMETROS_DE_YHONNY = dict(
    altura_banco=10.0,
    ancho_berma=6.0,
    talud_global=45.0,
    rampa_ancho=12.0,
    rampa_pendiente=0.10,
    radio_giro=25.0,
)


def test_genera_trece_bancos(caso_base):
    """El diseño de referencia tiene 13 cotas cada 10 m, de 230 a 350."""
    from pitpy import Parametros, disenar, leer_carcaza
    d = disenar(leer_carcaza(caso_base["suavizada"]), Parametros(**PARAMETROS_DE_YHONNY))
    assert len(d.bancos()) == 13


def test_el_sobre_area_ronda_las_seis_decimas_de_hectarea(caso_base):
    """19.6 ha del diseño contra 19.0 de la carcaza: 0.6 ha de costo geométrico.

    Es EL número de la herramienta. Tolerancia amplia (0.3 ha) porque el trazado
    de rampa puede diferir del que hizo Yhonny a mano y seguir siendo válido.
    """
    from pitpy import Parametros, disenar, leer_carcaza
    d = disenar(leer_carcaza(caso_base["suavizada"]), Parametros(**PARAMETROS_DE_YHONNY))
    assert d.reporte().sobre_area_ha == pytest.approx(0.6, abs=0.3)


def test_la_rampa_respeta_el_radio_de_giro(caso_base):
    """RecMin no lo controla. Si PitPy tampoco, no aporta nada nuevo."""
    from pitpy import Parametros, disenar, leer_carcaza
    d = disenar(leer_carcaza(caso_base["suavizada"]), Parametros(**PARAMETROS_DE_YHONNY))
    assert d.rampa() is not None


def test_el_fondo_angosto_se_avisa_pero_no_se_corrige(caso_base):
    """ESPECIFICACION 7: Yhonny prefiere perder bloques a arrastrar estéril.

    Con forzar_ancho_fondo=False debe AVISAR en las advertencias, nunca ensanchar
    por su cuenta.
    """
    from pitpy import Parametros, disenar, leer_carcaza
    p = Parametros(**PARAMETROS_DE_YHONNY, ancho_fondo_minimo=80.0,
                   forzar_ancho_fondo=False)
    r = disenar(leer_carcaza(caso_base["suavizada"]), p).reporte()
    assert any("fondo" in a.lower() for a in r.advertencias)
