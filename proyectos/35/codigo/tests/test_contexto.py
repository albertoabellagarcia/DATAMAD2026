"""Capas de contexto (D-16): lector XLSX con la biblioteca estándar y lectura de personas solas."""

import zipfile

import pandas as pd

from cercasalud import contexto, lector_xlsx

CONTENT_TYPES = ('<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                 '</Types>')
LIBRO = ('<?xml version="1.0"?><workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
         'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets>'
         '<sheet name="AMBOS SEXOS" sheetId="1" r:id="rId1"/></sheets></workbook>')
RELACIONES = ('<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
              '<Relationship Id="rId1" Target="worksheets/sheet1.xml" '
              'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet"/></Relationships>')


def escribir_xlsx(ruta, filas: dict[int, list]) -> None:
    """XLSX mínimo con una hoja: {fila (1..n): [valores desde la columna A]}; textos en línea."""
    celdas = []
    for numero, valores in filas.items():
        xml = []
        for j, valor in enumerate(valores):
            if valor is None:
                continue
            ref = f"{chr(65 + j)}{numero}"
            xml.append(f'<c r="{ref}"><v>{valor}</v></c>' if isinstance(valor, (int, float))
                       else f'<c r="{ref}" t="inlineStr"><is><t>{valor}</t></is></c>')
        celdas.append(f'<row r="{numero}">{"".join(xml)}</row>')
    hoja = ('<?xml version="1.0"?><worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
            f'<sheetData>{"".join(celdas)}</sheetData></worksheet>')
    with zipfile.ZipFile(ruta, "w") as libro:
        libro.writestr("[Content_Types].xml", CONTENT_TYPES)
        libro.writestr("xl/workbook.xml", LIBRO)
        libro.writestr("xl/_rels/workbook.xml.rels", RELACIONES)
        libro.writestr("xl/worksheets/sheet1.xml", hoja)


def test_lector_xlsx_respeta_posiciones_y_tipos(tmp_path):
    """Números como float, textos como str y huecos como None en su posición de Excel."""
    ruta = tmp_path / "libro.xlsx"
    escribir_xlsx(ruta, {1: ["a", None, 3], 3: [None, 2.5]})
    tabla = lector_xlsx.leer_hoja(ruta, "AMBOS SEXOS")
    assert tabla.shape == (3, 3)
    assert tabla.iloc[0, 0] == "a" and tabla.iloc[0, 2] == 3.0 and tabla.iloc[2, 1] == 2.5
    assert pd.isna(tabla.iloc[1, 0])


def test_personas_solas_suma_solo_los_grupos_de_65_y_mas(tmp_path):
    """Solo cuentan las filas de barrio (código de 3 cifras) y, en 65+, los grupos desde 65 años."""
    ruta = tmp_path / "solas.xlsx"
    cabecera = [None, None, "Total", "De 60 a 64 años", "De 65 a 69 años", "De 100 y más años", "No consta"]
    escribir_xlsx(ruta, {6: cabecera, 8: [None, "Ciudad de Madrid", 99, 9, 9, 9, 0],
                         10: [None, "01. Centro", 50, 5, 5, 5, 0], 11: [None, "011. Palacio", 20, 4, 3, 1, 2]})
    tabla = contexto.personas_solas(ruta)
    assert list(tabla["cod_barrio"]) == [11]
    assert tabla.loc[0, "solas_total"] == 20.0 and tabla.loc[0, "solas_65_mas"] == 4.0


def test_prueba_integracion_cuenta_coincidencias_y_jaccard():
    """Con barrios en los que C y A ordenan igual y B al revés, coinciden con A y no con B."""
    barrios = pd.DataFrame({"cod_barrio": [1, 2, 3, 4], "barrio": list("abcd"), "c_pie": [9, 8, 1, 0],
                            "sin_a_pie": [9, 8, 1, 0], "c_transporte": [9, 8, 1, 0], "sin_a_transporte": [0, 1, 8, 9],
                            "sin_b": [0, 1, 8, 9]})
    tabla = contexto.prueba_integracion(barrios, tamanos=(2,))
    fila_a = tabla[(tabla["modo_a"] == "pie") & (tabla["comparacion"] == "C frente a A")].iloc[0]
    fila_b = tabla[(tabla["modo_a"] == "pie") & (tabla["comparacion"] == "C frente a B")].iloc[0]
    assert fila_a["comunes"] == 2 and fila_a["jaccard"] == 1.0
    assert fila_b["comunes"] == 0 and fila_b["jaccard"] == 0.0 and fila_b["solo_en_c"] == "a, b"
