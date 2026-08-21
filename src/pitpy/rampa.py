"""Trazado de la rampa sobre la pared del pit.

POR QUÉ ESTE MÓDULO ES EL QUE IMPORTA
-------------------------------------
El radio de giro es la ventaja competitiva. RecMin no lo admite como parámetro:
hoy se resuelve a ojo, estirando la banqueta hasta que el camión entre. Si PitPy
respeta el radio de verdad, hace algo que la herramienta que ellos usan no hace.

CÓMO SE TRAZA (v1, ROADMAP §Etapa 4)
------------------------------------
Helicoidal simple: se sube por la pared a pendiente constante, dando vueltas
alrededor del pit. Para cada paso se busca dónde está la pared a la cota que toca
—un rayo desde el centro del pit hacia afuera hasta cruzar esa cota— y ahí va el
eje. La cota se reparte al final por longitud de arco real, así la pendiente sale
exacta y no aproximada.

LA RAMPA NO SIEMPRE LLEGA AL FONDO, Y ESTÁ BIEN
-----------------------------------------------
Cerca del piso el pit mide dos o tres decenas de metros: ninguna rampa gira ahí
con un radio de 25 m. Así que la rampa arranca en el nivel más bajo donde el
radio pedido entra de verdad, y se avisa por escrito hasta dónde llega. No es una
limitación del programa: es lo que hace Yhonny, que lo dijo con todas las letras
—«sin necesariamente llevar la rampa hasta el fondo… esos bloques podrían
recuperarse con una excavadora de brazo largo trabajando desde el banco
superior»— (ESPECIFICACION §7).

Forzar la espiral hasta el piso da una curva de 6 m de radio, que en el papel se
ve como una rampa y en la mina no la toma ningún camión.

**No se hace búsqueda de rutas.** Es lo que dice el ROADMAP y hay una razón:
puede que no haga falta, y es un pozo de tiempo. Elegir por qué sector sale la
rampa es v2 —«eso sería un boom», dijo Yhonny— y esto no lo elige: arranca en un
azimut fijo. Está declarado, no escondido.

LO QUE LA RAMPA LE HACE AL DISEÑO
---------------------------------
No se dibuja encima: **corta**. La plataforma se hunde en la pared, y todo lo que
queda por encima tiene que retirarse al talud global o quedaría en voladizo. Ese
retiro es el que empuja las paredes hacia afuera, y es de donde sale la mayor
parte del sobre-estéril que la herramienta existe para medir.
"""
from __future__ import annotations

import math

import numpy as np

from .modelo import Parametros, Rampa

# Cada cuántos metros se pone un punto del eje. Cinco: más fino no cambia el
# trazado (la pared se resuelve a 1 m) y hace lento el control de radio, que
# mira ternas de puntos consecutivos.
PASO_EJE = 5.0

# Cuántas pasadas de suavizado se admiten antes de declarar que el radio pedido
# no entra. Cada pasada redondea las curvas un poco; si después de estas el radio
# sigue sin cumplir, es que el pit es demasiado chico para ese giro.
PASADAS_DE_SUAVIZADO = 300

# Solo para redactar la sugerencia del error: si con la pendiente pedida no entra
# el radio, bajarla alarga el desarrollo y abre las curvas.
PENDIENTE_REFERENCIA = 0.10
PENDIENTE_SUAVE = 0.08

# Fracciones de la pendiente pedida con las que se intenta trazar. Trazar más
# tendido da una espiral más larga, que después del suavizado queda más larga
# también, y es lo que permite llegar a la salida. La pendiente FINAL siempre es
# la que pidió el usuario: esto es solo la traza.
FACTORES_DE_TRAZA = (1.0, 0.85, 0.7, 0.6, 0.5, 0.4)


