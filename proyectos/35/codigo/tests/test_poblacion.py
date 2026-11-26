"""Normalización de la población INE por sección y edad (R-DEM-01, R-DEM-03, R-OPS-01).

Datos sintéticos con la forma de la tabla 69213: filas de provincia, municipio y sección;
Sexo Total/Hombres/Mujeres; agregado «Todas las edades»; punto como separador de miles.
"""

import json

import pandas as pd
import pytest

from cercasalud import construccion, poblacion

CABECERA = "Provincias;Municipios;Secciones;Sexo;Edad;Periodo;Total\n"
EDADES = ("De 0 a 4 años", "De 75 a 79 años", "100 y más años")
# Población 2025 de cada sección por grupo de edad (en el orden de EDADES).
SECCIONES_2025 = {
    ("28001 Uno", "2800101001 Uno sección 01001"): (1200, 30, 1),
    ("28001 Uno", "2800101002 Uno sección 01002"): (10, 20, 0),
    ("28002 Dos", "2800201001 Dos sección 01001"): (5, 6, 7),
}
# Sección que existió en 2024 y ya no tiene dato en 2025 (como los 48 códigos reales).
SECCION_DESAPARECIDA = ("28002 Dos", "2800201002 Dos sección 01002")


def miles(valor: int | None) -> str:
    """Escribe un entero como el INE: '1.200'; None como celda vacía."""
    return "" if valor is None else f"{valor:,}".replace(",", ".")


def escala(valor: int | None, factor: float) -> int | None:
    """Parte de la población que corresponde a un sexo; None se mantiene."""
    return None if valor is None else int(valor * factor)


def filas_de(provincia, municipio, seccion, valores, periodo):
    """Filas de una unidad: Total y los dos sexos (la mitad cada uno; no se usan en el cálculo)."""
    total = None if valores is None else sum(valores)
    salida = []
    for sexo, factor in (("Total", 1), ("Hombres", 0.5), ("Mujeres", 0.5)):
        prefijo = f"{provincia};{municipio};{seccion};{sexo}"
        salida.append(f"{prefijo};Todas las edades;{periodo};{miles(escala(total, factor))}")
        for edad, v in zip(EDADES, valores or (None,) * len(EDADES)):
            salida.append(f"{prefijo};{edad};{periodo};{miles(escala(v, factor))}")
    return salida


def csv_sintetico(cambiar_municipio_uno: int = 0) -> str:
    """Construye la tabla; `cambiar_municipio_uno` altera el agregado del municipio 28001 en 0-4 años."""
    provincia, filas = "28 Madrid", []
    por_muni = {}
    for (muni, _), valores in SECCIONES_2025.items():
        por_muni[muni] = [a + b for a, b in zip(por_muni.get(muni, (0, 0, 0)), valores)]
    por_muni["28001 Uno"][0] += cambiar_municipio_uno
    filas += filas_de(provincia, "", "", [sum(v) for v in zip(*SECCIONES_2025.values())], "2025")
    for muni, valores in por_muni.items():
        filas += filas_de(provincia, muni, "", valores, "2025")
    for (muni, seccion), valores in SECCIONES_2025.items():
        filas += filas_de(provincia, muni, seccion, valores, "2025")
    filas += filas_de(provincia, *SECCION_DESAPARECIDA, None, "2025")
    filas += filas_de(provincia, *SECCION_DESAPARECIDA, (2, 2, 2), "2024")
    return CABECERA + "\n".join(filas) + "\n"


def poligonos() -> pd.DataFrame:
    """Atributos de la capa: dos secciones con polígono, una sin él y un polígono de distrito."""
    return pd.DataFrame({"CUSEC": ["2800101001", "2800101002", "2800101000"],
                         "TIPO": ["SECCIONADO", "SECCIONADO", "DISTRITO"]})


def normalizado(tmp_path, cambiar_municipio_uno: int = 0) -> dict:
    """Escribe el CSV sintético con BOM, como el origen, y lo normaliza."""
    ruta = tmp_path / "69213.csv"
    ruta.write_text(csv_sintetico(cambiar_municipio_uno), encoding="utf-8-sig")
    return poblacion.normalizar(poblacion.leer_tabla(ruta), poligonos())


