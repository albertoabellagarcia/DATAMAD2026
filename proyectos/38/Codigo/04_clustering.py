"""04 · Tipología de municipios (k-means) para 2025.

Población clasificada: municipios con los 3 componentes del índice (empleo >= 500 y >= 1.000
afiliados residentes). Los municipios pequeños (< 1.000 afiliados residentes) forman una clase
propia: con cifras tan bajas cualquier tipología sería inestable.

Variables (estandarizadas):
  A  déficit de empleo local          -ln(E / R corregido)                 [02_indice]
  B  presión de paro                  U / (U + R corregido)                [02_indice]
  C  desajuste sectorial (Duncan)                                          [02_indice]
  baja_cualif   % Peones + Oficiales de tercera y especialistas            [grupo de cotización, 1-ene-2025]
  alta_cualif   % Ingenieros y licenciados + Ingenieros técnicos           [grupo de cotización, 1-ene-2025]
                (denominador: grupos con categoría; sin «No procede» ni «No saben»)
  temporal      % contrato temporal sobre indefinido + temporal            [contrato, 1-ene-2025]
  var_paro      variación del paro registrado 31-mar-2021 -> 31-mar-2025  [paro]
k elegido entre 3 y 6 por silueta (semilla fija, reproducible).
"""
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler

from utilidades import LIMPIOS, RESULTADOS

ANIO = 2025
SEMILLA = 2026

ind = pd.read_csv(RESULTADOS / "indice_municipios.csv", dtype={"cod_mun": str})
gc = pd.read_csv(LIMPIOS / "residentes_grupo_cotizacion.csv", dtype={"cod_mun": str})
co = pd.read_csv(LIMPIOS / "residentes_contrato.csv", dtype={"cod_mun": str})
paro = pd.read_csv(LIMPIOS / "paro_registrado.csv", dtype={"cod_mun": str})

# --- perfil de cualificación (grupo de cotización)
g = gc[gc.anio == ANIO].set_index("cod_mun")
sin_cat = ["No procede", "No saben. No contestan"]
den = g.drop(columns=["anio"] + sin_cat).sum(axis=1)
perfil = pd.DataFrame({
    "baja_cualif": (g["Peones"] + g["Oficiales de tercera y especialistas"]) / den,
    "alta_cualif": (g["Ingenieros y licenciados"] + g["Ingenieros técnicos, peritos y ayudantes titulados"]) / den,
})
# --- temporalidad
c = co[co.anio == ANIO].set_index("cod_mun")
perfil["temporal"] = c["Contrato temporal"] / (c["Contrato indefinido"] + c["Contrato temporal"])
# --- variación del paro 2021-2025
p = paro.pivot_table(index="cod_mun", columns="anio_ref", values="paro_total")
perfil["var_paro"] = p[ANIO] / p[2021] - 1

df = ind[ind.anio == ANIO].set_index("cod_mun").join(perfil)
df = df.rename(columns={"comp_A_deficit_empleo": "A_deficit_empleo", "comp_B_presion_paro": "B_presion_paro",
                        "comp_C_desajuste_sectorial": "C_desajuste_sectorial"})
VARS = ["A_deficit_empleo", "B_presion_paro", "C_desajuste_sectorial",
        "baja_cualif", "alta_cualif", "temporal", "var_paro"]

clasificables = df[VARS].notna().all(axis=1) & (df["residentes"] >= 1000)
X = StandardScaler().fit_transform(df.loc[clasificables, VARS])

siluetas = {}
for k in range(3, 7):
    km = KMeans(n_clusters=k, n_init=50, random_state=SEMILLA).fit(X)
    siluetas[k] = silhouette_score(X, km.labels_)
k_opt = max(siluetas, key=siluetas.get)
km = KMeans(n_clusters=k_opt, n_init=50, random_state=SEMILLA).fit(X)
print("Silueta por k:", {k: round(v, 3) for k, v in siluetas.items()}, "-> k =", k_opt)

# Ordenar clústeres por índice medio (1 = mayor desajuste) para que la numeración sea estable
df.loc[clasificables, "cluster_raw"] = km.labels_
orden = df.loc[clasificables].groupby("cluster_raw")["indice"].mean().sort_values(ascending=False)
mapa_orden = {raw: i + 1 for i, raw in enumerate(orden.index)}
df["cluster"] = df["cluster_raw"].map(mapa_orden)
df.loc[~clasificables, "cluster"] = 0  # 0 = municipios pequeños, fuera de la tipología
df["cluster"] = df["cluster"].astype(int)

# Nombres asignados tras revisar las medianas de cada clase (23-nov). Si cambian los datos, revisar.
NOMBRES = {
    0: "Municipios pequeños (fuera de tipología)",
    1: "Paro alto y empleo poco cualificado",
    2: "Desajuste sectorial (el empleo local es de otros sectores)",
    3: "Residenciales cualificados (pocos empleos locales, poco paro)",
    4: "Grandes municipios metropolitanos de cualificación media",
    5: "Polos de empleo cualificado",
}
df["tipo"] = df["cluster"].map(NOMBRES)

resumen = df.groupby("cluster").agg(
    n=("municipio", "size"), paro=("paro", "sum"), residentes=("residentes", "sum"),
    indice=("indice", "mean"), ratio_empleo=("ratio_empleo", "median"),
    **{v: (v, "median") for v in VARS[1:]},
    ejemplos=("municipio", lambda s: ", ".join(s.head(0))),
)
# Ejemplos: los 4 municipios con más paro de cada clase
resumen["ejemplos"] = df.sort_values("paro", ascending=False).groupby("cluster")["municipio"].apply(
    lambda s: ", ".join(s.head(4)))
resumen["pct_paro_cm"] = resumen["paro"] / resumen["paro"].sum()
resumen.insert(0, "tipo", resumen.index.map(NOMBRES))

pd.set_option("display.width", 250)
print(resumen.round(3).to_string())

salida = df.reset_index()[["cod_mun", "municipio", "cluster", "tipo", "indice", "rango", "fiabilidad", "paro", "residentes",
                           "empleo", "ratio_empleo"] + VARS]
salida.to_csv(RESULTADOS / "tipologia_municipios.csv", index=False, float_format="%.4f")
resumen.reset_index().to_csv(RESULTADOS / "tipologia_resumen.csv", index=False, float_format="%.4f")
pd.Series(siluetas, name="silueta").rename_axis("k").to_csv(RESULTADOS / "tipologia_silueta.csv")
