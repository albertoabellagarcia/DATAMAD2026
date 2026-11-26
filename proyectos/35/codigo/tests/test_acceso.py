"""Estados de acceso a primaria (H3): conservación, «al menos uno» sin duplicar, monotonía
(R-MET-03), esquema (R-MET-01) y no evaluables. Datos sintéticos.
"""

import json

import numpy as np
import pandas as pd

from cercasalud import acceso
from cercasalud.configuracion import leer_config

CONFIG = leer_config()


def unidades_sinteticas(n: int = 400, semilla: int = 7) -> pd.DataFrame:
    """Unidades con tiempos a pie coherentes entre velocidades (más rápido, menos tiempo)."""
    azar = np.random.default_rng(semilla)
    t30 = np.round(azar.uniform(0, 70, n))
    t30[t30 > 60] = np.nan  # fuera del radio de cálculo
    tabla = pd.DataFrame({
        "unidad": [f"u{i}" for i in range(n)],
        "cusec": [("28079" if i % 2 else "28001") + f"{i % 20:05d}" for i in range(n)],
        "tiempo_pie_3.0": t30, "tiempo_pie_2.4": np.ceil(t30 * 1.25), "tiempo_pie_3.6": np.floor(t30 / 1.2),
        "enganchado": azar.uniform(size=n) > 0.02, "recta_m": azar.uniform(50, 3000, n),
        "poblacion_total": azar.uniform(1, 50, n),
    })
    tabla["poblacion_65_mas"] = tabla["poblacion_total"] * 0.2
    tabla["poblacion_75_mas"] = tabla["poblacion_total"] * 0.1
    tabla["poblacion_85_mas"] = tabla["poblacion_total"] * 0.03
    for v in ("2.4", "3.6"):
        tabla.loc[tabla["tiempo_pie_3.0"].isna(), f"tiempo_pie_{v}"] = np.nan
    return tabla


def matriz_sintetica(unidades: pd.DataFrame, semilla: int = 3) -> pd.DataFrame:
    """Mejor p50 y p80 por sección para la mitad de las secciones (el resto, sin matriz)."""
    secciones = sorted(unidades["cusec"].unique())[::2]
    azar = np.random.default_rng(semilla)
    p50 = np.round(azar.uniform(5, 60, len(secciones)))
    return pd.DataFrame({"p50": p50, "p80": p50 + 3}, index=pd.Index(secciones, name="cusec"))


def cobertura(unidades, matriz, escenario, modo) -> float:
    """Población con acceso en un modo y escenario."""
    estados = acceso.estados_escenario(unidades, matriz, escenario, CONFIG)[modo]
    return float(unidades.loc[estados["estado"] == acceso.CON, "poblacion_total"].sum())


def test_los_tres_estados_suman_el_denominador():
    """En cada fila, con acceso + sin opción + no evaluable = población del territorio y grupo."""
    unidades = unidades_sinteticas()
    matriz = matriz_sintetica(unidades)
    base = acceso.escenarios(CONFIG)[0]
    filas = acceso.resumir(unidades, acceso.estados_escenario(unidades, matriz, base, CONFIG), base)
    for fila in filas:
        suma = fila[acceso.CON] + fila[acceso.SIN] + fila[acceso.NO_EVAL]
        assert abs(suma - fila["denominador"]) < 1e-6


def test_esquema_de_resultado():
    """Cada fila lleva numerador, denominador, unidad, no evaluables y supuestos (R-MET-01)."""
    unidades = unidades_sinteticas()
    base = acceso.escenarios(CONFIG)[0]
    fila = acceso.resumir(unidades, acceso.estados_escenario(unidades, matriz_sintetica(unidades), base, CONFIG),
                          base)[0]
    for campo in (acceso.CON, "denominador", "unidad", acceso.NO_EVAL, "no_evaluable_por_motivo", "supuestos"):
        assert campo in fila
    assert fila["unidad"] == "personas"
    assert json.loads(fila["supuestos"])["umbral_tp_min"] == CONFIG["primaria"]["transporte"]["umbral_min"]


def test_al_menos_uno_no_duplica_personas():
    """La cobertura combinada está entre el máximo de los dos modos y su suma."""
    unidades = unidades_sinteticas()
    matriz = matriz_sintetica(unidades)
    base = acceso.escenarios(CONFIG)[0]
    pie, tp, algun = (cobertura(unidades, matriz, base, m) for m in acceso.MODOS)
    assert max(pie, tp) <= algun + 1e-9 <= pie + tp + 1e-9
    assert algun <= unidades["poblacion_total"].sum()


def test_monotonia_de_umbrales_y_velocidades():
    """Más umbral o más velocidad nunca reducen la cobertura; más margen nunca la aumenta."""
    unidades = unidades_sinteticas()
    matriz = matriz_sintetica(unidades)
    base = acceso.escenarios(CONFIG)[0]
    for clave, valores, modo in (("umbral_pie_min", (10, 15, 20), "pie"),
                                 ("velocidad_kmh", (2.4, 3.0, 3.6), "pie"),
                                 ("umbral_tp_min", (20, 30, 45), "transporte")):
        coberturas = [cobertura(unidades, matriz, {**base, clave: v}, modo) for v in valores]
        assert coberturas == sorted(coberturas), clave
    margenes = [cobertura(unidades, matriz, {**base, "margen_tp_min": m}, "transporte") for m in (0, 2, 4, 6)]
    assert margenes == sorted(margenes, reverse=True)


