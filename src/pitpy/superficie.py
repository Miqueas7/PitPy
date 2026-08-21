"""La superficie como grilla regular z(x, y).

Decisión 6 de docs/ARQUITECTURA.md, tomada midiendo el caso base: la carcaza se
rasteriza a celdas cuadradas y `bancos`, `topo` y `volumen` trabajan sobre eso.
El costo es la discretización (las líneas salen con precisión de media celda);
lo que se gana es que ensanchar un contorno, recortar contra la topografía y
recalcular volumen por zonas son operaciones de una línea.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from .modelo import Malla

try:
    from . import _nucleo
    NUCLEO_COMPILADO = True
except ImportError:      # instalación sin compilar: se cae a la referencia Python
    _nucleo = None
    NUCLEO_COMPILADO = False


def _triangulos(caras):
    """Los 3DFACE de RecMin traen 3 o 4 esquinas; acá todo es triángulo."""
    for c in caras:
        if len(c) == 3:
            yield c
        elif len(c) == 4:
            yield [c[0], c[1], c[2]]
            yield [c[0], c[2], c[3]]


@dataclass
class Superficie:
    """Grilla regular. `z` vale NaN donde la superficie no existe.

    El centro de la celda (i, j) está en
        x = origen[0] + (j + 0.5) * paso
        y = origen[1] + (i + 0.5) * paso
    """
    z: np.ndarray
    paso: float
    origen: tuple[float, float]

    @classmethod
    def desde_malla(cls, malla: Malla, paso: float) -> "Superficie":
        tris = np.array([t[:3] for t in _triangulos(malla.caras)], dtype=np.float64)
        if tris.size == 0:
            from . import GeometriaInvalida
            raise GeometriaInvalida(
                "la malla no tiene ninguna cara triangulable: no se puede armar "
                "la superficie. ¿Es un archivo de isolíneas? Usa la carcaza suavizada."
            )
        x0 = float(tris[:, :, 0].min())
        y0 = float(tris[:, :, 1].min())
        nx = max(1, math.ceil((float(tris[:, :, 0].max()) - x0) / paso))
        ny = max(1, math.ceil((float(tris[:, :, 1].max()) - y0) / paso))
        z = _rasterizar(tris, (x0, y0), paso, (ny, nx))
        return cls(z=z, paso=paso, origen=(x0, y0))

    def area_m2(self) -> float:
        return float(np.count_nonzero(~np.isnan(self.z))) * self.paso * self.paso

    def seccion(self, cota: float) -> np.ndarray:
        """Máscara de las celdas cuya superficie está a esa cota o por debajo."""
        return np.nan_to_num(self.z, nan=np.inf) <= cota

    def area_seccion_m2(self, mascara: np.ndarray) -> float:
        return float(np.count_nonzero(mascara)) * self.paso * self.paso

    def rango_z(self) -> tuple[float, float]:
        return (float(np.nanmin(self.z)), float(np.nanmax(self.z)))

    def contorno(self, cota: float) -> list[list[tuple]]:
        """Anillos cerrados de la sección a esa cota, del más grande al más chico."""
        return contornos(np.nan_to_num(self.z, nan=np.inf), cota, self.paso,
                         self.origen, cota)

    def contorno_de(self, campo: np.ndarray, valor: float, z: float) -> list[list[tuple]]:
        """Igual, pero sobre otro campo: el de distancia, para sacar la cresta."""
        return contornos(campo, valor, self.paso, self.origen, z)

    def contorno_de_la_huella(self) -> list[list[tuple]]:
        """Borde de la zona con superficie, con la cota real en cada punto.

        Es la silueta en planta: no depende de ninguna cota, solo de hasta dónde
        llega la carcaza.
        """
        campo = np.where(np.isnan(self.z), np.inf, 0.0)
        anillos = contornos(campo, 0.5, self.paso, self.origen, 0.0)
        return [[(x, y, self._z_cerca(x, y)) for x, y, _ in anillo] for anillo in anillos]

    def _z_cerca(self, x: float, y: float) -> float:
        """Cota de la celda con superficie más cercana al punto."""
        ny, nx = self.z.shape
        j0 = int((x - self.origen[0]) / self.paso - 0.5)
        i0 = int((y - self.origen[1]) / self.paso - 0.5)
        for radio in (0, 1, 2):
            mejor = None
            for i in range(max(0, i0 - radio), min(ny, i0 + radio + 2)):
                for j in range(max(0, j0 - radio), min(nx, j0 + radio + 2)):
                    if not math.isnan(self.z[i, j]):
                        v = float(self.z[i, j])
                        mejor = v if mejor is None else max(mejor, v)
            if mejor is not None:
                return mejor
        return float(np.nanmax(self.z))


def distancia_hasta(mascara: np.ndarray, paso: float, radio_max: float) -> np.ndarray:
    """Distancia de cada celda hasta la celda `True` más cercana, en metros.

    Vale 0 dentro de la región y se corta en `radio_max`: más allá, infinito. El
    corte no es capricho, es lo que le dice a la extracción de contornos dónde
    termina la línea.
    """
    if NUCLEO_COMPILADO:
        return _distancia_cpp(mascara, paso, radio_max)
    return _distancia_python(mascara, paso, radio_max)


def _distancia_cpp(mascara: np.ndarray, paso: float, radio_max: float) -> np.ndarray:
    if _nucleo is None:
        raise RuntimeError("el núcleo C++ no está compilado.")
    bytes_ = np.ascontiguousarray(mascara, dtype=bool).view(np.uint8)
    return _nucleo.distancia_hasta(bytes_, paso, radio_max)


def _distancia_python(mascara: np.ndarray, paso: float, radio_max: float) -> np.ndarray:
    """Referencia: fuerza bruta sobre una ventana del radio pedido.

    Exacta dentro de la ventana, pero cuesta O(celdas x offsets) y los offsets
    crecen con el cuadrado del radio. El núcleo hace lo mismo en O(celdas) con la
    transformada de distancia; tests/test_nucleo.py exige que coincidan.
    """
    r = int(math.ceil(radio_max / paso))
    d = np.where(mascara, 0.0, np.inf)
    ny, nx = mascara.shape
    for di in range(-r, r + 1):
        for dj in range(-r, r + 1):
            dist = math.hypot(di, dj) * paso
            if dist == 0.0 or dist > radio_max:
                continue
            i0, i1 = max(0, di), min(ny, ny + di)
            j0, j1 = max(0, dj), min(nx, nx + dj)
            if i0 >= i1 or j0 >= j1:
                continue
            origen = mascara[i0 - di:i1 - di, j0 - dj:j1 - dj]
            destino = d[i0:i1, j0:j1]
            np.minimum(destino, np.where(origen, dist, np.inf), out=destino)
    return d


def dilatar(mascara: np.ndarray, radio: float, paso: float) -> np.ndarray:
    """Ensancha la región `radio` metros en todas direcciones."""
    return distancia_hasta(mascara, paso, radio) <= radio


def erosionar(mascara: np.ndarray, radio: float, paso: float) -> np.ndarray:
    """Angosta la región `radio` metros. Es dilatar el complemento."""
    return ~dilatar(~mascara, radio, paso)


def cabe_circulo(mascara: np.ndarray, diametro: float, paso: float) -> bool:
    """¿Entra un círculo de ese diámetro dentro de la región?

    Es el criterio del fondo del pit (decisión 8 de ARQUITECTURA): una sección
    donde no cabe un banco completo es la punta del tazón, no un piso.
    """
    return bool(erosionar(mascara, diametro / 2.0, paso).any())


# --- extracción de contornos (marching squares) --------------------------------
#
# El borde de las celdas daría una línea en escalera del tamaño del paso. Marching
# squares interpola sobre el valor del campo y baja el error a una fracción de
# celda, que es lo que permite usar un paso grueso sin que la cresta se vea
# aserrada en el CAD.

_LADOS = ((0, 1), (1, 3), (3, 2), (2, 0))   # arriba, derecha, abajo, izquierda


def _corte(v1: float, v2: float, valor: float) -> float:
    """Dónde cruza el valor entre dos esquinas, en fracción de 0 a 1."""
    if not (math.isfinite(v1) and math.isfinite(v2)):
        return 0.5      # una esquina fuera de la superficie: al medio y seguimos
    if v2 == v1:
        return 0.5
    return min(1.0, max(0.0, (valor - v1) / (v2 - v1)))


def contornos(campo: np.ndarray, valor: float, paso: float,
              origen: tuple[float, float], z: float) -> list[list[tuple]]:
    """Anillos cerrados donde `campo` cruza `valor`. Dentro es `campo <= valor`."""
    if NUCLEO_COMPILADO:
        return _contornos_cpp(campo, valor, paso, origen, z)
    return _contornos_python(campo, valor, paso, origen, z)


def _contornos_cpp(campo: np.ndarray, valor: float, paso: float,
                   origen: tuple[float, float], z: float) -> list[list[tuple]]:
    if _nucleo is None:
        raise RuntimeError("el núcleo C++ no está compilado.")
    campo = np.ascontiguousarray(campo, dtype=np.float64)
    return _nucleo.contornos(campo, valor, paso, origen[0], origen[1], z)


def _contornos_python(campo: np.ndarray, valor: float, paso: float,
                      origen: tuple[float, float], z: float) -> list[list[tuple]]:
    """Referencia legible del marching squares. Ver _contornos_cpp."""
    # Un borde de celdas "afuera" alrededor de todo: si la región llega al borde
    # del arreglo, marching squares no ve el cruce y el anillo sale cortado. Le
    # pasó a la silueta de la carcaza, que por definición toca el borde.
    campo = np.pad(campo.astype(float), 1, constant_values=np.inf)
    ny, nx = campo.shape
    x0, y0 = origen[0] - paso, origen[1] - paso
    dentro = campo <= valor
    segmentos: list[tuple[tuple, tuple]] = []

    def punto(i: int, j: int, k1: int, k2: int) -> tuple:
        # k = 0,1,2,3 -> esquinas (i,j) (i,j+1) (i+1,j) (i+1,j+1) del cuadrado
        di1, dj1 = divmod(k1, 2)
        di2, dj2 = divmod(k2, 2)
        t = _corte(campo[i + di1, j + dj1], campo[i + di2, j + dj2], valor)
        gi = (i + di1) + t * (di2 - di1)
        gj = (j + dj1) + t * (dj2 - dj1)
        return (round(x0 + (gj + 0.5) * paso, 6), round(y0 + (gi + 0.5) * paso, 6), z)

    # Solo interesan los cuadrados donde el campo cruza el valor: son unos pocos
    # miles contra el medio millón de celdas de la grilla. Se buscan con numpy y
    # el lazo de Python recorre nada más esos.
    esquinas = (dentro[:-1, :-1].astype(np.uint8)
                | dentro[:-1, 1:].astype(np.uint8) << 1
                | dentro[1:, :-1].astype(np.uint8) << 2
                | dentro[1:, 1:].astype(np.uint8) << 3)
    for i, j in np.argwhere((esquinas != 0) & (esquinas != 15)):
        i, j = int(i), int(j)
        cruza = [(k1, k2) for k1, k2 in _LADOS
                 if dentro[i + k1 // 2, j + k1 % 2] != dentro[i + k2 // 2, j + k2 % 2]]
        if len(cruza) == 2:
            a, b = (punto(i, j, *cruza[0]), punto(i, j, *cruza[1]))
            if a != b:
                segmentos.append((a, b))
        elif len(cruza) == 4:
            # Silla de montar: se une por pares vecinos. Con qué par se une es
            # ambiguo por definición; a esta escala la diferencia es una celda.
            for par in ((0, 1), (2, 3)):
                a, b = (punto(i, j, *cruza[par[0]]), punto(i, j, *cruza[par[1]]))
                if a != b:
                    segmentos.append((a, b))

    return _encadenar(segmentos)


def _encadenar(segmentos: list[tuple[tuple, tuple]]) -> list[list[tuple]]:
    """Une los segmentos sueltos en anillos cerrados, del más grande al más chico."""
    vecinos: dict[tuple, list[tuple]] = {}
    for a, b in segmentos:
        vecinos.setdefault(a, []).append(b)
        vecinos.setdefault(b, []).append(a)

    vistos: set[tuple[tuple, tuple]] = set()
    anillos: list[list[tuple]] = []
    for a, b in segmentos:
        if (a, b) in vistos or (b, a) in vistos:
            continue
        anillo = [a, b]
        vistos.add((a, b))
        while True:
            actual, previo = anillo[-1], anillo[-2]
            siguiente = None
            for cand in vecinos.get(actual, ()):
                if cand != previo and (actual, cand) not in vistos and (cand, actual) not in vistos:
                    siguiente = cand
                    break
            if siguiente is None:
                break
            vistos.add((actual, siguiente))
            anillo.append(siguiente)
            if siguiente == anillo[0]:
                break
        if len(anillo) > 3:
            if anillo[0] != anillo[-1]:
                anillo.append(anillo[0])   # cierre forzado: el anillo se cortó en un borde
            anillos.append(anillo)

    anillos.sort(key=_area_anillo, reverse=True)
    return anillos


def _area_anillo(anillo: list[tuple]) -> float:
    a = 0.0
    for (x1, y1, _), (x2, y2, _) in zip(anillo, anillo[1:]):
        a += x1 * y2 - x2 * y1
    return abs(a) / 2.0


# --- rasterizado: núcleo C++ y su referencia en Python -------------------------
#
# La versión de Python NO es código muerto. Es el oráculo contra el que
# tests/test_nucleo.py compara la extensión: si el kernel C++ se desvía aunque
# sea en una celda, el test lo agarra. También es la red si alguien instala el
# paquete desde el sdist sin compilador.


def _rasterizar(tris: np.ndarray, origen: tuple[float, float], paso: float,
                forma: tuple[int, int]) -> np.ndarray:
    """Rasteriza por el camino rápido si hay núcleo compilado."""
    if NUCLEO_COMPILADO:
        return _rasterizar_cpp(tris, origen, paso, forma)
    return _rasterizar_python(tris, origen, paso, forma)


def _rasterizar_cpp(tris: np.ndarray, origen: tuple[float, float], paso: float,
                    forma: tuple[int, int]) -> np.ndarray:
    if _nucleo is None:
        raise RuntimeError(
            "el núcleo C++ no está compilado. Reinstala con `pip install -e .` "
            "(necesita un compilador de C++20) o usa _rasterizar_python."
        )
    ny, nx = forma
    return _nucleo.rasterizar(np.ascontiguousarray(tris, dtype=np.float64),
                              origen[0], origen[1], paso, ny, nx)


def _rasterizar_python(tris: np.ndarray, origen: tuple[float, float], paso: float,
                       forma: tuple[int, int]) -> np.ndarray:
    """Referencia legible. Misma fórmula, mismas tolerancias, mismo redondeo.

    Si se toca esto, hay que tocar include/pitpy/rasterizar.hpp igual, o el test
    diferencial cae. Es a propósito: la que se lee para entender la geometría es
    esta.
    """
    ny, nx = forma
    x0, y0 = origen
    z = np.full((ny, nx), np.nan)
    for t in tris:
        (ax, ay, az), (bx, by, bz), (cx, cy, cz) = t
        det = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy)
        if det == 0:
            continue   # triángulo degenerado en planta: no aporta cota
        j0 = max(0, int((min(ax, bx, cx) - x0) / paso) - 1)
        j1 = min(nx - 1, int((max(ax, bx, cx) - x0) / paso) + 1)
        i0 = max(0, int((min(ay, by, cy) - y0) / paso) - 1)
        i1 = min(ny - 1, int((max(ay, by, cy) - y0) / paso) + 1)
        for i in range(i0, i1 + 1):
            py = y0 + (i + 0.5) * paso
            for j in range(j0, j1 + 1):
                px = x0 + (j + 0.5) * paso
                w1 = ((by - cy) * (px - cx) + (cx - bx) * (py - cy)) / det
                w2 = ((cy - ay) * (px - cx) + (ax - cx) * (py - cy)) / det
                w3 = 1.0 - w1 - w2
                if w1 < -1e-9 or w2 < -1e-9 or w3 < -1e-9:
                    continue
                zc = w1 * az + w2 * bz + w3 * cz
                # La cota más baja: la carcaza es un tazón y lo que interesa es el
                # piso, no un techo si lo hubiera.
                if math.isnan(z[i, j]) or zc < z[i, j]:
                    z[i, j] = zc
    return z
