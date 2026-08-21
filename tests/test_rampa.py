"""Trazado de la rampa.

El radio de giro es la ventaja competitiva del proyecto: RecMin no lo admite como
parámetro y hoy se resuelve a ojo estirando la banqueta. Si PitPy no lo respeta
de verdad, no aporta nada nuevo — así que acá se mide, no se declara.
"""
import math

import pytest

from pitpy import Parametros
from pitpy.modelo import Carcaza
from tests.test_superficie import malla_cono

PARAMETROS = dict(altura_banco=10.0, ancho_berma=6.0, talud_global=45.0,
                  rampa_ancho=12.0, rampa_pendiente=0.10, radio_giro=25.0)


def radio_de_giro(eje):
    """Radio de la circunferencia que pasa por cada terna de puntos consecutivos.

    Es la medida de un tramo curvo: tres puntos definen un arco, y el radio de ese
    arco es lo que el camión tiene que poder girar.
    """
    radios = []
    for a, b, c in zip(eje, eje[1:], eje[2:]):
        ab = math.dist(a[:2], b[:2])
        bc = math.dist(b[:2], c[:2])
        ca = math.dist(c[:2], a[:2])
        cruz = abs((b[0] - a[0]) * (c[1] - a[1]) - (c[0] - a[0]) * (b[1] - a[1]))
        if cruz < 1e-9 or ab * bc * ca == 0:
            continue          # tramo recto: radio infinito, no restringe
        radios.append(ab * bc * ca / (2 * cruz))
    return min(radios) if radios else float("inf")


@pytest.fixture(scope="module")
def cono():
    m = malla_cono(radio=110.0, altura=110.0, lados=360)
    return Carcaza(caras=m.caras)


@pytest.fixture(scope="module")
def rampa_del_cono(cono):
    from pitpy.bancos import construir
    from pitpy.rampa import trazar

    construccion = construir(cono, Parametros(**PARAMETROS), talud_global=45.0)
    return trazar(construccion, Parametros(**PARAMETROS)), construccion


def test_la_rampa_llega_a_la_cresta(rampa_del_cono):
    rampa, construccion = rampa_del_cono

    assert max(p[2] for p in rampa.eje) == pytest.approx(construccion.cotas[-1], abs=1.0)


def test_la_rampa_arranca_donde_el_giro_entra_de_verdad(rampa_del_cono):
    """Cerca del piso el cono mide 20 m de ancho: ahí no gira nada con radio 25.

    En este cono la sección a la cota z es un círculo de radio z, así que para que
    entre una curva de 25 m de radio hace falta llegar a la cota 25; el primer
    nivel de banco que cumple es el 30. No llegar al fondo NO es una limitación
    del programa: es lo que hace Yhonny (ESPECIFICACION §7).
    """
    rampa, construccion = rampa_del_cono

    assert min(p[2] for p in rampa.eje) == pytest.approx(30.0, abs=1.0)
    assert min(p[2] for p in rampa.eje) > construccion.fondo


def test_la_rampa_nunca_es_mas_parada_que_la_pendiente_pedida(rampa_del_cono):
    """La pendiente pedida es un MÁXIMO: es lo que el camión puede subir cargado.

    Más tendida es válido —cuesta más desarrollo y más excavación, no seguridad—;
    más parada no. Y la pendiente que informa la rampa es la lograda, no la
    pedida, o el reporte diría 10 % cuando el diseño entrega 9.6 %.
    """
    rampa, construccion = rampa_del_cono

    assert rampa.pendiente <= 0.10 + 1e-9
    assert rampa.pendiente > 0.05, "tan tendida ya no es la rampa que se pidió"


def test_el_desarrollo_cierra_con_el_desnivel_y_la_pendiente(rampa_del_cono):
    """La cuenta que hace el ingeniero de una: desnivel = largo x pendiente."""
    rampa, construccion = rampa_del_cono

    desnivel = max(p[2] for p in rampa.eje) - min(p[2] for p in rampa.eje)
    assert rampa.longitud * rampa.pendiente == pytest.approx(desnivel, rel=0.01)
    assert rampa.longitud >= desnivel / 0.10


