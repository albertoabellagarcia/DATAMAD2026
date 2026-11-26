"""Filtro reproducible de atención primaria pública (R-DAT-02, R-DAT-03).

Portado de historico/decision_audit/scripts/compare_spatial.py:16-17 (lectura) y :65-72
(deduplicado por `centro_nro_registro`, filtro por tipo y dependencia y validez de
coordenadas). Cambios respecto al original:
- la columna personal `NIF` se elimina nada más leer (R-DAT-03);
- las discrepancias entre filas del mismo centro se detectan ANTES de deduplicar;
- cada centro de tipo primaria que queda fuera se lista con su motivo.
- desde el 15/11/2026, A2 aceptada por delegación: también se incluye la dependencia
  patrimonial SERMAS; la vía de inclusión y las discrepancias patrimoniales quedan separadas.

El registro tiene varias filas por centro (una por oferta asistencial, según la auditoría),
así que una fila no es un centro.
"""

from pathlib import Path

import pandas as pd

CLAVE = "centro_nro_registro"
TIPO = "centro_tipo"
DEPENDENCIA = "dependecia_funcional"  # sic: así se llama la columna en el origen
PATRIMONIAL = "dependecia_patrimonial"  # sic: también falta la «n» en el origen
MUNICIPIO = "municipio_nombre"
X, Y = "localizacion_coordenada_x", "localizacion_coordenada_y"
COLUMNAS_PERSONALES = ("NIF",)

TIPOS_PRIMARIA = ("Centro de salud", "Consultorio de atención primaria")
DEPENDENCIA_PUBLICA = "Servicios o Institutos de Salud de las CC.AA"
PATRIMONIAL_PUBLICA = "Servicio Madrileño de Salud"
MUNICIPIO_CAPITAL = "Madrid"
# Umbrales del original (compare_spatial.py:72): descartan ceros y centinelas fuera de la Comunidad.
X_MINIMA, Y_MINIMA = 300_000, 4_350_000
CAMPOS_A_CONTRASTAR = (TIPO, DEPENDENCIA, PATRIMONIAL, MUNICIPIO, X, Y)


def leer_registro(ruta: Path) -> pd.DataFrame:
    """Lee el registro sanitario como texto, sin convertir vacíos en NaN, y quita columnas personales."""
    tabla = pd.read_csv(ruta, sep=";", dtype=str, keep_default_na=False, encoding="utf-8-sig")
    tabla = tabla.drop(columns=[c for c in COLUMNAS_PERSONALES if c in tabla.columns])
    return tabla.apply(lambda columna: columna.str.strip())


def a_numero(serie: pd.Series) -> pd.Series:
    """Convierte coordenadas escritas como texto en números (coma decimal admitida)."""
    return pd.to_numeric(serie.str.replace(",", ".", regex=False), errors="coerce")


def detectar_discrepancias(tabla: pd.DataFrame) -> pd.DataFrame:
    """Centros de tipo primaria cuyas filas no coinciden en algún campo que decide el filtro."""
    ids_primaria = tabla.loc[tabla[TIPO].isin(TIPOS_PRIMARIA), CLAVE].unique()
    subconjunto = tabla[tabla[CLAVE].isin(ids_primaria)]
    distintos = subconjunto.groupby(CLAVE)[list(CAMPOS_A_CONTRASTAR)].nunique()
    filas = [
        {CLAVE: centro, "campo": campo, "valores_distintos": int(n)}
        for centro, fila in distintos.iterrows() for campo, n in fila.items() if n > 1
    ]
    return pd.DataFrame(filas, columns=[CLAVE, "campo", "valores_distintos"])


def un_registro_por_centro(tabla: pd.DataFrame) -> pd.DataFrame:
    """Deja la primera fila de cada centro (criterio del original) y cuenta sus filas de origen."""
    filas = tabla.groupby(CLAVE).size().rename("filas_origen")
    centros = tabla.drop_duplicates(CLAVE, keep="first").set_index(CLAVE)
    return centros.join(filas).reset_index()


def motivo_exclusion(centro: pd.Series) -> str:
    """Motivo por el que un centro de tipo primaria no entra en la oferta pública, o '' si entra."""
    if not via_inclusion(centro):
        return "dependencia_no_publica_autonomica" if centro[DEPENDENCIA] else "dependencia_vacia"
    x, y = centro["x"], centro["y"]
    if pd.isna(x) or pd.isna(y):
        return "sin_coordenadas"
    if x <= X_MINIMA or y <= Y_MINIMA:
        return "coordenadas_fuera_de_rango"
    return ""


