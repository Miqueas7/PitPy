"""Test de regresión del motor completo.

Lo que todavía no existe va marcado xfail de a uno. A medida que se implemente,
se le quita la marca. NO relajar los números para que pasen: el archivo 4 lo
diseñó un ingeniero y es la referencia.

Al 2026-08-21 queda un solo xfail: la rampa (MOT-4).
"""
import pytest


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

    Al 2026-08-21 da 0.21 ha, que es lo que cuestan los bancos y las bermas solos.
    Estuvo brevemente en verde durante MOT-2, pero por un error de modelado —el
    diseño pintaba una berma sobre el banco más alto, que no existe— que inflaba
    la huella 0.22 ha. Corregido en MOT-3, vuelve a xfail hasta que haya rampa.
    """
    from pitpy import Parametros, disenar, leer_carcaza
    d = disenar(leer_carcaza(caso_base["suavizada"]), Parametros(**PARAMETROS_DE_YHONNY))
    assert d.reporte().sobre_area_ha == pytest.approx(0.6, abs=0.3)


def test_la_rampa_respeta_el_radio_de_giro(caso_base):
    """RecMin no lo controla. Si PitPy tampoco, no aporta nada nuevo."""
    from pitpy import Parametros, disenar, leer_carcaza
    from tests.test_rampa import radio_de_giro

    d = disenar(leer_carcaza(caso_base["suavizada"]), Parametros(**PARAMETROS_DE_YHONNY))

    assert d.rampa() is not None
    assert radio_de_giro(d.rampa().eje) >= PARAMETROS_DE_YHONNY["radio_giro"]


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


def desvio_contra_referencia(diseno, ruta_referencia, paso=2.0):
    """Mediana de la distancia entre el pie de cada banco y el contorno del
    diseño del ingeniero a esa misma cota, en metros.

    Compara PIES y no crestas a propósito: el pie es el borde de la sección del
    pit a su cota, que es lo mismo que se puede medir en el archivo 4 sin saber
    cómo lo construyó. Las crestas del archivo 4 no vienen rotuladas.
    """
    import numpy as np

    from pitpy import leer_malla
    from pitpy.superficie import Superficie, distancia_hasta

    ref = Superficie.desde_malla(leer_malla(ruta_referencia), paso)
    x0, y0 = ref.origen
    ny, nx = ref.z.shape
    distancias = []
    for banco in diseno.bancos():
        cota_pie = banco.cota - diseno.parametros.altura_banco
        seccion = ref.seccion(cota_pie)
        borde = np.zeros_like(seccion)
        borde[1:-1, 1:-1] = seccion[1:-1, 1:-1] & ~(
            seccion[:-2, 1:-1] & seccion[2:, 1:-1]
            & seccion[1:-1, :-2] & seccion[1:-1, 2:])
        campo = distancia_hasta(borde, paso, 40.0)
        for x, y, _ in banco.pie:
            j = int((x - x0) / paso)
            i = int((y - y0) / paso)
            if 0 <= i < ny and 0 <= j < nx and np.isfinite(campo[i, j]):
                distancias.append(float(campo[i, j]))
    return float(np.median(distancias)) if distancias else float("inf")


def test_los_bancos_caen_sobre_el_diseno_que_hizo_el_ingeniero(caso_base):
    """La prueba de fuego: el archivo 4 es la referencia, no una sugerencia.

    Medido el 2026-08-21: mediana 2.83 m sobre 19,292 puntos de pie. El umbral de
    4 m son dos celdas de la grilla de comparación. El p90 (8.2 m) es más alto
    porque el ingeniero tiene rampa y este diseño todavía no (MOT-4): la rampa le
    corre la pared varios metros donde pasa.
    """
    from pitpy import Parametros, disenar, leer_carcaza

    d = disenar(leer_carcaza(caso_base["suavizada"]), Parametros(**PARAMETROS_DE_YHONNY))

    assert desvio_contra_referencia(d, caso_base["disenado"]) <= 4.0


def test_la_topografia_recorta_el_diseno_del_caso_base(caso_base):
    """El caso real: terreno benigno (93 % de caras bajo 5 grados), pero no
    perfectamente plano — el diseño protrude sobre él en un puñado de celdas.

    Medido el 2026-08-21: 0.40 ha (2.1 % de la huella) con los parámetros de
    Yhonny y la rampa puesta. No es cero: confirma que incluso un terreno
    "benigno" no es plano, y por eso el recorte hace falta.
    """
    from pitpy import Parametros, disenar, leer_carcaza, leer_topografia

    d = disenar(leer_carcaza(caso_base["suavizada"]), Parametros(**PARAMETROS_DE_YHONNY),
                topografia=leer_topografia(caso_base["topografia"]))
    r = d.reporte()

    assert any("topograf" in a.lower() for a in r.advertencias)
    assert 0.05 < r.sobre_area_ha < 1.0    # sigue habiendo un numero, no cero ni disparatado


def test_el_diseno_recortado_nunca_supera_la_topografia_real(caso_base):
    """La garantía física de `topo.recortar`: ni una celda del diseño puede
    quedar por encima del terreno real donde el terreno cubre."""
    import numpy as np

    from pitpy import Parametros, disenar, leer_carcaza, leer_topografia
    from pitpy.bancos import superficie_disenada
    from pitpy.superficie import muestrear_en

    topo = leer_topografia(caso_base["topografia"])
    d = disenar(leer_carcaza(caso_base["suavizada"]), Parametros(**PARAMETROS_DE_YHONNY),
                topografia=topo)
    con = d.construccion_
    z = superficie_disenada(con)
    z_terreno = muestrear_en(topo, con.superficie.origen, con.superficie.paso, z.shape)

    cubre = ~np.isnan(z_terreno) & ~np.isnan(z)
    assert float((z[cubre] - z_terreno[cubre]).max()) < 1e-6
