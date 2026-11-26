"""Formato del mapa de minutos (pantalla 2): colores, encuadre, textos, leyenda y tarjeta."""

import pandas as pd

from cercasalud import vista_mapa


def test_colores_por_clase_y_gris_para_no_evaluable():
    """Clase 0 = primer color de la paleta; -1 = gris de no evaluable."""
    colores = vista_mapa.colores(pd.Series([0, 6, -1]), vista_mapa.AZUL_ROJO).tolist()
    assert colores == [[69, 117, 180], [215, 48, 39], [158, 158, 158]]


def test_zoom_mayor_cuanto_menor_es_el_territorio():
    """La Comunidad entra con un zoom de unas 8 unidades; un distrito, con bastante más."""
    comunidad = vista_mapa.zoom_para(-4.58, 39.88, -3.05, 41.17, 980, 680)
    distrito = vista_mapa.zoom_para(-3.72, 40.40, -3.69, 40.43, 980, 680)
    assert 7.5 < comunidad < 8.5 and distrito > comunidad + 4


def test_texto_de_minutos_y_mas_alla_del_ultimo_limite():
    assert vista_mapa.texto_minutos(23.4, 60) == "23 min"
    assert vista_mapa.texto_minutos(75.0, 60) == "más de 60 min"
    assert vista_mapa.texto_minutos(float("nan"), 60) == "más de 60 min"


def test_caracteres_incluyen_tildes_y_letras_de_los_rotulos():
    """deck.gl solo dibuja los caracteres de su lista: tienen que estar la «j», las tildes y la eñe."""
    juego = vista_mapa.caracteres(["Alcalá de Henares", "Majadahonda", "Peñuelas"])
    assert all(c in juego for c in "ájñ")


def test_numeros_con_formato_espanol():
    assert vista_mapa.personas(289239.7) == "289.240"
    assert vista_mapa.porcentaje(4.0658) == "4,1 %"


def test_leyenda_con_barras_umbral_y_texto_escapado():
    """Cada clase lleva su porcentaje; la raya del umbral va tras la clase indicada; el texto se escapa."""
    tramos = pd.DataFrame({"clase": [-1, 0, 1, 2], "pct": [0.1, 50.0, 30.0, 20.0]})
    filas, no_eval = vista_mapa.filas_tramos(tramos, ["≤ 10 min", "10–20", "<b>20–30</b>"], vista_mapa.AZUL_ROJO[:3])
    assert [f[2] for f in filas] == [50.0, 30.0, 20.0] and no_eval == 0.1
    texto = vista_mapa.leyenda_html("Minutos", "y %", filas, 1, [("No evaluable", vista_mapa.NO_EVALUABLE, no_eval)])
    assert "50,0 %" in texto and "umbral" in texto and "<b>20–30</b>" not in texto
    assert texto.index("10–20") < texto.index("umbral") < texto.index("20–30")


def test_tarjeta_con_estados_del_territorio():
    """La tarjeta da población, porcentaje con acceso y personas sin opción por modo, sin inventar modos."""
    fila = {"nombre": "Getafe", "poblacion": 1000.0, "transporte_con_acceso": 900.0,
            "transporte_sin_opcion_verificada": 100.0, "transporte_no_evaluable": 0.0}
    texto = vista_mapa.tarjeta(fila, [("transporte", "En transporte"), ("pie", "A pie")])
    assert "### Getafe" in texto and "con acceso 90,0 %" in texto and "100 (10,0 %)" in texto
    assert "A pie" not in texto and "no evaluable" not in texto


def test_rotulos_que_se_pisan_se_quitan_en_orden_de_prioridad():
    """A zoom de la Comunidad, dos nombres a 1 km se pisan y se queda el primero; uno lejano se queda.

    Con más zoom, los dos cercanos caben.
    """
    rotulos = pd.DataFrame({"lon": [-3.70, -3.69, -3.20], "lat": [40.42, 40.42, 40.90],
                            "nombre": ["Madrid", "Pozuelo", "Lozoya"], "tamano": [20, 14, 14]})
    lejos = vista_mapa.rotulos_sin_solape(rotulos, zoom=8.5)
    assert lejos["nombre"].tolist() == ["Madrid", "Lozoya"]
    cerca = vista_mapa.rotulos_sin_solape(rotulos, zoom=14)
    assert cerca["nombre"].tolist() == ["Madrid", "Pozuelo", "Lozoya"]
