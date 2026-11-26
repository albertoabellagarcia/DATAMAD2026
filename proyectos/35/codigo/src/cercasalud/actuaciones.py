"""Preparación de datos para las actuaciones de H5 (candidatos de A y demanda de B1).

**Candidatos de A (D-15):** una «zona de búsqueda» por cada celda de una malla de 250 m que
contiene alguna unidad de demanda (es decir, con soporte residencial). Su punto es el centro de
gravedad de la población de sus unidades. No es un solar ni un edificio concreto.

**B1:** grupos de unidades sin acceso en una hora del tipo de día, con los refugios que hoy
están cerrados esa hora y las cubrirían si abrieran.
"""

import numpy as np
import pandas as pd

from .acceso import CON, SIN
from .horarios import CERRADO

LADO_CANDIDATO_M = 250


def celda_candidato(unidades: pd.DataFrame) -> pd.Series:
    """Identificador del candidato (celda de 250 m) en el que cae cada unidad."""
    return ("z" + np.floor(unidades["x"] / LADO_CANDIDATO_M).astype(int).astype(str) + "_"
            + np.floor(unidades["y"] / LADO_CANDIDATO_M).astype(int).astype(str))


def candidatos(unidades: pd.DataFrame, estado_pie: pd.Series) -> pd.DataFrame:
    """Un candidato por celda de 250 m con unidades; con su población y la población sin opción a pie.

    `estado_pie`: estado base a pie de cada unidad (mismo índice que `unidades`).
    """
    tabla = unidades.assign(candidato=celda_candidato(unidades), xp=unidades["x"] * unidades["poblacion_total"],
                            yp=unidades["y"] * unidades["poblacion_total"],
                            sin_total=np.where(estado_pie == SIN, unidades["poblacion_total"], 0.0),
                            sin_65=np.where(estado_pie == SIN, unidades["poblacion_65_mas"], 0.0))
    suma = tabla.groupby("candidato")[["xp", "yp", "poblacion_total", "sin_total", "sin_65"]].sum()
    centro = tabla.groupby("candidato")[["x", "y"]].mean()
    con_poblacion = suma["poblacion_total"] > 0
    x = np.where(con_poblacion, suma["xp"] / suma["poblacion_total"].where(con_poblacion, 1), centro["x"])
    y = np.where(con_poblacion, suma["yp"] / suma["poblacion_total"].where(con_poblacion, 1), centro["y"])
    return pd.DataFrame({"candidato": suma.index, "x": x, "y": y, "poblacion": suma["poblacion_total"].to_numpy(),
                         "sin_opcion_pie_total": suma["sin_total"].to_numpy(),
                         "sin_opcion_pie_65": suma["sin_65"].to_numpy()}).reset_index(drop=True)


def conjuntos_cobertura(pares: pd.DataFrame, unidades_sin: pd.Series, umbral_min: float) -> list[frozenset]:
    """Para cada unidad sin opción (en el orden dado), los candidatos a `umbral_min` o menos."""
    cerca = pares[pares["minutos"] <= umbral_min].groupby("unidad")["candidato"].agg(frozenset)
    return [cerca.get(u, frozenset()) for u in unidades_sin]


