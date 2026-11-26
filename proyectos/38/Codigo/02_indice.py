"""02 · Índice de desajuste territorial del mercado laboral (179 municipios, 2021-2025).

Para cada año Y (alineación de CLAUDE.md):
  E = afiliados por centro de trabajo, fila Total, 31-dic de Y-1      (afiliados_centro_trabajo_rama)
  R = afiliados por residencia, fila Total, 1-ene de Y                (afiliados_residencia_rama)
  U = paro registrado, Nacionalidad=Sexo=Total, suma 5 sectores, 31-mar de Y (paro_registrado_municipios)

Corrección proporcional del 999: R_corr = R / (1 - s_Y), con s_Y = % de afiliados por residencia
sin municipio asignado en Y (supone que los no asignados se reparten como los asignados).
Dentro de un año es un factor común: no cambia rangos, sí niveles y tendencia.

Componentes (mayor valor = más desajuste):
  A. Déficit de empleo local   = -ln(E / R_corr)
  B. Presión de paro           = U / (U + R_corr)
  C. Desajuste sectorial       = índice de disimilitud de Duncan entre la distribución sectorial
                                 del paro y la del empleo local (4 sectores: Agricultura, Industria,
                                 Construcción, Servicios). Sin 'Sin sector' (paro) ni 'No consta' (empleo).
     C solo se calcula si E >= 500 y los sectores del empleo están completos (opción A, 23-nov):
     - 2021 (empleo 31-dic-2020) tiene '-' en ramas -> C no disponible ese año.
     - 2022-2025: ramas redondeadas a 5 -> en municipios < 500 empleos C es poco fiable.
Índice = media de los z-scores disponibles (cada componente estandarizado entre los 179 municipios
del año). Es un índice RELATIVO (posición entre municipios), no una cifra absoluta.
"""
import numpy as np
import pandas as pd

from utilidades import ANIOS_ATIPICOS, ANIOS_INDICE, COD_SIN_ASIGNAR, LIMPIOS, RESULTADOS, zscore

UMBRAL_EMPLEO_SECTORIAL = 500
SECTORES = ["agricultura", "industria", "construccion", "servicios"]

mun = pd.read_csv(LIMPIOS / "municipios.csv", dtype={"cod_mun": str})
emp = pd.read_csv(LIMPIOS / "empleo_centro_trabajo.csv", dtype={"cod_mun": str})
res = pd.read_csv(LIMPIOS / "residentes_afiliados.csv", dtype={"cod_mun": str})
paro = pd.read_csv(LIMPIOS / "paro_registrado.csv", dtype={"cod_mun": str})
cob = pd.read_csv(RESULTADOS / "cobertura_sin_asignar.csv")

s999 = cob[cob.fichero == "residencia"].set_index("anio_ref")["pct_sin_asignar"]


def construir_base() -> pd.DataFrame:
    """Une E, R, U por municipio y año del índice (sin el 999)."""
    e = emp[emp.anio_indice.isin(ANIOS_INDICE)].rename(columns={"total": "empleo"})
    e = e.rename(columns={f"sec_{s}": f"emp_{s}" for s in SECTORES})
    r = res[res.anio_indice.isin(ANIOS_INDICE)].rename(columns={"total": "residentes"})
    u = paro[paro.anio_indice.isin(ANIOS_INDICE)].rename(columns={"paro_total": "paro"})
    b = (e[["cod_mun", "anio_indice", "empleo", "sectores_completos"] + [f"emp_{s}" for s in SECTORES]]
         .merge(r[["cod_mun", "anio_indice", "residentes"]], on=["cod_mun", "anio_indice"], how="inner")
         .merge(u[["cod_mun", "anio_indice", "paro"] + [f"paro_{s}" for s in SECTORES]],
                on=["cod_mun", "anio_indice"], how="inner"))
    b = b[b.cod_mun != COD_SIN_ASIGNAR].rename(columns={"anio_indice": "anio"})
    assert b.groupby("anio").size().eq(179).all(), "Faltan municipios en algún año"
    return b


