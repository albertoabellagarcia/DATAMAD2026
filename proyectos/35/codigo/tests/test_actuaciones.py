"""Preparación de datos de H5: candidatos de 250 m, conjuntos de cobertura y demanda de B1."""

import pandas as pd

from cercasalud import actuaciones
from cercasalud.acceso import CON, NO_EVAL, SIN
from cercasalud.horarios import ABIERTO, CERRADO


def test_candidatos_conservan_la_poblacion():
    """Cada unidad cae en una celda de 250 m; la suma de población de los candidatos es la de las unidades."""
    unidades = pd.DataFrame({"x": [10.0, 60.0, 300.0], "y": [10.0, 90.0, 10.0], "poblacion_total": [5.0, 3.0, 2.0],
                             "poblacion_65_mas": [1.0, 0.0, 1.0]})
    tabla = actuaciones.candidatos(unidades, pd.Series([SIN, CON, SIN]))
    assert len(tabla) == 2 and tabla["poblacion"].sum() == 10.0
    assert tabla.set_index("candidato").loc["z0_0", "sin_opcion_pie_total"] == 5.0
    assert abs(tabla.set_index("candidato").loc["z0_0", "x"] - (10 * 5 + 60 * 3) / 8) < 1e-9


def test_conjuntos_de_cobertura_respetan_el_umbral():
    """Solo entran los candidatos a umbral o menos; una unidad sin pares queda con conjunto vacío."""
    pares = pd.DataFrame({"unidad": ["u1", "u1", "u2"], "candidato": ["a", "b", "a"], "minutos": [10.0, 20.0, 15.0]})
    assert actuaciones.conjuntos_cobertura(pares, pd.Series(["u1", "u2", "u3"]), 15) == [
        frozenset({"a"}), frozenset({"a"}), frozenset()]


def test_demanda_b1_solo_sin_opcion_y_bloques_cerrados():
    """La demanda incluye solo unidades sin opción; los no evaluables no cuentan; los bloques son los cerrados."""
    unidades = pd.DataFrame({"unidad": ["u1", "u2", "u3"], "poblacion_total": [5.0, 7.0, 2.0]})
    estados_b = pd.DataFrame({"unidad": ["u1", "u2", "u3"], "tipo_dia": "laborable_julio", "hora": 14,
                              "estado": [SIN, CON, NO_EVAL], "motivo": ["", "", "horario"]})
    pares = pd.DataFrame({"unidad": ["u1", "u2", "u3"], "refugio": ["r1", "r2", "r1"], "minutos": [5.0, 5.0, 5.0]})
    estados_ref = pd.DataFrame({"refugio": ["r1", "r2"], "tipo_dia": "laborable_julio", "hora": 14,
                                "estado": [CERRADO, ABIERTO]})
    demanda, cubiertos, bloques = actuaciones.demanda_b1(estados_b, pares, estados_ref, unidades,
                                                         "laborable_julio", 10, "poblacion_total")
    assert demanda == [{"hora": 14, "refugios": ["r1"], "peso": 5.0}]
    assert cubiertos == {14: 7.0} and bloques == [("r1", 14)]


def test_cobertura_en_transporte_combina_pie_y_matriz_y_el_margen_solo_toca_la_matriz():
    """Un candidato cubre si se llega andando o con el tiempo de la sección; el margen no alarga ir andando."""
    sin = pd.DataFrame({"unidad": ["u1", "u2"], "cusec": ["s1", "s2"]})
    pares_pie = pd.DataFrame({"unidad": ["u1", "u9"], "candidato": ["a", "c"], "minutos": [12.0, 5.0]})
    pares_tp = pd.DataFrame({"from_id": ["s1", "s2", "s2"], "to_id": ["b", "a", "b"],
                             "travel_time_p50": [28.0, 25.0, 40.0], "travel_time_p80": [33.0, 26.0, 41.0]})
    base = actuaciones.conjuntos_cobertura_transporte(sin, pares_pie, pares_tp, 30)
    assert base == [frozenset({"a", "b"}), frozenset({"a"})]  # u9 no está sin opción: no entra
    # Con 4 min de margen, b (28 + 4) deja de cubrir a u1, pero a sigue cubriéndola andando (12 min).
    margen = actuaciones.conjuntos_cobertura_transporte(sin, pares_pie, pares_tp, 30, margen_min=4)
    assert margen == [frozenset({"a"}), frozenset({"a"})]
    assert actuaciones.conjuntos_cobertura_transporte(sin, pares_pie, pares_tp, 30, percentil=80) == [
        frozenset({"a"}), frozenset({"a"})]


def test_fusionar_equivalentes_no_cambia_la_cobertura_maxima():
    """Los candidatos con las mismas unidades cubiertas se funden; el óptimo es el mismo."""
    import numpy as np

    from cercasalud import optimizacion
    cubre = [frozenset({"a", "b", "c"}), frozenset({"a", "b"}), frozenset({"c", "d"}), frozenset({"d"})]
    pesos = np.array([5.0, 3.0, 4.0, 1.0])
    reducido, equivalentes = actuaciones.fusionar_equivalentes(cubre, {"a": 1.0, "b": 9.0})
    # a y b cubren las unidades 0 y 1: se queda b (más población en su celda).
    assert equivalentes["b"] == ["a"] and "a" not in {c for s in reducido for c in s}
    for k in (1, 2):
        assert optimizacion.cobertura_maxima(reducido, pesos, k)["ganancia"] == optimizacion.enumeracion_exhaustiva(
            cubre, pesos, k)


def test_celda_candidato_coincide_con_candidatos():
    """La celda de cada unidad es el identificador de su candidato."""
    unidades = pd.DataFrame({"x": [10.0, 300.0], "y": [10.0, 10.0], "poblacion_total": [5.0, 2.0],
                             "poblacion_65_mas": [1.0, 1.0]})
    assert list(actuaciones.celda_candidato(unidades)) == ["z0_0", "z1_0"]
    assert set(actuaciones.candidatos(unidades, pd.Series([SIN, SIN]))["candidato"]) == {"z0_0", "z1_0"}
