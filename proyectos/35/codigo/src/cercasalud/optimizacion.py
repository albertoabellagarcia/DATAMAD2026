"""Optimización de actuaciones (H5): cobertura máxima de A y ampliación de horas de B (B1).

Solver: `scipy.optimize.milp` (HiGHS) con límite de tiempo (R-OPS-02). Cada resultado registra
su estado (R-OPT-01):
- `optimo`: HiGHS demuestra el óptimo dentro de la tolerancia;
- `tiempo_agotado`: se detuvo por tiempo; la solución no se presenta como óptima y se da la brecha;
- `inviable`: las restricciones no admiten solución;
- `sin_ganancia`: el óptimo no mejora nada (R-OPT-04);
- `error`: cualquier otro fallo del solver.

**A (cobertura máxima):** se eligen hasta `k` candidatos para cubrir la mayor población que hoy
está sin opción verificada. La oferta existente no consume actuaciones, y cada persona cuenta
una vez aunque la cubran varios candidatos (R-OPT-03). Las unidades con el mismo conjunto de
candidatos que las cubren se agrupan para reducir el problema; el óptimo no cambia.

**B1 (ampliar horas, D-24, R-OPT-06):** se abren bloques de 1 hora (refugio, hora) que hoy están
cerrados, con un máximo de centros y de centro-horas. Se resuelve en dos etapas:
1. maximizar la cobertura de la peor hora;
2. con esa peor hora fijada, maximizar las personas-hora.

La población que ya tiene acceso en una hora no cuenta como ganancia en esa hora.
"""

import itertools
import time

import numpy as np
from scipy.optimize import Bounds, LinearConstraint, milp
from scipy.sparse import csr_matrix, hstack, identity, vstack

OPTIMO, TIEMPO, INVIABLE, SIN_GANANCIA, ERROR = "optimo", "tiempo_agotado", "inviable", "sin_ganancia", "error"
TOLERANCIA_GAP = 1e-4
ESCALA_B1 = 1000.0  # B1 se resuelve en miles de personas (ver `ampliar_horas`)


def agrupar(cubre: list[frozenset], pesos: np.ndarray) -> tuple[list[frozenset], np.ndarray]:
    """Une las unidades con el mismo conjunto de candidatos que las cubren (sumando sus pesos)."""
    grupos: dict[frozenset, float] = {}
    for conjunto, peso in zip(cubre, pesos, strict=True):
        if conjunto and peso > 0:
            grupos[conjunto] = grupos.get(conjunto, 0.0) + float(peso)
    return list(grupos), np.array(list(grupos.values()), dtype=float)


def estado_solver(resultado, objetivo: float) -> str:
    """Traduce el estado de HiGHS (vía SciPy) a los estados de R-OPT-01 y R-OPT-04."""
    if resultado.status == 2:
        return INVIABLE
    if resultado.x is None:
        return TIEMPO if resultado.status == 1 else ERROR
    if resultado.status == 1:
        return TIEMPO
    if resultado.status != 0:
        return ERROR
    return SIN_GANANCIA if objetivo <= 1e-9 else OPTIMO


