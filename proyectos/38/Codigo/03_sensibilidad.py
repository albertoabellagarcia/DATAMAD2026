"""03 · Sensibilidad del índice al denominador (riesgo del 999 en afiliados por residencia).

Base:        denominador = afiliados por residencia corregidos por el % sin asignar (R_corr).
Alternativa: denominador = población INE de 15 a 64 años (1-ene; solo 2021 y 2025).
             (El INE publica grupos quinquenales: 15-64 en lugar de 16-64; decisión 23-nov.)

Se comparan los rankings con Spearman (todos los municipios y solo fiabilidad 'alta')
y el solapamiento del top 20. También se cuantifica el efecto de la corrección proporcional
sobre el cociente agregado empleo/residentes de la Comunidad.
"""
import importlib

import pandas as pd

from utilidades import LIMPIOS, RESULTADOS, spearman

ind_mod = importlib.import_module("02_indice")

base = ind_mod.construir_base()
pob = pd.read_csv(LIMPIOS / "poblacion_15_64.csv", dtype={"cod_mun": str})
base = base.merge(pob[["cod_mun", "anio", "pob_15_64"]], on=["cod_mun", "anio"], how="left")

filas = []
for anio in (2021, 2025):
    b = base[base.anio == anio]
    assert b["pob_15_64"].notna().all() and len(b) == 179
    i_base = ind_mod.calcular_indice(b, "residentes_corr", "afiliados_residencia_corr").set_index("cod_mun")
    i_alt = ind_mod.calcular_indice(b, "pob_15_64", "poblacion_15_64").set_index("cod_mun")
    alta = i_base.index[i_base["fiabilidad"] == "alta"]

    def top_n(serie, n=20):
        return set(serie.sort_values(ascending=False).head(n).index)

    for nombre, col in [("indice", "indice"), ("A_deficit_empleo", "comp_A_deficit_empleo"),
                        ("B_presion_paro", "comp_B_presion_paro")]:
        filas.append({
            "anio": anio, "medida": nombre,
            "spearman_todos": spearman(i_base[col], i_alt[col]),
            "spearman_fiabilidad_alta": spearman(i_base.loc[alta, col], i_alt.loc[alta, col]),
            "top20_coincidentes_todos": len(top_n(i_base[col]) & top_n(i_alt[col])),
            "top20_coincidentes_alta": len(top_n(i_base.loc[alta, col]) & top_n(i_alt.loc[alta, col])),
            "n_todos": len(i_base), "n_alta": len(alta),
        })

sens = pd.DataFrame(filas)
sens.to_csv(RESULTADOS / "sensibilidad.csv", index=False, float_format="%.3f")
print(sens.round(3).to_string(index=False))

# Efecto de la corrección proporcional en el agregado de la Comunidad (179 municipios)
cob = pd.read_csv(RESULTADOS / "cobertura_sin_asignar.csv")
s999 = cob[cob.fichero == "residencia"].set_index("anio_ref")["pct_sin_asignar"]
agg = base.groupby("anio")[["empleo", "residentes", "pob_15_64"]].sum(min_count=1)
agg["pct_999_residencia"] = s999.reindex(agg.index)
agg["ratio_sin_corregir"] = agg["empleo"] / agg["residentes"]
agg["ratio_corregido"] = agg["empleo"] / (agg["residentes"] / (1 - agg["pct_999_residencia"]))
agg["ratio_empleo_pob1564"] = agg["empleo"] / agg["pob_15_64"]
agg = agg.reset_index()
agg.to_csv(RESULTADOS / "correccion_999_agregado.csv", index=False, float_format="%.4f")
print("\nEfecto de la corrección del 999 en el agregado CM:")
print(agg.round(3).to_string(index=False))
