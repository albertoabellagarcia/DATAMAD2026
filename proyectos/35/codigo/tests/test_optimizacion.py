"""Optimización (H5): coincidencia con la enumeración (R-OPT-02), sin doble conteo (R-OPT-03),
estados del solver (R-OPT-01, R-OPT-04, R-OPS-02) y B1 en dos etapas (R-OPT-06).
"""

import numpy as np

from cercasalud import optimizacion as opt


def caso_a(n: int = 40, candidatos: int = 8, semilla: int = 1):
    """Unidades sin opción con conjuntos de candidatos que las cubren, al azar."""
    azar = np.random.default_rng(semilla)
    cubre = [frozenset(f"c{j}" for j in range(candidatos) if azar.uniform() < .2) for _ in range(n)]
    return cubre, azar.uniform(1, 20, n)


def test_milp_coincide_con_la_enumeracion_exhaustiva():
    """En instancias pequeñas, la ganancia del MILP es la de la enumeración (R-OPT-02)."""
    for semilla in range(5):
        cubre, pesos = caso_a(semilla=semilla)
        for k in (1, 2, 3):
            resultado = opt.cobertura_maxima(cubre, pesos, k, limite_s=30)
            assert resultado["estado"] == opt.OPTIMO
            assert abs(resultado["ganancia"] - opt.enumeracion_exhaustiva(cubre, pesos, k)) < 1e-6
            assert abs(resultado["ganancia"] - opt.ganancia_de(cubre, pesos, resultado["elegidos"])) < 1e-6


def test_nadie_cuenta_dos_veces():
    """Una unidad cubierta por dos candidatos elegidos suma su población una sola vez (R-OPT-03)."""
    cubre = [frozenset({"a", "b"}), frozenset({"a"}), frozenset({"b"})]
    resultado = opt.cobertura_maxima(cubre, np.array([10.0, 1.0, 1.0]), 2, limite_s=10)
    assert resultado["ganancia"] == 12.0


def test_sin_ganancia_no_es_un_error():
    """Si ningún candidato cubre a nadie sin opción, el estado es «sin_ganancia» con su causa (R-OPT-04)."""
    resultado = opt.cobertura_maxima([frozenset(), frozenset()], np.array([5.0, 3.0]), 3)
    assert resultado["estado"] == opt.SIN_GANANCIA and resultado["causa"]


def test_registro_del_solver():
    """El resultado registra estado, brecha, tolerancia, candidatos y límite de tiempo (R-OPT-01, R-OPS-02)."""
    cubre, pesos = caso_a()
    resultado = opt.cobertura_maxima(cubre, pesos, 2, limite_s=5)
    for campo in ("estado", "brecha", "tolerancia_gap", "candidatos", "limite_s", "k"):
        assert campo in resultado


def test_regla_simple_ordena_por_poblacion_local():
    """La regla de comparación elige las celdas con más población sin opción en su interior."""
    assert opt.regla_simple({"a": 5, "b": 9, "c": 1}, 2) == ["b", "a"]


def test_b1_prioriza_la_peor_hora_y_despues_las_personas_hora():
    """Caso construido (R-OPT-06): con un solo bloque, se abre la hora peor aunque otra hora gane más personas."""
    cubiertos = {14: 10.0, 15: 50.0}
    demanda = [{"hora": 14, "peso": 5.0, "refugios": ["r1"]}, {"hora": 15, "peso": 40.0, "refugios": ["r1"]}]
    bloques = [("r1", 14), ("r1", 15)]
    resultado = opt.ampliar_horas(demanda, cubiertos, bloques, max_centros=1, max_centro_horas=1, limite_s=10)
    assert resultado["bloques"] == [("r1", 14)]
    assert resultado["peor_hora_despues"] == 15.0
    # con dos bloques, se abren los dos y las personas-hora suben a 45
    dos = opt.ampliar_horas(demanda, cubiertos, bloques, max_centros=1, max_centro_horas=2, limite_s=10)
    assert sorted(dos["bloques"]) == bloques and abs(dos["personas_hora_ganadas"] - 45.0) < 1e-6