def test_ningun_tramo_baja_ni_se_pone_horizontal(rampa_del_cono):
    """Una rampa que en algún tramo pierde cota es un error de trazado, no un
    diseño conservador."""
    rampa, _ = rampa_del_cono

    for a, b in zip(rampa.eje, rampa.eje[1:]):
        assert b[2] > a[2]


def test_la_rampa_respeta_el_radio_de_giro_minimo(rampa_del_cono):
    """El corazón del asunto."""
    rampa, _ = rampa_del_cono

    assert radio_de_giro(rampa.eje) >= 25.0


def test_un_radio_de_giro_imposible_se_avisa_diciendo_que_aflojar(cono):
    """RampaImposible es el error que más va a ver el usuario: sin la pista de
    qué parámetro relajar, no sabe qué hacer con él."""
    from pitpy import RampaImposible
    from pitpy.bancos import construir
    from pitpy.rampa import trazar

    p = Parametros(**{**PARAMETROS, "radio_giro": 400.0})   # más que el pit entero
    construccion = construir(cono, p, talud_global=45.0)

    with pytest.raises(RampaImposible) as e:
        trazar(construccion, p)

    mensaje = str(e.value).lower()
    assert "radio" in mensaje and "400" in mensaje


def test_la_rampa_se_come_parte_de_la_pared(cono):
    """La rampa no se dibuja encima del diseño: lo corta. Si el volumen no cambia,
    la rampa es un adorno."""
    from pitpy import disenar

    sin_rampa = disenar(cono, Parametros(**{**PARAMETROS, "trazar_rampa": False}))
    con_rampa = disenar(cono, Parametros(**PARAMETROS))

    assert con_rampa.reporte().volumen_diseno_m3 > sin_rampa.reporte().volumen_diseno_m3
    assert con_rampa.reporte().area_diseno_ha > sin_rampa.reporte().area_diseno_ha


def test_la_rampa_sale_en_el_dxf_en_su_capa(cono, tmp_path):
    from pitpy import disenar, leer_malla

    ruta = str(tmp_path / "con_rampa.dxf")
    disenar(cono, Parametros(**PARAMETROS)).a_dxf(ruta)

    assert "RAMPA" in leer_malla(ruta).capas


# --- REQ-APP-002: saber si la rampa cabe ANTES de calcular ---------------------

def test_cabe_dice_que_si_cuando_la_rampa_se_puede_trazar(cono):
    from pitpy.rampa import cabe

    entra, mensaje = cabe(cono, Parametros(**PARAMETROS))

    assert entra is True
    assert mensaje, "el texto viene siempre, también cuando cabe"


def test_cabe_dice_que_no_y_nombra_el_parametro_a_relajar(cono):
    """La App muestra este texto tal cual: sin la pista de qué aflojar, el usuario
    solo sabe que algo falló."""
    from pitpy.rampa import cabe

    entra, mensaje = cabe(cono, Parametros(**{**PARAMETROS, "radio_giro": 400.0}))

    assert entra is False
    assert "radio" in mensaje.lower() and "400" in mensaje


def test_el_texto_de_cabe_nunca_viene_vacio(cono):
    """Un `str` que a veces está vacío es una trampa: la interfaz termina con un
    `if` que nadie recuerda por qué existe. Se prometió por escrito en el REQ."""
    from pitpy.rampa import cabe

    for radio in (25.0, 400.0):
        _, mensaje = cabe(cono, Parametros(**{**PARAMETROS, "radio_giro": radio}))
        assert mensaje.strip()


def test_cuando_cabe_dice_que_si_el_diseno_completo_no_falla(cono):
    """Lo que hace útil a `cabe()` es que no mienta: si dice que sí y después el
    cálculo revienta con RampaImposible, es peor que no tenerlo."""
    from pitpy import disenar
    from pitpy.rampa import cabe

    entra, _ = cabe(cono, Parametros(**PARAMETROS))
    assert entra is True

    disenar(cono, Parametros(**PARAMETROS))     # no debe levantar RampaImposible