def duncan(df: pd.DataFrame, pref_a: str, pref_b: str) -> pd.Series:
    a = df[[f"{pref_a}_{s}" for s in SECTORES]].to_numpy(float)
    b = df[[f"{pref_b}_{s}" for s in SECTORES]].to_numpy(float)
    with np.errstate(invalid="ignore", divide="ignore"):
        pa = a / a.sum(axis=1, keepdims=True)
        pb = b / b.sum(axis=1, keepdims=True)
    return pd.Series(0.5 * np.abs(pa - pb).sum(axis=1), index=df.index)


def calcular_indice(b: pd.DataFrame, denom_col: str = "residentes_corr", etiqueta: str = "base") -> pd.DataFrame:
    """Calcula componentes e índice. denom_col permite cambiar el denominador (sensibilidad)."""
    b = b.copy()
    if denom_col == "residentes_corr":
        b["s999"] = b["anio"].map(s999)
        b["residentes_corr"] = b["residentes"] / (1 - b["s999"])
        b["ratio_empleo"] = b["empleo"] / b["residentes_corr"]
        b["comp_A_deficit_empleo"] = -np.log(b["ratio_empleo"])
        b["comp_B_presion_paro"] = b["paro"] / (b["paro"] + b["residentes_corr"])
    else:  # denominador poblacional (p. ej. pob_15_64)
        b["ratio_empleo"] = b["empleo"] / b[denom_col]
        b["comp_A_deficit_empleo"] = -np.log(b["ratio_empleo"])
        b["comp_B_presion_paro"] = b["paro"] / b[denom_col]

    valido_c = (b["sectores_completos"] & (b["empleo"] >= UMBRAL_EMPLEO_SECTORIAL) & (b["anio"] >= 2022))
    b["comp_C_desajuste_sectorial"] = duncan(b, "paro", "emp").where(valido_c)

    comps = ["comp_A_deficit_empleo", "comp_B_presion_paro", "comp_C_desajuste_sectorial"]
    for c in comps:
        b["z_" + c[5:]] = b.groupby("anio")[c].transform(zscore)
    zcols = ["z_" + c[5:] for c in comps]
    b["n_componentes"] = b[zcols].notna().sum(axis=1)
    b["indice"] = b[zcols].mean(axis=1)
    b["rango"] = b.groupby("anio")["indice"].rank(ascending=False, method="min").astype(int)
    b["percentil"] = b.groupby("anio")["indice"].rank(pct=True).round(3)
    b["fiabilidad"] = np.select(
        [b["residentes"] < 1000, b["empleo"] < UMBRAL_EMPLEO_SECTORIAL],
        ["baja (municipio < 1.000 afiliados residentes)", "media (sin componente sectorial: < 500 empleos)"],
        default="alta")
    b["nota_anio"] = b["anio"].map(ANIOS_ATIPICOS).fillna("")
    b["denominador"] = etiqueta
    return b


if __name__ == "__main__":
    base = construir_base()
    ind = calcular_indice(base)
    ind = mun.merge(ind, on="cod_mun", how="right")
    cols = ["cod_mun", "municipio", "anio", "empleo", "residentes", "s999", "residentes_corr", "paro",
            "ratio_empleo", "comp_A_deficit_empleo", "comp_B_presion_paro", "comp_C_desajuste_sectorial",
            "z_A_deficit_empleo", "z_B_presion_paro", "z_C_desajuste_sectorial",
            "n_componentes", "indice", "rango", "percentil", "fiabilidad", "nota_anio"]
    ind = ind[cols].sort_values(["anio", "rango"])
    ind.to_csv(RESULTADOS / "indice_municipios.csv", index=False, float_format="%.4f")

    print("Componentes disponibles por año:\n", ind.groupby("anio")["n_componentes"].value_counts().unstack())
    print("\nCorrelación entre componentes (2025, Spearman vía rangos):")
    print(ind[ind.anio == 2025][["comp_A_deficit_empleo", "comp_B_presion_paro",
                                 "comp_C_desajuste_sectorial"]].rank().corr().round(2))
    print("\nTop 15 desajuste 2025:")
    print(ind[ind.anio == 2025].head(15)[["municipio", "empleo", "residentes", "paro", "ratio_empleo",
                                           "comp_B_presion_paro", "comp_C_desajuste_sectorial",
                                           "indice", "fiabilidad"]].to_string(index=False))
    print("\nÚltimos 5 (menor desajuste) 2025:")
    print(ind[ind.anio == 2025].tail(5)[["municipio", "ratio_empleo", "indice"]].to_string(index=False))