def test_evaluador_y_regla_simple_de_b1():
    """El evaluador reproduce el MILP; la regla simple no supera al MILP en la peor hora."""
    cubiertos = {14: 10.0, 15: 50.0}
    demanda = [{"hora": 14, "peso": 5.0, "refugios": ["r1"]}, {"hora": 15, "peso": 40.0, "refugios": ["r2"]}]
    bloques = [("r1", 14), ("r2", 15)]
    milp_b1 = opt.ampliar_horas(demanda, cubiertos, bloques, max_centros=1, max_centro_horas=1, limite_s=10)
    evaluado = opt.evaluar_b1(demanda, cubiertos, milp_b1["bloques"])
    assert evaluado["peor_hora"] == milp_b1["peor_hora_despues"]
    regla = opt.regla_simple_b1(demanda, cubiertos, bloques, {"r1": 5.0, "r2": 40.0}, 1, 1)
    assert regla == [("r2", 15)]
    assert opt.evaluar_b1(demanda, cubiertos, regla)["peor_hora"] <= evaluado["peor_hora"]


def test_b1_no_depende_de_la_escala_de_la_poblacion():
    """Multiplicar toda la población por 100.000 da los mismos bloques y cifras proporcionales."""
    cubiertos = {14: 10.0, 15: 50.0, 16: 30.0}
    demanda = [{"hora": 14, "peso": 5.0, "refugios": ["r1"]}, {"hora": 15, "peso": 40.0, "refugios": ["r1", "r2"]},
               {"hora": 16, "peso": 25.0, "refugios": ["r2"]}]
    bloques = [("r1", 14), ("r1", 15), ("r2", 15), ("r2", 16)]
    pequeno = opt.ampliar_horas(demanda, cubiertos, bloques, 2, 2, limite_s=10)
    factor = 1e5
    grande = opt.ampliar_horas([{**d, "peso": d["peso"] * factor} for d in demanda],
                               {h: v * factor for h, v in cubiertos.items()}, bloques, 2, 2, limite_s=10)
    assert sorted(grande["bloques"]) == sorted(pequeno["bloques"])
    assert abs(grande["peor_hora_despues"] - pequeno["peor_hora_despues"] * factor) < 1e-3 * factor


def test_b1_respeta_el_limite_de_centros():
    """Con un máximo de 1 centro, no se abren bloques de dos refugios distintos."""
    cubiertos = {14: 0.0}
    demanda = [{"hora": 14, "peso": 5.0, "refugios": ["r1"]}, {"hora": 14, "peso": 6.0, "refugios": ["r2"]}]
    resultado = opt.ampliar_horas(demanda, cubiertos, [("r1", 14), ("r2", 14)], max_centros=1, max_centro_horas=2)
    assert resultado["centros"] == 1 and resultado["bloques"] == [("r2", 14)]


def test_alternativas_b1_distinguen_empate_de_eleccion_firme():
    """Sin r1 entra su gemelo r2 (empate, pérdida 0 %); sin r3 no hay sustituto (pérdida del 100 % de lo que aporta)."""
    cubiertos = {14: 0.0, 15: 0.0}
    demanda = [{"hora": 14, "peso": 10.0, "refugios": ["r1", "r2"]}, {"hora": 15, "peso": 10.0, "refugios": ["r3"]}]
    bloques = [("r1", 14), ("r2", 14), ("r3", 15)]
    elegida = opt.ampliar_horas(demanda, cubiertos, bloques, max_centros=2, max_centro_horas=2, limite_s=10)
    assert elegida["peor_hora_despues"] == 10.0
    alternativas = {a["excluido"]: a for a in opt.alternativas_b1(demanda, cubiertos, bloques, elegida["bloques"], 2, 2,
                                                                  limite_s=10)}
    assert set(alternativas) == {r for r, _ in elegida["bloques"]} and "r3" in alternativas
    assert alternativas["r3"]["perdida_peor_hora_pct"] == 100.0
    assert "r3" not in alternativas["r3"]["refugios"]
    gemelo = alternativas.get("r1") or alternativas["r2"]
    assert gemelo["perdida_peor_hora_pct"] == 0.0 and gemelo["peor_hora_despues"] == 10.0
    for campo in ("estado", "refugios", "peor_hora_despues", "personas_hora_ganadas"):
        assert campo in gemelo


