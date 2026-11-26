"""Población INE por sección censal y edad quinquenal (H1, entregable 2; R-DEM-01 y R-DEM-03).

Fuente: INE, tabla 69213, «Población por sección censal, sexo y edad» (CC BY 4.0).
Perfil del archivo en fases/H1_datos_normalizados/perfiles/ine_69213_20261113.json.
Hechos del perfil del 13/11/2026 en los que se apoya este módulo:
- separador «;», UTF-8 con BOM y punto como separador de miles: todos los valores son
  enteros, escritos como «512» o «7.113.886»;
- las filas agregadas se reconocen por campos vacíos: sin municipio es la provincia, y sin
  sección es el municipio. Sexo «Total» y Edad «Todas las edades» son también agregados;
- si una sección no tiene dato en un periodo, están vacías todas sus celdas de ese periodo.
  Son secciones que dejaron de existir (los 48 «códigos sin polígono» de la auditoría).

Solo se usa Sexo «Total»: el análisis desagrega por edad, no por sexo.
"""

import re
from pathlib import Path

import pandas as pd
import pyogrio

PERIODO = "2025"
SEXO_TOTAL = "Total"
EDAD_TOTAL = "Todas las edades"
CODIGO_MADRID_CAPITAL = "28079"
# Desgloses comunes de mayores (SPEC D-14): 65+, 75+ y 85+.
UMBRALES_MAYORES = (65, 75, 85)
TIPO_POLIGONO_SECCION = "SECCIONADO"  # la capa 2025 trae también polígonos de tipo DISTRITO

NUMERO_INE = re.compile(r"^(\d+|\d{1,3}(\.\d{3})+)$")
EDAD_QUINQUENAL = re.compile(r"^De (\d+) a (\d+) años$")
EDAD_ABIERTA = re.compile(r"^(\d+) y más años$")


def leer_tabla(ruta: Path) -> pd.DataFrame:
    """Lee la tabla 69213 como texto, sin convertir los vacíos en NaN."""
    return pd.read_csv(ruta, sep=";", dtype=str, keep_default_na=False, encoding="utf-8-sig")


def a_entero(serie: pd.Series) -> pd.Series:
    """Convierte '7.113.886' o '512' en entero y '' en nulo; falla con cualquier otra forma."""
    rellenos = serie[serie != ""]
    raras = rellenos[~rellenos.str.match(NUMERO_INE)]
    if len(raras):
        raise ValueError(f"{len(raras)} valores de Total con una forma no prevista")
    return pd.to_numeric(serie.str.replace(".", "", regex=False).replace("", None)).astype("Int64")


def limites_de_edad(etiqueta: str) -> tuple[int, int | None]:
    """Edad mínima y máxima de un grupo: 'De 65 a 69 años' -> (65, 69); '100 y más años' -> (100, None)."""
    if quinquenal := EDAD_QUINQUENAL.match(etiqueta):
        return int(quinquenal.group(1)), int(quinquenal.group(2))
    if abierta := EDAD_ABIERTA.match(etiqueta):
        return int(abierta.group(1)), None
    raise ValueError(f"Grupo de edad no reconocido: {etiqueta!r}")


def con_codigos(tabla: pd.DataFrame) -> pd.DataFrame:
    """Añade nivel ('provincia', 'municipio' o 'seccion'), código del municipio y CUSEC."""
    tabla = tabla.copy()
    tabla["nivel"] = "seccion"
    tabla.loc[tabla["Secciones"] == "", "nivel"] = "municipio"
    tabla.loc[tabla["Municipios"] == "", "nivel"] = "provincia"
    tabla["cumun"] = tabla["Municipios"].str.extract(r"^(\d{5}) ", expand=False)
    tabla["cusec"] = tabla["Secciones"].str.extract(r"^(\d{10}) ", expand=False)
    tabla["municipio"] = tabla["Municipios"].str.replace(r"^\d{5} ", "", regex=True)
    sin_codigo = ((tabla["nivel"] != "provincia") & tabla["cumun"].isna()) | (
        (tabla["nivel"] == "seccion") & tabla["cusec"].isna())
    if sin_codigo.any():
        raise ValueError(f"{int(sin_codigo.sum())} filas sin código de municipio o sección reconocible")
    if (tabla.loc[tabla["nivel"] == "seccion", "cusec"].str[:5]
            != tabla.loc[tabla["nivel"] == "seccion", "cumun"]).any():
        raise ValueError("Hay secciones cuyo código no empieza por el de su municipio")
    tabla["poblacion"] = a_entero(tabla["Total"])
    return tabla


