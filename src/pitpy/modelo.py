"""Tipos del dominio. Sin lógica: solo datos.

Los nombres están en español a propósito — el vocabulario del dominio es el del
ingeniero de minas, y traducirlo a inglés solo agrega una capa de traducción
mental para quien lea el código.
"""
from __future__ import annotations

from dataclasses import dataclass, field

Punto = tuple[float, float, float]


@dataclass
class Malla:
    """Superficie triangulada leída de un DXF.

    caras: cada una es una lista de 3 o 4 puntos (los 3DFACE de RecMin traen 4,
    a veces con la última esquina repetida = triángulo).
    """
    caras: list[list[Punto]] = field(default_factory=list)
    polilineas: list[list[Punto]] = field(default_factory=list)
    capas: dict[str, int] = field(default_factory=dict)
    origen: str = ""

    @property
    def puntos(self) -> list[Punto]:
        return [p for c in self.caras for p in c] + [p for pl in self.polilineas for p in pl]

    def rango_z(self) -> tuple[float, float]:
        zs = [p[2] for p in self.puntos]
        return (min(zs), max(zs)) if zs else (0.0, 0.0)

    def extension(self) -> tuple[float, float]:
        pts = self.puntos
        if not pts:
            return (0.0, 0.0)
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        return (max(xs) - min(xs), max(ys) - min(ys))


@dataclass
class Carcaza(Malla):
    """Carcaza de pit optimizado. Puede venir en bruto, suavizada o como isolíneas."""

    @classmethod
    def desde_dxf(cls, ruta: str) -> "Carcaza":
        from .dxf import leer_carcaza
        return leer_carcaza(ruta)

    def talud_detectado(self) -> float:
        """Atajo: mediana del ángulo de las caras, en grados."""
        from .taludes import detectar_talud
        return detectar_talud(self).mediana


@dataclass(frozen=True)
class Parametros:
    """Geometría pedida. Ver docs/API_CONTRACTS.md."""
    altura_banco: float                      # m
    ancho_berma: float                       # m
    rampa_ancho: float                       # m
    rampa_pendiente: float                   # fracción: 0.10 = 10 %
    radio_giro: float                        # m, mínimo
    talud_global: float | None = None        # grados; None => auto-detectar
    ancho_fondo_minimo: float | None = None  # None => sin restricción
    forzar_ancho_fondo: bool = False         # ver ESPECIFICACION §7
    bancos_sobre_topografia: int = 2

    def __post_init__(self) -> None:
        if self.altura_banco <= 0:
            raise ValueError("la altura de banco debe ser positiva")
        if self.ancho_berma < 0:
            raise ValueError("el ancho de berma no puede ser negativo")
        if not 0 < self.rampa_pendiente < 0.5:
            raise ValueError("la pendiente de rampa se expresa como fracción (0.10 = 10 %)")


@dataclass
class TaludDetectado:
    mediana: float
    p10: float
    p90: float
    es_variable: bool
    por_sector: dict = field(default_factory=dict)   # azimut -> grados (v2)


@dataclass
class Banco:
    """Un banco: su cota, la cresta y el pie."""
    cota: float
    cresta: list[Punto] = field(default_factory=list)
    pie: list[Punto] = field(default_factory=list)


@dataclass
class Rampa:
    eje: list[Punto] = field(default_factory=list)
    ancho: float = 0.0
    pendiente: float = 0.0

    @property
    def longitud(self) -> float:
        import math
        return sum(
            math.dist(a, b) for a, b in zip(self.eje, self.eje[1:])
        ) if len(self.eje) > 1 else 0.0


@dataclass
class Reporte:
    area_carcaza_ha: float = 0.0
    area_diseno_ha: float = 0.0
    sobre_area_ha: float = 0.0
    volumen_carcaza_m3: float = 0.0
    volumen_diseno_m3: float = 0.0
    sobre_esteril_m3: float = 0.0
    bancos: int = 0
    cota_fondo: float = 0.0
    cota_cresta: float = 0.0
    longitud_rampa_m: float = 0.0
    advertencias: list[str] = field(default_factory=list)


@dataclass
class Diseno:
    """Resultado: la geometría operativa lista para exportar."""
    bancos_: list[Banco] = field(default_factory=list)
    rampa_: Rampa | None = None
    carcaza: Carcaza | None = None
    parametros: Parametros | None = None

    def bancos(self) -> list[Banco]:
        return self.bancos_

    def rampa(self) -> Rampa | None:
        return self.rampa_

    def reporte(self) -> Reporte:
        from .volumen import calcular
        return calcular(self)

    def a_dxf(self, ruta: str) -> None:
        from .dxf import escribir_diseno
        escribir_diseno(self, ruta)
