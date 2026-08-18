"""Lectura y escritura de DXF de RecMin.

REGLA APRENDIDA A GOLPES
------------------------
Los DXF de RecMin son mallas de 3DFACE, NO polilíneas. Un parser que asuma
polilíneas lee datos sin sentido y NO lanza error: en el caso base devolvía 816
vértices todos a la misma cota, en vez de 84,320 repartidos en 145 m de altura.

Formato: DXF ASCII, pares (código, valor) en líneas alternas.

    0            tipo de entidad
    8            capa
    10/20/30     primera esquina  (X/Y/Z)
    11/21/31     segunda esquina   (solo 3DFACE)
    12/22/32     tercera esquina   (solo 3DFACE)
    13/23/33     cuarta esquina    (solo 3DFACE; puede repetir la 3a => triángulo)

Las isolíneas sí vienen como POLYLINE/VERTEX.
"""
from __future__ import annotations

import io
from collections import Counter

from .modelo import Carcaza, Malla, Punto

# Las 4 esquinas de un 3DFACE, en orden.
_ESQUINAS = (("10", "20", "30"), ("11", "21", "31"), ("12", "22", "32"), ("13", "23", "33"))


def leer_malla(ruta: str) -> Malla:
    """Lee un DXF y devuelve su geometría. Soporta 3DFACE y POLYLINE/VERTEX."""
    try:
        texto = io.open(ruta, encoding="latin-1", errors="ignore").read()
    except OSError as e:
        from . import DXFIlegible
        raise DXFIlegible(f"no pude abrir {ruta}: {e}") from e

    lineas = texto.split("\n")
    caras: list[list[Punto]] = []
    polilineas: list[list[Punto]] = []
    capas: Counter = Counter()

    entidad: str | None = None
    buf: dict[str, float] = {}
    poli: list[Punto] | None = None

    def cerrar_entidad() -> None:
        nonlocal buf
        if entidad == "3DFACE" and buf:
            pts = [
                (buf[cx], buf[cy], buf[cz])
                for cx, cy, cz in _ESQUINAS
                if cx in buf and cy in buf and cz in buf
            ]
            # La 4a esquina repetida significa triángulo: se descarta el duplicado.
            if len(pts) == 4 and pts[3] == pts[2]:
                pts = pts[:3]
            if len(pts) >= 3:
                caras.append(pts)
        elif entidad == "VERTEX" and poli is not None and "10" in buf:
            poli.append((buf["10"], buf.get("20", 0.0), buf.get("30", 0.0)))
        buf = {}

    for i in range(0, len(lineas) - 1, 2):
        cod = lineas[i].strip()
        val = lineas[i + 1].strip()

        if cod == "0":
            cerrar_entidad()
            if val == "POLYLINE":
                if poli:
                    polilineas.append(poli)
                poli = []
            elif val == "SEQEND":
                if poli:
                    polilineas.append(poli)
                poli = None
            entidad = val
        elif cod == "8":
            capas[val] += 1
        else:
            try:
                buf[cod] = float(val)
            except ValueError:
                pass

    cerrar_entidad()
    if poli:
        polilineas.append(poli)

    if not caras and not polilineas:
        from . import DXFIlegible
        raise DXFIlegible(
            f"{ruta} no tiene 3DFACE ni POLYLINE legibles. "
            "Los DXF binarios no están soportados: exporta en ASCII."
        )

    return Malla(caras=caras, polilineas=polilineas, capas=dict(capas), origen=ruta)


def leer_carcaza(ruta: str) -> Carcaza:
    """Lee la carcaza del pit optimizado (bruta, suavizada o isolíneas)."""
    m = leer_malla(ruta)
    return Carcaza(caras=m.caras, polilineas=m.polilineas, capas=m.capas, origen=m.origen)


def leer_topografia(ruta: str) -> Malla:
    """Lee la superficie topográfica. Es una malla como cualquier otra."""
    return leer_malla(ruta)


def escribir_diseno(diseno, ruta: str) -> None:
    """Exporta el diseño operativo a DXF.

    PENDIENTE DE IMPLEMENTAR.

    Debe escribir en capas separadas, para que se distingan al abrirlo en el CAD:

        CRESTA   la línea de cresta de cada banco
        PIE      la línea de pie de cada banco
        BERMA    la superficie de berma
        RAMPA    el eje y los bordes de la rampa
        TALUD    las caras de banco

    Yhonny abre esto en RecMin y en AutoCAD. Las capas tienen que ser legibles
    para alguien que no escribió el código: ese es el criterio de aceptación.
    """
    raise NotImplementedError(
        "Escribir por capas CRESTA/PIE/BERMA/RAMPA/TALUD. Ver docstring."
    )
