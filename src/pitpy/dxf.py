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


# --- escritura -----------------------------------------------------------------

# Colores del CAD (índice ACI). No es decoración: el criterio de aceptación de la
# etapa 3 es que las capas SE DISTINGAN al abrir el archivo, y un DXF donde todo
# sale del mismo color no se distingue aunque las capas estén bien puestas.
_CAPAS = {
    "CRESTA": 1,   # rojo
    "PIE": 3,      # verde
    "RAMPA": 2,    # amarillo
    # BERMA y TALUD van a existir cuando se escriba la malla de superficie. Ver
    # la nota de escribir_diseno().
}


def escribir_diseno(diseno, ruta: str, paso_salida: float = 5.0) -> None:
    """Exporta el diseno operativo a DXF: las lineas de diseno, en capas separadas.

    Capas: `CRESTA` y `PIE`, una polilinea 3D cerrada por banco, cada una con su
    color para que se distingan al abrir el archivo. `RAMPA` cuando exista.

    **Las capas de superficie (`BERMA` y `TALUD`) NO se escriben todavia**, y es a
    proposito. Tejer una malla entre el pie y la cresta de cada banco parece
    directo y no lo es: los dos anillos salen de una grilla, tienen distinta
    cantidad de vertices y distinta forma local, y pareandolos por longitud de arco
    la cinta se corta en diagonal. Medido sobre el caso base: la malla sumaba 23.4
    ha de caras para un diseno de 19.2 ha, o sea 4 ha de caras montadas unas sobre
    otras, y la firma de angulos salia con caras de 85 grados que en el diseno no
    existen. Un DXF asi se abre y se ve mal, que es peor que no tenerlo. Hacerlo
    bien pide emparejar los anillos por cercania con restriccion de monotonia, o
    triangular la superficie completa; queda anotado en el ROADMAP.

    Las lineas alcanzan para lo que hay que hacer ahora: superponerlas sobre el
    diseno del ingeniero y comparar. Es ademas como se intercambian los disenos de
    pit en la practica.

    `paso_salida` es cada cuantos metros se deja un vertice. Por omision 5 m: las
    lineas salen de una grilla de 1 m y dejarlas asi son 2,000 vertices por banco,
    mucho mas densos que cualquier linea dibujada a mano. El remuestreo ademas
    saca la ondulacion de tamano de celda que traen los contornos de la grilla.
    """
    partes: list[str] = []
    _encabezado(partes, diseno)

    for banco in diseno.bancos():
        _polilinea(partes, _remuestrear(banco.pie, _puntos(banco.pie, paso_salida)), "PIE")
        _polilinea(partes, _remuestrear(banco.cresta, _puntos(banco.cresta, paso_salida)),
                   "CRESTA")

    rampa = diseno.rampa()
    if rampa is not None and rampa.eje:
        _polilinea(partes, rampa.eje, "RAMPA")

    partes.append(_par(0, "ENDSEC") + _par(0, "EOF"))
    io.open(ruta, "w", encoding="latin-1", newline="\r\n").write("".join(partes))


def _remuestrear(anillo: list, n: int) -> list:
    """Reparte n puntos equiespaciados en longitud de arco sobre el anillo.

    Dos cosas de una: deja los dos anillos de una cinta con la misma cantidad de
    puntos —para poder tejerlos de a pares— y suaviza la ondulación de celda que
    traen los contornos de la grilla. Una línea de diseño con un vértice cada
    metro y dientes de medio metro no es lo que dibuja un ingeniero.
    """
    import math

    if len(anillo) < 4 or n < 4:
        return anillo
    acumulado = [0.0]
    for p, q in zip(anillo, anillo[1:]):
        acumulado.append(acumulado[-1] + math.dist(p[:2], q[:2]))
    total = acumulado[-1]
    if total <= 0:
        return anillo

    salida = []
    j = 0
    for k in range(n):
        objetivo = total * k / n
        while j < len(acumulado) - 2 and acumulado[j + 1] < objetivo:
            j += 1
        tramo = acumulado[j + 1] - acumulado[j]
        t = 0.0 if tramo <= 0 else (objetivo - acumulado[j]) / tramo
        p, q = anillo[j], anillo[j + 1]
        salida.append((p[0] + t * (q[0] - p[0]),
                       p[1] + t * (q[1] - p[1]),
                       p[2] + t * (q[2] - p[2])))
    salida.append(salida[0])
    return salida


def _puntos(anillo: list, paso_salida: float) -> int:
    """Cuantos vertices darle a un anillo: uno cada `paso_salida` metros."""
    import math

    largo = sum(math.dist(p[:2], q[:2]) for p, q in zip(anillo, anillo[1:]))
    return max(8, int(round(largo / paso_salida)))


def _par(codigo: int, valor) -> str:
    """Un par (código, valor) del DXF: dos líneas."""
    return "{}\n{}\n".format(codigo, valor)


def _encabezado(partes: list, diseno) -> None:
    """Tabla de capas con su color, y apertura de la sección de entidades."""
    capas = ["CRESTA", "PIE"]
    if diseno.rampa() is not None:
        capas.append("RAMPA")
    partes.append(_par(0, "SECTION") + _par(2, "TABLES")
                  + _par(0, "TABLE") + _par(2, "LAYER") + _par(70, len(capas)))
    for capa in capas:
        partes.append(_par(0, "LAYER") + _par(2, capa) + _par(70, 0)
                      + _par(62, _CAPAS[capa]) + _par(6, "CONTINUOUS"))
    partes.append(_par(0, "ENDTAB") + _par(0, "ENDSEC")
                  + _par(0, "SECTION") + _par(2, "ENTITIES"))


def _polilinea(partes: list, puntos: list, capa: str) -> None:
    if len(puntos) < 2:
        return
    partes.append(_par(0, "POLYLINE") + _par(8, capa) + _par(66, 1) + _par(70, 8)
                  + _par(10, "0.0") + _par(20, "0.0") + _par(30, "0.0"))
    for x, y, z in puntos:
        partes.append(_par(0, "VERTEX") + _par(8, capa)
                      + _par(10, "{:.4f}".format(x))
                      + _par(20, "{:.4f}".format(y))
                      + _par(30, "{:.4f}".format(z)) + _par(70, 32))
    partes.append(_par(0, "SEQEND") + _par(8, capa))