def cobertura_maxima(cubre: list[frozenset], pesos: np.ndarray, k: int, limite_s: float = 600.0) -> dict:
    """Elige hasta `k` candidatos que maximizan la población cubierta nueva.

    `cubre[i]`: candidatos que cubren a la unidad i (solo unidades hoy sin opción verificada).
    `pesos[i]`: su población.
    """
    grupos, w = agrupar(cubre, pesos)
    candidatos = sorted(set().union(*grupos)) if grupos else []
    registro = {"k": k, "candidatos": len(candidatos), "grupos_demanda": len(grupos), "limite_s": limite_s,
                "tolerancia_gap": TOLERANCIA_GAP}
    if not grupos or k <= 0:
        return {**registro, "estado": SIN_GANANCIA, "elegidos": [], "ganancia": 0.0, "brecha": 0.0,
                "causa": "nadie sin opción alcanzable por los candidatos" if k > 0 else "k = 0", "segundos": 0.0}
    indice = {c: j for j, c in enumerate(candidatos)}
    n_c, n_g = len(candidatos), len(grupos)
    filas, columnas = [], []
    for i, conjunto in enumerate(grupos):
        for c in conjunto:
            filas.append(i)
            columnas.append(indice[c])
    a = csr_matrix((np.ones(len(filas)), (filas, columnas)), shape=(n_g, n_c))
    # variables: x (candidatos, binarias) y y (grupos, continuas en [0, 1])
    c = np.concatenate([np.zeros(n_c), -w])
    restricciones = [LinearConstraint(hstack([-a, identity(n_g)]), -np.inf, 0),             # y_i ≤ Σ a_ij x_j
                     LinearConstraint(hstack([csr_matrix(np.ones((1, n_c))), csr_matrix((1, n_g))]), 0, k)]
    integralidad = np.concatenate([np.ones(n_c), np.zeros(n_g)])
    inicio = time.monotonic()
    res = milp(c, constraints=restricciones, integrality=integralidad, bounds=Bounds(0, 1),
               options={"time_limit": limite_s, "mip_rel_gap": TOLERANCIA_GAP})
    segundos = time.monotonic() - inicio
    ganancia = -float(res.fun) if res.x is not None else 0.0
    elegidos = [candidatos[j] for j in np.flatnonzero(res.x[:n_c] > 0.5)] if res.x is not None else []
    return {**registro, "estado": estado_solver(res, ganancia), "elegidos": elegidos, "ganancia": ganancia,
            "brecha": float(getattr(res, "mip_gap", np.nan) or 0.0), "segundos": round(segundos, 2),
            "causa": "" if ganancia > 1e-9 else "ningún candidato cubre población sin opción"}


def cobertura_max_min(escenarios: list[tuple[list[frozenset], np.ndarray]], k: int, limite_s: float = 600.0) -> dict:
    """Alternativa max-min (SPEC §9): la cartera de hasta `k` candidatos cuya peor ganancia entre
    escenarios es la mayor posible.

    `escenarios`: para cada escenario, los conjuntos de candidatos de cada unidad sin opción y sus
    pesos (la población sin opción cambia de un escenario a otro). La ganancia se mide en
    personas en cada escenario; el objetivo es maximizar la menor de ellas.
    """
    agrupados = [agrupar(cubre, pesos) for cubre, pesos in escenarios]
    candidatos = sorted(set().union(*[c for grupos, _ in agrupados for c in grupos]))
    registro = {"k": k, "escenarios": len(escenarios), "candidatos": len(candidatos), "limite_s": limite_s,
                "tolerancia_gap": TOLERANCIA_GAP}
    if not candidatos or k <= 0:
        return {**registro, "estado": SIN_GANANCIA, "elegidos": [], "peor_ganancia": 0.0, "brecha": 0.0, "segundos": 0.0}
    indice = {c: j for j, c in enumerate(candidatos)}
    n_c = len(candidatos)
    tamanos = [len(grupos) for grupos, _ in agrupados]
    n_y = sum(tamanos)
    n = n_c + n_y + 1  # x, y de cada escenario, t
    bloques_cobertura, filas_t, desplazamiento = [], [], n_c
    for (grupos, w), tamano in zip(agrupados, tamanos, strict=True):
        filas, columnas = [], []
        for i, conjunto in enumerate(grupos):
            for c in conjunto:
                filas.append(i)
                columnas.append(indice[c])
        a = csr_matrix((np.ones(len(filas)), (filas, columnas)), shape=(tamano, n_c))
        # y_i ≤ Σ a_ij x_j
        y = csr_matrix((np.ones(tamano), (np.arange(tamano), desplazamiento + np.arange(tamano))), shape=(tamano, n))
        bloques_cobertura.append(y - hstack([a, csr_matrix((tamano, n - n_c))]))
        # t ≤ Σ w_i y_i  →  t − Σ w_i y_i ≤ 0
        fila = np.zeros(n)
        fila[desplazamiento:desplazamiento + tamano] = -w
        fila[-1] = 1.0
        filas_t.append(fila)
        desplazamiento += tamano
    presupuesto = np.concatenate([np.ones(n_c), np.zeros(n - n_c)])
    restricciones = [LinearConstraint(vstack(bloques_cobertura), -np.inf, 0),
                     LinearConstraint(csr_matrix(np.array(filas_t)), -np.inf, 0),
                     LinearConstraint(csr_matrix(presupuesto), 0, k)]
    integralidad = np.concatenate([np.ones(n_c), np.zeros(n - n_c)])
    cotas = Bounds(np.zeros(n), np.concatenate([np.ones(n - 1), [np.inf]]))
    inicio = time.monotonic()
    res = milp(np.concatenate([np.zeros(n - 1), [-1.0]]), constraints=restricciones, integrality=integralidad,
               bounds=cotas, options={"time_limit": limite_s, "mip_rel_gap": TOLERANCIA_GAP})
    peor = -float(res.fun) if res.x is not None else 0.0
    elegidos = [candidatos[j] for j in np.flatnonzero(res.x[:n_c] > 0.5)] if res.x is not None else []
    return {**registro, "estado": estado_solver(res, peor), "elegidos": elegidos, "peor_ganancia": peor,
            "brecha": float(getattr(res, "mip_gap", np.nan) or 0.0), "segundos": round(time.monotonic() - inicio, 2)}


