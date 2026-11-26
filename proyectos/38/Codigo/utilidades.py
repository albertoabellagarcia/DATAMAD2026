"""Utilidades comunes de ForMadrid: rutas, lectura de ficheros CM y normalización de códigos."""
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
DATOS = RAIZ / "Datos"
RESULTADOS = RAIZ / "Resultados"
LIMPIOS = RESULTADOS / "datos_limpios"

COD_SIN_ASIGNAR = "999"          # «Sin municipio asignado» (código CM 9999)
ANIOS_INDICE = list(range(2021, 2026))  # último año completo: 2025
ANIOS_ATIPICOS = {2020: "COVID", 2021: "atípico (post-COVID; sectores centro de trabajo 2020 incompletos)"}


def leer_cm(nombre: str) -> pd.DataFrame:
    """Lee un CSV del portal CM (UTF-8-sig, ';') y devuelve solo filas de municipios.

    - Filtra Tipo territorio == 'Municipios' (descarta Comunidad y Zonas Estadísticas).
    - cod_mun = 3 primeros dígitos del código de 4 (coincide con CDMUNI / INE).
    - Valor '-' = suprimido -> NaN (nunca 0).
    """
    df = pd.read_csv(DATOS / nombre, sep=";", encoding="utf-8-sig", dtype=str)
    df = df[df["Tipo territorio"] == "Municipios"].copy()
    df["cod_mun"] = df["Código territorio"].str.zfill(4).str[:3]
    df["anio"] = df["Año"].astype(int)
    df["suprimido"] = df["Valor"].eq("-")
    df["valor"] = pd.to_numeric(df["Valor"].where(~df["suprimido"]), errors="raise")
    return df.drop(columns=["Año", "Tipo territorio", "Unidad", "Estado dato", "Valor"])


def leer_poblacion_ine() -> pd.DataFrame:
    """Población INE (tabla 68535): latin-1, tabulador, miles con punto. Quita el total provincial."""
    df = pd.read_csv(DATOS / "poblacion_municipios_ine_202125.csv", sep="\t", encoding="latin-1", dtype=str)
    df = df[df["Municipios"].notna() & df["Municipios"].str.strip().ne("")].copy()
    df["cod_mun"] = df["Municipios"].str.extract(r"^28(\d{3})", expand=False)
    df["municipio_ine"] = df["Municipios"].str.replace(r"^\d{5}\s*", "", regex=True)
    df["anio"] = df["Periodo"].astype(int)
    df["valor"] = pd.to_numeric(df["Total"].str.replace(".", "", regex=False), errors="raise")
    return df[["cod_mun", "municipio_ine", "anio", "Edad", "Sexo", "Nacionalidad", "valor"]]


def spearman(a: pd.Series, b: pd.Series) -> float:
    """Correlación de Spearman sin scipy: Pearson sobre rangos (empates con rango medio)."""
    m = pd.concat([a, b], axis=1).dropna()
    r = m.rank(method="average")
    return float(np.corrcoef(r.iloc[:, 0], r.iloc[:, 1])[0, 1])


def zscore(s: pd.Series) -> pd.Series:
    return (s - s.mean()) / s.std(ddof=0)
