"""01 · Carga y limpieza de los ficheros de ForMadrid.

Aplica las reglas de CLAUDE.md:
  1. Solo Tipo territorio == 'Municipios'.
  2. La categoría 'Total' no se suma con las demás; para totales municipales se usa la fila 'Total'.
  3. cod_mun = 3 dígitos (CM: 3 primeros de 4; INE: 3 últimos de 5). 999 se guarda aparte.
  4. Paro: Nacionalidad = Total y Sexo = Total, suma de los 5 sectores
     (el fichero no trae Nacionalidad=Total con Sector=Total; se valida contra Españoles+Extranjeros).
  5. Alineación: residencia Y (1-ene) ↔ centro de trabajo Y-1 (31-dic) ↔ paro Y (31-mar).
  6. '-' = suprimido (NaN), nunca 0.

Salidas en Resultados/datos_limpios/ y Resultados/validaciones_01.txt.
Los ficheros de Datos/ no se modifican.
"""
import pandas as pd

from utilidades import COD_SIN_ASIGNAR, LIMPIOS, RESULTADOS, leer_cm, leer_poblacion_ine

LIMPIOS.mkdir(parents=True, exist_ok=True)
log = []


def registrar(msg: str) -> None:
    print(msg)
    log.append(msg)


def comprobar(cond: bool, msg: str) -> None:
    registrar(("OK   " if cond else "FALLO ") + msg)
    if not cond:
        raise SystemExit(f"Anomalía de datos: {msg}. Parar y revisar con el equipo.")


# Agregación común a 4 grandes sectores (comparables entre empleo, residentes y paro).
# 'No consta' (afiliados) y 'Sin sector de actividad' (paro) no tienen sector: fuera de la distribución.
SECTOR4 = {
    "Agricultura y ganadería": "Agricultura",
    "Minería, industria y energía": "Industria",
    "Construcción": "Construcción",
    "Servicios de distribución y hostelería": "Servicios",
    "Servicios a empresas y financieros": "Servicios",
    "Otros servicios": "Servicios",
    "Inmobiliarias": "Servicios",
    "Agricultura": "Agricultura",
    "Industria": "Industria",
    "Servicios": "Servicios",
}

# ---------------------------------------------------------------- municipios (maestro)
pob = leer_poblacion_ine()
maestro = pob[["cod_mun", "municipio_ine"]].drop_duplicates().sort_values("cod_mun")
comprobar(len(maestro) == 179, f"INE: {len(maestro)} municipios (esperado 179)")

# ---------------------------------------------------------------- población 15-64 (INE)
GRUPOS_1564 = [f"De {a} a {a + 4} años" for a in range(15, 65, 5)]
p = pob[(pob["Sexo"] == "Total") & (pob["Nacionalidad"] == "Total")]
comprobar(set(GRUPOS_1564) <= set(p["Edad"]), "INE: existen los 10 grupos quinquenales 15-64")
p1564 = (p[p["Edad"].isin(GRUPOS_1564)].groupby(["cod_mun", "anio"])["valor"].sum()
         .rename("pob_15_64").reset_index())
ptot = p[p["Edad"] == "Todas las edades"].set_index(["cod_mun", "anio"])["valor"].rename("pob_total")
p1564 = p1564.join(ptot, on=["cod_mun", "anio"])
# Control: la suma de todos los grupos quinquenales = 'Todas las edades'
suma_grupos = p[p["Edad"] != "Todas las edades"].groupby(["cod_mun", "anio"])["valor"].sum()
comprobar((suma_grupos - ptot).abs().max() == 0, "INE: suma de grupos de edad = Todas las edades")
registrar(f"INE: pob. 15-64 CM 2021 = {p1564.query('anio==2021').pob_15_64.sum():,.0f}; "
          f"2025 = {p1564.query('anio==2025').pob_15_64.sum():,.0f}")
p1564.to_csv(LIMPIOS / "poblacion_15_64.csv", index=False)


def comprobar_codigos(df: pd.DataFrame, fichero: str, con_999: bool = True) -> None:
    cods = set(df["cod_mun"]) - {COD_SIN_ASIGNAR}
    comprobar(cods == set(maestro["cod_mun"]), f"{fichero}: 179 códigos coinciden con INE")
    if con_999:
        comprobar(COD_SIN_ASIGNAR in set(df["cod_mun"]), f"{fichero}: contiene 999 (sin municipio asignado)")


