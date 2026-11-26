"""Capas del mapa de minutos (SPEC P-27): clases, coherencia con los estados, piezas y tramos."""

import json

import geopandas as gpd
import numpy as np
import pandas as pd
import pytest
import shapely

from cercasalud import capas_mapa

CONFIG = {"primaria": {"pie": {"velocidad_kmh": 3.0, "umbral_min": 15},
                       "transporte": {"umbral_min": 30, "percentil_estado": 50}}}


def test_clases_de_un_tercio_del_umbral_con_el_umbral_en_el_tercer_limite():
    """Siete clases: el paso del azul al cálido cae justo en el umbral."""
    assert capas_mapa.limites_clases(30) == [10, 20, 30, 40, 50, 60]
    assert capas_mapa.limites_clases(15) == [5, 10, 15, 20, 25, 30]
    assert capas_mapa.etiquetas_minutos([5, 10, 15, 20, 25, 30]) == [
        "≤ 5 min", "5–10", "10–15", "15–20", "20–25", "25–30", "> 30"]


def test_clase_limite_incluido_sin_tiempo_en_la_ultima_y_no_evaluable_aparte():
    """El límite cuenta en su clase; sin tiempo, la última; no evaluable, -1 (nunca «lejos»)."""
    valores = pd.Series([0.0, 10.0, 10.5, 30.0, 61.0, np.nan, 5.0])
    evaluable = pd.Series([True] * 6 + [False])
    assert capas_mapa.clase(valores, [10, 20, 30, 40, 50, 60], evaluable).tolist() == [0, 0, 1, 2, 6, 6, -1]


def test_minutos_en_transporte_son_el_menor_entre_andar_y_la_seccion():
    """Mismas reglas que `acceso`: mínimo de ir andando y del tiempo de la sección; sin matriz, a pie."""
    unidades = pd.DataFrame({"unidad": ["u1", "u2", "u3"], "cusec": ["s1", "s1", "s2"],
                             "tiempo_pie_3.0": [40.0, 12.0, np.nan]})
    por_seccion = {"9_13": pd.DataFrame({"p50": [25.0], "p80": [35.0]}, index=pd.Index(["s1"], name="cusec"))}
    tabla = capas_mapa.minutos_unidades(unidades, por_seccion, CONFIG)
    assert tabla["min_tp_9_13"].tolist()[:2] == [25.0, 12.0] and np.isnan(tabla["min_tp_9_13"].iloc[2])
    assert tabla["min_pie"].tolist()[:2] == [40.0, 12.0]


def test_incoherencia_entre_minutos_y_estado_se_detecta():
    """Una unidad evaluable con minutos dentro del umbral pero sin acceso es una incoherencia; las no
    evaluables no cuentan."""
    catalogo = capas_mapa.variables_minutos(CONFIG, ["9_13"])
    tabla = pd.DataFrame({"min_pie": [10.0, 20.0, np.nan], "min_tp_9_13": [10.0, 20.0, np.nan],
                          "estado_pie": ["con_acceso", "sin_opcion_verificada", "no_evaluable"],
                          "estado_transporte": ["con_acceso", "sin_opcion_verificada", "no_evaluable"]})
    assert capas_mapa.incoherencias(tabla, catalogo) == {"min_pie": 0, "min_tp_9_13": 1}


def test_pieza_de_una_unidad_es_su_celda_recortada_por_su_seccion():
    """Una celda partida entre dos secciones da dos piezas de 50 × 100 m; sin sección, la celda entera."""
    secciones = gpd.GeoDataFrame({"CUSEC": ["s1", "s2"]},
                                 geometry=[shapely.box(0, 0, 50, 1000), shapely.box(50, 0, 1000, 1000)],
                                 crs=capas_mapa.CRS_CALCULO)
    unidades = pd.DataFrame({"celda": ["0_0", "0_0", "3_3"], "cusec": ["s1", "s2", "s9"]})
    areas = capas_mapa.piezas_unidades(unidades, secciones).area.round().tolist()
    assert areas == [5000.0, 5000.0, 10000.0]


def test_contornos_en_grados_ordenados_de_mayor_a_menor_superficie():
    """Cada parte es un anillo JSON en WGS84; las piezas pequeñas quedan después (se dibujan encima)."""
    piezas = gpd.GeoSeries([shapely.box(440000, 4470000, 440050, 4470100),
                            shapely.box(440000, 4470200, 440100, 4470300)], crs=capas_mapa.CRS_CALCULO)
    tabla = capas_mapa.contornos(piezas)
    assert tabla["fila"].tolist() == [1, 0]
    anillo = json.loads(tabla["contorno"].iloc[0])
    assert len(anillo) == 5 and -4 < anillo[0][0] < -3 and 40 < anillo[0][1] < 41


def test_tramos_suman_cien_sobre_la_poblacion_evaluable():
    """Los porcentajes de las clases suman 100 sobre la población evaluable; el no evaluable va sobre el total."""
    tabla = pd.DataFrame({"cusec": ["2807901001", "2807902001", "2800101001", "2800101001"],
                          "poblacion_total": [100.0, 300.0, 50.0, 50.0], "clase_min_pie": [0, 1, 1, -1]})
    resultado = capas_mapa.tramos(tabla, ["clase_min_pie"])
    comunidad = resultado[resultado["tipo"] == "comunidad"].set_index("clase")["pct"]
    assert comunidad[0] == pytest.approx(100 / 450 * 100) and comunidad[1] == pytest.approx(350 / 450 * 100)
    assert comunidad[-1] == pytest.approx(10.0)
    assert set(resultado.loc[resultado["tipo"] == "distrito", "codigo"]) == {"01", "02"}


def test_porcentaje_sin_opcion_por_municipio_sobre_la_poblacion_total():
    """Denominador = toda la población (también la no evaluable); clase 0 solo si es exactamente 0 %."""
    territorio = pd.DataFrame({"pie_con_acceso": [90.0, 100.0], "pie_sin_opcion_verificada": [5.0, 0.0],
                               "pie_no_evaluable": [5.0, 0.0], "transporte_con_acceso": [95.0, 100.0],
                               "transporte_sin_opcion_verificada": [0.5, 0.0], "transporte_no_evaluable": [4.5, 0.0]})
    resultado = capas_mapa.porcentajes_sin_opcion(territorio)
    assert resultado["pct_sin_pie"].tolist() == [5.0, 0.0] and resultado["clase_pct_sin_pie"].tolist() == [2, 0]
    assert resultado["clase_pct_sin_transporte"].tolist() == [1, 0]


def test_nombre_legible_de_municipio():
    assert capas_mapa.nombre_legible("Rozas de Madrid, Las") == "Las Rozas de Madrid"
    assert capas_mapa.nombre_legible("Getafe") == "Getafe"
