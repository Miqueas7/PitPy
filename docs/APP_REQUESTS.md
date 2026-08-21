# APP_REQUESTS — Pedidos del Motor a la App · PitPy → PitForge

> Canal del Motor hacia PitForge. Acá se escribe lo que el motor necesita **de la aplicación**:
> que adopte una firma nueva, que deje de usar una vieja, que verifique algo en la ventana real,
> que muestre una advertencia que el motor empezó a emitir.
>
> **El agente de PitPy no toca `../../PitForge/`.** Escribe el pedido acá y sigue.
> El tablero que espeja estos pedidos está en [`../../docs/ESTADO.md`](../../docs/ESTADO.md).

**Prefijo de ID:** `REQ-MOT-001`, `REQ-MOT-002`, … Numeración propia del canal, **nunca se reusa un número**.

## Cuándo abrir un REQ-MOT y cuándo no

**Sí, abre un REQ-MOT cuando:**

- Cambiaste una firma pública y la App tiene que migrar (di **qué cambió, a qué, y para cuándo**).
- Agregaste un campo a `Reporte` o una advertencia que la App debería mostrar.
- Cambiaron las etapas del callback `progreso(etapa, fraccion)` — la App tiene los textos de la barra
  mapeados uno a uno en `UI.md`.
- Necesitas que la App verifique algo que solo se ve ejecutando la ventana.

**No, esto no es un REQ-MOT:**

- Publicar una función nueva sin quitar nada. Eso va en `API_CONTRACTS.md` + `CHANGELOG.md`;
  que la App la adopte es trabajo interno suyo.
- Opinar sobre cómo se ve la interfaz. La App es dueña de sus decisiones de UI.
- Pedirle a la App que calcule algo. **Toda la geometría es tuya**, sin excepción.

## Plantilla

```
### REQ-MOT-00N — <título corto> <🔴|🟡|🟢>

**Fecha:** aaaa-mm-dd · **Prioridad:** ALTA/MEDIA/BAJA · **Estado:** 📝 Pedido
**Qué necesito de la App:** …
**Por qué:** qué cambió en el motor que lo obliga
**Antes → después:** firma vieja → firma nueva, si aplica
**Rompe si no se hace:** qué se ve mal o revienta si la App no migra
**Commit del motor:** SHA donde entró el cambio

**Respuesta de la App** — _(la escribe el agente de PitForge)_
> **Fecha:** — · **Veredicto:** — · **Conectado en:** —
```

**Regla simétrica:** la App **escribe su respuesta acá**, en el bloque **Respuesta de la App**, y
nada más. Es la única excepción a «no toques el otro repo».

---

## PENDIENTES

_(ninguno — canal creado el 2026-08-21)_

---

## COMPLETADOS

_(vacío)_
