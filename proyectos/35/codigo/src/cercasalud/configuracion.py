"""Lectura de los supuestos del análisis (config/base.toml).

Los supuestos viven en la configuración y no en el código (CLAUDE.md, «Parámetros base»).
"""

import os
import tomllib
from pathlib import Path

CONFIG_BASE = Path(__file__).resolve().parents[2] / "config" / "base.toml"
VARIABLE_CONFIG = "CERCASALUD_CONFIG"  # otra configuración (escenarios de sensibilidad), sin tocar la base


def leer_config(ruta: Path | None = None) -> dict:
    """Devuelve la configuración como diccionario anidado: `ruta`, la de CERCASALUD_CONFIG o la base."""
    ruta = ruta or Path(os.environ.get(VARIABLE_CONFIG, CONFIG_BASE))
    with ruta.open("rb") as archivo:
        return tomllib.load(archivo)
