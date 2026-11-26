"""Clasificación del uso de los `building=yes` que `demanda.py` toma como vivienda (14/11/2026).

`demanda.py` cuenta como vivienda los `building=yes` cuyo punto interior cae en
`landuse=residential`. Algunos llevan en OSM etiquetas de otro uso. Este módulo los clasifica:

- **claro_no_residencial:** usos que no alojan población empadronada: culto, enseñanza,
  sanidad, administración, cultura, deporte, seguridad, transporte, monumentos, hoteles,
  museos, instalaciones técnicas y militares.
- **mixto:** usos que suelen ocupar la planta baja de un edificio de viviendas: comercio,
  hostelería, farmacias, bancos, gimnasios.
- **ambiguo:** puede haber residentes o no hay forma de saberlo con la etiqueta: residencias
  y centros sociales (el padrón incluye a quien vive en una residencia), clínicas, oficinas
  genéricas, edificios históricos sin más detalle, alojamientos turísticos pequeños.

Un edificio sin ninguna de estas etiquetas no se clasifica (''). Si tiene etiquetas de varias
clases, manda la primera de este orden: claro > ambiguo > mixto (un ayuntamiento con una
cafetería sigue siendo un ayuntamiento).

**El criterio es una decisión del análisis,** documentada aquí y en
`fases/H2_demanda_red/edificios_no_residenciales/`. Los valores no listados de una clave se
tratan como ambiguos.
"""

import re

import pandas as pd

CLARO, MIXTO, AMBIGUO = "claro_no_residencial", "mixto", "ambiguo"

# Valores por clave. Las claves en columna propia del controlador OSM de GDAL y las de `other_tags`
# (comprobado con pyogrio.read_info el 14/11/2026).
CLAROS = {
    "amenity": {"place_of_worship", "hospital", "community_centre", "police", "townhall", "theatre",
                "library", "school", "college", "university", "kindergarten", "marketplace", "parking",
                "social_centre", "fire_station", "courthouse", "post_office", "bus_station", "cinema",
                "arts_centre", "events_venue", "conference_centre", "exhibition_centre", "prison",
                "public_building", "music_school", "monastery", "grave_yard", "crematorium", "funeral_hall",
                "ferry_terminal", "car_wash", "fuel", "recycling", "waste_transfer_station", "bus_garage",
                "studio", "planetarium", "toilets", "shelter"},
    "leisure": {"sports_centre", "sports_hall", "stadium", "swimming_pool", "pitch", "marina", "bowling_alley",
                "bandstand", "bleachers", "ice_rink", "water_park", "track", "horse_riding", "golf_course"},
    "historic": {"castle", "monument", "palace", "archaeological_site", "city_gate", "tomb", "church", "memorial",
                 "wayside_shrine", "ruins", "fort", "chapel", "monastery", "tower", "aqueduct", "bridge"},
    "tourism": {"hotel", "museum", "gallery", "attraction", "information", "artwork", "hostel", "motel",
                "theme_park", "zoo", "aquarium"},
    "office": {"government", "diplomatic", "research", "educational_institution"},
    "military": None,   # cualquier valor
    "man_made": None,
    "sport": None,      # instalación deportiva (sin vivienda)
}
CLAROS_OTRAS = ("government", "healthcare", "public_transport", "religion")  # en `other_tags`
MIXTOS = {
    "shop": None,
    "amenity": {"restaurant", "cafe", "bar", "pub", "fast_food", "pharmacy", "bank", "ice_cream", "veterinary",
                "dentist", "doctors", "driving_school", "language_school", "bureau_de_change", "atm",
                "vending_machine", "car_rental", "bicycle_rental", "biergarten", "nightclub", "casino"},
    "leisure": {"fitness_centre", "dance", "escape_game", "amusement_arcade", "adult_gaming_centre"},
    "office": {"estate_agent", "insurance", "lawyer", "financial_advisor", "tax_advisor", "travel_agent",
               "notary", "accountant", "architect"},
    "tourism": {"apartment", "guest_house", "chalet"},
}
AMBIGUOS_VALORES = {
    "amenity": {"social_facility", "nursing_home", "clinic", "childcare", "social_club"},
    "historic": {"yes", "building", "manor", "house"},
}
CLAVES = ("amenity", "historic", "leisure", "tourism", "office", "military", "man_made", "sport", "shop")


def _coincide(valor, permitidos) -> bool:
    """True si el valor está en el conjunto (o el conjunto es None = cualquier valor)."""
    return isinstance(valor, str) and valor != "" and (permitidos is None or valor in permitidos)


def clasificar(fila: pd.Series) -> str:
    """Clase de uso de un edificio a partir de sus etiquetas (ver docstring del módulo)."""
    otras = fila.get("other_tags") if isinstance(fila.get("other_tags"), str) else ""
    if any(_coincide(fila.get(c), v) for c, v in CLAROS.items()) or any(
            re.search(rf'"{c}"=>', otras) for c in CLAROS_OTRAS):
        return CLARO
    con_etiqueta = [c for c in CLAVES if _coincide(fila.get(c), None)]
    if not con_etiqueta:
        return ""
    if any(_coincide(fila.get(c), v) for c, v in AMBIGUOS_VALORES.items()):
        return AMBIGUO
    if all(_coincide(fila.get(c), MIXTOS.get(c, set())) for c in con_etiqueta):
        return MIXTO
    return AMBIGUO  # valores no listados


def clasificar_tabla(edificios: pd.DataFrame) -> pd.Series:
    """Clase de uso de cada edificio de una tabla con las columnas de etiquetas (las que falten, vacías)."""
    tabla = edificios.reindex(columns=[*CLAVES, "other_tags"])
    return tabla.apply(clasificar, axis=1)