def test_alternativas_b1_sin_ganancia_no_divide_por_cero():
    """Si la cartera elegida no mejora la peor hora, la pérdida es None, no un error."""
    cubiertos = {14: 0.0, 15: 0.0}
    demanda = [{"hora": 14, "peso": 10.0, "refugios": ["r1"]}]
    alternativas = opt.alternativas_b1(demanda, cubiertos, [("r1", 14)], [("r1", 14)], 1, 1, limite_s=10)
    assert alternativas[0]["perdida_peor_hora_pct"] is None and alternativas[0]["refugios"] == []


def test_alternativas_con_nombres_cambia_identificadores_y_conserva_cifras():
    """La ficha recibe nombres de mercado, sin la clave interna `refugios` y con las cifras intactas."""
    from cercasalud.construccion import alternativas_con_nombres
    entrada = [{"excluido": "1", "estado": "optimo", "refugios": ["2", "9"], "peor_hora_despues": 5.0,
                "personas_hora_ganadas": 7.0, "perdida_peor_hora_pct": 1.5}]
    salida = alternativas_con_nombres(entrada, {"1": "Mercado A", "2": "Mercado B"})
    assert salida == [{"excluido": "Mercado A", "mercados": ["Mercado B", "9"], "estado": "optimo",
                       "peor_hora_despues": 5.0, "personas_hora_ganadas": 7.0, "perdida_peor_hora_pct": 1.5}]
    assert "refugios" in entrada[0]  # no modifica la entrada


def test_max_min_coincide_con_la_enumeracion_y_protege_el_peor_escenario():
    """La alternativa max-min maximiza la peor ganancia entre escenarios (comprobado combinación a combinación)."""
    import itertools

    azar = np.random.default_rng(11)
    candidatos = list("abcdefg")
    escenarios = []
    for _ in range(3):
        cubre = [frozenset(azar.choice(candidatos, size=azar.integers(0, 3), replace=False)) for _ in range(25)]
        escenarios.append((cubre, azar.uniform(1, 20, 25)))
    for k in (1, 2, 3):
        mejor = max(min(opt.ganancia_de(c, p, list(combo)) for c, p in escenarios)
                    for tamano in range(1, k + 1) for combo in itertools.combinations(candidatos, tamano))
        resultado = opt.cobertura_max_min(escenarios, k)
        assert resultado["estado"] == opt.OPTIMO
        assert abs(resultado["peor_ganancia"] - mejor) < 1e-6
        assert abs(min(opt.ganancia_de(c, p, resultado["elegidos"]) for c, p in escenarios) - mejor) < 1e-6


def test_robustez_b1_en_otros_tipos_de_dia():
    """La cartera se evalúa con la demanda de cada tipo de día; sin demanda en esa hora no gana nada."""
    from cercasalud.construccion import robustez_b1_tipos_dia
    otros = {"fin_de_semana": ([{"hora": 14, "refugios": ["r1"], "peso": 7.0}], {14: 3.0, 15: 5.0}, []),
             "laborable_agosto": ([], {14: 9.0, 15: 9.0}, [])}
    fila = robustez_b1_tipos_dia(otros, [("r1", 14)])
    assert fila["robustez_fin_de_semana_peor_hora_antes"] == 3.0
    assert fila["robustez_fin_de_semana_peor_hora_despues"] == 5.0  # 14 h sube a 10; la peor pasa a ser 15 h
    assert fila["robustez_fin_de_semana_personas_hora"] == 7.0
    assert fila["robustez_laborable_agosto_personas_hora"] == 0.0


def test_robustez_completa_devuelve_reoptimo_y_max_min():
    """Por cada escenario no base hay una cartera reoptimizada; el max-min no empeora la peor ganancia."""
    from cercasalud.construccion import robustez_completa
    base, otro = caso_a(semilla=1), caso_a(semilla=2)
    elegidos = opt.cobertura_maxima(*base, 2)["elegidos"]
    fila = robustez_completa({"base": base, "otro": otro}, elegidos, 2, 60)
    assert {"reoptimo_ganancia_otro", "reoptimo_estado_otro", "reoptimo_elegidos_otro"} <= set(fila)
    assert "reoptimo_ganancia_base" not in fila
    assert fila["reoptimo_ganancia_otro"] >= opt.ganancia_de(*otro, elegidos) - 1e-9
    assert fila["maxmin_peor_ganancia"] >= fila["cartera_base_peor_ganancia"] - 1e-9
