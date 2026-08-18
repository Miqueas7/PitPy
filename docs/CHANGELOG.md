# Bitácora — PitPy

Formato: una entrada por sesión, con **Reporte de Cierre** (qué se hizo, qué se
verificó, qué quedó pendiente).

---

## 2026-08-17 — Andamiaje inicial

**Qué se hizo**
- Se creó el repositorio con su estructura y documentación completa.
- Se documentó la especificación funcional a partir de la conversación con el
  Ing. Yhonny Ruiz (`docs/ESPECIFICACION.md`), con citas textuales.
- Se analizaron los 5 archivos DXF del caso base y se midió su geometría
  (`docs/CASO_BASE.md`).
- Se implementó `pitpy.dxf`: lector de mallas 3DFACE y de polilíneas.

**Qué se verificó**
- El lector se probó contra los 5 archivos reales: 20,876 / 18,703 / 21 / 5,923
  / 7,220 entidades respectivamente.
- Se confirmó que el talud global de 45° declarado por Yhonny es detectable desde
  la malla: mediana 48.2°, con 68 % de caras entre 45° y 50°.
- Se verificó la consistencia geométrica del caso base: banco 10 m + cara 68° +
  berma 6 m = 44.9° global ≈ los 45° declarados.

**Qué quedó pendiente**
- Todo el motor salvo la lectura: `taludes`, `bancos`, `rampa`, `topo`, `volumen`.
- Decidir la representación interna de la superficie (ver ARQUITECTURA).
- Los tests del caso base están escritos pero la mayoría marcados `xfail`.

**Nota para quien siga**
Empezar por `taludes` — el método ya está validado, solo falta empaquetarlo. Es
la victoria más rápida y desbloquea `bancos`.