def test_miles_con_punto_se_leen_como_enteros(tmp_path):
    """'1.200' es mil doscientos, no 1,2."""
    por_edad = normalizado(tmp_path)["por_edad"].set_index(["cusec", "grupo_edad"])
    assert por_edad.loc[("2800101001", "De 0 a 4 años"), "poblacion"] == 1200


def test_forma_numerica_no_prevista_falla():
    """Un decimal con coma u otra forma rara no se convierte en silencio."""
    with pytest.raises(ValueError):
        poblacion.a_entero(pd.Series(["12", "3,5"]))


def test_totales_y_desgloses_de_mayores(tmp_path):
    """La suma de las secciones conserva el total y los desgloses 65+, 75+ y 85+ (D-14)."""
    resultado = normalizado(tmp_path)
    assert resultado["descuadres"] == []
    conteos = resultado["conteos"]
    assert conteos["poblacion_total"] == 1279
    assert (conteos["poblacion_65_mas"], conteos["poblacion_75_mas"], conteos["poblacion_85_mas"]) == (64, 64, 8)
    assert conteos["secciones_con_dato"] == 3 and conteos["municipios"] == 2


def test_solo_se_usa_sexo_total(tmp_path):
    """Las filas de Hombres y Mujeres no se suman a las de Total."""
    por_edad = normalizado(tmp_path)["por_edad"]
    assert len(por_edad) == 3 * len(EDADES)


def test_descuadre_con_agregado_ine_se_detecta(tmp_path):
    """Si el municipio publicado no es la suma de sus secciones, se informa."""
    descuadres = normalizado(tmp_path, cambiar_municipio_uno=5)["descuadres"]
    assert descuadres == ["municipio 28001, De 0 a 4 años: INE distinto de la suma de secciones"]


def test_seccion_desaparecida_se_lista_y_no_se_imputa(tmp_path):
    """El código sin dato en 2025 se documenta con los periodos en que sí lo tuvo (R-DEM-03)."""
    resultado = normalizado(tmp_path)
    sin_dato = resultado["codigos_sin_dato"].to_dict("records")
    assert sin_dato == [{"cusec": "2800201002", "cumun": "28002", "municipio": "Dos",
                         "periodos_con_dato": "2024"}]
    assert "2800201002" not in set(resultado["por_seccion"]["cusec"])


def test_cruce_con_poligonos_ignora_distritos(tmp_path):
    """Los polígonos de tipo DISTRITO no cuentan como secciones; se detecta la sección sin polígono."""
    cruce = normalizado(tmp_path)["cruce_poligonos"]
    assert cruce["secciones_con_dato_y_poligono"] == 2
    assert cruce["secciones_con_dato_sin_poligono"] == ["2800201001"]
    assert cruce["poligonos_de_seccion_sin_codigo_ine"] == []


@pytest.mark.parametrize("etiqueta, esperado", [
    ("De 0 a 4 años", (0, 4)), ("De 95 a 99 años", (95, 99)), ("100 y más años", (100, None))])
def test_limites_de_edad(etiqueta, esperado):
    """Cada etiqueta del INE da su edad mínima y máxima."""
    assert poblacion.limites_de_edad(etiqueta) == esperado


def test_etapa_con_descuadre_no_publica(tmp_path, monkeypatch):
    """Si los totales no cuadran, la etapa falla y no deja carpeta final (R-DEM-01, R-OPS-01)."""
    origen = tmp_path / "69213.csv"
    origen.write_text(csv_sintetico(cambiar_municipio_uno=5), encoding="utf-8-sig")
    monkeypatch.setattr(construccion, "leer_snapshot", lambda raiz, id_: {"id": id_})
    monkeypatch.setattr(construccion, "ruta_en_snapshot", lambda raiz, snap, fuente, nombre: origen)
    monkeypatch.setattr(poblacion, "leer_poligonos", lambda ruta: poligonos())
    with pytest.raises(ValueError, match="descuadres"):
        construccion.etapa_poblacion(tmp_path, "PRUEBA")
    carpeta = tmp_path / "procesados" / "PRUEBA"
    assert not (carpeta / "poblacion").exists()
    resumen = json.loads((carpeta / "poblacion.parcial" / "resumen.json").read_text(encoding="utf-8"))
    assert resumen["descuadres_con_agregados_ine"]
