"""Situación inicial de A: acceso a atención primaria por unidad de demanda (H3).

Estados por unidad y modo (SPEC §7): `con_acceso`, `sin_opcion_verificada` y `no_evaluable`
con motivo. «Al menos uno de los dos modos» cuenta a cada persona una sola vez (P-19).

**A pie:** tiempo de R5 de la unidad al centro más cercano, clasificado con `red.clasificar`
(R-RED-02). Los fallos de conexión o de enlace son `no_evaluable` (`conexion`).

**En transporte público:** la matriz de transporte se calculó por sección, desde su centro de
gravedad residencial, y solo para las secciones con alguna unidad a más de 20 min a pie
(fases/noches/ejecutor_nocturno.py, `origenes_transporte`). El tiempo de una unidad es el menor
entre:
- su tiempo a pie a 3,0 km/h (R5 incluye ir andando como opción del modo transporte);
- el de su sección en la matriz.

En las secciones sin matriz, todas las unidades llegan a pie en 20 min o menos, así que su
tiempo en transporte es el tiempo a pie. Supuesto declarado: todas las unidades de una
sección comparten el tiempo en transporte de su centro de gravedad. La unidad sin conexión a
la red a pie es `no_evaluable` (`conexion`) también en transporte.

El estado en transporte se decide con la mediana de las salidas de la franja (p50, P-18). El
p80 se publica como escenario. Los escenarios de margen suman minutos al tiempo de la sección
en la matriz, no al de ir andando, para reflejar un posible sesgo optimista de la matriz urbana
(seguimiento del 14/11/2026).

Consecuencia declarada: como el modo transporte incluye ir andando (igual que R5), quien llega a
pie dentro del umbral de transporte tiene acceso también en transporte. En el escenario base,
«al menos uno» coincide con transporte; solo difieren cuando el modo a pie es más generoso (por
ejemplo, a 3,6 km/h).

Las sensibilidades de velocidad solo cambian el modo a pie. El transporte mantiene 3,0 km/h,
como en la matriz.
"""

import json

import numpy as np
import pandas as pd

from . import red

CON, SIN, NO_EVAL = "con_acceso", "sin_opcion_verificada", "no_evaluable"
ESTADOS = (CON, SIN, NO_EVAL)
MODOS = ("pie", "transporte", "al_menos_uno")
GRUPOS_EDAD = {"total": "poblacion_total", "65+": "poblacion_65_mas", "75+": "poblacion_75_mas",
               "85+": "poblacion_85_mas"}
MADRID_CAPITAL = "28079"


def columna_pie(velocidad_kmh: float) -> str:
    """Nombre de la columna con el tiempo a pie a una velocidad."""
    return f"tiempo_pie_{velocidad_kmh:.1f}"


def estado_pie(unidades: pd.DataFrame, velocidad_kmh: float, umbral_min: float,
               radio_min: float) -> pd.DataFrame:
    """Estado y motivo a pie de cada unidad (clases de R-RED-02)."""
    recta_min = unidades["recta_m"] / (velocidad_kmh * 1000 / 60)
    clase = red.clasificar(unidades[columna_pie(velocidad_kmh)], unidades["enganchado"], umbral_min,
                           radio_min, recta_min)
    pares = clase.map(red.ESTADO_SEGUN_CLASE)
    return pd.DataFrame({"estado": pares.str[0], "motivo": pares.str[1]}, index=unidades.index)


def tiempo_transporte(unidades: pd.DataFrame, por_seccion: pd.Series, velocidad_base_kmh: float) -> pd.Series:
    """Menor tiempo entre ir a pie (3,0 km/h) y el de la sección en la matriz; NaN si ninguno."""
    seccion = unidades["cusec"].map(por_seccion).astype(float)
    return pd.Series(np.fmin(unidades[columna_pie(velocidad_base_kmh)].to_numpy(dtype=float),
                             seccion.to_numpy()), index=unidades.index)


def estado_transporte(tiempo: pd.Series, umbral_min: float, sin_conexion: pd.Series) -> pd.DataFrame:
    """Estado en transporte: `no_evaluable` si la unidad no conecta con la red; si no, umbral."""
    estado = np.where(sin_conexion, NO_EVAL, np.where(tiempo.to_numpy() <= umbral_min, CON, SIN))
    motivo = np.where(sin_conexion, "conexion", "")
    return pd.DataFrame({"estado": estado, "motivo": motivo}, index=tiempo.index)