def trazar(construccion, parametros: Parametros) -> Rampa:
    """Traza la rampa desde el fondo hasta la cresta.

    Raises:
        RampaImposible: si no se puede con esos parámetros. El mensaje dice qué
            aflojar, porque es el error que más va a ver el usuario.
    """
    from . import RampaImposible
    from .bancos import superficie_de_bancos

    superficie = construccion.superficie
    z = superficie_de_bancos(construccion)
    fondo = construccion.fondo
    cresta = construccion.cotas[-1]
    desnivel = cresta - fondo
    largo_necesario = desnivel / parametros.rampa_pendiente

    arranque = _cota_de_arranque(construccion, parametros.radio_giro)
    if arranque is None:
        raise RampaImposible(
            f"con un radio de giro de {parametros.radio_giro:.0f} m no entra una "
            f"rampa en ningún nivel de este pit: ni siquiera arriba, en la cota "
            f"{cresta:.0f}, la sección da para una curva de ese radio. Reduce el "
            f"radio de giro."
        )
    desnivel = cresta - arranque
    largo_necesario = desnivel / parametros.rampa_pendiente

    anillos = _anillos(construccion)

    # Suavizar las curvas se come las esquinas y con eso acorta el desarrollo, y
    # una rampa más corta no llega a la cresta con la pendiente pedida. Se traza,
    # se suaviza, se mide, y si quedó corta se vuelve a trazar con la pendiente
    # ajustada. Converge en dos o tres vueltas.
    # Suavizar para cumplir el radio se come las esquinas y acorta el desarrollo
    # —hasta un 30 % medido—, y una rampa corta no llega a la salida. La cuenta
    # obvia sería trazar con la pendiente reducida en esa misma proporción, pero
    # el acortamiento NO es proporcional: medido en el caso base, trazar al 8.6 %
    # da 818 m de rampa suavizada y trazar al 6.5 % da 1219 m. Así que se prueba
    # una escalera de pendientes de traza y se toma la primera que alcanza.
    mejor = None
    for factor in FACTORES_DE_TRAZA:
        crudo = _espiral(anillos, arranque, cresta,
                         parametros.rampa_pendiente * factor)
        if len(crudo) < 3:
            continue
        try:
            eje = _suavizar_hasta_el_radio(crudo, parametros.radio_giro,
                                           largo_necesario)
        except RampaImposible:
            continue          # con esa traza el radio no entra; se prueba la próxima
        if mejor is None or _largo(eje) > _largo(mejor):
            mejor = eje
        if _largo(mejor) >= largo_necesario * 0.999:
            break

    if mejor is None:
        raise RampaImposible(
            f"el radio de giro de {parametros.radio_giro:.0f} m no entra en este "
            f"pit con ninguna traza: las curvas que impone la pared son más "
            f"cerradas que eso. Probá bajar el radio de giro — o, aunque suene al "
            f"revés, subirlo: con un radio mayor la rampa arranca más arriba, donde "
            f"el pit es ancho, y necesita menos desarrollo. En el caso base con "
            f"40 m no entra y con 60 sí. También ayuda bajar la altura de banco, "
            f"para que la pared suba en escalones más chicos."
        )
    eje = mejor

    eje = _repartir_cotas(eje, arranque, parametros.rampa_pendiente, cresta)
    # La pendiente que se informa es la LOGRADA, no la pedida. Suelen coincidir,
    # pero cuando el suavizado deja la rampa más larga de lo mínimo, el desnivel
    # se reparte sobre más metros y la rampa queda más tendida. Eso es correcto
    # —la pendiente pedida es un máximo, no un objetivo— pero mentiría el reporte
    # si dijera 10 % cuando el diseño entrega 9.6 %.
    largo = _largo(eje)
    lograda = (eje[-1][2] - eje[0][2]) / largo if largo > 0 else 0.0
    return Rampa(eje=eje, ancho=parametros.rampa_ancho, pendiente=lograda)


