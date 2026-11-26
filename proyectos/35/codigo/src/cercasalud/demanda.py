"""Unidades de demanda residencial: malla de 100 m con soporte residencial de OSM (H2; P-05, P-16).

Qué es una unidad: el trozo de una celda de 100 m que cae dentro de una sección censal y
tiene soporte residencial. Una celda partida por el límite de dos secciones da dos unidades.

Soporte residencial (OSM; el Catastro queda fuera por su licencia, SPEC F-02), por orden:
1. «edificios»: edificios con etiqueta de vivienda (`TIPOS_VIVIENDA`), más los `building=yes`
   cuyo punto interior cae en una zona `landuse=residential`. Peso: superficie de la planta.
2. «uso_suelo»: si la sección no tiene ninguno de esos edificios, la superficie de
   `landuse=residential` dentro de la sección.
3. «edificios_sin_tipo»: si tampoco hay `landuse=residential`, los `building=yes` de la
   sección (sin tipo declarado: confianza menor, y así consta en cada unidad).
4. Sin ninguno: la sección queda «pendiente_localizar» con su población, y no se reparte
   (R-DEM-02).

Reparto: la población de cada sección y grupo de edad se reparte entre sus unidades en
proporción al peso, así que la suma por sección y edad reproduce el INE (R-DEM-01). La
posición dentro de la sección es una estimación: no son hogares.

Límite declarado: el peso es la superficie de planta, no la de vivienda; no usa el número de
plantas.
"""

from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import pyogrio
from shapely.geometry import box

CRS_CALCULO = "EPSG:25830"
LADO_CELDA_M = 100
TIPOS_VIVIENDA = ("apartments", "house", "residential", "detached", "terrace",
                  "semidetached_house", "bungalow", "dormitory", "farm")
SOPORTE_EDIFICIOS, SOPORTE_USO_SUELO, SOPORTE_SIN_TIPO = "edificios", "uso_suelo", "edificios_sin_tipo"


def leer_osm(pbf: Path, condicion: str, columnas_extra: tuple[str, ...] = ()) -> gpd.GeoDataFrame:
    """Lee polígonos del PBF de OSM que cumplen una condición SQL y los pasa a EPSG:25830."""
    capa = pyogrio.read_dataframe(pbf, layer="multipolygons",
                                  columns=["osm_id", "osm_way_id", "building", "landuse", *columnas_extra],
                                  where=condicion)
    return capa.to_crs(CRS_CALCULO)


def leer_soporte_osm(pbf: Path) -> tuple[gpd.GeoDataFrame, gpd.GeoDataFrame]:
    """Edificios (cualquier valor de `building`, con las etiquetas de uso) y zonas `landuse=residential`."""
    from .usos_edificios import CLAVES
    return (leer_osm(pbf, "building IS NOT NULL", (*CLAVES, "other_tags")),
            leer_osm(pbf, "landuse = 'residential'"))


def leer_secciones(ruta: Path) -> gpd.GeoDataFrame:
    """Polígonos de sección 2025 (solo TIPO SECCIONADO: los de DISTRITO se solapan)."""
    capa = pyogrio.read_dataframe(ruta, columns=["CUSEC", "TIPO"])
    capa = capa[capa["TIPO"] == "SECCIONADO"].rename(columns={"CUSEC": "cusec"})
    return capa[["cusec", "geometry"]].to_crs(CRS_CALCULO).reset_index(drop=True)


def puntos_en_poligonos(puntos: gpd.GeoDataFrame, poligonos: gpd.GeoDataFrame, columna: str) -> pd.Series:
    """Para cada punto, el valor de `columna` del polígono que lo contiene (NaN si ninguno)."""
    unidos = gpd.sjoin(puntos[["geometry"]], poligonos[[columna, "geometry"]], how="left", predicate="within")
    return unidos[~unidos.index.duplicated(keep="first")][columna]


def edificios_residenciales(edificios: gpd.GeoDataFrame, usos: gpd.GeoDataFrame,
                            excluir_usos: tuple[str, ...] = ()) -> gpd.GeoDataFrame:
    """Edificios que cuentan como vivienda, con su punto interior, su superficie y el criterio usado.

    `excluir_usos`: clases de `usos_edificios` cuyos `building=yes` no cuentan como vivienda
    (escenario de sensibilidad; por defecto no se excluye ninguno). Los edificios con etiqueta
    explícita de vivienda nunca se excluyen.
    """
    from .usos_edificios import clasificar_tabla
    explicitos = edificios["building"].isin(TIPOS_VIVIENDA)
    ambiguos = edificios["building"] == "yes"
    if excluir_usos:
        ambiguos &= ~clasificar_tabla(edificios).isin(excluir_usos)
    candidatos = edificios[explicitos | ambiguos].copy()
    candidatos["area_m2"] = candidatos.geometry.area
    candidatos["geometry"] = candidatos.geometry.representative_point()
    usos_marcados = usos[["geometry"]].assign(uso_residencial=True)
    en_uso = puntos_en_poligonos(candidatos, usos_marcados, "uso_residencial").fillna(False).astype(bool)
    candidatos["criterio"] = np.where(candidatos["building"] == "yes", "yes_en_uso_residencial", "etiqueta_vivienda")
    seleccion = candidatos[(candidatos["building"] != "yes") | en_uso]
    return seleccion[["osm_id", "osm_way_id", "building", "criterio", "area_m2", "geometry"]]