def conjuntos_cobertura_transporte(sin: pd.DataFrame, pares_pie: pd.DataFrame, pares_tp: pd.DataFrame,
                                   umbral_min: float, percentil: int = 50, margen_min: float = 0) -> list[frozenset]:
    """Candidatos que dejarían a cada unidad sin opción a `umbral_min` o menos en transporte.

    Mismo criterio que la situación inicial de A en transporte (`acceso.tiempo_transporte`): el
    tiempo de una unidad a un candidato es el menor entre ir andando desde la unidad
    (`pares_pie`, hasta 19 min) y el de su sección en la matriz de transporte (`pares_tp`, desde
    el centro de gravedad residencial de la sección). El margen de sesgo se suma solo al tiempo
    de la matriz, no al de ir andando (REGISTRO-FALLOS, entrada 24).

    `sin`: unidades sin opción (columnas `unidad` y `cusec`), en el orden de los pesos.
    """
    pie = pares_pie.loc[pares_pie["minutos"] <= umbral_min, ["unidad", "candidato"]]
    cerca_tp = pares_tp[pares_tp[f"travel_time_p{percentil}"] + margen_min <= umbral_min]
    tp = sin[["unidad", "cusec"]].merge(cerca_tp.rename(columns={"from_id": "cusec", "to_id": "candidato"}),
                                        on="cusec")[["unidad", "candidato"]]
    cerca = pd.concat([pie[pie["unidad"].isin(sin["unidad"])], tp]).groupby("unidad")["candidato"].agg(frozenset)
    return [cerca.get(u, frozenset()) for u in sin["unidad"]]


def fusionar_equivalentes(cubre: list[frozenset], prioridad: dict) -> tuple[list[frozenset], dict]:
    """Une los candidatos que cubren exactamente las mismas unidades (columnas idénticas).

    En cobertura máxima con «hasta k», dos candidatos con el mismo conjunto de unidades cubiertas
    son intercambiables: el óptimo no cambia si se deja uno solo. Se queda el de mayor
    `prioridad` (población de su celda; a igualdad, el nombre menor) y se devuelven los
    equivalentes de cada representante, que la ficha de decisión muestra como alternativas.
    """
    por_candidato: dict = {}
    for i, conjunto in enumerate(cubre):
        for c in conjunto:
            por_candidato.setdefault(c, []).append(i)
    clases: dict[tuple, list] = {}
    for c, unidades in por_candidato.items():
        clases.setdefault(tuple(unidades), []).append(c)
    representante, equivalentes = {}, {}
    for miembros in clases.values():
        elegido = min(miembros, key=lambda c: (-prioridad.get(c, 0.0), c))
        equivalentes[elegido] = sorted(m for m in miembros if m != elegido)
        representante.update({m: elegido for m in miembros})
    return [frozenset(representante[c] for c in conjunto) for conjunto in cubre], equivalentes


def demanda_b1(estados_b: pd.DataFrame, pares: pd.DataFrame, estados_refugio: pd.DataFrame, unidades: pd.DataFrame,
               tipo_dia: str, umbral_min: float, columna: str) -> tuple[list[dict], dict, list[tuple]]:
    """Demanda agrupada, población cubierta hoy por hora y bloques (refugio, hora) que se pueden abrir.

    Solo cuentan las unidades `sin_opcion_verificada` en esa hora: las `no_evaluable` no se
    contabilizan como ganancia.
    """
    estados = estados_b[estados_b["tipo_dia"] == tipo_dia].merge(unidades[["unidad", columna]], on="unidad")
    cubiertos = estados[estados["estado"] == CON].groupby("hora")[columna].sum()
    horas = sorted(estados["hora"].unique())
    cubiertos_hoy = {int(h): float(cubiertos.get(h, 0.0)) for h in horas}
    cerrados = estados_refugio[(estados_refugio["tipo_dia"] == tipo_dia) & (estados_refugio["estado"] == CERRADO)]
    bloques = sorted({(r, int(h)) for r, h in zip(cerrados["refugio"], cerrados["hora"], strict=True)})
    cerca = pares[pares["minutos"] <= umbral_min].groupby("unidad")["refugio"].agg(frozenset)
    sin = estados[estados["estado"] == SIN].assign(refugios=lambda t: t["unidad"].map(cerca))
    sin = sin[sin["refugios"].notna()]
    grupos = sin.groupby(["hora", "refugios"])[columna].sum()
    demanda = [{"hora": int(h), "refugios": sorted(r), "peso": float(p)} for (h, r), p in grupos.items() if p > 0]
    return demanda, cubiertos_hoy, bloques
