"""Interfaz de línea de comandos.

Es para ITERAR DURANTE EL DESARROLLO, no para Yhonny: él nunca programó y su
interfaz es PitForge. Pero tener CLI hace que el motor se pueda probar sin
levantar la app, y eso acelera todo.

    pitpy disenar --carcaza suavizada.dxf --topografia topo.dxf \
                  --banco 10 --berma 6 --rampa-ancho 12 \
                  --rampa-pendiente 10 --radio-giro 25 \
                  --salida pit_v1.dxf

    pitpy inspeccionar carcaza.dxf     # qué trae el archivo y qué talud detecta
"""
from __future__ import annotations

import argparse
import sys


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="pitpy", description=__doc__)
    sub = ap.add_subparsers(dest="comando", required=True)

    insp = sub.add_parser("inspeccionar", help="qué trae un DXF y qué talud detecta")
    insp.add_argument("archivo")

    dis = sub.add_parser("disenar", help="genera el pit operativo")
    dis.add_argument("--carcaza", required=True)
    dis.add_argument("--topografia")
    dis.add_argument("--banco", type=float, required=True, help="altura de banco, m")
    dis.add_argument("--berma", type=float, required=True, help="ancho de berma, m")
    dis.add_argument("--talud", type=float, help="grados; si se omite, se detecta")
    dis.add_argument("--rampa-ancho", type=float, required=True)
    dis.add_argument("--rampa-pendiente", type=float, required=True, help="en %%")
    dis.add_argument("--radio-giro", type=float, required=True)
    dis.add_argument("--ancho-fondo", type=float, help="mínimo; si se omite, sin restricción")
    dis.add_argument("--forzar-ancho-fondo", action="store_true")
    dis.add_argument("--salida", required=True)

    args = ap.parse_args(argv)

    if args.comando == "inspeccionar":
        from .dxf import leer_malla
        from .taludes import detectar_talud
        m = leer_malla(args.archivo)
        zmin, zmax = m.rango_z()
        ancho, largo = m.extension()
        print(f"caras 3DFACE : {len(m.caras):,}")
        print(f"polilíneas   : {len(m.polilineas):,}")
        print(f"extensión    : {ancho:,.0f} x {largo:,.0f} m")
        print(f"cotas        : {zmin:,.1f} a {zmax:,.1f}  (desnivel {zmax - zmin:,.0f} m)")
        print(f"capas        : {m.capas}")
        if m.caras:
            t = detectar_talud(m)
            variable = " (parece VARIABLE)" if t.es_variable else ""
            print(f"talud        : mediana {t.mediana} grados  "
                  f"[p10 {t.p10} - p90 {t.p90}]{variable}")
        return 0

    raise NotImplementedError("`disenar` espera a que el motor esté implementado")


if __name__ == "__main__":
    sys.exit(main())
