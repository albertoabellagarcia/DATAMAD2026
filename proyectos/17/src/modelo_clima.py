"""Análogos mensuales de sequedad y tabla municipal del Plan Anual CAM."""
from pathlib import Path
import re
import unicodedata

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"
RESULTS = ROOT / "results"
SCENARIOS = {"Favorable": .20, "Central": .50, "Adverso": .80}


def name_key(name):
    clean = unicodedata.normalize("NFKD", name.strip().lower())
    clean = "".join(c for c in clean if not unicodedata.combining(c))
    clean = re.sub(r"^(.+?)\s*(?:\(|,\s*)(la|el|las|los)\)?$", r"\2 \1", clean)
    return re.sub("[^a-z0-9]", "", clean)


def official_counts():
    raw = ROOT / "data" / "raw"
    source = pd.read_csv(raw / "anexo_plan_2025_cam.csv")
    # Errata literal del anexo frente al nomenclátor municipal.
    source["key"] = source.nombre_original.replace({"FRESNEDILLA DE LA OLIVA": "Fresnedillas de la Oliva"}).map(name_key)
    catalogue = pd.read_csv(raw / "municipios.csv", sep=";", encoding="cp1252")
    catalogue["cod_ine"] = catalogue.municipio_codigo_ine.astype(str).str[:5]
    catalogue["key"] = catalogue.municipio_nombre.map(name_key)
    merged = source.merge(catalogue[["key", "cod_ine", "municipio_nombre"]], on="key", how="left", validate="one_to_one")
    if merged.loc[merged.cod_ine.isna(), "nombre_original"].tolist() != ["OTRA PROVINCIA"]:
        raise ValueError("Nombre del anexo sin identificar")
    amounts = ["rayo", "negligencia_accidente", "intencionado", "desconocida", "reproducido"]
    if not merged[amounts].sum(axis=1).eq(merged.total).all() or merged.total.sum() != 2987:
        raise ValueError("Totales municipales incompatibles con el anexo publicado")
    final = merged.dropna(subset="cod_ine").rename(columns={"municipio_nombre": "nombre"})
    final[["cod_ine", "nombre", *amounts, "total"]].to_csv(DATA / "incendios_municipales_cam.csv", index=False)


def weather_summaries():
    daily = pd.read_csv(DATA / "estaciones_diarias.csv", dtype={"estacion": str}, parse_dates=["fecha"])
    if daily.duplicated(["estacion", "fecha"]).any():
        raise ValueError("Estación y fecha duplicadas")
    daily["anio"] = daily.fecha.dt.year
    daily["mes"] = daily.fecha.dt.month
    daily["dias_mes"] = daily.fecha.dt.days_in_month
    complete_years = daily[daily.anio.between(2020, 2025)].copy()
    keys = ["estacion", "anio", "mes"]
    grouped = complete_years.groupby(keys)
    monthly = grouped.agg(
        dias_mes=("dias_mes", "first"), n_vpd=("vpd_max_kpa", "count"),
        vpd_kpa=("vpd_max_kpa", "mean"), tmax_c=("tmax_c", "mean"),
        n_tmax=("tmax_c","count"), humedad_pct=("humedad_pct", "mean"),
        n_hum=("humedad_pct","count"), lluvia_mm=("lluvia_mm","sum"), n_lluvia=("lluvia_mm","count")
    ).reset_index()
    monthly.loc[monthly.n_vpd < .8 * monthly.dias_mes, "vpd_kpa"] = np.nan
    monthly.loc[monthly.n_tmax < .8 * monthly.dias_mes, "tmax_c"] = np.nan
    monthly.loc[monthly.n_hum < .8 * monthly.dias_mes, "humedad_pct"] = np.nan
    monthly.loc[monthly.n_lluvia != monthly.dias_mes, "lluvia_mm"] = np.nan
    return monthly, complete_years


def seasonal_scenarios(municipalities, monthly, daily):
    rows = []
    for (station, month), block in monthly.dropna(subset=["vpd_kpa"]).groupby(["estacion", "mes"]):
        if len(block) < 3:
            continue
        ordered = block.sort_values(["vpd_kpa", "anio"]).reset_index(drop=True)
        for label, quantile in SCENARIOS.items():
            pos = int(np.floor(quantile * (len(ordered) - 1) + .5))
            record = ordered.iloc[pos]
            rows.append(dict(estacion=station, mes=month, escenario=label,
                             anio_analogo=int(record.anio), n_anios=len(block),
                             vpd_min_kpa=block.vpd_kpa.min(), vpd_max_kpa=block.vpd_kpa.max(),
                             **{key: record[key] for key in ["vpd_kpa", "tmax_c", "humedad_pct", "lluvia_mm"]}))
    pairs = municipalities[["cod_ine", "estacion"]]
    calendar = pd.MultiIndex.from_product([range(1,13), SCENARIOS], names=["mes","escenario"]).to_frame(index=False)
    out = pairs.merge(calendar, how="cross").merge(pd.DataFrame(rows), on=["estacion","mes","escenario"], how="left", validate="many_to_one")
    out["n_anios"] = out.n_anios.fillna(0).astype(int)
    out.to_csv(RESULTS / "escenarios.csv", index=False, float_format="%.5f")
    domain = daily.groupby(["estacion","mes"], as_index=False).agg(tmin_c=("tmin_c","min"),tmax_c=("tmax_c","max"),
                        hr_min=("humedad_pct","min"),hr_max=("humedad_pct","max"),lluvia_max_mm=("lluvia_mm","max"))
    pairs.merge(domain,on="estacion").to_csv(RESULTS / "dominio_simulador.csv",index=False,float_format="%.4f")


if __name__ == "__main__":
    official_counts()
