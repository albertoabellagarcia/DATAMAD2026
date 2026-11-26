"""Formato del comparador, los resultados y la ficha (pantallas 5 a 7): sin cifras nuevas."""

import json

import pandas as pd

from cercasalud import vista_resultados

FILA_TP = {"objetivo": "total", "k": 3, "milp_estado": "optimo", "milp_ganancia": 51489.16,
           "regla_simple_ganancia": 9421.0, "robustez_ganancia_tp_p80": 33467.16, "reoptimo_ganancia_tp_p80": 41636.57,
           "reoptimo_estado_tp_p80": "optimo", "robustez_ganancia_franja_16_20": 51489.16}


def test_barras_del_comparador_son_las_dos_ganancias_sin_sumar():
    """Una barra por opción con su propia cifra: la cartera no se apila sobre la regla simple."""
    barras = vista_resultados.barras_comparacion(FILA_TP, "a_transporte")
    assert barras["Opción"].tolist() == ["Regla simple", "Cartera calculada"]
    assert barras["Personas"].tolist() == [9421, 51489]


def test_barras_de_b1_en_la_peor_hora():
    fila = {"milp_peor_hora_antes": 87621.6, "regla_simple_peor_hora": 165447.6, "milp_peor_hora_despues": 165447.6,
            "cota_todos_abiertos_peor_hora": 689461.1}
    barras = vista_resultados.barras_comparacion(fila, "b1")
    assert barras["Personas"].tolist() == [87622, 165448, 165448, 689461]


def test_escenarios_de_la_cartera_salen_de_sus_columnas_y_no_inventa_los_que_faltan():
    """Base primero; misma cartera = robustez_*, reoptimizada = reoptimo_*; sin columna, vacío."""
    tabla = vista_resultados.escenarios_cartera(FILA_TP, "a_transporte").set_index("Escenario")
    assert tabla.loc["Base", "Misma cartera"] == 51489
    p80 = "Percentil 80 de las salidas (en vez de la mediana)"
    assert tabla.loc[p80, "Misma cartera"] == 33467 and tabla.loc[p80, "Mejor cartera para ese escenario"] == 41637
    assert pd.isna(tabla.loc["Franja de 16 a 20 h", "Mejor cartera para ese escenario"])
    assert pd.isna(tabla.loc["Transporte 6 min más lento", "Misma cartera"])


def test_escenarios_a_pie_con_los_nombres_de_columna_de_la_tabla_a_pie():
    fila = {"milp_ganancia": 92368.2, "milp_estado": "optimo", "robustez_ganancia_2.4": 56450.0,
            "reoptimo_ganancia_velocidad_2.4": 60000.0, "reoptimo_estado_velocidad_2.4": "optimo"}
    tabla = vista_resultados.escenarios_cartera(fila, "a_pie").set_index("Escenario")
    assert tabla.loc["A pie a 2,4 km/h", "Misma cartera"] == 56450
    assert tabla.loc["A pie a 2,4 km/h", "Mejor cartera para ese escenario"] == 60000


def test_municipios_de_las_zonas_en_orden_y_con_nombre():
    detalle = pd.DataFrame({"orden": [2, 1, 3], "municipio": [28006, 28022, 28123]})
    nombres = {"28022": "Boadilla del Monte", "28006": "Alcobendas", "28123": "Rivas-Vaciamadrid"}
    assert vista_resultados.municipios_de_zonas(detalle, nombres) == "Boadilla del Monte, Alcobendas y Rivas-Vaciamadrid"
    assert vista_resultados.municipios_de_zonas(detalle.head(1), nombres) == "Alcobendas"


def test_horas_de_b1_agrupadas_en_tramos():
    """Bloques de una hora consecutivos se juntan: 14, 15, 16, 17 y 20 → «14–18 h y 20–21 h»."""
    bloques = [{"mercado": "Prosperidad", "hora_inicio": h} for h in (14, 15, 16, 17, 20)]
    tabla = vista_resultados.bloques_b1_legibles({"milp_bloques_detalle": json.dumps(bloques)})
    assert tabla.loc[0, "Horas ampliadas"] == "14–18 h y 20–21 h" and tabla.loc[0, "Número de horas"] == 5
    assert vista_resultados.bloques_b1_legibles({"milp_bloques_detalle": "[]"}).empty


def test_condiciones_leidas_de_la_configuracion():
    primaria = {"pie": {"umbral_min": 15, "velocidad_kmh": 3.0},
                "transporte": {"umbral_min": 30, "franja": "09:00-13:00", "percentil_estado": 50}}
    assert vista_resultados.condiciones("a_pie", primaria) == "A pie · 15 min a 3,0 km/h"
    assert "30 min · de 9 a 13 h · percentil 50" in vista_resultados.condiciones("a_transporte", primaria)
    assert "10 min" in vista_resultados.condiciones("b1", primaria, {"umbral_min": 10})


def test_estado_del_solver_tal_cual_y_con_su_lectura():
    assert vista_resultados.texto_estado("optimo").startswith("optimo (")
    assert "no acredita el óptimo" in vista_resultados.texto_estado("tiempo_agotado")