def enumeracion_exhaustiva(cubre: list[frozenset], pesos: np.ndarray, k: int) -> float:
    """Mejor ganancia probando todas las combinaciones de hasta k candidatos (solo casos pequeños)."""
    candidatos = sorted(set().union(*[c for c in cubre if c])) if any(cubre) else []
    mejor = 0.0
    for tamano in range(1, min(k, len(candidatos)) + 1):
        for combinacion in itertools.combinations(candidatos, tamano):
            elegido = set(combinacion)
            mejor = max(mejor, float(sum(p for conjunto, p in zip(cubre, pesos, strict=True) if conjunto & elegido)))
    return mejor


def ganancia_de(cubre: list[frozenset], pesos: np.ndarray, elegidos: list) -> float:
    """Población cubierta por una cartera dada (cada persona una vez)."""
    elegido = set(elegidos)
    return float(sum(p for conjunto, p in zip(cubre, pesos, strict=True) if conjunto & elegido))


def regla_simple(poblacion_local: dict, k: int) -> list:
    """Regla de comparación (SPEC §10): los k candidatos con más población sin opción en su propia celda."""
    return [c for c, _ in sorted(poblacion_local.items(), key=lambda par: -par[1])[:k]]


def evaluar_b1(demanda: list[dict], cubiertos_hoy: dict[int, float], abiertos: list[tuple]) -> dict:
    """Cobertura por hora, peor hora y personas-hora ganadas con unos bloques abiertos."""
    abiertos = set(abiertos)
    ganada = {h: 0.0 for h in cubiertos_hoy}
    for d in demanda:
        if any((r, d["hora"]) in abiertos for r in d["refugios"]):
            ganada[d["hora"]] += d["peso"]
    por_hora = {h: cubiertos_hoy[h] + ganada[h] for h in cubiertos_hoy}
    return {"por_hora": por_hora, "peor_hora": min(por_hora.values()), "personas_hora_ganadas": sum(ganada.values())}


def regla_simple_b1(demanda: list[dict], cubiertos_hoy: dict[int, float], bloques: list[tuple],
                    poblacion_cerca: dict, max_centros: int, max_centro_horas: int) -> list[tuple]:
    """Regla de comparación (SPEC §10): ampliar los refugios con más población alrededor.

    Toma los `max_centros` refugios con más población a menos del umbral y abre sus horas
    cerradas, de la hora con menos cobertura hoy a la de más, hasta `max_centro_horas`.
    """
    elegidos = [r for r, _ in sorted(poblacion_cerca.items(), key=lambda par: -par[1])[:max_centros]]
    orden_horas = sorted(cubiertos_hoy, key=lambda h: cubiertos_hoy[h])
    posibles = [(r, h) for h in orden_horas for r in elegidos if (r, h) in set(bloques)]
    return posibles[:max_centro_horas]


