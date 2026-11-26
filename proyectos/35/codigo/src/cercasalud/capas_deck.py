"""Capas del mapa de minutos listas para deck.gl, como archivos JSON (etapa `capas_app`; SPEC P-27).

Por qué archivos y no tablas en memoria: pasar a pydeck los 56.003 polígonos de las celdas en cada
ejecución de la app enviaba al navegador 37 MB de JSON, y el conversor de deck.gl los recorría
enteros antes de dibujar (unos 25 s por vista, medido el 15/11/2026). Servidos como archivo, el
navegador los descarga una vez y deck.gl los lee sin conversión.

Cada fila lleva ya el color y el texto de la tarjeta flotante de **todas** las variables
(`c_<variable>`, `d_<variable>`): cambiar de variable en la app solo cambia qué campo se pinta.
Claves cortas para que el archivo pese menos: `p` contorno o camino, `l` lugar, `g` población.

Solo da formato a lo que prepara `capas_mapa.py`; no calcula resultados (R-UI-01).
"""

import json
from pathlib import Path

import pandas as pd

from . import vista_mapa

CALIDAD_RENTA = {"dato": "dato del INE", "cota_superior": "el INE da solo la cota superior (secreto estadístico)",
                 "cota_inferior": "el INE da solo la cota inferior (secreto estadístico)",
                 "media_comarca": "media de la comarca agraria (sin dato propio)"}
NO_EVALUABLE_PIE = "no evaluable (sin conexión con la red a pie)"
PALETA_CELDAS = {"quintil_renta": vista_mapa.ROJO_AZUL_5}  # el resto de variables de celdas: minutos
VARIABLES_MUNICIPIO = ("pct_sin_transporte", "pct_sin_pie")


def nombre_de_territorio(celdas: pd.DataFrame, territorios: pd.DataFrame) -> pd.Series:
    """Nombre del distrito (en Madrid capital) o del municipio de cada celda."""
    capital = celdas["cusec"].str.startswith("28079")
    clave = ("municipio:" + celdas["cusec"].str[:5]).where(~capital, "distrito:" + celdas["cusec"].str[5:7])
    nombres = pd.Series(territorios["nombre"].to_numpy(), index=territorios["tipo"] + ":" + territorios["codigo"])
    return clave.map(nombres).fillna("")


def detalle_minutos(celdas: pd.DataFrame, variable: str, ultimo_limite: float) -> list[str]:
    """«18 min», «más de 60 min» o «no evaluable …» de cada celda."""
    return [NO_EVALUABLE_PIE if clase == -1 else vista_mapa.texto_minutos(minutos, ultimo_limite)
            for minutos, clase in zip(celdas[variable], celdas[f"clase_{variable}"], strict=True)]


def detalle_renta(celdas: pd.DataFrame) -> list[str]:
    """«Renta: Q3 (dato del INE)» de cada celda."""
    return [f"Renta: Q{int(q)} ({CALIDAD_RENTA.get(c, c)})" if pd.notna(q) else "sin dato de renta"
            for q, c in zip(celdas["quintil_renta"], celdas["calidad_renta"], strict=True)]


def registros_celdas(celdas: pd.DataFrame, territorios: pd.DataFrame, catalogo: dict) -> list[dict]:
    """Una fila por pieza de celda: contorno, lugar, población y color y texto de cada variable."""
    columnas = {"p": [json.loads(t) for t in celdas["contorno"]],
                "l": (nombre_de_territorio(celdas, territorios) + " · sección " + celdas["cusec"]).tolist(),
                "g": [f"≈ {round(p)} personas (estimación)" for p in celdas["poblacion_total"]]}
    for variable, datos in catalogo.items():
        columnas[f"c_{variable}"] = vista_mapa.colores(celdas[f"clase_{variable}"], vista_mapa.AZUL_ROJO).tolist()
        columnas[f"d_{variable}"] = detalle_minutos(celdas, variable, datos["limites"][-1])
    columnas["c_quintil_renta"] = vista_mapa.colores(celdas["clase_quintil_renta"], vista_mapa.ROJO_AZUL_5).tolist()
    columnas["d_quintil_renta"] = detalle_renta(celdas)
    return pd.DataFrame(columnas).to_dict("records")


def registros_municipios(contornos: pd.DataFrame, territorios: pd.DataFrame) -> list[dict]:
    """Una fila por parte de municipio: contorno, nombre y color y texto del % sin opción."""
    fila = territorios[territorios["tipo"] == "municipio"].set_index("codigo").loc[contornos["cumun"]]
    columnas = {"p": [json.loads(t) for t in contornos["contorno"]], "l": fila["nombre"].tolist(),
                "g": [f"de {vista_mapa.personas(p)} habitantes" for p in fila["poblacion"]]}
    for variable in VARIABLES_MUNICIPIO:
        columnas[f"c_{variable}"] = vista_mapa.colores(fila[f"clase_{variable}"].reset_index(drop=True),
                                                       vista_mapa.AMARILLO_ROJO).tolist()
        columnas[f"d_{variable}"] = [f"{vista_mapa.porcentaje(p)} sin opción verificada" for p in fila[variable]]
    return pd.DataFrame(columnas).to_dict("records")


def registros_lineas(lineas: pd.DataFrame) -> dict[str, list[dict]]:
    """Un conjunto de caminos por tipo de línea (límites y vías)."""
    return {f"lineas_{tipo}": [{"p": json.loads(t)} for t in grupo["camino"]] for tipo, grupo in lineas.groupby("tipo")}


def escribir(carpeta: Path, capas: dict) -> dict[str, int]:
    """Escribe los JSON compactos de deck.gl y devuelve cuántas filas tiene cada uno."""
    carpeta.mkdir(parents=True, exist_ok=True)
    archivos = {"celdas": registros_celdas(capas["celdas"], capas["territorios"], capas["catalogo"]),
                "municipios": registros_municipios(capas["municipios"], capas["territorios"]),
                **registros_lineas(capas["lineas"])}
    for nombre, registros in archivos.items():
        (carpeta / f"{nombre}.json").write_text(json.dumps(registros, ensure_ascii=False, separators=(",", ":")),
                                                encoding="utf-8")
    return {nombre: len(registros) for nombre, registros in archivos.items()}