def total_y_sectores(df: pd.DataFrame, col_cat: str, fichero: str,
                     anio_redondeo: int | None = None) -> pd.DataFrame:
    """Devuelve por municipio-año: fila Total, suma de categorías, n suprimidos y 4 sectores.

    anio_redondeo: desde ese año los valores vienen redondeados a múltiplos de 5
    (control de confidencialidad del centro de trabajo). Tolerancia Total vs suma:
    n_categorías × 2,5 (decisión 23-nov, opción A).
    """
    tot = df[df[col_cat] == "Total"].set_index(["cod_mun", "anio"])["valor"].rename("total")
    cats = df[df[col_cat] != "Total"]
    suma = cats.groupby(["cod_mun", "anio"])["valor"].sum(min_count=1).rename("suma_categorias")
    nsup = cats.groupby(["cod_mun", "anio"])["suprimido"].sum().rename("n_suprimidos")
    s4 = (cats.assign(sector=cats[col_cat].map(SECTOR4)).dropna(subset=["sector"])
          .groupby(["cod_mun", "anio", "sector"])["valor"].sum(min_count=1).unstack("sector"))
    # Si algún componente de un sector está suprimido, el sector no es fiable -> NaN
    sup4 = (cats.assign(sector=cats[col_cat].map(SECTOR4)).dropna(subset=["sector"])
            .groupby(["cod_mun", "anio", "sector"])["suprimido"].any().unstack("sector"))
    s4 = s4.mask(sup4.reindex_like(s4).fillna(False).astype(bool))
    s4.columns = [f"sec_{c.lower().replace('ó', 'o')}" for c in s4.columns]
    out = pd.concat([tot, suma, nsup, s4], axis=1).reset_index()
    out["sectores_completos"] = out["n_suprimidos"].eq(0)
    # Control regla 2: donde no hay suprimidos, suma de categorías = Total
    ok = out[out["sectores_completos"] & out["total"].notna() & out["suma_categorias"].notna()]
    dif = (ok["total"] - ok["suma_categorias"]).abs()
    if anio_redondeo is None:
        comprobar(dif.max() == 0, f"{fichero}: Total = suma de categorías sin suprimidos (máx. dif {dif.max()})")
    else:
        exacto = ok["anio"] < anio_redondeo
        tol = cats[col_cat].nunique() * 2.5
        # Antes de anio_redondeo casi todos los municipios tienen algún '-' (al menos 'No consta'),
        # así que puede no haber filas comparables: la comprobación es vacía, no un fallo.
        comprobar(dif[exacto].fillna(0).max() == 0 if exacto.any() else True,
                  f"{fichero}: Total = suma de categorías (años < {anio_redondeo}; "
                  f"{int(exacto.sum())} filas comparables sin '-')")
        comprobar(dif[~exacto].max() <= tol,
                  f"{fichero}: |Total - suma| <= {tol} por redondeo a 5 (años >= {anio_redondeo}; "
                  f"máx. {dif[~exacto].max()}, {int((dif[~exacto] > 0).sum())} filas con diferencia)")
        mult5 = (cats.loc[cats.anio >= anio_redondeo, "valor"].dropna() % 5 == 0).mean()
        registrar(f"{fichero}: valores múltiplos de 5 desde {anio_redondeo}: {mult5:.1%}")
        out["redondeado_5"] = out["anio"] >= anio_redondeo
    return out


# ---------------------------------------------------------------- empleo por centro de trabajo (31-dic)
ct = leer_cm("afiliados_centro_trabajo_rama.csv")
comprobar_codigos(ct, "centro_trabajo")
emp = total_y_sectores(ct, "Rama de actividad", "centro_trabajo", anio_redondeo=2021)
# El código 999 no tiene fila Total en ningún año: su total = suma de ramas (sin '-').
es999 = emp["cod_mun"].eq(COD_SIN_ASIGNAR)
comprobar(emp.loc[es999 & emp.anio.between(2020, 2024), "n_suprimidos"].eq(0).all(),
          "centro_trabajo 999: sin fila Total, ramas sin '-' -> total = suma de ramas")
emp["total_desde_suma"] = es999 & emp["total"].isna()
emp.loc[emp["total_desde_suma"], "total"] = emp.loc[emp["total_desde_suma"], "suma_categorias"]
comprobar(emp.loc[emp.anio.between(2020, 2024), "total"].notna().all(),
          "centro_trabajo: total disponible 2020-2024 para 179 municipios + 999")
sup = emp[emp.anio.between(2020, 2024)].groupby("anio")["n_suprimidos"].sum()
registrar(f"centro_trabajo: valores '-' por año (2020-2024): {sup.to_dict()}")
emp["anio_indice"] = emp["anio"] + 1  # 31-dic Y-1 -> índice del año Y
emp = emp.rename(columns={"anio": "anio_ref"})
emp.to_csv(LIMPIOS / "empleo_centro_trabajo.csv", index=False)

# ---------------------------------------------------------------- afiliados por residencia (1-ene)
rr = leer_cm("afiliados_residencia_rama.csv")
comprobar_codigos(rr, "residencia_rama")
res = total_y_sectores(rr, "Rama de actividad", "residencia_rama")
res["anio_indice"] = res["anio"]
res = res.rename(columns={"anio": "anio_ref"})
res.to_csv(LIMPIOS / "residentes_afiliados.csv", index=False)

# ---------------------------------------------------------------- paro registrado (31-mar)
pr = leer_cm("paro_registrado_municipios.csv")
comprobar_codigos(pr, "paro", con_999=False)
comprobar(not pr["suprimido"].any(), "paro: sin valores '-'")
pt = pr[(pr["Nacionalidad"] == "Total") & (pr["Sexo"] == "Total")]
comprobar(pt.loc[pt.anio <= 2025, "Sector"].ne("Total").all(),
          "paro: Nacionalidad=Total no trae Sector=Total (se suman los 5 sectores)")