def al_menos_uno(pie: pd.DataFrame, transporte: pd.DataFrame) -> pd.DataFrame:
    """Con acceso si lo tiene en algún modo; no evaluable si en ninguno lo tiene y alguno no se
    puede evaluar; si no, sin opción verificada. Una persona cuenta una vez (P-19)."""
    con = (pie["estado"] == CON) | (transporte["estado"] == CON)
    no_eval = ~con & ((pie["estado"] == NO_EVAL) | (transporte["estado"] == NO_EVAL))
    estado = np.where(con, CON, np.where(no_eval, NO_EVAL, SIN))
    motivo = np.where(no_eval, np.where(pie["estado"] == NO_EVAL, pie["motivo"], transporte["motivo"]), "")
    return pd.DataFrame({"estado": estado, "motivo": motivo}, index=pie.index)


def escenarios(config: dict) -> list[dict]:
    """Escenario base y sensibilidades; cada uno cambia un solo supuesto respecto al base."""
    pie, tp = config["primaria"]["pie"], config["primaria"]["transporte"]
    base = {"nombre": "base", "velocidad_kmh": pie["velocidad_kmh"], "umbral_pie_min": pie["umbral_min"],
            "umbral_tp_min": tp["umbral_min"], "percentil_tp": tp["percentil_estado"], "margen_tp_min": 0}
    lista = [base]
    lista += [{**base, "nombre": f"pie_umbral_{u}", "umbral_pie_min": u} for u in pie["umbrales_sensibilidad_min"]]
    lista += [{**base, "nombre": f"pie_velocidad_{v}", "velocidad_kmh": v} for v in pie["velocidades_sensibilidad_kmh"]]
    lista += [{**base, "nombre": f"tp_umbral_{u}", "umbral_tp_min": u} for u in tp["umbrales_sensibilidad_min"]]
    lista += [{**base, "nombre": "tp_p80", "percentil_tp": 80}]
    lista += [{**base, "nombre": f"tp_margen_{m}", "margen_tp_min": m} for m in tp["margenes_sesgo_min"]]
    return lista


def sin_motor(indice: pd.Index) -> pd.DataFrame:
    """Modo degradado (R-RED-05): sin matriz de transporte, el modo es no evaluable por el motor."""
    return pd.DataFrame({"estado": NO_EVAL, "motivo": "motor"}, index=indice)


def estados_escenario(unidades: pd.DataFrame, transporte_seccion: pd.DataFrame | None, escenario: dict,
                      config: dict) -> dict[str, pd.DataFrame]:
    """Estados de las unidades en los tres modos para un escenario.

    `transporte_seccion`: índice cusec, columnas `p50` y `p80` (mejor tiempo de la sección), o
    None si no hay matriz de transporte (modo degradado R-RED-05).
    """
    pie_cfg = config["primaria"]["pie"]
    radio = pie_cfg["radio_calculo_min"]
    pie = estado_pie(unidades, escenario["velocidad_kmh"], escenario["umbral_pie_min"], radio)
    if transporte_seccion is None:
        transporte = sin_motor(unidades.index)
    else:
        base_pie = estado_pie(unidades, pie_cfg["velocidad_kmh"], pie_cfg["umbral_min"], radio)
        # El margen refleja un posible sesgo de la matriz: se suma al tiempo de la sección, no al de ir andando.
        por_seccion = transporte_seccion[f"p{escenario['percentil_tp']}"] + escenario["margen_tp_min"]
        tiempo = tiempo_transporte(unidades, por_seccion, pie_cfg["velocidad_kmh"])
        transporte = estado_transporte(tiempo, escenario["umbral_tp_min"], base_pie["estado"] == NO_EVAL)
    return {"pie": pie, "transporte": transporte, "al_menos_uno": al_menos_uno(pie, transporte)}


def ambas_franjas(manana: pd.DataFrame, tarde: pd.DataFrame) -> pd.DataFrame:
    """Transporte con acceso en las dos franjas de D-17 (criterio estricto).

    Con acceso si lo tiene de 9 a 13 h y de 16 a 20 h; no evaluable si alguna franja no se puede
    evaluar; si no, sin opción verificada en al menos una franja.
    """
    no_eval = (manana["estado"] == NO_EVAL) | (tarde["estado"] == NO_EVAL)
    con = (manana["estado"] == CON) & (tarde["estado"] == CON)
    estado = np.where(no_eval, NO_EVAL, np.where(con, CON, SIN))
    motivo = np.where(no_eval, np.where(manana["estado"] == NO_EVAL, manana["motivo"], tarde["motivo"]), "")
    return pd.DataFrame({"estado": estado, "motivo": motivo}, index=manana.index)


