"""Unidades de demanda (R-DEM-01, R-DEM-02) con geometrías sintéticas en EPSG:25830.

Cuatro secciones cuadradas de 200 × 200 m, una por nivel de soporte:
- S1: edificios de vivienda y un building=yes dentro de landuse=residential (nivel 1);
- S2: sin edificios de vivienda, con landuse=residential (nivel 2);
- S3: solo un building=yes fuera de cualquier landuse=residential (nivel 3);
- S4: nada (pendiente de localizar).
"""

import geopandas as gpd
import pandas as pd
import pytest
from shapely.geometry import box

from cercasalud import demanda

CRS = demanda.CRS_CALCULO
ORIGEN_X, ORIGEN_Y = 440_000, 4_470_000


def cuadrado(dx, dy, lado):
    """Cuadrado de `lado` metros con la esquina en (ORIGEN_X + dx, ORIGEN_Y + dy)."""
    return box(ORIGEN_X + dx, ORIGEN_Y + dy, ORIGEN_X + dx + lado, ORIGEN_Y + dy + lado)


def secciones():
    """S1 a S4, una al lado de otra."""
    return gpd.GeoDataFrame({"cusec": ["S1", "S2", "S3", "S4"]},
                            geometry=[cuadrado(i * 200, 0, 200) for i in range(4)], crs=CRS)


def edificios():
    """Edificios de S1 (dos celdas distintas) y S3; un garaje en S4 que no cuenta."""
    return gpd.GeoDataFrame({
        "osm_id": [None] * 5, "osm_way_id": ["1", "2", "3", "4", "5"],
        "building": ["apartments", "house", "yes", "yes", "garage"], "landuse": [None] * 5},
        geometry=[cuadrado(10, 10, 20), cuadrado(110, 110, 10), cuadrado(150, 10, 10),
                  cuadrado(450, 50, 10), cuadrado(650, 50, 10)], crs=CRS)


def usos():
    """landuse=residential en S1 (contiene el building=yes de S1) y en S2."""
    return gpd.GeoDataFrame({"osm_id": ["10", "11"], "osm_way_id": [None, None], "building": [None, None],
                             "landuse": ["residential", "residential"]},
                            geometry=[cuadrado(140, 0, 50), cuadrado(220, 20, 60)], crs=CRS)


def por_edad():
    """Población por sección y dos grupos de edad (formato de la etapa `poblacion`)."""
    filas = []
    for cusec, (jovenes, mayores) in {"S1": (100, 50), "S2": (30, 3), "S3": (7, 1), "S4": (11, 2)}.items():
        filas.append({"cusec": cusec, "grupo_edad": "De 0 a 4 años", "edad_min": 0, "edad_max": 4,
                      "poblacion": jovenes})
        filas.append({"cusec": cusec, "grupo_edad": "100 y más años", "edad_min": 100, "edad_max": pd.NA,
                      "poblacion": mayores})
    return pd.DataFrame(filas).astype({"edad_min": "Int64", "edad_max": "Int64"})


@pytest.fixture
def resultado():
    return demanda.construir_unidades(edificios(), usos(), secciones(), por_edad())


def test_conserva_ine_por_seccion_y_edad(resultado):
    """R-DEM-01: la suma de las unidades iguala el INE en cada sección localizada y grupo de edad."""
    ancha = demanda.poblacion_ancha(por_edad())
    assert demanda.diferencia_maxima_con_ine(resultado["unidades"], ancha) <= 1e-6


def test_nivel_de_soporte_por_seccion(resultado):
    """Cada sección usa el primer nivel de soporte que tiene."""
    soporte = resultado["unidades"].groupby("cusec")["soporte"].unique().map(list).to_dict()
    assert soporte == {"S1": ["edificios"], "S2": ["uso_suelo"], "S3": ["edificios_sin_tipo"]}


def test_seccion_sin_soporte_queda_pendiente(resultado):
    """R-DEM-02: S4 no se reparte; queda listada con su población y motivo."""
    assert resultado["pendientes"].to_dict("records") == [
        {"cusec": "S4", "poblacion_total": 13.0, "estado": "no_evaluable", "motivo": "pendiente_localizar"}]
    assert "S4" not in set(resultado["unidades"]["cusec"])


def test_reparto_proporcional_a_la_superficie(resultado):
    """En S1, la celda con más superficie de vivienda recibe más población, en la misma proporción."""
    s1 = resultado["unidades"].query("cusec == 'S1'").set_index("celda")
    # apartments (400 m²) en la celda 4400_44700; house (100 m²) en 4401_44701; yes (100 m²) en 4401_44700
    assert s1["poblacion_total"].sum() == pytest.approx(150)
    assert s1.loc["4400_44700", "fraccion"] == pytest.approx(400 / 600)


def test_building_yes_fuera_de_uso_residencial_no_cuenta_en_nivel_1():
    """Un building=yes fuera de landuse=residential no es vivienda en el nivel 1."""
    elegidos = demanda.edificios_residenciales(edificios(), usos())
    assert sorted(elegidos["osm_way_id"]) == ["1", "2", "3"]
