"""Clasificación de resultados de ruta (R-RED-02) y preparación de GTFS; sin Java."""

import datetime
import zipfile

import geopandas as gpd
import numpy as np
import pandas as pd
import pytest
from shapely.geometry import Point

from cercasalud import red
from cercasalud.manifiestos import sha256_archivo


def test_clasificacion_de_los_cinco_casos():
    """Cada combinación de enganche, tiempo y línea recta da su clase."""
    tiempo = pd.Series([10.0, 20.0, np.nan, np.nan, np.nan])
    enganchado = pd.Series([True, True, True, False, True])
    recta = pd.Series([5.0, 12.0, 30.0, 1.0, 8.0])
    clases = red.clasificar(tiempo, enganchado, umbral_min=15, radio_min=60, recta_min=recta)
    assert clases.tolist() == ["dentro_umbral", "fuera_umbral", "fuera_radio", "fallo_conexion", "fallo_enlace"]


def test_umbral_es_inclusivo_y_sin_recta_no_hay_fallo_de_enlace():
    """15 min con umbral 15 está dentro; sin línea recta, un NaN enganchado es fuera de radio."""
    clases = red.clasificar(pd.Series([15.0, np.nan]), pd.Series([True, True]), umbral_min=15, radio_min=60)
    assert clases.tolist() == ["dentro_umbral", "fuera_radio"]


def test_radio_menor_que_umbral_falla():
    """Un radio de cálculo menor que el umbral confundiría «fuera de radio» con carencia."""
    with pytest.raises(ValueError):
        red.clasificar(pd.Series([1.0]), pd.Series([True]), umbral_min=30, radio_min=20)


def test_los_fallos_son_no_evaluable_conexion():
    """Correspondencia con los estados de la SPEC §7."""
    assert red.ESTADO_SEGUN_CLASE["fallo_conexion"] == ("no_evaluable", "conexion")
    assert red.ESTADO_SEGUN_CLASE["fallo_enlace"] == ("no_evaluable", "conexion")
    assert red.ESTADO_SEGUN_CLASE["fuera_radio"][0] == "sin_opcion_verificada"


def test_minimo_por_origen_con_origen_sin_ruta():
    """El destino más cercano por origen; un origen sin ninguna ruta queda en NaN."""
    tiempos = pd.DataFrame({"from_id": ["a", "a", "b"], "to_id": ["x", "y", "x"],
                            "travel_time": [9.0, 4.0, np.nan]})
    minimos = red.minimo_por_origen(tiempos).set_index("id")
    assert minimos.loc["a", "travel_time"] == 4.0 and minimos.loc["a", "to_id"] == "y"
    assert np.isnan(minimos.loc["b", "travel_time"])


def test_recta_al_mas_cercano():
    """Distancia euclídea en metros al destino más próximo."""
    origenes = gpd.GeoDataFrame(geometry=[Point(0, 0), Point(100, 0)], crs="EPSG:25830")
    destinos = gpd.GeoDataFrame(geometry=[Point(30, 40), Point(1000, 0)], crs="EPSG:25830")
    assert red.recta_al_mas_cercano_m(origenes, destinos).tolist() == pytest.approx([50.0, 80.62257748])


def test_gtfs_en_subcarpeta_se_copia_a_la_raiz(tmp_path):
    """El zip con una subcarpeta se copia con los archivos en la raíz; el original no cambia."""
    origen = tmp_path / "gtfs_urbanos.zip"
    with zipfile.ZipFile(origen, "w") as z:
        z.writestr("google_transit_M9/", "")
        z.writestr("google_transit_M9/stops.txt", "stop_id\n1\n")
    copia, cambios = red.preparar_gtfs(origen, tmp_path / "derivados")
    assert cambios == ["archivos sacados de la subcarpeta google_transit_M9"]
    assert zipfile.ZipFile(copia).namelist() == ["stops.txt"]
    assert "google_transit_M9/stops.txt" in zipfile.ZipFile(origen).namelist()