def test_tabla_legible_redondea_personas_y_traduce_columnas():
    tabla = pd.DataFrame({"k": [3], "milp_ganancia": [51489.16], "milp_brecha": [0.00004], "otra": [1]})
    legible = vista_resultados.tabla_legible(tabla, ["k", "milp_ganancia", "milp_brecha", "no_existe"])
    assert list(legible.columns) == ["Zonas (k)", "Ganancia", "Brecha del solver"]
    assert legible.loc[0, "Ganancia"] == 51489 and legible.loc[0, "Brecha del solver"] == 0.00004


def test_barras_html_proporcionales_desde_cero_y_sin_recursos_externos():
    """La barra mayor mide el ancho máximo; la otra, su proporción. Cifras con punto de miles."""
    barras = vista_resultados.barras_comparacion(FILA_TP, "a_transporte")
    html = vista_resultados.barras_html(barras, ancho_max_px=500)
    assert "width:500px" in html and f"width:{round(500 * 9421 / 51489)}px" in html
    assert "51.489" in html and "9.421" in html
    assert "<script" not in html and "http" not in html


def test_para_mostrar_pone_punto_de_miles_y_raya_en_vacios():
    tabla = pd.DataFrame({"k": pd.array([3, 5], dtype="Int64"), "Ganancia": pd.array([51489, None], dtype="Int64"),
                          "Estado": ["optimo", "optimo"]})
    mostrada = vista_resultados.para_mostrar(tabla)
    assert mostrada["Ganancia"].tolist() == ["51.489", "—"] and mostrada["k"].tolist() == ["3", "5"]
    assert mostrada["Estado"].tolist() == ["optimo", "optimo"]


def test_resumen_de_la_ficha_con_cifras_de_la_tabla():
    """Los valores salen de las columnas de la cartera; lo que falta queda «—», no se calcula."""
    fila = {**FILA_TP, "sin_opcion_antes": 289239.7, "sin_opcion_despues": 237750.6,
            "cartera_base_peor_ganancia": 30629.3}
    resumen = dict(vista_resultados.resumen_ficha(fila, "a_transporte", "30 min", "Población total"))
    assert resumen["Ganancia (personas que pasan a tener opción)"] == "51.489"
    assert resumen["Sin opción verificada, después"] == "237.751"
    assert resumen["Peor ganancia de la cartera entre los escenarios calculados"] == "30.629"
    assert resumen["Estado del solver"].startswith("optimo")
    sin_peor = dict(vista_resultados.resumen_ficha(FILA_TP, "a_transporte", "30 min", "Población total"))
    assert sin_peor["Peor ganancia de la cartera entre los escenarios calculados"] == "—"


def test_resumen_de_la_ficha_de_b1():
    fila = {"max_centros": 1, "max_centro_horas": 12, "milp_peor_hora_antes": 8979.1, "milp_peor_hora_despues": 12569.3,
            "regla_simple_peor_hora": 12569.3, "milp_personas_hora_ganadas": 17950.6, "milp_centros": 1,
            "milp_centro_horas": 5, "milp_estado": "optimo", "robustez_laborable_agosto_peor_hora_antes": 9000.0,
            "robustez_laborable_agosto_peor_hora_despues": 12000.0}
    resumen = dict(vista_resultados.resumen_ficha(fila, "b1", "10 min", "Personas de 75 años o más"))
    assert resumen["Actuación que se propone estudiar"].startswith("Ampliar el horario de hasta 1 mercado municipal,")
    assert resumen["Misma cartera en laborable de agosto: peor hora hoy → con la cartera"] == "9.000 → 12.000"
    assert "Misma cartera en fin de semana: peor hora hoy → con la cartera" not in resumen


def test_peor_hora_cero_en_fin_de_semana_se_explica():
    fila = {"max_centros": 3, "max_centro_horas": 12, "milp_estado": "optimo",
            "robustez_fin_de_semana_peor_hora_antes": 0.0, "robustez_fin_de_semana_peor_hora_despues": 0.0,
            "robustez_fin_de_semana_personas_hora": 312713.2}
    resumen = dict(vista_resultados.resumen_ficha(fila, "b1", "10 min", "Población total"))
    valor = resumen["Misma cartera en fin de semana: peor hora hoy → con la cartera"]
    assert valor.startswith("0 → 0 (a alguna hora ningún mercado") and "312.713 personas-hora" in valor


def test_para_mostrar_decimales_con_coma():
    tabla = pd.DataFrame({"Pérdida": [9.4, 0.3, None], "Grande": [1234.5, 0.0, 1.0]})
    mostrada = vista_resultados.para_mostrar(tabla)
    assert mostrada["Pérdida"].tolist() == ["9,4", "0,3", "—"] and mostrada["Grande"].tolist()[0] == "1.234,5"


def test_series_por_cota_en_orden_fijo_con_su_color():
    por_hora = pd.DataFrame({"hora": [12, 12, 12, 13, 13, 13], "cota": ["superior", "acreditable", "central"] * 2,
                             "con_acceso": [700.0, 0.0, 100.0, 650.0, 0.0, 90.0]})
    series, colores = vista_resultados.series_por_cota(por_hora)
    assert list(series.columns) == ["Acreditable (sin supuesto)", "Estimada, cota superior", "Estimada, cota central"]
    assert colores == ["#D73027", "#BDBDBD", "#1A1A1A"] and series.loc[13, "Estimada, cota central"] == 90.0
