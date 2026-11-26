"""05 · Tendencias 2021-2025.

- Agregado de la Comunidad (179 municipios): empleo, residentes (brutos y corregidos), paro.
- Por municipio: cambio del índice y del ranking 2022 -> 2025 (mismos 3 componentes; 2021 no tiene
  componente sectorial, por eso la comparación homogénea empieza en 2022) y variación del paro 2021 -> 2025.
- Figura: el artefacto del 999 (cociente empleo/residentes sin corregir vs corregido).
Años marcados: 2021 atípico (post-COVID; empleo de 31-dic-2020).
"""
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from utilidades import RESULTADOS

FIG = RESULTADOS / "figuras"
FIG.mkdir(exist_ok=True)

# Paleta (referencia dataviz): ink y series
INK, INK2, MUTED, GRID, BASE, SURF = "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7", "#fcfcfb"
S1, S2 = "#2a78d6", "#eb6834"

ind = pd.read_csv(RESULTADOS / "indice_municipios.csv", dtype={"cod_mun": str})
tip = pd.read_csv(RESULTADOS / "tipologia_municipios.csv", dtype={"cod_mun": str})
agg = pd.read_csv(RESULTADOS / "correccion_999_agregado.csv")

# ---------------------------------------------------------------- agregado CM
cm = ind.groupby("anio").agg(empleo=("empleo", "sum"), residentes=("residentes", "sum"),
                             residentes_corr=("residentes_corr", "sum"), paro=("paro", "sum")).reset_index()
cm["ratio_sin_corregir"] = cm["empleo"] / cm["residentes"]
cm["ratio_corregido"] = cm["empleo"] / cm["residentes_corr"]
cm["pct_999"] = agg.set_index("anio").loc[cm["anio"], "pct_999_residencia"].to_numpy()
cm["nota"] = cm["anio"].map({2021: "atípico (post-COVID)"}).fillna("")
cm.to_csv(RESULTADOS / "tendencias_cm.csv", index=False, float_format="%.4f")
print(cm.round(3).to_string(index=False))

# ---------------------------------------------------------------- por municipio
w = ind.pivot_table(index="cod_mun", columns="anio", values=["indice", "rango", "paro", "ratio_empleo",
                                                             "comp_B_presion_paro"])
t = pd.DataFrame({
    "indice_2022": w[("indice", 2022)], "indice_2025": w[("indice", 2025)],
    "rango_2022": w[("rango", 2022)], "rango_2025": w[("rango", 2025)],
    "paro_2021": w[("paro", 2021)], "paro_2025": w[("paro", 2025)],
    "presion_paro_2021": w[("comp_B_presion_paro", 2021)], "presion_paro_2025": w[("comp_B_presion_paro", 2025)],
})
t["cambio_indice_22_25"] = t["indice_2025"] - t["indice_2022"]
t["cambio_rango_22_25"] = t["rango_2022"] - t["rango_2025"]  # positivo = sube en desajuste
t["var_paro_21_25"] = t["paro_2025"] / t["paro_2021"] - 1
t = tip[["cod_mun", "municipio", "cluster", "tipo", "fiabilidad"]].merge(t.reset_index(), on="cod_mun")
t.to_csv(RESULTADOS / "tendencias_municipios.csv", index=False, float_format="%.4f")

alta = t[t.fiabilidad == "alta"]
print("\nEmpeoran más (fiabilidad alta, cambio de índice 2022->2025):")
print(alta.nlargest(8, "cambio_indice_22_25")[["municipio", "tipo", "indice_2022", "indice_2025",
                                                "var_paro_21_25"]].round(3).to_string(index=False))
print("\nMejoran más:")
print(alta.nsmallest(5, "cambio_indice_22_25")[["municipio", "indice_2022", "indice_2025"]].round(3).to_string(index=False))
por_tipo = t.groupby(["cluster", "tipo"])[["paro_2021", "paro_2025"]].sum()
por_tipo["var_paro"] = por_tipo["paro_2025"] / por_tipo["paro_2021"] - 1
print("\nParo por tipo 2021->2025:\n", por_tipo.round(3).to_string())
por_tipo.reset_index().to_csv(RESULTADOS / "tendencias_por_tipo.csv", index=False, float_format="%.4f")

# ---------------------------------------------------------------- figura: artefacto del 999
fig, ax = plt.subplots(figsize=(7.5, 4.2), dpi=200)
fig.patch.set_facecolor(SURF); ax.set_facecolor(SURF)
for col, color, etiqueta in [("ratio_sin_corregir", S2, "Sin corregir"), ("ratio_corregido", S1, "Corregido por el 999")]:
    ax.plot(cm["anio"], cm[col], color=color, lw=2, marker="o", ms=6, mec=SURF, mew=2, label=etiqueta)
    ax.annotate(f"{etiqueta}  {cm[col].iloc[-1]:.2f}".replace(".", ","), (cm["anio"].iloc[-1], cm[col].iloc[-1]),
                xytext=(8, 0), textcoords="offset points", va="center", color=INK, fontsize=9)
    ax.annotate(f"{cm[col].iloc[0]:.2f}".replace(".", ","), (cm["anio"].iloc[0], cm[col].iloc[0]),
                xytext=(-8, 0), textcoords="offset points", va="center", ha="right", color=INK2, fontsize=9)
ax.set_xticks(cm["anio"]); ax.set_xlim(2020.5, 2026.6); ax.set_ylim(0.9, 1.25)
ax.set_ylabel("Empleos por afiliado residente", color=INK2, fontsize=9)
ax.grid(axis="y", color=GRID, lw=0.6); ax.set_axisbelow(True)
for s in ("top", "right", "left"):
    ax.spines[s].set_visible(False)
ax.spines["bottom"].set_color(BASE)
ax.tick_params(colors=MUTED, labelsize=9, length=0)
ax.legend(frameon=False, loc="upper left", fontsize=9, labelcolor=INK)
ax.set_title("El aumento del cociente empleo/residentes es un artefacto del dato",
             loc="left", fontsize=11, color=INK, fontweight="bold")
ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:.2f}".replace(".", ",")))
fig.text(0.01, 0.015, "Afiliados por residencia sin municipio asignado: 14,1 % (2021) → 16,7 % (2025).\n"
         "Fuente: Comunidad de Madrid, afiliados por residencia y por centro de trabajo (índice del año Y: "
         "residencia 1-ene-Y, centro de trabajo 31-dic-(Y-1)).", fontsize=7, color=MUTED)
fig.tight_layout(rect=(0, 0.07, 1, 1))
fig.savefig(FIG / "artefacto_999.png", facecolor=SURF)
print("\nFigura:", FIG / "artefacto_999.png")
