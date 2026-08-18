# Especificación funcional — PitPy

> Fuente: Ing. **Yhonny Ruiz**, instructor oficial de RecMin (SOLMINE), en
> conversación del 17 de agosto de 2026. Las citas son textuales.

---

## 1. El problema, en sus palabras

> «Para mí una gran oportunidad está en el diseño operativo del PIT. Hoy existen
> varios softwares y algoritmos, incluso gratuitos, que optimizan rápidamente y
> generan una corta a partir de un modelo de bloques. El cuello de botella muchas
> veces viene luego: convertir esa optimización en un diseño geométrico realmente
> operativo. **De poco sirve optimizar rápido si luego diseñar bancos, bermas,
> rampas, etc., toma bastante tiempo** y al final solo puedes evaluar uno o pocos
> diseños.»

El valor no es acelerar un paso. Es **cuántas alternativas se pueden comparar**.

---

## 2. Entrada

### 2.1 Qué formato

> «Considero que **partir desde la carcaza sería mejor** que importar el modelo de
> bloques optimizado a la nueva aplicación, ya que con bloques puede que resulte
> más complicado.»

RecMin exporta la carcaza del pit optimizado en tres formas, y las tres se
recibieron en el caso base:

| Forma | Qué es | Utilidad |
|---|---|---|
| **En bruto** | Escalera de bloques: paredes verticales y techos planos | Muestra la resolución del modelo de bloques |
| **Suavizada** (mallas/mesh) | Superficie continua al ángulo de talud | **Entrada principal sugerida** |
| **Isolíneas** | Curvas por cota, «no suavizadas sino con efecto serrucho» | Muy liviana; requiere suavizado previo |

> «Al final, DXF, TXT o CSV son formatos bastante universales y facilitarían esa
> interoperabilidad y tendrías más usuarios interesados.»

**No atar la herramienta a RecMin.** Es una instrucción explícita.

### 2.2 Topografía

Se recibe como malla aparte. Ver sección 6.

---

## 3. Taludes

### 3.1 La pregunta que dejó abierta

> «No sé si sería necesario volver a introducir esos parámetros o si, teniendo la
> carcaza optimizada como guía, la aplicación podría **deducir o reconocer los
> taludes globales variables** y generar el PIT operativo siguiendo esa geometría.
> Esto último sería muy interesante.»

**RESUELTO: se puede deducir.** Ver `CASO_BASE.md` — midiendo el ángulo de cada
cara de la malla, la carcaza suavizada del caso base arroja mediana 48.2° con el
68 % de las caras entre 45° y 50°, que es el talud global de 45° que él declaró.

Para taludes variables, el mismo cálculo se aplica segmentando las caras por
azimut y por rango de cota.

**Decisión de diseño:** auto-detectar y **mostrar** el valor al usuario para que
lo confirme o lo corrija. No obligarlo a tipear lo que el archivo ya sabe, pero
tampoco decidir en silencio.

### 3.2 Taludes variables (v2)

> «Que la aplicación pueda reconocer si el ángulo de la carcaza es único o
> variable, o que permita al usuario introducir **una roseta de ángulos**. Por
> ejemplo: de 0° a 90°, talud de 45°; de 90° a 270°, otro determinado ángulo.
> Incluso podría definirse **por elevación**: desde la cota A hasta la cota B, un
> determinado ángulo. Que es lo habitual o lo que interesa a muchos.»

Contexto que dio: los pits complejos se diseñan con rosetas de taludes y pueden
tener ángulos distintos según profundidad, elevación o sector — «un ángulo en la
zona profunda y otro cerca de superficie, es lo habitual».

---

## 4. Bancos y bermas

| Parámetro | v1 | v2 |
|---|---|---|
| Altura de banco | constante, configurable | variable |
| Ancho de berma | constante, configurable | **variable** — «no necesariamente tiene que ser constante y puede depender del ángulo de talud o del sector» |

El ancho de berma variable lo pidió explícitamente para v1, pero se difiere: sin
el caso constante funcionando, el variable no se puede validar.

---

## 5. Rampa

### 5.1 v1

> «Para una primera versión pienso que se podría comenzar con **una sola rampa**.
> Pedirle al nuevo algoritmo que determine automáticamente cuántas rampas son
> necesarias ya sería bastante más complejo.»

Parámetros básicos:

| Parámetro | Nota |
|---|---|
| Ancho | 12 m en el caso base, «porque es un tajo pequeño» |
| Pendiente | 10 % en el caso base, «es un valor que puede variar» |
| Radio mínimo de giro | **RecMin no lo permite como parámetro.** «En la práctica, uno va estirando o acomodando la banqueta para generar suficiente espacio para que el camión pueda girar. Supongo la aplicación deberá considerarlo.» |

El radio de giro es una **ventaja competitiva**: RecMin no lo tiene.

### 5.2 v2

- Varias rampas, decididas por el algoritmo.
- Rampa de un carril desde cierta cota hacia el fondo y de dos carriles desde
  ahí hasta superficie.

---

## 6. Topografía

Dos niveles, y él mismo los ordenó:

**Suficiente:** diseñar el pit uno o dos bancos por encima de la cota máxima de
la topografía y recortarlo después con cualquier software (booleano).

**Mucho mejor:** que la aplicación entregue directamente el diseño ya limitado
por la topografía.

### 6.1 La función estrella

> «Algo que me parecería especialmente potente sería poder **indicar por qué
> sector queremos que salga la rampa** cuando intercepte la topografía. Muchas
> veces buscamos que la rampa salga por la cota más baja o por el sector más
> conveniente para conectarla posteriormente con caminos o accesos existentes. Si
> pudiéramos señalar aproximadamente la zona de salida y que el algoritmo diseñe
> la rampa buscando llegar allí, **eso sería un boom**.»

Es v2, pero es la función que vuelve la herramienta indispensable. La
arquitectura no debe cerrarle la puerta.

---

## 7. Ancho mínimo del fondo — criterio importante

> «Si el fondo de la carcaza optimizada queda demasiado angosto, **prefiero perder
> algunos bloques antes que ensanchar artificialmente el PIT** únicamente para
> alcanzar un ancho mínimo de minado. Forzar ese ancho puede desplazar las paredes
> finales y terminar incorporando una cantidad considerable de estéril adicional.»

> «Cuando es posible, en mis diseños intento conservar los bloques económicos del
> último banco, pero sin necesariamente llevar la rampa hasta el fondo.
> Dependiendo de la geometría y de los equipos disponibles, esos bloques podrían
> recuperarse, por ejemplo, con una excavadora de brazo largo trabajando desde el
> banco superior.»

**Por lo tanto: el ancho mínimo de fondo es un parámetro CONFIGURABLE, no una
restricción obligatoria.** La herramienta debe permitir desactivarlo y reportar
qué se gana y qué se pierde en cada caso.

---

## 8. Idea alternativa de flujo (v2/v3)

Segundo mensaje, textual:

> «Que el algoritmo suavice la carcaza en una primera etapa sin rampa y luego en
> una segunda etapa darle indicaciones o puntos por donde hacer la rampa, y el
> algoritmo con esa guía de rampa entienda y **desplace las paredes dinámicamente
> y me vaya informando en tiempo real cuánto volumen está aumentando el Pit** si
> se hiciera por ese lado la rampa. Y en el proceso uno se detenga y diga: esto
> quiero, con esto me quedo.»

Un flujo interactivo con retroalimentación de volumen en vivo. Es lo que
convierte la herramienta en algo que nadie más ofrece. La arquitectura debe
permitir recalcular volúmenes de forma incremental.

---

## 9. Estándar de calidad

> «Esta última no pretende ser un diseño definitivo de ingeniería, porque
> normalmente yo trabajo este tipo de diseños para etapas preliminares o informes
> tipo PEA.»

El listón es **"sirve para un PEA"**, no "reemplaza a un ingeniero de diseño de
detalle". No sobre-construir.

---

## 10. Resumen del alcance

### v1 — construir esto
- [ ] Una carcaza, un talud global (auto-detectado y editable)
- [ ] Altura de banco y ancho de berma constantes
- [ ] Una rampa: ancho, pendiente, radio mínimo de giro
- [ ] Ancho mínimo de fondo configurable y desactivable
- [ ] Recorte contra topografía
- [ ] Salida DXF + reporte de volúmenes (sobre-estéril de cada decisión)

### v2 — no ahora
- [ ] Roseta de taludes por azimut y por cota
- [ ] Berma y altura de banco variables
- [ ] Varias rampas; un carril al fondo, dos a superficie
- [ ] Selección interactiva del sector de salida de la rampa
- [ ] Volumen en tiempo real durante el trazado