def poblacion_por_edad(tabla: pd.DataFrame, periodo: str = PERIODO) -> pd.DataFrame:
    """Formato largo: una fila por sección con dato y grupo quinquenal, con su población."""
    filas = tabla[(tabla["nivel"] == "seccion") & (tabla["Periodo"] == periodo)
                  & (tabla["Sexo"] == SEXO_TOTAL) & (tabla["Edad"] != EDAD_TOTAL)
                  & tabla["poblacion"].notna()]
    salida = filas[["cusec", "cumun", "municipio", "Edad", "poblacion"]].rename(
        columns={"Edad": "grupo_edad"})
    limites = salida["grupo_edad"].map(limites_de_edad)
    salida["edad_min"] = limites.str[0].astype("Int64")
    salida["edad_max"] = limites.str[1].astype("Int64")
    return salida.sort_values(["cusec", "edad_min"]).reset_index(drop=True)


def poblacion_por_seccion(por_edad: pd.DataFrame) -> pd.DataFrame:
    """Una fila por sección: población total y desgloses de mayores (D-14)."""
    secciones = por_edad.groupby(["cusec", "cumun", "municipio"], as_index=False)["poblacion"].sum()
    for umbral in UMBRALES_MAYORES:
        mayores = por_edad[por_edad["edad_min"] >= umbral].groupby("cusec")["poblacion"].sum()
        secciones[f"poblacion_{umbral}_mas"] = secciones["cusec"].map(mayores).fillna(0).astype("Int64")
    return secciones.rename(columns={"poblacion": "poblacion_total"})


def descuadres(tabla: pd.DataFrame, por_edad: pd.DataFrame, periodo: str = PERIODO) -> list[str]:
    """Compara las sumas de las secciones con los agregados que publica el propio INE.

    Comprueba, por grupo de edad: municipio frente a suma de sus secciones y provincia frente
    a suma de todas; y por sección, 'Todas las edades' frente a la suma de sus grupos.
    Devuelve una lista vacía si todo cuadra (son enteros: tolerancia cero, dentro de 10⁻⁶).
    """
    agregados = tabla[(tabla["Periodo"] == periodo) & (tabla["Sexo"] == SEXO_TOTAL)]
    problemas = []
    suma_muni = por_edad.groupby(["cumun", "grupo_edad"])["poblacion"].sum()
    ine_muni = agregados[(agregados["nivel"] == "municipio") & (agregados["Edad"] != EDAD_TOTAL)]
    ine_muni = ine_muni.set_index(["cumun", "Edad"])["poblacion"].rename_axis(["cumun", "grupo_edad"])
    distintos = ine_muni.sub(suma_muni, fill_value=0).abs() > 1e-6
    problemas += [f"municipio {m}, {e}: INE distinto de la suma de secciones" for m, e in ine_muni[distintos].index]
    suma_prov = por_edad.groupby("grupo_edad")["poblacion"].sum()
    ine_prov = agregados[(agregados["nivel"] == "provincia") & (agregados["Edad"] != EDAD_TOTAL)]
    ine_prov = ine_prov.set_index("Edad")["poblacion"]
    problemas += [f"provincia, {e}: INE distinto de la suma de secciones"
                  for e in ine_prov.index if abs(ine_prov[e] - suma_prov.get(e, 0)) > 1e-6]
    total_sec = agregados[(agregados["nivel"] == "seccion") & (agregados["Edad"] == EDAD_TOTAL)
                          & agregados["poblacion"].notna()].set_index("cusec")["poblacion"]
    suma_sec = por_edad.groupby("cusec")["poblacion"].sum()
    distintas = total_sec.sub(suma_sec, fill_value=0).abs() > 1e-6
    problemas += [f"sección {s}: 'Todas las edades' distinto de la suma de grupos" for s in total_sec[distintas].index]
    return problemas


