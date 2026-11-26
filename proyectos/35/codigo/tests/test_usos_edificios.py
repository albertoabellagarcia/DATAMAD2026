"""Clasificación del uso de los edificios (escenario de sensibilidad de la demanda)."""

import geopandas as gpd
import pandas as pd
from shapely.geometry import box

from cercasalud import demanda
from cercasalud import usos_edificios as ue


def fila(**etiquetas) -> pd.Series:
    """Edificio con unas etiquetas; el resto, vacías."""
    return pd.Series({c: None for c in (*ue.CLAVES, "other_tags")} | etiquetas)


def test_clases_basicas():
    """Culto o deporte son claros; comercio, mixto; residencias, ambiguas; sin etiquetas, sin clase."""
    assert ue.clasificar(fila(amenity="place_of_worship")) == ue.CLARO
    assert ue.clasificar(fila(leisure="sports_centre")) == ue.CLARO
    assert ue.clasificar(fila(other_tags='"healthcare"=>"centre"')) == ue.CLARO
    assert ue.clasificar(fila(shop="bakery")) == ue.MIXTO
    assert ue.clasificar(fila(amenity="restaurant", shop="deli")) == ue.MIXTO
    assert ue.clasificar(fila(amenity="social_facility")) == ue.AMBIGUO
    assert ue.clasificar(fila(historic="building")) == ue.AMBIGUO
    assert ue.clasificar(fila(office="company")) == ue.AMBIGUO  # valor no listado
    assert ue.clasificar(fila()) == ""


def test_prioridad_claro_sobre_mixto():
    """Un ayuntamiento con cafetería sigue siendo claro; un comercio con residencia es ambiguo."""
    assert ue.clasificar(fila(amenity="townhall", shop="kiosk")) == ue.CLARO
    assert ue.clasificar(fila(amenity="nursing_home", shop="bakery")) == ue.AMBIGUO


def test_excluir_solo_afecta_a_building_yes():
    """La exclusión quita los building=yes de la clase pedida, nunca los de vivienda explícita."""
    edificios = gpd.GeoDataFrame({"osm_id": ["1", "2", "3"], "osm_way_id": [None] * 3,
                                  "building": ["yes", "yes", "apartments"], "landuse": [None] * 3,
                                  "amenity": ["place_of_worship", None, "place_of_worship"]},
                                 geometry=[box(0, 0, 10, 10), box(20, 0, 30, 10), box(40, 0, 50, 10)],
                                 crs=demanda.CRS_CALCULO)
    usos = gpd.GeoDataFrame({"landuse": ["residential"]}, geometry=[box(-5, -5, 60, 20)], crs=demanda.CRS_CALCULO)
    base = demanda.edificios_residenciales(edificios, usos)
    sin_claros = demanda.edificios_residenciales(edificios, usos, (ue.CLARO,))
    assert sorted(base["osm_id"]) == ["1", "2", "3"]
    assert sorted(sin_claros["osm_id"]) == ["2", "3"]