def ampliar_horas(demanda: list[dict], cubiertos_hoy: dict[int, float], bloques: list[tuple],
                  max_centros: int, max_centro_horas: int, limite_s: float = 600.0) -> dict:
    """B1 en dos etapas (D-24), con la población reescalada para el solver.

    Con la población en personas, HiGHS devolvió «Solve error» (estado 4) en 2 de 10 instancias
    reales el 14/11/2026. Con la población en miles de personas, las 10 se resolvieron como
    óptimas. Una escala que llevaba los valores a 100 o menos falló en 4 de 10. La escala de
    1.000 es, por tanto, una elección empírica (`ESCALA_B1`), comprobada en esas 10 instancias.
    Las cifras que se devuelven están en personas.
    """
    escala = ESCALA_B1
    resultado = _ampliar_horas([{**d, "peso": d["peso"] / escala} for d in demanda],
                               {h: v / escala for h, v in cubiertos_hoy.items()}, bloques, max_centros,
                               max_centro_horas, limite_s)
    for clave in ("peor_hora_antes", "peor_hora_despues", "personas_hora_ganadas"):
        if clave in resultado:
            resultado[clave] *= escala
    return {**resultado, "escala_solver": escala}


def alternativas_b1(demanda: list[dict], cubiertos_hoy: dict[int, float], bloques: list[tuple], abiertos: list[tuple],
                    max_centros: int, max_centro_horas: int, limite_s: float = 600.0) -> list[dict]:
    """Para cada refugio de la cartera elegida, la mejor cartera sin él y cuánto se pierde.

    Sirve para distinguir una elección firme de un empate: si excluir un refugio apenas reduce
    la peor hora, la elección de ese refugio es casi indiferente. La pérdida se da en porcentaje
    de la ganancia en la peor hora de la cartera elegida (peor hora después − antes); es `None`
    si esa ganancia es cero. Las cifras se recalculan con `evaluar_b1`, en personas.
    """
    peor_antes = min(cubiertos_hoy.values())
    elegida = evaluar_b1(demanda, cubiertos_hoy, abiertos)
    ganancia = elegida["peor_hora"] - peor_antes
    salida = []
    for refugio in sorted({r for r, _ in abiertos}):
        permitidos = [b for b in bloques if b[0] != refugio]
        sin = (ampliar_horas(demanda, cubiertos_hoy, permitidos, max_centros, max_centro_horas, limite_s)
               if permitidos else {"estado": SIN_GANANCIA, "bloques": []})
        evaluada = evaluar_b1(demanda, cubiertos_hoy, sin["bloques"])
        perdida = elegida["peor_hora"] - evaluada["peor_hora"]
        salida.append({"excluido": refugio, "estado": sin["estado"],
                       "refugios": sorted({r for r, _ in sin["bloques"]}),
                       "peor_hora_despues": evaluada["peor_hora"],
                       "personas_hora_ganadas": evaluada["personas_hora_ganadas"],
                       "perdida_peor_hora_pct": 100 * perdida / ganancia if ganancia > 1e-9 else None})
    return salida