def cabe(carcaza, parametros: Parametros,
         talud_global: float | None = None) -> tuple[bool, str]:
    """¿Entra la rampa con estos parámetros? Pedido de PitForge (REQ-APP-002).

    Devuelve `(entra, explicación)`. **El texto viene siempre**, también cuando
    entra: un `str` que a veces está vacío obliga a la interfaz a un `if` que nadie
    recuerda por qué existe. Se prometió así por escrito en el REQ.

    No estima: **traza la rampa de verdad**, sobre una grilla más gruesa. Es a
    propósito, y es lo que se contestó en el REQ: una estimación barata —«¿alcanza
    el perímetro para ganar 10 m al 10 %?»— es fácil de escribir y miente justo en
    los pits donde importa, los de geometría rara, donde el perímetro alcanza pero
    el radio de giro no. Un validador que dice «cabe» y después el cálculo falla es
    peor que no tener validador.

    El costo es el de un diseño en borrador. Medido sobre el caso base: entre 0.06
    y 0.92 s según los parámetros, contra los 2.0-2.7 s del diseño completo. Sirve
    para validar cuando el usuario termina de escribir un campo, no en cada tecla.

    Los números del texto son del borrador: del orden correcto, no exactos. Por eso
    van dichos como aproximados y el texto lo aclara.

    **Que no entre con un radio y sí con uno más grande no es un error.** Medido
    sobre el caso base: con 40 m no entra y con 60 sí, porque con un radio mayor la
    rampa arranca más arriba —donde el pit es ancho—, tiene menos desnivel que subir
    y necesita menos desarrollo. Si la interfaz sugiere algo cuando no cabe, que no
    dé por sentado que hay que achicar el radio.
    """
    from . import PitPyError
    from .bancos import construir

    if talud_global is None:
        talud_global = parametros.talud_global or carcaza.talud_detectado()

    ancho, largo = carcaza.extension()
    paso = max(_paso_de_borrador(max(ancho, largo)),
               parametros.rampa_ancho / 2.0)
    try:
        construccion = construir(carcaza, parametros, talud_global, paso=paso)
        rampa = trazar(construccion, parametros)
    except PitPyError as e:
        # Cualquier error del dominio —rampa imposible, geometría inválida— es una
        # respuesta válida acá: la App quiere el motivo, no la excepción.
        return (False, str(e))

    arranque = rampa.eje[0][2]
    salida = rampa.eje[-1][2]
    # Los números salen de la grilla gruesa: son del orden correcto, no exactos.
    # Se dicen como aproximados a propósito. El fondo del borrador puede diferir un
    # nivel del real (medido: 210 contra 220 en el caso base), así que no se cita.
    detalles = [
        f"la rampa cabe: unos {rampa.longitud:.0f} m de desarrollo, saliendo cerca "
        f"de la cota {salida:.0f}, al {100 * rampa.pendiente:.1f} % aproximadamente"
    ]
    if arranque > construccion.fondo + 0.5:
        detalles.append(
            f"pero no llegaría hasta el fondo del pit: más abajo de la cota "
            f"{arranque:.0f} no hay lugar para un radio de "
            f"{parametros.radio_giro:.0f} m")
    if rampa.pendiente < parametros.rampa_pendiente - 0.002:
        detalles.append(
            f"y quedaría más tendida que el {100 * parametros.rampa_pendiente:.0f} % "
            f"pedido, porque respetar el radio obliga a alargarla")
    return (True, ", ".join(detalles) + ". Los valores exactos salen del cálculo.")


def _paso_de_borrador(extension: float) -> float:
    """Celda para la verificación rápida: 300 por lado en vez de 2000.

    Con 300 celdas la pared se resuelve a 2 m en un pit de 600 y a 13 m en uno de
    4 km — grueso para diseñar, suficiente para decidir si la rampa entra, y unas
    cuarenta veces más barato.
    """
    return extension / 300.0


def aplicar(z: np.ndarray, construccion, rampa: Rampa,
            talud_global: float) -> np.ndarray:
    """Hunde la rampa en la superficie del diseño y retira lo que queda arriba.

    Dos pasos, y el segundo es el que cuesta material: la plataforma baja la cota
    donde pasa el eje, y desde ahí hacia afuera nada puede estar más alto que lo
    que permite el talud global. Sin ese segundo paso la rampa sería un surco con
    paredes verticales encima.
    """
    superficie = construccion.superficie
    limite = _plataforma(z.shape, superficie, rampa)
    limite = _retirar_al_talud(limite, superficie.paso, talud_global)

    # Fuera del diseño de bancos lo que hay es carcaza. Si el límite obliga a
    # excavar ahí, el pit CRECE: esa es la mayor parte del sobre-estéril que la
    # rampa cuesta, y por eso el corte no puede limitarse a bajar celdas que ya
    # estaban diseñadas.
    afuera = np.isnan(z)
    base = np.where(afuera, superficie.z, z)
    resultado = np.minimum(base, limite)
    # Donde no había diseño y el límite no obliga a nada, sigue sin haber diseño.
    # (La comparación con NaN da False, así que más allá de la carcaza no se
    # inventa superficie: eso es asunto de topo, MOT-5.)
    resultado[afuera & ~(limite < superficie.z)] = np.nan
    return resultado