def test_transporte_sin_matriz_usa_el_tiempo_a_pie():
    """En una sección sin matriz, el tiempo en transporte es el tiempo a pie a 3,0 km/h."""
    unidades = unidades_sinteticas()
    matriz = matriz_sintetica(unidades)
    sin_matriz = ~unidades["cusec"].isin(matriz.index)
    tiempo = acceso.tiempo_transporte(unidades, matriz["p50"], 3.0)
    pd.testing.assert_series_equal(tiempo[sin_matriz], unidades.loc[sin_matriz, "tiempo_pie_3.0"],
                                   check_names=False)


def test_unidad_sin_conexion_no_es_evaluable_en_ningun_modo():
    """Una unidad que no engancha a la red es no evaluable (conexión) a pie, en transporte y combinada."""
    unidades = unidades_sinteticas()
    unidades.loc[0, "enganchado"] = False
    estados = acceso.estados_escenario(unidades, matriz_sintetica(unidades), acceso.escenarios(CONFIG)[0], CONFIG)
    for modo in acceso.MODOS:
        assert estados[modo].loc[0, "estado"] == acceso.NO_EVAL
        assert estados[modo].loc[0, "motivo"] == "conexion"


def test_margen_no_se_suma_a_ir_andando():
    """En una sección sin matriz, el margen de sesgo no cambia el estado en transporte."""
    unidades = unidades_sinteticas()
    matriz = matriz_sintetica(unidades)
    sin_matriz = ~unidades["cusec"].isin(matriz.index)
    base = acceso.escenarios(CONFIG)[0]
    con_margen = acceso.estados_escenario(unidades, matriz, {**base, "margen_tp_min": 6}, CONFIG)["transporte"]
    sin_margen = acceso.estados_escenario(unidades, matriz, base, CONFIG)["transporte"]
    pd.testing.assert_series_equal(con_margen.loc[sin_matriz, "estado"], sin_margen.loc[sin_matriz, "estado"])


def test_modo_degradado_sin_motor_de_transporte():
    """Sin matriz, el transporte es no evaluable (motor) y la combinada se apoya solo en ir a pie (R-RED-05)."""
    unidades = unidades_sinteticas()
    estados = acceso.estados_escenario(unidades, None, acceso.escenarios(CONFIG)[0], CONFIG)
    assert set(estados["transporte"]["motivo"]) == {"motor"}
    con_pie = estados["pie"]["estado"] == acceso.CON
    assert (estados["al_menos_uno"]["estado"][con_pie] == acceso.CON).all()
    assert (estados["al_menos_uno"]["estado"][~con_pie] == acceso.NO_EVAL).all()


def test_mejor_por_seccion_toma_el_minimo_de_cada_percentil():
    """El mejor p50 y el mejor p80 se toman por separado entre los centros de la sección."""
    matriz = pd.DataFrame({"from_id": ["s1", "s1"], "to_id": ["a", "b"],
                           "travel_time_p50": [20.0, 25.0], "travel_time_p80": [30.0, 26.0]})
    mejor = acceso.mejor_por_seccion(matriz)
    assert (mejor.loc["s1", "p50"], mejor.loc["s1", "p80"]) == (20.0, 26.0)


def test_centros_extra_solo_mejoran_tiempos():
    """Con centros extra, cada tiempo a pie es el mínimo; las unidades sin dato extra no cambian."""
    unidades = unidades_sinteticas()
    extra = pd.DataFrame({"unidad": ["u0", "u1"], "tiempo_pie_3.0": [0.0, np.nan]})
    tabla = acceso.con_centros_extra(unidades, extra)
    assert tabla.loc[0, "tiempo_pie_3.0"] == 0.0
    pd.testing.assert_series_equal(tabla["tiempo_pie_3.0"].iloc[1:], unidades["tiempo_pie_3.0"].iloc[1:])
    pd.testing.assert_series_equal(tabla["tiempo_pie_2.4"], unidades["tiempo_pie_2.4"])


def test_escenarios_cambian_un_solo_supuesto():
    """Cada sensibilidad difiere del escenario base en un único parámetro."""
    lista = acceso.escenarios(CONFIG)
    base = {k: v for k, v in lista[0].items() if k != "nombre"}
    for esc in lista[1:]:
        distintos = [k for k, v in base.items() if esc[k] != v]
        assert len(distintos) == 1, esc["nombre"]


def test_ambas_franjas_exige_acceso_en_las_dos():
    """Con acceso solo si lo tiene en las dos franjas; lo no evaluable manda; nunca más que una sola franja."""
    manana = pd.DataFrame({"estado": [acceso.CON, acceso.CON, acceso.SIN, acceso.NO_EVAL],
                           "motivo": ["", "", "", "conexion"]})
    tarde = pd.DataFrame({"estado": [acceso.CON, acceso.SIN, acceso.CON, acceso.CON], "motivo": ""})
    ambas = acceso.ambas_franjas(manana, tarde)
    assert list(ambas["estado"]) == [acceso.CON, acceso.SIN, acceso.SIN, acceso.NO_EVAL]
    assert ambas.loc[3, "motivo"] == "conexion"


def test_estados_franjas_ambas_no_supera_ninguna_franja():
    """La cobertura en las dos franjas es menor o igual que en cada una (datos sintéticos)."""
    unidades = unidades_sinteticas()
    manana = matriz_sintetica(unidades, semilla=3)
    tarde = matriz_sintetica(unidades, semilla=5)
    todos = acceso.estados_franjas(unidades, {"9_13": manana, "16_20": tarde}, CONFIG)
    def con(nombre):
        return float(unidades.loc[todos[nombre]["transporte"]["estado"] == acceso.CON, "poblacion_total"].sum())
    assert con("ambas_franjas") <= min(con("franja_9_13"), con("franja_16_20"))
    base = acceso.estados_escenario(unidades, manana, acceso.escenarios(CONFIG)[0], CONFIG)
    assert (todos["franja_9_13"]["transporte"]["estado"] == base["transporte"]["estado"]).all()