def edificios_sin_tipo(edificios: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Todos los `building=yes`, con punto interior y superficie (respaldo del nivel 3)."""
    sin_tipo = edificios[edificios["building"] == "yes"].copy()
    sin_tipo["area_m2"] = sin_tipo.geometry.area
    sin_tipo["geometry"] = sin_tipo.geometry.representative_point()
    sin_tipo["criterio"] = "yes_sin_tipo"
    return sin_tipo[["osm_id", "osm_way_id", "building", "criterio", "area_m2", "geometry"]]


def indice_celda(x: pd.Series, y: pd.Series) -> pd.Series:
    """Identificador de la celda de 100 m que contiene cada coordenada: 'ix_iy' en EPSG:25830."""
    ix = np.floor(x / LADO_CELDA_M).astype(int).astype(str)
    iy = np.floor(y / LADO_CELDA_M).astype(int).astype(str)
    return ix + "_" + iy


def unidades_desde_edificios(edificios: gpd.GeoDataFrame, secciones: gpd.GeoDataFrame,
                              soporte: str = SOPORTE_EDIFICIOS) -> pd.DataFrame:
    """Agrupa los edificios por sección y celda: peso = superficie; punto = media ponderada."""
    edificios = edificios.copy()
    edificios["cusec"] = puntos_en_poligonos(edificios, secciones, "cusec")
    edificios = edificios.dropna(subset=["cusec"])
    edificios["celda"] = indice_celda(edificios.geometry.x, edificios.geometry.y)
    edificios["xa"] = edificios.geometry.x * edificios["area_m2"]
    edificios["ya"] = edificios.geometry.y * edificios["area_m2"]
    grupos = edificios.groupby(["cusec", "celda"], as_index=False).agg(
        peso=("area_m2", "sum"), xa=("xa", "sum"), ya=("ya", "sum"), edificios=("area_m2", "size"))
    grupos["x"], grupos["y"] = grupos["xa"] / grupos["peso"], grupos["ya"] / grupos["peso"]
    grupos["soporte"] = soporte
    return grupos.drop(columns=["xa", "ya"])


def malla_sobre(geometria: gpd.GeoSeries) -> gpd.GeoDataFrame:
    """Celdas de 100 m alineadas a múltiplos de 100 que cubren la extensión de una geometría."""
    xmin, ymin, xmax, ymax = geometria.total_bounds
    ixs = np.arange(np.floor(xmin / LADO_CELDA_M), np.ceil(xmax / LADO_CELDA_M)).astype(int)
    iys = np.arange(np.floor(ymin / LADO_CELDA_M), np.ceil(ymax / LADO_CELDA_M)).astype(int)
    rejilla = [(ix, iy) for ix in ixs for iy in iys]
    return gpd.GeoDataFrame(
        {"celda": [f"{ix}_{iy}" for ix, iy in rejilla]},
        geometry=[box(ix * LADO_CELDA_M, iy * LADO_CELDA_M, (ix + 1) * LADO_CELDA_M, (iy + 1) * LADO_CELDA_M)
                  for ix, iy in rejilla], crs=CRS_CALCULO)


def unidades_desde_uso_suelo(usos: gpd.GeoDataFrame, secciones: gpd.GeoDataFrame) -> pd.DataFrame:
    """Para secciones sin edificios: trozos de landuse=residencial ∩ sección ∩ celda; peso = superficie."""
    if secciones.empty or usos.empty:
        return pd.DataFrame(columns=["cusec", "celda", "peso", "edificios", "x", "y", "soporte"])
    trozos = gpd.overlay(usos[["geometry"]], secciones[["cusec", "geometry"]], how="intersection",
                         keep_geom_type=True)
    if trozos.empty:
        return pd.DataFrame(columns=["cusec", "celda", "peso", "edificios", "x", "y", "soporte"])
    piezas = gpd.overlay(trozos, malla_sobre(trozos.geometry), how="intersection", keep_geom_type=True)
    piezas = piezas.dissolve(by=["cusec", "celda"], as_index=False)
    piezas["peso"] = piezas.geometry.area
    piezas = piezas[piezas["peso"] > 0]
    puntos = piezas.geometry.representative_point()
    return pd.DataFrame({"cusec": piezas["cusec"], "celda": piezas["celda"], "peso": piezas["peso"],
                         "edificios": 0, "x": puntos.x, "y": puntos.y, "soporte": SOPORTE_USO_SUELO})


def poblacion_ancha(por_edad: pd.DataFrame) -> pd.DataFrame:
    """Población por sección con una columna por grupo de edad: 'edad_000_004', ..., 'edad_100_mas'."""
    def nombre(fila):
        maximo = "mas" if pd.isna(fila["edad_max"]) else f"{int(fila['edad_max']):03d}"
        return f"edad_{int(fila['edad_min']):03d}_{maximo}"
    tabla = por_edad.assign(columna=por_edad.apply(nombre, axis=1))
    ancha = tabla.pivot_table(index="cusec", columns="columna", values="poblacion", aggfunc="sum", fill_value=0)
    return ancha[sorted(ancha.columns)].astype(float)


def repartir(unidades: pd.DataFrame, ancha: pd.DataFrame) -> pd.DataFrame:
    """Reparte la población de cada sección entre sus unidades en proporción al peso."""
    unidades = unidades.copy()
    unidades["fraccion"] = unidades["peso"] / unidades.groupby("cusec")["peso"].transform("sum")
    columnas = list(ancha.columns)
    poblacion = ancha.reindex(unidades["cusec"]).to_numpy() * unidades["fraccion"].to_numpy()[:, None]
    unidades[columnas] = poblacion
    unidades["poblacion_total"] = poblacion.sum(axis=1)
    for umbral in (65, 75, 85):
        mayores = [c for c in columnas if int(c.split("_")[1]) >= umbral]
        unidades[f"poblacion_{umbral}_mas"] = unidades[mayores].sum(axis=1)
    return unidades


def puntos_interiores(secciones: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Punto interior de cada sección (garantizado dentro del polígono): referencia de P-05."""
    return gpd.GeoDataFrame({"cusec": secciones["cusec"]}, geometry=secciones.geometry.representative_point(),
                            crs=secciones.crs)


def construir_unidades(edificios: gpd.GeoDataFrame, usos: gpd.GeoDataFrame, secciones: gpd.GeoDataFrame,
                       por_edad: pd.DataFrame, excluir_usos: tuple[str, ...] = ()) -> dict:
    """Unidades con población, listado de secciones pendientes de localizar y conteos."""
    residenciales = edificios_residenciales(edificios, usos, excluir_usos)
    por_edificios = unidades_desde_edificios(residenciales, secciones)
    con_dato = set(por_edad["cusec"])
    sin_edificios = secciones[secciones["cusec"].isin(con_dato - set(por_edificios["cusec"]))]
    por_uso = unidades_desde_uso_suelo(usos, sin_edificios)
    restantes = sin_edificios[~sin_edificios["cusec"].isin(set(por_uso["cusec"]))]
    por_sin_tipo = unidades_desde_edificios(edificios_sin_tipo(edificios), restantes, SOPORTE_SIN_TIPO)
    unidades = pd.concat([por_edificios, por_uso, por_sin_tipo], ignore_index=True)
    unidades = unidades[unidades["cusec"].isin(con_dato)]
    ancha = poblacion_ancha(por_edad)
    unidades = repartir(unidades, ancha)
    unidades.insert(0, "unidad", unidades["cusec"] + "_" + unidades["celda"])
    pendientes = ancha.loc[sorted(con_dato - set(unidades["cusec"]))]
    listado = pd.DataFrame({"cusec": pendientes.index, "poblacion_total": pendientes.sum(axis=1).to_numpy(),
                            "estado": "no_evaluable", "motivo": "pendiente_localizar"})
    return {"unidades": unidades.reset_index(drop=True), "pendientes": listado,
            "conteos": conteos_unidades(residenciales, unidades, listado, ancha)}


def conteos_unidades(residenciales, unidades, pendientes, ancha) -> dict:
    """Resumen: edificios usados, unidades por soporte, secciones y población por estado."""
    secciones_por_soporte = unidades.groupby("soporte")["cusec"].nunique().to_dict()
    return {
        "edificios_residenciales": len(residenciales),
        "edificios_por_criterio": residenciales["criterio"].value_counts().to_dict(),
        "unidades": len(unidades),
        "unidades_por_soporte": unidades["soporte"].value_counts().to_dict(),
        "celdas_distintas": int(unidades["celda"].nunique()),
        "secciones_por_soporte": {k: int(v) for k, v in secciones_por_soporte.items()},
        "secciones_pendiente_localizar": len(pendientes),
        "poblacion_pendiente_localizar": float(pendientes["poblacion_total"].sum()),
        "poblacion_en_unidades": float(unidades["poblacion_total"].sum()),
        "poblacion_ine": float(ancha.to_numpy().sum()),
    }


def diferencia_maxima_con_ine(unidades: pd.DataFrame, ancha: pd.DataFrame) -> float:
    """Mayor diferencia absoluta, por sección y grupo de edad, entre la suma de unidades y el INE."""
    columnas = list(ancha.columns)
    sumas = unidades.groupby("cusec")[columnas].sum()
    comunes = ancha.loc[sumas.index, columnas]
    return float((sumas - comunes).abs().to_numpy().max()) if len(sumas) else 0.0