def _cota_de_arranque(construccion, radio_giro: float):
    """El nivel más bajo donde una curva del radio pedido entra en el pit.

    Criterio: que en la sección quepa un círculo de diámetro `2 * radio_giro`. Es
    el mismo criterio con el que se elige el fondo (ARQUITECTURA §8), con otro
    diámetro: allá es que quepa un banco, acá que quepa el giro del camión.
    """
    from .superficie import cabe_circulo

    superficie = construccion.superficie
    for cota in [construccion.fondo] + list(construccion.cotas):
        if cabe_circulo(superficie.seccion(cota), 2.0 * radio_giro, superficie.paso):
            return cota
    return None


def _anillos(construccion) -> list:
    """Los contornos del diseño, uno por nivel, listos para caminarlos.

    Se remuestrean a paso uniforme porque salen de una grilla y traen ondulación
    del tamaño de la celda: caminar sobre esos dientes daría radios de giro que no
    vienen de la geometría del pit sino del muestreo.
    """
    superficie = construccion.superficie
    anillos = []
    # Todos los niveles, incluida la cresta: sin el anillo de arriba la rampa se
    # queda sin dónde apoyarse para subir el último banco y termina una altura de
    # banco por debajo de la salida.
    for cota in [construccion.fondo] + list(construccion.cotas):
        contorno = superficie.contorno(cota)
        if contorno:
            anillos.append((cota, _uniforme(contorno[0], PASO_EJE)))
    return anillos


def _uniforme(anillo: list, paso: float) -> list:
    """Reparte puntos equiespaciados sobre un anillo cerrado."""
    largo = [0.0]
    for a, b in zip(anillo, anillo[1:]):
        largo.append(largo[-1] + math.dist(a[:2], b[:2]))
    total = largo[-1]
    if total <= paso:
        return anillo
    n = max(8, int(total / paso))
    salida = []
    j = 0
    for k in range(n):
        objetivo = total * k / n
        while j < len(largo) - 2 and largo[j + 1] < objetivo:
            j += 1
        tramo = largo[j + 1] - largo[j]
        t = 0.0 if tramo <= 0 else (objetivo - largo[j]) / tramo
        p, q = anillo[j], anillo[j + 1]
        salida.append((p[0] + t * (q[0] - p[0]), p[1] + t * (q[1] - p[1]), p[2]))
    return salida


def _espiral(anillos: list, arranque: float, cresta: float,
             pendiente: float) -> list:
    """Sube pegada a la pared, interpolando entre los contornos de cada nivel.

    Antes esto se hacía lanzando rayos desde el centro del pit hacia afuera. Anda
    en un cono y se rompe en un pit de verdad: entre dos azimuts vecinos el rayo
    cruza la pared a radios muy distintos, y el eje pegaba saltos de 265 m medidos
    en el caso base.

    Caminar los contornos es continuo, pero cambiar de anillo de golpe mete un
    paso lateral del ancho de un banco y ahí el radio de giro se desploma. Así que
    la posición se interpola entre el contorno de abajo y el de arriba según la
    cota: la rampa se aleja de la pared de a poco mientras sube, que es lo que
    hace una rampa.
    """
    if len(anillos) < 2:
        return []
    nivel = _nivel_de(anillos, arranque)
    k = 0
    eje = []
    recorrido = 0.0
    cota = arranque

    for _ in range(100000):
        if nivel + 1 >= len(anillos):
            break
        cota_baja, abajo = anillos[nivel]
        cota_alta, arriba = anillos[nivel + 1]
        t = 0.0
        if cota_alta > cota_baja:
            t = min(1.0, max(0.0, (cota - cota_baja) / (cota_alta - cota_baja)))
        p = abajo[k % len(abajo)]
        q = arriba[_mas_cercano(arriba, p)]
        punto = (p[0] + t * (q[0] - p[0]), p[1] + t * (q[1] - p[1]), cota)

        if eje:
            recorrido += math.dist(punto[:2], eje[-1][:2])
        eje.append(punto)
        cota = min(cresta, arranque + pendiente * recorrido)
        if cota >= cresta:
            break
        k += 1
        if cota >= cota_alta:
            nivel += 1
            k = _mas_cercano(anillos[nivel][1], punto)
    return eje