def via_inclusion(centro: pd.Series) -> str:
    """Vía de R-DAT-02: funcional autonómica, o patrimonial SERMAS si falla la primera.

    A2 aceptada por delegación el 15/11/2026. La vía patrimonial queda identificada para
    revisar sus altas; no sustituye la comprobación de tipo, coordenadas o discrepancias.
    """
    if centro[DEPENDENCIA] == DEPENDENCIA_PUBLICA:
        return "funcional_autonomica"
    if centro[PATRIMONIAL] == PATRIMONIAL_PUBLICA:
        return "patrimonial_sermas"
    return ""


def leer_coordenadas_curadas(ruta: Path) -> pd.DataFrame:
    """Coordenadas curadas (curado/primaria_coordenadas_osm.csv): id, x, y y precisión."""
    return pd.read_csv(ruta, dtype={CLAVE: str, "osm_id": str}, keep_default_na=False)


def completar_coordenadas(candidatos: pd.DataFrame, curadas: pd.DataFrame | None) -> pd.DataFrame:
    """Rellena x, y vacíos con las coordenadas curadas; nunca sustituye las del registro.

    Añade `origen_coordenadas` ('registro' o 'curado_osm') y `precision_coordenadas`.
    """
    tabla = candidatos.assign(origen_coordenadas="registro", precision_coordenadas="registro")
    if curadas is None or curadas.empty:
        return tabla
    curadas = curadas.set_index(CLAVE)
    vacias = tabla["x"].isna() & tabla["y"].isna() & tabla[CLAVE].isin(curadas.index)
    ids = tabla.loc[vacias, CLAVE]
    tabla.loc[vacias, "x"] = ids.map(curadas["x"]).astype(float).to_numpy()
    tabla.loc[vacias, "y"] = ids.map(curadas["y"]).astype(float).to_numpy()
    tabla.loc[vacias, "origen_coordenadas"] = "curado_osm"
    tabla.loc[vacias, "precision_coordenadas"] = ids.map(curadas["precision"]).to_numpy()
    return tabla


def filtrar_primaria(tabla: pd.DataFrame, curadas: pd.DataFrame | None = None) -> dict:
    """Aplica el filtro completo y devuelve centros incluidos, excluidos, discrepancias y conteos.

    `curadas`: coordenadas para los centros que el registro publica sin ellas (opcional).
    """
    discrepancias = detectar_discrepancias(tabla)
    centros = un_registro_por_centro(tabla)
    candidatos = centros[centros[TIPO].isin(TIPOS_PRIMARIA)].copy()
    candidatos["x"], candidatos["y"] = a_numero(candidatos[X]), a_numero(candidatos[Y])
    candidatos = completar_coordenadas(candidatos, curadas)
    candidatos["via_inclusion"] = candidatos.apply(via_inclusion, axis=1)
    candidatos["motivo_exclusion"] = candidatos.apply(motivo_exclusion, axis=1)
    candidatos["discrepancia_entre_filas"] = candidatos[CLAVE].isin(discrepancias[CLAVE])
    incluidos = candidatos[candidatos["motivo_exclusion"] == ""].drop(columns="motivo_exclusion")
    excluidos = candidatos[candidatos["motivo_exclusion"] != ""]
    return {"incluidos": incluidos, "excluidos": excluidos, "discrepancias": discrepancias,
            "conteos": conteos(tabla, centros, candidatos, incluidos, discrepancias)}


def conteos(tabla, centros, candidatos, incluidos, discrepancias) -> dict:
    """Cadena de conteos que reconcilia filas, centros, tipo, dependencia, coordenadas y capital."""
    publicos = candidatos[candidatos["via_inclusion"] != ""]
    capital = incluidos[incluidos[MUNICIPIO] == MUNICIPIO_CAPITAL]
    return {
        "filas": len(tabla),
        "centros_unicos": len(centros),
        "centros_tipo_primaria": len(candidatos),
        "centros_tipo_primaria_por_tipo": candidatos[TIPO].value_counts().to_dict(),
        "dependencias_de_tipo_primaria": candidatos[DEPENDENCIA].value_counts().to_dict(),
        "tras_filtro_dependencia": len(publicos),
        "con_coordenadas_validas": len(incluidos),
        "incluidos_por_via": incluidos["via_inclusion"].value_counts().to_dict(),
        "codigos_via_patrimonial": sorted(incluidos.loc[
            incluidos["via_inclusion"] == "patrimonial_sermas", CLAVE].tolist()),
        "coordenadas_curadas_osm": int((incluidos["origen_coordenadas"] == "curado_osm").sum()),
        "en_madrid_capital": len(capital),
        "en_madrid_capital_por_tipo": capital[TIPO].value_counts().to_dict(),
        "centros_con_discrepancia_entre_filas": int(discrepancias[CLAVE].nunique()),
    }
