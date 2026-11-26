"""Fondo de contexto del mapa web: resto de España y países vecinos, sin datos (petición del usuario del 22/11/2026).

El mapa de la página solo tenía la Comunidad de Madrid sobre un fondo liso. Esta capa dibuja alrededor las
provincias españolas y los países vecinos para situarla. **No entra en ningún cálculo** y no lleva cifras: es
solo dibujo.

Fuente: Natural Earth, provincias y regiones de primer nivel a escala 1:10 millones (dominio público; catálogo
`natural_earth`). Su límite de la provincia de Madrid no coincide con el del INE (la escala es mucho más gruesa),
así que la Comunidad se dibuja siempre con las capas propias del INE, por encima, y de Natural Earth se quitan:
- el relleno de la provincia de Madrid (lo tapa la capa del INE; donde los límites no casan, se ve tierra lisa);
- los tramos de límite que comparte con las provincias vecinas, para que no salga un segundo contorno de la
  Comunidad junto al del INE.
"""

from pathlib import Path

import geopandas as gpd
import shapely

from .catalogo import CATALOGO
from .ingesta import versiones_locales
from .manifiestos import sha256_archivo

# Lon/lat: península, Baleares, Canarias, Ceuta y Melilla, y lo que se ve de Portugal, Francia y el norte de África.
CAJA_CONTEXTO = (-19.0, 26.5, 6.0, 45.5)
CRS_METRICO = "EPSG:3035"          # Lambert equivalente de Europa: para simplificar y recortar en metros
TOLERANCIA_M = 300                 # simplificación; a escala 1:10 M el dato ya tiene errores de ese orden
MARGEN_LIMITE_MADRID_M = 60        # ancho con el que se quitan los tramos compartidos con la provincia de Madrid
ISO_MADRID = "ES-M"
# Natural Earth usa algunas formas castellanizadas o antiguas; en el mapa van los nombres oficiales.
NOMBRES_OFICIALES = {"Gerona": "Girona", "Lérida": "Lleida", "La Coruña": "A Coruña", "Orense": "Ourense",
                     "Baleares": "Illes Balears", "Álava": "Araba/Álava", "Alicante": "Alicante/Alacant",
                     "Castellón": "Castellón/Castelló", "Valencia": "Valencia/València"}
PAISES = {"PRT": "Portugal", "FRA": "Francia", "MAR": "Marruecos", "DZA": "Argelia"}
COLUMNAS = ["adm0_a3", "name", "iso_3166_2", "longitude", "latitude"]


def copia_natural_earth(raiz: Path) -> tuple[Path, dict] | None:
    """(ruta, manifiesto) de la última copia local de Natural Earth, con su SHA-256 comprobado.

    Devuelve None si no se ha descargado (`uv run cercasalud fetch --fuente natural_earth`): la página
    funciona igual, sin el fondo de contexto.
    """
    archivo = next(a for a in CATALOGO if a.fuente == "natural_earth")
    versiones = versiones_locales(raiz, archivo)
    if not versiones:
        return None
    ruta, manifiesto = versiones[-1]
    if sha256_archivo(ruta) != manifiesto.get("sha256"):
        raise ValueError(f"{ruta}: el SHA-256 no coincide con su manifiesto.")
    return ruta, manifiesto


def leer_natural_earth(ruta: Path) -> gpd.GeoDataFrame:
    """Provincias y regiones que caen en la caja de contexto, recortadas a ella (WGS84)."""
    capa = gpd.read_file(f"/vsizip/{ruta.as_posix()}", columns=COLUMNAS, bbox=CAJA_CONTEXTO)
    return capa.clip(shapely.box(*CAJA_CONTEXTO)).reset_index(drop=True)


def simplificar_cobertura(capa: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Simplifica las piezas en metros conservando los límites compartidos (sin huecos ni solapes entre vecinas)."""
    metrica = capa.to_crs(CRS_METRICO)
    geometrias = shapely.make_valid(metrica.geometry.to_numpy())
    metrica["geometry"] = shapely.coverage_simplify(geometrias, TOLERANCIA_M)
    return metrica


def poligonos_wgs84(geometria) -> list:
    """Polígonos sueltos (sin colecciones ni líneas) de una geometría métrica, pasados a WGS84."""
    serie = gpd.GeoSeries([geometria], crs=CRS_METRICO).to_crs("EPSG:4326").explode(index_parts=False)
    return [g for g in serie if g.geom_type == "Polygon" and not g.is_empty]


def lineas_wgs84(geometria) -> list:
    """Líneas sueltas de una geometría métrica, pasadas a WGS84."""
    serie = gpd.GeoSeries([geometria], crs=CRS_METRICO).to_crs("EPSG:4326").explode(index_parts=False)
    return [g for g in serie if g.geom_type == "LineString" and not g.is_empty]


def limites_sin_madrid(provincias: gpd.GeoDataFrame):
    """Límites provinciales y costa de España, sin los tramos que tocan a la provincia de Madrid."""
    madrid = provincias[provincias["iso_3166_2"] == ISO_MADRID].geometry.union_all()
    resto = provincias[provincias["iso_3166_2"] != ISO_MADRID]
    bordes = shapely.union_all([g.boundary for g in resto.geometry])
    if madrid is not None and not madrid.is_empty:
        bordes = bordes.difference(madrid.boundary.buffer(MARGEN_LIMITE_MADRID_M))
    return shapely.line_merge(bordes)  # une los tramos sueltos que deja la unión en líneas continuas


def rotulos_contexto(capa: gpd.GeoDataFrame, vecinos: gpd.GeoDataFrame) -> list[list]:
    """[lon, lat, texto, tipo] de las provincias y de los países vecinos.

    Madrid lleva el tipo «madrid»: la página solo lo enseña de lejos, cuando no caben los rótulos del INE.
    """
    espana = capa[capa["adm0_a3"] == "ESP"]
    rotulos = [[round(float(f.longitude), 4), round(float(f.latitude), 4), NOMBRES_OFICIALES.get(f.name, f.name),
                "madrid" if f.iso_3166_2 == ISO_MADRID else "provincia"] for f in espana.itertuples()]
    for codigo, pais in vecinos.to_crs("EPSG:4326").iterrows():
        if codigo in PAISES:
            punto = pais.geometry.representative_point()
            rotulos.append([round(punto.x, 4), round(punto.y, 4), PAISES[codigo], "pais"])
    return rotulos


def contexto(capa: gpd.GeoDataFrame) -> dict:
    """Geometrías del fondo en WGS84: tierra de España, países vecinos, límites y rótulos.

    `capa` son las provincias y regiones de Natural Earth en WGS84 (columnas de `COLUMNAS`).
    """
    metrica = simplificar_cobertura(capa)
    espana = metrica[metrica["adm0_a3"] == "ESP"]
    vecinos = metrica[metrica["adm0_a3"] != "ESP"].dissolve("adm0_a3")
    return {"tierra": poligonos_wgs84(espana.geometry.union_all()),
            "vecinos": [p for g in vecinos.geometry for p in poligonos_wgs84(g)],
            "limites": lineas_wgs84(limites_sin_madrid(espana)),
            "rotulos": rotulos_contexto(capa, vecinos)}