def _nivel_de(anillos: list, cota: float) -> int:
    """Índice del anillo cuyo nivel es el más alto que no pasa esa cota."""
    indice = 0
    for i, (nivel, _) in enumerate(anillos):
        if nivel <= cota:
            indice = i
    return indice


def _mas_cercano(anillo: list, punto) -> int:
    return min(range(len(anillo)), key=lambda i: math.dist(anillo[i][:2], punto[:2]))


def _suavizar_hasta_el_radio(eje: list, radio_min: float,
                             largo_necesario: float) -> list:
    """Redondea las curvas hasta que el radio mínimo cumpla.

    Cada pasada es un promedio móvil más un re-espaciado a paso uniforme. El
    re-espaciado no es cosmético: sin él los puntos se amontonan en las curvas,
    aparecen tríos casi degenerados, y el radio medido **empeora** por más que se
    siga suavizando. Medido en el caso base: solo con promedio móvil se estanca en
    17 m; con re-espaciado llega a 25 m en 160 pasadas.

    Suavizar es, físicamente, comerse la esquina: la rampa se mete un poco en la
    pared para poder girar. Es lo mismo que hace el humano estirando la banqueta
    (ROADMAP §Etapa 4), y el costo en material lo recoge el corte.
    """
    from . import RampaImposible

    for _ in range(PASADAS_DE_SUAVIZADO):
        if _radio_minimo(eje) >= radio_min:
            return eje
        eje = _reespaciar(_promedio_movil(eje), PASO_EJE)
    raise RampaImposible(
        f"el radio de giro de {radio_min:.0f} m no entra en este pit: lo más "
        f"holgado que se consigue son {_radio_minimo(eje):.0f} m, y seguir "
        f"redondeando la curva ya deforma la rampa. Reduce el radio de giro, o "
        f"baja la pendiente: al {100 * PENDIENTE_SUAVE:.0f} % la rampa necesita "
        f"{largo_necesario * PENDIENTE_REFERENCIA / PENDIENTE_SUAVE:.0f} m de "
        f"desarrollo y da vueltas más largas, con curvas más abiertas."
    )


def _reespaciar(eje: list, paso: float) -> list:
    """Reparte los puntos de una polilínea abierta cada `paso` metros."""
    largo = [0.0]
    for a, b in zip(eje, eje[1:]):
        largo.append(largo[-1] + math.dist(a[:2], b[:2]))
    total = largo[-1]
    if total <= paso or len(eje) < 3:
        return eje
    n = max(4, int(total / paso))
    salida = []
    j = 0
    for k in range(n + 1):
        objetivo = total * k / n
        while j < len(largo) - 2 and largo[j + 1] < objetivo:
            j += 1
        tramo = largo[j + 1] - largo[j]
        t = 0.0 if tramo <= 0 else (objetivo - largo[j]) / tramo
        a, b = eje[j], eje[j + 1]
        salida.append((a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1]),
                       a[2] + t * (b[2] - a[2])))
    return salida


def _promedio_movil(eje: list) -> list:
    """Cada punto se corre hacia el medio de sus vecinos. Solo en planta: la cota
    se vuelve a repartir después, para no perder la pendiente."""
    if len(eje) < 3:
        return eje
    suavizado = [eje[0]]
    for a, b, c in zip(eje, eje[1:], eje[2:]):
        suavizado.append(((a[0] + 2 * b[0] + c[0]) / 4.0,
                          (a[1] + 2 * b[1] + c[1]) / 4.0, b[2]))
    suavizado.append(eje[-1])
    return suavizado


def _radio_minimo(eje: list) -> float:
    """Radio de la circunferencia por cada terna consecutiva. El mínimo manda."""
    minimo = float("inf")
    for a, b, c in zip(eje, eje[1:], eje[2:]):
        ab = math.dist(a[:2], b[:2])
        bc = math.dist(b[:2], c[:2])
        ca = math.dist(c[:2], a[:2])
        cruz = abs((b[0] - a[0]) * (c[1] - a[1]) - (c[0] - a[0]) * (b[1] - a[1]))
        if cruz < 1e-9 or ab * bc * ca == 0:
            continue          # tramo recto: no restringe
        minimo = min(minimo, ab * bc * ca / (2 * cruz))
    return minimo