def estados_franjas(unidades: pd.DataFrame, por_seccion: dict[str, pd.DataFrame], config: dict) -> dict:
    """Estados del escenario base en cada franja y en las dos a la vez (H3 con la franja de tarde).

    `por_seccion[franja]`: mejor tiempo por sección de la matriz de esa franja. Devuelve un
    diccionario {nombre de escenario: estados por modo}; el modo a pie no depende de la franja.
    """
    base = escenarios(config)[0]
    por_franja = {f: estados_escenario(unidades, tabla, base, config) for f, tabla in por_seccion.items()}
    resultado = {f"franja_{f}": por_modo for f, por_modo in por_franja.items()}
    if {"9_13", "16_20"} <= set(por_franja):
        pie = por_franja["9_13"]["pie"]
        transporte = ambas_franjas(por_franja["9_13"]["transporte"], por_franja["16_20"]["transporte"])
        resultado["ambas_franjas"] = {"pie": pie, "transporte": transporte, "al_menos_uno": al_menos_uno(pie, transporte)}
    return resultado


def con_centros_extra(unidades: pd.DataFrame, pie_extra: pd.DataFrame) -> pd.DataFrame:
    """Unidades con el tiempo a pie mínimo entre los centros base y unos centros extra.

    `pie_extra`: columna `unidad` y las columnas `tiempo_pie_*` hacia los centros extra (solo
    para las unidades que pueden cambiar). Nunca empeora un tiempo.
    """
    extra = pie_extra.set_index("unidad")
    tabla = unidades.copy()
    for columna in [c for c in extra.columns if c.startswith("tiempo_pie_")]:
        tabla[columna] = np.fmin(tabla[columna].to_numpy(dtype=float),
                                 tabla["unidad"].map(extra[columna]).to_numpy(dtype=float))
    return tabla


def mejor_por_seccion(matriz: pd.DataFrame) -> pd.DataFrame:
    """Mejor p50 y mejor p80 de cada sección origen entre todos los centros.

    El p80 es el menor p80 entre centros, que puede ser de un centro distinto del del p50.
    """
    return (matriz.groupby("from_id")[["travel_time_p50", "travel_time_p80"]].min()
            .rename(columns={"travel_time_p50": "p50", "travel_time_p80": "p80"}).rename_axis("cusec"))


def territorios(unidades: pd.DataFrame) -> dict[str, pd.Series]:
    """Máscaras de la Comunidad, Madrid capital y el resto."""
    capital = unidades["cusec"].str.startswith(MADRID_CAPITAL)
    return {"comunidad": pd.Series(True, index=unidades.index), "madrid_capital": capital, "resto": ~capital}


def fila_resumen(poblacion: pd.Series, estados: pd.DataFrame) -> dict:
    """Personas por estado, denominador, porcentajes y no evaluables por motivo (R-MET-01)."""
    por_estado = poblacion.groupby(estados["estado"]).sum()
    cuentas = {e: float(por_estado.get(e, 0.0)) for e in ESTADOS}
    denominador = float(poblacion.sum())
    evaluable = cuentas[CON] + cuentas[SIN]
    motivos = poblacion[estados["estado"] == NO_EVAL].groupby(estados["motivo"]).sum()
    return {**cuentas, "denominador": denominador, "unidad": "personas",
            "pct_con_acceso_sobre_total": 100 * cuentas[CON] / denominador if denominador else np.nan,
            "pct_con_acceso_sobre_evaluable": 100 * cuentas[CON] / evaluable if evaluable else np.nan,
            "no_evaluable_por_motivo": json.dumps({k: float(v) for k, v in motivos.items()}, ensure_ascii=False)}


def resumir(unidades: pd.DataFrame, por_modo: dict[str, pd.DataFrame], escenario: dict) -> list[dict]:
    """Filas de resumen por modo, territorio y grupo de edad, con los supuestos del escenario."""
    supuestos = json.dumps({k: v for k, v in escenario.items() if k != "nombre"}, ensure_ascii=False)
    filas = []
    for modo, estados in por_modo.items():
        for territorio, mascara in territorios(unidades).items():
            for grupo, columna in GRUPOS_EDAD.items():
                filas.append({"escenario": escenario["nombre"], "modo": modo, "territorio": territorio,
                              "grupo_edad": grupo, **fila_resumen(unidades.loc[mascara, columna], estados[mascara]),
                              "supuestos": supuestos})
    return filas


def por_municipio(unidades: pd.DataFrame, por_modo: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Población total por municipio, modo y estado (escenario base)."""
    filas = []
    for modo, estados in por_modo.items():
        tabla = unidades.assign(cumun=unidades["cusec"].str[:5], estado=estados["estado"])
        suma = tabla.pivot_table(index="cumun", columns="estado", values="poblacion_total", aggfunc="sum",
                                 fill_value=0.0)
        filas.append(suma.reindex(columns=list(ESTADOS), fill_value=0.0).assign(modo=modo).reset_index())
    return pd.concat(filas, ignore_index=True)