def _ampliar_horas(demanda: list[dict], cubiertos_hoy: dict[int, float], bloques: list[tuple],
                   max_centros: int, max_centro_horas: int, limite_s: float) -> dict:
    """B1 en dos etapas (D-24). Devuelve los bloques abiertos y la cobertura por hora.

    `demanda`: grupos de unidades sin acceso en una hora, cada uno con `hora`, `peso` y
    `refugios` (los que lo cubrirían si abrieran esa hora). `cubiertos_hoy[h]`: población con
    acceso en la hora h. `bloques`: pares (refugio, hora) que hoy están cerrados y se pueden abrir.
    """
    horas = sorted(cubiertos_hoy)
    refugios = sorted({r for r, _ in bloques})
    n_z, n_u = len(bloques), len(refugios)
    demanda = [d for d in demanda if any((r, d["hora"]) in set(bloques) for r in d["refugios"])]
    n_y = len(demanda)
    idx_z = {b: j for j, b in enumerate(bloques)}
    idx_u = {r: j for j, r in enumerate(refugios)}
    n = n_z + n_u + n_y + 1  # z, u, y, t
    filas, columnas, valores, lo, hi = [], [], [], [], []

    def restriccion(coeficientes: list[tuple[int, float]], minimo: float, maximo: float) -> None:
        """Añade una fila dispersa minimo ≤ Σ coef·var ≤ maximo."""
        fila = len(lo)
        for columna, valor in coeficientes:
            filas.append(fila)
            columnas.append(columna)
            valores.append(valor)
        lo.append(minimo)
        hi.append(maximo)

    # y_i ≤ Σ z_(r,h) de sus refugios en su hora
    for i, d in enumerate(demanda):
        restriccion([(n_z + n_u + i, 1.0)] + [(idx_z[(r, d["hora"])], -1.0) for r in d["refugios"]
                                               if (r, d["hora"]) in idx_z], -np.inf, 0)
    # z_(r,h) ≤ u_r
    for (r, _h), j in idx_z.items():
        restriccion([(j, 1.0), (n_z + idx_u[r], -1.0)], -np.inf, 0)
    restriccion([(n_z + j, 1.0) for j in range(n_u)], 0, max_centros)
    restriccion([(j, 1.0) for j in range(n_z)], 0, max_centro_horas)
    # t ≤ cubiertos_hoy[h] + Σ y de esa hora
    for h in horas:
        restriccion([(n - 1, 1.0)] + [(n_z + n_u + i, -d["peso"]) for i, d in enumerate(demanda) if d["hora"] == h],
                    -np.inf, cubiertos_hoy[h])
    a = csr_matrix((valores, (filas, columnas)), shape=(len(lo), n))
    lo, hi = np.array(lo, dtype=float), np.array(hi, dtype=float)
    integralidad = np.concatenate([np.ones(n_z + n_u), np.zeros(n_y + 1)])
    cotas = Bounds(np.zeros(n), np.concatenate([np.ones(n_z + n_u + n_y), [np.inf]]))
    pesos = np.array([d["peso"] for d in demanda])
    opciones = {"time_limit": limite_s, "mip_rel_gap": TOLERANCIA_GAP}
    inicio = time.monotonic()
    etapa1 = milp(np.concatenate([np.zeros(n - 1), [-1]]), constraints=LinearConstraint(a, lo, hi),
                  integrality=integralidad, bounds=cotas, options=opciones)
    peor_hoy = min(cubiertos_hoy.values())
    if etapa1.x is None:
        return {"estado": estado_solver(etapa1, 0.0), "etapa": 1, "bloques": [], "segundos": round(time.monotonic() - inicio, 2)}
    peor = -float(etapa1.fun)
    fijar = np.zeros(n)
    fijar[-1] = 1
    a2 = vstack([a, csr_matrix(fijar)])
    etapa2 = milp(np.concatenate([np.zeros(n_z + n_u), -pesos, [0]]),
                  constraints=LinearConstraint(a2, np.append(lo, peor - 1e-6), np.append(hi, np.inf)),
                  integrality=integralidad, bounds=cotas, options=opciones)
    segundos = round(time.monotonic() - inicio, 2)
    if etapa2.x is None:
        return {"estado": estado_solver(etapa2, 0.0), "etapa": 2, "bloques": [], "segundos": segundos}
    abiertos = [bloques[j] for j in np.flatnonzero(etapa2.x[:n_z] > 0.5)]
    personas_hora = float(pesos @ etapa2.x[n_z + n_u:n_z + n_u + n_y])
    estados = (estado_solver(etapa1, peor - peor_hoy + personas_hora), estado_solver(etapa2, personas_hora))
    estado = TIEMPO if TIEMPO in estados else (SIN_GANANCIA if personas_hora <= 1e-9 else estados[1])
    return {"estado": estado, "estado_etapa1": estados[0], "estado_etapa2": estados[1], "bloques": abiertos,
            "peor_hora_antes": peor_hoy, "peor_hora_despues": peor, "personas_hora_ganadas": personas_hora,
            "centros": len({r for r, _ in abiertos}), "centro_horas": len(abiertos), "segundos": segundos,
            "max_centros": max_centros, "max_centro_horas": max_centro_horas, "limite_s": limite_s}
