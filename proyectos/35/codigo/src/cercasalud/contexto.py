"""Capas de contexto de Madrid capital (SPEC D-16): personas que viven solas por barrio e IGUALA
por distrito. **Solo contexto:** no intervienen en ninguna puntuación, priorización ni
optimización, no se trasladan a secciones y se muestran con su año.

**Personas que viven solas** (Ayuntamiento de Madrid, explotación del Padrón a 1/1/2026,
`personas_solas.xlsx`, hoja «AMBOS SEXOS»): total y 65 años o más por barrio. Vivir solo no
equivale a soledad no deseada. Los datos no son oficiales de población (nota del propio archivo).

**IGUALA** (índice de vulnerabilidad territorial agregado, Ayuntamiento de Madrid,
`informe_globales.xlsx`, hoja «Vul. esferas distritos»): solo se publica agregado **por
distrito**; por barrio solo hay indicadores sueltos de cada esfera. Se toma el último año.

**Enlace con las unidades:** cada unidad de demanda de la capital se asigna al barrio que
contiene su punto (EPSG:25830; `barrios.zip`, 131 barrios). Junto a cada barrio se muestran,
para comparar, su población 65+ (INE 2025, unidades de demanda) y sus personas sin opción en A
y en C, ya calculadas en las etapas anteriores.
"""

import re
from pathlib import Path

import geopandas as gpd
import pandas as pd

from .lector_xlsx import leer_hoja

ARCHIVO_SOLAS = ("madrid_personas_solas", "personas_solas.xlsx")
ARCHIVO_IGUALA = ("madrid_iguala", "informe_globales.xlsx")
ARCHIVO_BARRIOS = ("madrid_barrios", "barrios.zip")
PATRON_BARRIO = re.compile(r"^(\d{3})\.\s+(.+)$")


def personas_solas(ruta: Path) -> pd.DataFrame:
    """Personas que viven solas por barrio: total y 65+ (suma de los grupos de 65 años en adelante)."""
    hoja = leer_hoja(ruta, "AMBOS SEXOS")
    cabecera = [str(c) if c is not None else "" for c in hoja.iloc[5]]
    mayores = [j for j, nombre in enumerate(cabecera) if re.match(r"De (6[5-9]|[7-9]\d|100)", nombre)]
    total = cabecera.index("Total")
    filas = []
    for _, fila in hoja.iloc[6:].iterrows():
        coincide = PATRON_BARRIO.match(str(fila[1] or "").strip())
        if coincide:
            filas.append({"cod_barrio": int(coincide.group(1)), "barrio": coincide.group(2),
                          "solas_total": float(fila[total]), "solas_65_mas": float(sum(fila[j] or 0 for j in mayores))})
    return pd.DataFrame(filas)


def iguala_distritos(ruta: Path) -> pd.DataFrame:
    """IGUALA agregado y por esfera, por distrito, del último año publicado."""
    hoja = leer_hoja(ruta, "Vul. esferas distritos")
    tabla = hoja.iloc[1:].set_axis([str(c) for c in hoja.iloc[0]], axis=1).dropna(subset=["Codigo distrito"])
    tabla = tabla[[c for c in tabla.columns if "media ciudad" not in c]]
    ultimo = tabla["Fecha datos"].max()
    return tabla[tabla["Fecha datos"] == ultimo].rename(columns={"Codigo distrito": "cod_distrito"}).assign(
        cod_distrito=lambda t: t["cod_distrito"].astype(int)).reset_index(drop=True)


def barrio_de_unidades(unidades: pd.DataFrame, barrios: gpd.GeoDataFrame) -> pd.Series:
    """Código de barrio de cada unidad de la capital (por su punto), o NaN si no cae en ninguno."""
    puntos = gpd.GeoDataFrame(unidades[["unidad"]], geometry=gpd.points_from_xy(unidades["x"], unidades["y"]),
                              crs="EPSG:25830")
    unidos = gpd.sjoin(puntos, barrios[["COD_BAR", "geometry"]].to_crs(25830), how="left", predicate="within")
    unidos = unidos[~unidos.index.duplicated(keep="first")]
    return pd.to_numeric(unidos["COD_BAR"], errors="coerce").reindex(unidades.index)


def tabla_barrios(unidades: pd.DataFrame, estados: pd.DataFrame, solas: pd.DataFrame,
                  barrios: gpd.GeoDataFrame) -> pd.DataFrame:
    """Contexto por barrio junto a las cifras de A y C ya calculadas (columnas `estado_*`)."""
    tabla = unidades.assign(cod_barrio=barrio_de_unidades(unidades, barrios)).merge(estados, on="unidad")
    tabla = tabla.dropna(subset=["cod_barrio"]).assign(cod_barrio=lambda t: t["cod_barrio"].astype(int))

    def poblacion_en(columna_estado: str, estado: str) -> pd.Series:
        """Población total de cada unidad si está en ese estado; 0 si no."""
        return (tabla[columna_estado] == estado) * tabla["poblacion_total"]

    resumen = tabla.assign(
        sin_a_pie=poblacion_en("estado_pie", "sin_opcion_verificada"),
        sin_a_transporte=poblacion_en("estado_transporte", "sin_opcion_verificada"),
        c_pie=poblacion_en("estado_c_pie", "carencia_coincidente"),
        c_transporte=poblacion_en("estado_c_transporte", "carencia_coincidente"),
        sin_b=poblacion_en("estado_b", "sin_opcion_verificada"),
    ).groupby("cod_barrio")[["poblacion_total", "poblacion_65_mas", "sin_a_pie", "sin_a_transporte", "sin_b",
                             "c_pie", "c_transporte"]].sum().reset_index()
    nombres = barrios.assign(cod_barrio=pd.to_numeric(barrios["COD_BAR"]))[["cod_barrio", "NOMBRE", "CODDIS", "NOMDIS"]]
    salida = nombres.merge(solas.drop(columns="barrio"), on="cod_barrio", how="left").merge(
        resumen, on="cod_barrio", how="left")
    return salida.rename(columns={"NOMBRE": "barrio", "CODDIS": "cod_distrito", "NOMDIS": "distrito"})


def prueba_integracion(barrios: pd.DataFrame, tamanos: tuple[int, ...] = (10, 20)) -> pd.DataFrame:
    """Prueba de integración (SPEC §10, R-BCH-02): barrios que prioriza C frente a los que
    priorizan A o B por separado.

    Para cada modo de A y cada tamaño N, compara los N barrios con más población en C con los N
    con más población sin opción en A y en B: cuántos coinciden y su índice de Jaccard. Se
    informa tal como sale, sin umbral de éxito (SPEC §10). Prioridad = población, no tasa.
    """
    filas = []
    for modo in ("pie", "transporte"):
        rangos = {"C": f"c_{modo}", "A": f"sin_a_{modo}", "B": "sin_b"}
        for n in tamanos:
            top = {k: set(barrios.nlargest(n, col)["cod_barrio"]) for k, col in rangos.items()}
            for otro in ("A", "B"):
                comunes = top["C"] & top[otro]
                filas.append({"modo_a": modo, "n": n, "comparacion": f"C frente a {otro}", "comunes": len(comunes),
                              "jaccard": len(comunes) / len(top["C"] | top[otro]),
                              "solo_en_c": ", ".join(sorted(barrios.loc[barrios["cod_barrio"].isin(top["C"] - top[otro]),
                                                                         "barrio"]))})
    return pd.DataFrame(filas)
