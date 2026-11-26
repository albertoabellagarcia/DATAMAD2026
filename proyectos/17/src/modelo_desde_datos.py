"""Ejecutar desde la raíz: python -m src.modelo_desde_datos."""
import pandas as pd

from .modelo_clima import DATA, RESULTS, ROOT, official_counts, seasonal_scenarios, weather_summaries
from .modelo_mensual import run


def main():
    RESULTS.mkdir(exist_ok=True)
    (ROOT / "models").mkdir(exist_ok=True)
    municipalities = pd.read_csv(DATA / "municipios.csv",dtype={"cod_ine":str,"estacion":str})
    monthly, daily = weather_summaries()
    seasonal_scenarios(municipalities, monthly, daily)
    run(municipalities, monthly)


if __name__ == "__main__":
    main()