def _largo(eje: list) -> float:
    """Desarrollo horizontal del eje, en metros."""
    return sum(math.dist(a[:2], b[:2]) for a, b in zip(eje, eje[1:]))


def _repartir_cotas(eje: list, fondo: float, pendiente: float,
                    cresta: float) -> list:
    """Reparte la cota por longitud de arco real, para que la pendiente sea exacta.

    Durante el trazado la cota se estima con el avance previsto; después de
    suavizar, el recorrido real es otro. Repartir al final es lo que hace que
    `longitud * pendiente == desnivel` en vez de "más o menos".
    """
    largo = [0.0]
    for a, b in zip(eje, eje[1:]):
        largo.append(largo[-1] + math.dist(a[:2], b[:2]))
    total = largo[-1]
    if total <= 0:
        return eje
    # El desnivel que realmente se puede ganar con ese desarrollo, sin pasarse
    # de la cresta.
    desnivel = min(cresta - fondo, total * pendiente)
    escala = desnivel / (total * pendiente)
    return [(x, y, fondo + pendiente * escala * s) for (x, y, _), s in zip(eje, largo)]


def _plataforma(forma, superficie, rampa: Rampa) -> np.ndarray:
    """Cota de la plataforma en cada celda; infinito donde la rampa no pasa."""
    limite = np.full(forma, np.inf)
    paso = superficie.paso
    x0, y0 = superficie.origen
    ny, nx = forma
    medio = rampa.ancho / 2.0
    r = max(1, int(math.ceil(medio / paso)))
    di, dj = np.mgrid[-r:r + 1, -r:r + 1]
    disco = (di * di + dj * dj) * paso * paso <= medio * medio

    for x, y, z in rampa.eje:
        j = int((x - x0) / paso)
        i = int((y - y0) / paso)
        i0, i1 = max(0, i - r), min(ny, i + r + 1)
        j0, j1 = max(0, j - r), min(nx, j + r + 1)
        if i0 >= i1 or j0 >= j1:
            continue
        recorte = disco[i0 - (i - r):i1 - (i - r), j0 - (j - r):j1 - (j - r)]
        ventana = limite[i0:i1, j0:j1]
        np.minimum(ventana, np.where(recorte, z, np.inf), out=ventana)
    return limite


def _retirar_al_talud(limite: np.ndarray, paso: float,
                      talud_global: float) -> np.ndarray:
    """Propaga hacia afuera la restricción de talud desde la plataforma.

    Nada puede estar más alto que la plataforma más lo que permite el talud a esa
    distancia. Se propaga celda a celda en las ocho direcciones hasta que deja de
    cambiar; propagar solo desde la rampa es la clave, porque aplicar la misma
    restricción a todo el diseño aplanaría también las caras de banco, que son
    más paradas que el talud global a propósito.
    """
    subida = paso * math.tan(math.radians(talud_global))
    diagonal = subida * math.sqrt(2.0)
    for _ in range(limite.shape[0] + limite.shape[1]):
        antes = limite.copy()
        limite[1:, :] = np.minimum(limite[1:, :], limite[:-1, :] + subida)
        limite[:-1, :] = np.minimum(limite[:-1, :], limite[1:, :] + subida)
        limite[:, 1:] = np.minimum(limite[:, 1:], limite[:, :-1] + subida)
        limite[:, :-1] = np.minimum(limite[:, :-1], limite[:, 1:] + subida)
        limite[1:, 1:] = np.minimum(limite[1:, 1:], limite[:-1, :-1] + diagonal)
        limite[:-1, :-1] = np.minimum(limite[:-1, :-1], limite[1:, 1:] + diagonal)
        limite[1:, :-1] = np.minimum(limite[1:, :-1], limite[:-1, 1:] + diagonal)
        limite[:-1, 1:] = np.minimum(limite[:-1, 1:], limite[1:, :-1] + diagonal)
        if np.array_equal(antes, limite):
            break
    return limite
