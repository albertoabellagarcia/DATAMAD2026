"""Fondo de contexto del mapa web (resto de España, sin datos): qué se dibuja y qué se quita.

Datos sintéticos: cuadrados de 1 grado con los códigos de Natural Earth. Madrid comparte un lado con
Toledo; Toledo, otro con «Gerona» (nombre antiguo, para probar el nombre oficial); y hay un país vecino.
"""

import geopandas as gpd
import shapely

from cercasalud import contexto_mapa


def cuadrado(x, y):
    """Cuadrado de 1 grado con la esquina inferior izquierda en (x, y)."""
    return shapely.box(x, y, x + 1, y + 1)


def capa_sintetica() -> gpd.GeoDataFrame:
    """Madrid encima de Toledo, Gerona a la derecha de Toledo y Portugal aparte."""
    filas = [("ESP", "Madrid", "ES-M", cuadrado(-4, 40)), ("ESP", "Toledo", "ES-TO", cuadrado(-4, 39)),
             ("ESP", "Gerona", "ES-GI", cuadrado(-3, 39)), ("PRT", "Beja", "PT-02", cuadrado(-8, 38))]
    return gpd.GeoDataFrame(
        {"adm0_a3": [f[0] for f in filas], "name": [f[1] for f in filas], "iso_3166_2": [f[2] for f in filas],
         "longitude": [f[3].centroid.x for f in filas], "latitude": [f[3].centroid.y for f in filas]},
        geometry=[f[3] for f in filas], crs="EPSG:4326")


def test_quita_el_limite_compartido_con_madrid_y_conserva_los_demas():
    """El lado Madrid–Toledo no se dibuja (lo dibuja el INE); el lado Toledo–Gerona, sí."""
    limites = shapely.union_all(contexto_mapa.contexto(capa_sintetica())["limites"])
    madrid_toledo = shapely.Point(-3.5, 40.0)
    toledo_gerona = shapely.Point(-3.0, 39.5)
    # Distancias en grados: 0,005° ≈ 0,5 km, por encima de la simplificación (300 m) en esta latitud.
    assert limites.distance(madrid_toledo) > 0.005
    assert limites.distance(toledo_gerona) < 0.005


def test_la_tierra_de_espana_incluye_madrid_y_los_vecinos_van_aparte():
    """Donde el límite del INE y el de Natural Earth no casan se ve tierra, no mar."""
    datos = contexto_mapa.contexto(capa_sintetica())
    tierra = shapely.union_all(datos["tierra"])
    assert tierra.contains(shapely.Point(-3.5, 40.5))
    assert not tierra.contains(shapely.Point(-7.5, 38.5))
    assert len(datos["vecinos"]) == 1


def test_rotulos_con_nombre_oficial_madrid_aparte_y_el_pais():
    """Madrid va con su propio tipo (solo de lejos); «Gerona» sale como «Girona»; Portugal, como país."""
    rotulos = {r[2]: r[3] for r in contexto_mapa.contexto(capa_sintetica())["rotulos"]}
    assert rotulos == {"Madrid": "madrid", "Toledo": "provincia", "Girona": "provincia", "Portugal": "pais"}
