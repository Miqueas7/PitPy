"""Los archivos del caso base no se versionan (10 MB). Se buscan por entorno.

    set PITPY_CASO_BASE=C:/Users/mique/OneDrive/TRABAJOS/Yhonny Ruiz - Recmin

Si la variable no está, los tests que dependen de ellos se saltan en vez de
fallar: así el repo sigue siendo clonable por cualquiera.
"""
import os

import pytest

ARCHIVOS = {
    "bruta": "Miqueas 1_Carcaza bruta total.dxf",
    "suavizada": "Miqueas 2_Carcaza suavizada.dxf",
    "isolineas": "Miqueas 3_Carcaza Isolineas.dxf",
    "disenado": "Miqueas 4_Pit Geometric Diseñado.dxf",
    "topografia": "Miqueas 5_Topografia.dxf",
}


@pytest.fixture(scope="session")
def caso_base():
    carpeta = os.environ.get("PITPY_CASO_BASE")
    if not carpeta or not os.path.isdir(carpeta):
        pytest.skip("PITPY_CASO_BASE no apunta a la carpeta del caso base")
    rutas = {k: os.path.join(carpeta, v) for k, v in ARCHIVOS.items()}
    faltan = [k for k, r in rutas.items() if not os.path.isfile(r)]
    if faltan:
        pytest.skip(f"faltan archivos del caso base: {faltan}")
    return rutas
