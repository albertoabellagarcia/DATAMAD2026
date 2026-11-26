"""Capas de deck.gl en archivo (SPEC P-27): cada fila lleva color y texto de todas las variables."""

import json

import pandas as pd

from cercasalud import capas_deck

CATALOGO = {"min_pie": {"limites": [5, 10, 15, 20, 25, 30]}}
TERRITORIOS = pd.DataFrame({"tipo": ["municipio", "distrito"], "codigo": ["28001", "01"],
                            "nombre": ["Acebeda, La", "Centro"], "poblacion": [70.0, 141018.0],
                            "pct_sin_transporte": [0.0, 1.0], "clase_pct_sin_transporte": [0, 1],
                            "pct_sin_pie": [12.5, 3.0], "clase_pct_sin_pie": [4, 2]})


def celdas() -> pd.DataFrame:
    return pd.DataFrame({"contorno": ["[[-3.7,40.4],[-3.69,40.4],[-3.69,40.41],[-3.7,40.4]]"] * 2,
                         "cusec": ["2800101001", "2807901001"], "poblacion_total": [12.4, 30.6],
                         "min_pie": [7.0, float("nan")], "clase_min_pie": [1, -1],
                         "quintil_renta": [3.0, float("nan")], "calidad_renta": ["dato", None],
                         "clase_quintil_renta": [2, -1]})


def test_celdas_con_color_y_texto_de_cada_variable():
    """Lugar = distrito en la capital y municipio fuera; no evaluable en gris y con su texto."""
    filas = capas_deck.registros_celdas(celdas(), TERRITORIOS, CATALOGO)
    assert filas[0]["l"] == "Acebeda, La · sección 2800101001" and filas[1]["l"] == "Centro · sección 2807901001"
    assert filas[0]["d_min_pie"] == "7 min" and filas[1]["d_min_pie"] == capas_deck.NO_EVALUABLE_PIE
    assert filas[1]["c_min_pie"] == [158, 158, 158] and filas[0]["g"] == "≈ 12 personas (estimación)"
    assert filas[0]["d_quintil_renta"] == "Renta: Q3 (dato del INE)" and filas[1]["d_quintil_renta"] == "sin dato de renta"
    assert filas[0]["p"][0] == [-3.7, 40.4]


def test_municipios_con_porcentaje_sin_opcion():
    contornos = pd.DataFrame({"contorno": ["[[-3.7,40.4],[-3.69,40.4],[-3.7,40.4]]"], "cumun": ["28001"]})
    fila = capas_deck.registros_municipios(contornos, TERRITORIOS)[0]
    assert fila["d_pct_sin_pie"] == "12,5 % sin opción verificada" and fila["g"] == "de 70 habitantes"


def test_escribe_json_compacto_por_capa(tmp_path):
    lineas = pd.DataFrame({"tipo": ["via_principal", "limite_municipio"], "codigo": ["", "28001"],
                           "camino": ["[[-3.7,40.4],[-3.6,40.5]]", "[[-3.7,40.4],[-3.69,40.4]]"]})
    contornos = pd.DataFrame({"contorno": ["[[-3.7,40.4],[-3.69,40.4],[-3.7,40.4]]"], "cumun": ["28001"]})
    filas = capas_deck.escribir(tmp_path, {"celdas": celdas(), "municipios": contornos, "lineas": lineas,
                                           "territorios": TERRITORIOS, "catalogo": CATALOGO})
    assert filas == {"celdas": 2, "municipios": 1, "lineas_limite_municipio": 1, "lineas_via_principal": 1}
    texto = (tmp_path / "celdas.json").read_text(encoding="utf-8")
    assert '": ' not in texto and json.loads(texto)[1]["l"].startswith("Centro")