paro = pt.pivot_table(index=["cod_mun", "anio"], columns="Sector", values="valor", aggfunc="sum")
paro.columns = [f"paro_{c.lower().replace(' ', '_').replace('ó', 'o')}" for c in paro.columns]
paro["paro_total"] = paro.sum(axis=1, min_count=5)
# Validación cruzada: Españoles + Extranjeros con Sector=Total
ee = (pr[(pr["Nacionalidad"] != "Total") & (pr["Sexo"] == "Total") & (pr["Sector"] == "Total")]
      .groupby(["cod_mun", "anio"])["valor"].sum())
chk = paro["paro_total"].dropna().to_frame().join(ee.rename("esp_mas_ext"), how="inner")
dif = (chk["paro_total"] - chk["esp_mas_ext"]).abs()
anios_dif = sorted(set(dif[dif > 0].index.get_level_values("anio")))
registrar(f"paro: años con diferencia Total vs Españoles+Extranjeros (fuera del análisis si < 2021): {anios_dif}")
en_ventana = dif.index.get_level_values("anio") >= 2014
comprobar(dif[en_ventana].max() == 0,
          f"paro: suma 5 sectores = Españoles+Extranjeros (Sector=Total), 2014+ ({int(en_ventana.sum())} filas)")
paro = paro.reset_index()
paro["anio_indice"] = paro["anio"]
paro = paro.rename(columns={"anio": "anio_ref"})
paro = paro[paro.anio_ref <= 2025]  # 2026 sin desglose sectorial: último año completo 2025
paro.to_csv(LIMPIOS / "paro_registrado.csv", index=False)

# ---------------------------------------------------------------- perfil de afiliados residentes
gc = leer_cm("afiliados_residencia_grupo_cotizacion.csv")
comprobar_codigos(gc, "grupo_cotizacion")
gct = gc[gc["Grupo de cotización"] != "Total"].pivot_table(
    index=["cod_mun", "anio"], columns="Grupo de cotización", values="valor", aggfunc="sum")
gtot = gc[gc["Grupo de cotización"] == "Total"].set_index(["cod_mun", "anio"])["valor"]
comprobar((gct.sum(axis=1) - gtot).abs().max() == 0, "grupo_cotizacion: Total = suma de grupos")
gct.reset_index().to_csv(LIMPIOS / "residentes_grupo_cotizacion.csv", index=False)

co = leer_cm("afiliados_residencia_contrato.csv")
comprobar_codigos(co, "contrato")
cot = co[co["Tipo de contrato"] != "Total"].pivot_table(
    index=["cod_mun", "anio"], columns="Tipo de contrato", values="valor", aggfunc="sum")
ctot = co[co["Tipo de contrato"] == "Total"].set_index(["cod_mun", "anio"])["valor"]
dif = (cot.fillna(0).sum(axis=1) - ctot).abs()
registrar(f"contrato: años sin fila 'Contrato temporal': "
          f"{sorted(set(co.anio) - set(co.loc[co['Tipo de contrato'] == 'Contrato temporal', 'anio']))}")
comprobar(dif[dif.index.get_level_values("anio") >= 2016].max() == 0,
          "contrato: Total = suma de tipos (2016+)")
cot.reset_index().to_csv(LIMPIOS / "residentes_contrato.csv", index=False)

# ---------------------------------------------------------------- % sin municipio asignado (999) por año
def pct_999(df: pd.DataFrame, nombre: str) -> pd.DataFrame:
    t = df.dropna(subset=["total"]).groupby("anio_ref").apply(
        lambda g: pd.Series({"total_cm": g["total"].sum(),
                             "sin_asignar": g.loc[g.cod_mun == COD_SIN_ASIGNAR, "total"].sum()}),
        include_groups=False)
    t["pct_sin_asignar"] = t["sin_asignar"] / t["total_cm"]
    t["fichero"] = nombre
    return t.reset_index()


cob = pd.concat([pct_999(res, "residencia"), pct_999(emp, "centro_trabajo")])
cob.to_csv(RESULTADOS / "cobertura_sin_asignar.csv", index=False)
for f, g in cob.groupby("fichero"):
    g = g[g.anio_ref >= 2014]
    registrar(f"% 999 {f}: " + ", ".join(f"{a}: {v:.1%}" for a, v in zip(g.anio_ref, g.pct_sin_asignar)))

# ---------------------------------------------------------------- maestro con nombres CM
nombres = res[["cod_mun"]].drop_duplicates().merge(
    rr[["cod_mun", "Territorio"]].drop_duplicates("cod_mun"), on="cod_mun")
maestro = maestro.merge(nombres.rename(columns={"Territorio": "municipio"}), on="cod_mun", how="left")
maestro.to_csv(LIMPIOS / "municipios.csv", index=False)

(RESULTADOS / "validaciones_01.txt").write_text("\n".join(log), encoding="utf-8")
print("\nListo: tablas en", LIMPIOS)