def test_copia_lleva_su_propia_huella_y_es_determinista(tmp_path):
    """r5py cachea por nombre: la copia se llama como el original más la huella de la copia,
    y dos preparaciones del mismo origen dan el mismo archivo."""
    origen = tmp_path / "gtfs_metro.zip"
    with zipfile.ZipFile(origen, "w") as z:
        z.writestr("stops.txt", "stop_id" + chr(10) + "1" + chr(10))
    copia, cambios = red.preparar_gtfs(origen, tmp_path / "derivados")
    assert cambios == [] and copia.name == f"gtfs_metro_{sha256_archivo(copia)[:12]}.zip"
    otra, _ = red.preparar_gtfs(origen, tmp_path / "otra")
    assert otra.name == copia.name and otra.read_bytes() == copia.read_bytes()


def test_reglas_distintas_dan_nombre_distinto(tmp_path):
    """Si cambia el contenido de la copia, cambia su nombre (no reutiliza una caché vieja)."""
    salto = chr(10)
    origen_a, origen_b = tmp_path / "a" / "gtfs_x.zip", tmp_path / "b" / "gtfs_x.zip"
    for ruta, extra in ((origen_a, ""), (origen_b, "2" + salto)):
        ruta.parent.mkdir()
        with zipfile.ZipFile(ruta, "w") as z:
            z.writestr("stops.txt", "stop_id" + salto + "1" + salto + extra)
    assert red.preparar_gtfs(origen_a, tmp_path / "d")[0].name != red.preparar_gtfs(origen_b, tmp_path / "d")[0].name


def test_tabla_opcional_vacia_se_omite(tmp_path):
    """R5 rechaza fare_rules.txt con solo cabecera: la copia lo omite y lo declara."""
    origen = tmp_path / "gtfs_metro.zip"
    with zipfile.ZipFile(origen, "w") as z:
        z.writestr("stops.txt", "stop_id\n1\n")
        z.writestr("fare_rules.txt", "fare_id,route_id\r\n")
    copia, cambios = red.preparar_gtfs(origen, tmp_path / "derivados")
    assert zipfile.ZipFile(copia).namelist() == ["stops.txt"]
    assert cambios == ["omitida tabla opcional vacía fare_rules.txt"]


def test_tabla_obligatoria_vacia_no_se_omite(tmp_path):
    """Una tabla obligatoria vacía no se esconde: se deja para que R5 falle y se vea."""
    origen = tmp_path / "gtfs_x.zip"
    with zipfile.ZipFile(origen, "w") as z:
        z.writestr("stops.txt", "stop_id" + chr(10))
    copia, cambios = red.preparar_gtfs(origen, tmp_path / "derivados")
    assert cambios == [] and zipfile.ZipFile(copia).namelist() == ["stops.txt"]


def test_feed_info_con_varios_registros_se_omite(tmp_path):
    """El estándar admite un registro en feed_info.txt; R5 rechaza más. La copia lo omite."""
    origen = tmp_path / "gtfs_interurbanos.zip"
    salto = chr(10)
    with zipfile.ZipFile(origen, "w") as z:
        z.writestr("stops.txt", "stop_id" + salto + "1" + salto)
        z.writestr("feed_info.txt", salto.join(["feed_publisher_name", "A", "B"]) + salto)
    copia, cambios = red.preparar_gtfs(origen, tmp_path / "derivados")
    assert zipfile.ZipFile(copia).namelist() == ["stops.txt"]
    assert cambios == ["omitido feed_info.txt con 2 registros (el estándar GTFS admite uno)"]


def test_extender_calendario_es_supuesto_declarado(tmp_path):
    """Solo cambia end_date de los servicios que terminaban antes; cada cambio se declara."""
    salto = chr(10)
    calendario = salto.join([
        "service_id,monday,tuesday,wednesday,thursday,friday,saturday,sunday,start_date,end_date",
        "L,1,1,1,1,0,0,0,20250527,20260527",
        "V,0,0,0,0,1,0,0,20250527,20271231"]) + salto
    origen = tmp_path / "gtfs_metro.zip"
    with zipfile.ZipFile(origen, "w") as z:
        z.writestr("calendar.txt", calendario)
    copia, cambios = red.preparar_gtfs(origen, tmp_path / "d", extender_hasta=datetime.date(2027, 12, 31))
    assert cambios == ["SUPUESTO: servicio L extendido de 20260527 a 20271231"]
    filas = zipfile.ZipFile(copia).read("calendar.txt").decode("utf-8").splitlines()
    assert filas[1] == "L,1,1,1,1,0,0,0,20250527,20271231" and filas[2].endswith("20271231")
    assert "20250527,20260527" in zipfile.ZipFile(origen).read("calendar.txt").decode("utf-8")