def codigos_sin_dato(tabla: pd.DataFrame, periodo: str = PERIODO) -> pd.DataFrame:
    """Secciones que la tabla nombra pero sin población en el periodo, con los periodos en que sí la tienen."""
    totales = tabla[(tabla["nivel"] == "seccion") & (tabla["Sexo"] == SEXO_TOTAL)
                    & (tabla["Edad"] == EDAD_TOTAL)]
    sin = totales[(totales["Periodo"] == periodo) & totales["poblacion"].isna()]
    con_dato = totales[totales["poblacion"].notna()].groupby("cusec")["Periodo"].agg(
        lambda periodos: ",".join(sorted(periodos)))
    salida = sin[["cusec", "cumun", "municipio"]].copy()
    salida["periodos_con_dato"] = salida["cusec"].map(con_dato).fillna("")
    return salida.sort_values("cusec").reset_index(drop=True)


def leer_poligonos(ruta: Path) -> pd.DataFrame:
    """Atributos de la capa de secciones 2025 (sin geometría): CUSEC y TIPO."""
    return pyogrio.read_dataframe(ruta, columns=["CUSEC", "TIPO"], read_geometry=False)


def cruce_con_poligonos(secciones: pd.DataFrame, sin_dato: pd.DataFrame, poligonos: pd.DataFrame) -> dict:
    """Cruza los códigos del INE con los polígonos de tipo sección; devuelve conteos y listados."""
    de_seccion = set(poligonos.loc[poligonos["TIPO"] == TIPO_POLIGONO_SECCION, "CUSEC"])
    con_dato, sin = set(secciones["cusec"]), set(sin_dato["cusec"])
    return {
        "poligonos": len(poligonos),
        "poligonos_por_tipo": poligonos["TIPO"].value_counts().to_dict(),
        "secciones_con_dato_y_poligono": len(con_dato & de_seccion),
        "secciones_con_dato_sin_poligono": sorted(con_dato - de_seccion),
        "codigos_sin_dato_con_poligono": sorted(sin & de_seccion),
        "poligonos_de_seccion_sin_codigo_ine": sorted(de_seccion - con_dato - sin),
    }


def normalizar(tabla_cruda: pd.DataFrame, poligonos: pd.DataFrame, periodo: str = PERIODO) -> dict:
    """Aplica la normalización completa y devuelve tablas, listados, cruce y conteos."""
    tabla = con_codigos(tabla_cruda)
    por_edad = poblacion_por_edad(tabla, periodo)
    secciones = poblacion_por_seccion(por_edad)
    sin_dato = codigos_sin_dato(tabla, periodo)
    capital = secciones[secciones["cumun"] == CODIGO_MADRID_CAPITAL]
    return {
        "por_edad": por_edad, "por_seccion": secciones, "codigos_sin_dato": sin_dato,
        "descuadres": descuadres(tabla, por_edad, periodo),
        "cruce_poligonos": cruce_con_poligonos(secciones, sin_dato, poligonos),
        "conteos": {
            "periodo": periodo,
            "filas_origen": len(tabla_cruda),
            "municipios": int(secciones["cumun"].nunique()),
            "secciones_con_dato": len(secciones),
            "codigos_sin_dato": len(sin_dato),
            "poblacion_total": int(secciones["poblacion_total"].sum()),
            **{f"poblacion_{u}_mas": int(secciones[f"poblacion_{u}_mas"].sum()) for u in UMBRALES_MAYORES},
            "capital_secciones": len(capital),
            "capital_poblacion_total": int(capital["poblacion_total"].sum()),
            "capital_poblacion_65_mas": int(capital["poblacion_65_mas"].sum()),
        },
    }
