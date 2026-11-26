"""B por unidad y hora con cotas (R-TMP-03, R-TMP-04), C (R-CMP-02, R-CMP-03) y unión sin
duplicados (R-MET-02). Datos sintéticos.
"""

import numpy as np
import pandas as pd

from cercasalud import refugios
from cercasalud.acceso import CON, NO_EVAL, SIN
from cercasalud.horarios import ABIERTO, CERRADO, HORAS, PENDIENTE, TIPOS_DIA


def caso(n: int = 60, semilla: int = 5):
    """Unidades (mitad en la capital), refugios con estados al azar y pares a distancias al azar."""
    azar = np.random.default_rng(semilla)
    unidades = pd.DataFrame({"unidad": [f"u{i}" for i in range(n)],
                             "cusec": [("28079" if i % 2 else "28005") + f"{i:05d}" for i in range(n)],
                             "enganchado": [i != 1 for i in range(n)],
                             "poblacion_total": azar.uniform(1, 30, n)})
    for columna, factor in (("poblacion_65_mas", .2), ("poblacion_75_mas", .1), ("poblacion_85_mas", .03)):
        unidades[columna] = unidades["poblacion_total"] * factor
    estados = pd.DataFrame([{"refugio": f"r{r}", "tipo_dia": t, "hora": h,
                             "estado": azar.choice([ABIERTO, CERRADO, PENDIENTE]), "acceso_verificado": False}
                            for r in range(5) for t in TIPOS_DIA for h in HORAS])
    pares = pd.DataFrame([{"unidad": f"u{i}", "refugio": f"r{r}", "minutos": float(azar.integers(0, 16))}
                          for i in range(n) for r in range(5) if azar.uniform() < .5])
    return unidades, pares, estados


def con_acceso(tabla: pd.DataFrame, unidades: pd.DataFrame) -> pd.Series:
    """Población con acceso por tipo de día y hora."""
    pob = tabla.merge(unidades[["unidad", "poblacion_total"]], on="unidad")
    return pob[pob["estado"] == CON].groupby(["tipo_dia", "hora"])["poblacion_total"].sum() \
        .reindex(pd.MultiIndex.from_product([TIPOS_DIA, HORAS]), fill_value=0.0)


def test_cotas_ordenadas_y_acreditable_nula_sin_acceso_verificado():
    """acreditable ≤ inferior ≤ central ≤ superior en cada hora; sin acceso verificado, acreditable = 0."""
    unidades, pares, estados = caso()
    territorio = refugios.territorio_b(unidades)
    valores = {c: con_acceso(refugios.estados_b(unidades, pares, estados, 10, c, territorio), unidades)
               for c in refugios.COTAS}
    assert (valores["acreditable"] == 0).all()
    for menor, mayor in zip(refugios.COTAS, refugios.COTAS[1:]):
        assert (valores[menor] <= valores[mayor] + 1e-9).all(), (menor, mayor)


def test_fuera_del_inventario_y_sin_red_no_evaluable():
    """Fuera de la capital: no evaluable (inventario); sin enganche: no evaluable (conexión)."""
    unidades, pares, estados = caso()
    tabla = refugios.estados_b(unidades, pares, estados, 10, "central", refugios.territorio_b(unidades))
    fuera = tabla[tabla["unidad"] == "u0"]
    assert set(fuera["estado"]) == {NO_EVAL} and set(fuera["motivo"]) == {"inventario"}
    assert set(tabla.loc[tabla["unidad"] == "u1", "motivo"]) == {"conexion"}


def test_mas_umbral_nunca_reduce_la_cobertura():
    """Con 5, 10 y 15 min, la población con acceso no baja en ninguna hora (R-MET-03)."""
    unidades, pares, estados = caso()
    territorio = refugios.territorio_b(unidades)
    serie = [con_acceso(refugios.estados_b(unidades, pares, estados, u, "central", territorio), unidades)
             for u in (5, 10, 15)]
    assert (serie[0] <= serie[1] + 1e-9).all() and (serie[1] <= serie[2] + 1e-9).all()


def test_metricas_sin_duplicar_personas():
    """Personas únicas ≤ denominador; personas-hora ≥ peor hora × 1; estados por hora suman la población."""
    unidades, pares, estados = caso()
    tabla = refugios.estados_b(unidades, pares, estados, 10, "central", refugios.territorio_b(unidades))
    por_hora, resumen = refugios.metricas_b(tabla, unidades, {"nombre": "prueba"})
    total = unidades["poblacion_total"].sum()
    for fila in [f for f in por_hora if f["grupo_edad"] == "total"]:
        assert abs(fila[CON] + fila[SIN] + fila[NO_EVAL] - total) < 1e-6
    for fila in [f for f in resumen if f["grupo_edad"] == "total"]:
        assert fila["personas_unicas_con_alguna_hora"] <= fila["denominador"] + 1e-9
        assert fila["personas_hora_con_acceso"] >= fila["con_acceso_peor_hora"] - 1e-9


def test_c_solo_donde_a_y_b_son_evaluables_y_union_sin_duplicar():
    """C exige las dos carencias en la misma unidad; si una no es evaluable, C tampoco (R-CMP-03)."""
    a = pd.DataFrame({"unidad": ["u1", "u2", "u3", "u4"], "estado": [SIN, SIN, CON, SIN],
                      "motivo": ["", "", "", ""]})
    b = pd.DataFrame({"unidad": ["u1", "u2", "u3", "u4"], "estado": [SIN, CON, SIN, NO_EVAL],
                      "motivo": ["", "", "", "inventario"]})
    c = refugios.estados_c(a, b).set_index("unidad")
    assert list(c["estado"]) == ["carencia_coincidente", "sin_coincidencia", "sin_coincidencia", NO_EVAL]
    assert c.loc["u4", "motivo"] == "b_inventario"
    union = refugios.union_con_acceso(a, b)
    assert union.sum() <= (a["estado"] == CON).sum() + (b["estado"] == CON).sum()
    assert list(union) == [False, True, True, False]


def test_c_por_hora_repite_c_en_cada_hora_y_conserva_la_poblacion():
    """Una fila por tipo de día, hora y grupo; los tres estados suman la población de cada hora."""
    unidades = pd.DataFrame({"unidad": ["u1", "u2", "u3"], "poblacion_total": [5.0, 7.0, 2.0]})
    estado_a = pd.DataFrame({"unidad": ["u1", "u2", "u3"], "estado": [SIN, SIN, CON], "motivo": ""})
    estados_b = pd.DataFrame({"unidad": ["u1", "u2", "u3"] * 2, "tipo_dia": "laborable_julio",
                              "hora": [12, 12, 12, 13, 13, 13], "estado": [SIN, CON, SIN, SIN, SIN, NO_EVAL],
                              "motivo": ["", "", "", "", "", "inventario"]})
    filas = refugios.c_por_hora(estado_a, estados_b, unidades, {"total": "poblacion_total"})
    assert [(f["hora"], f["carencia_coincidente"]) for f in filas] == [(12, 5.0), (13, 12.0)]
    assert all(f["carencia_coincidente"] + f["sin_coincidencia"] + f["no_evaluable"] == 14.0 for f in filas)
