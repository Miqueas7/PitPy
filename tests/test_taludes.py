"""Detección de taludes: el método que ya está validado."""
import pytest

from pitpy.dxf import leer_malla
from pitpy.taludes import (angulo_cara, cara_banco_desde_global,
                           detectar_talud, talud_global_desde_banco)


def test_la_geometria_del_caso_base_cierra():
    """Banco 10 m + cara 68 grados + berma 6 m = 45 grados global.

    Yhonny declaró el talud global de 45 y la berma de 6, pero NO la cara de
    banco. Que el ángulo medido en su diseño (65-70) cierre con su berma es lo
    que confirma que el caso base es coherente.
    """
    assert talud_global_desde_banco(10.0, 68.0, 6.0) == pytest.approx(44.9, abs=0.1)


def test_ida_y_vuelta_entre_cara_y_global():
    cara = cara_banco_desde_global(10.0, 45.0, 6.0)
    assert talud_global_desde_banco(10.0, cara, 6.0) == pytest.approx(45.0, abs=0.01)


def test_berma_imposible_avisa_que_relajar():
    from pitpy import GeometriaInvalida
    with pytest.raises(GeometriaInvalida, match="berma"):
        cara_banco_desde_global(altura_banco=10.0, talud_global=30.0, ancho_berma=20.0)


def test_cara_horizontal_da_cero_grados():
    assert angulo_cara([(0, 0, 0), (10, 0, 0), (0, 10, 0)]) == pytest.approx(0.0)


def test_cara_vertical_da_noventa():
    assert angulo_cara([(0, 0, 0), (10, 0, 0), (0, 0, 10)]) == pytest.approx(90.0)


def test_detecta_los_45_grados_de_la_carcaza_suavizada(caso_base):
    """El resultado que responde la pregunta de Yhonny: SÍ se puede deducir."""
    t = detectar_talud(leer_malla(caso_base["suavizada"]))
    assert t.mediana == pytest.approx(48.2, abs=0.5)
    assert not t.es_variable


def test_la_carcaza_bruta_es_una_escalera(caso_base):
    """Sin ignorar las planas, la bruta da 90 grados: paredes verticales."""
    t = detectar_talud(leer_malla(caso_base["bruta"]), ignorar_planas=False)
    assert t.mediana == pytest.approx(90.0, abs=1.0)


def test_isolineas_sin_caras_da_error_claro(caso_base):
    from pitpy import GeometriaInvalida
    with pytest.raises(GeometriaInvalida, match="isolíneas|inclinadas"):
        detectar_talud(leer_malla(caso_base["isolineas"]))
