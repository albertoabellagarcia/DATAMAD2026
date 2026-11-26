"""Renta por sección (INE, Atlas de Distribución de Renta de los Hogares, ADRH 2024) para
estratificar A y C (SPEC D-16: edad y renta por sección, sin índice compuesto).

**Fuente:** capa `ADRH_secciones_2024` del servicio ArcGIS del INE, descargada el 13/11/2026 en
`datos/crudos/ine_adrh_2024/adrh_madrid_2024_completo.json`, con su manifiesto `.source.json`.
No está en la versión de datos de `fetch` (añadirla crearía otra versión y obligaría a
recalcular el transporte); por eso se lee de `crudos/` y se comprueba su SHA-256 contra el
manifiesto antes de usarla. Licencia: CC BY 4.0, licencia general del INE (LICENCIAS.md).

**Indicador:** `dato1`, renta neta media por persona, en euros. El campo `anyo` vale 2024; el
año de referencia de los ingresos no figura en la capa (sin verificar).

**Armonización con las secciones de 2025 (comprobada el 14/11/2026):** las 4.518 secciones del
ADRH coinciden código a código con las de la demanda, en los dos sentidos, y su superficie
(`SHAPE__Area`, EPSG:25830) es la misma que la del polígono del INE de 2025 en las 4.518
(cociente 1,0000). Se asigna por código.

**Calidad del dato** (`nota1` de la capa):
- `dato`: valor publicado;
- `cota_superior` / `cota_inferior`: secreto estadístico; el INE da la cota, no el valor (124 y 1
  secciones). Caen igualmente en el quintil más alto o más bajo;
- `media_comarca`: renta media de la comarca agraria (6 secciones de municipios pequeños).

**Quintiles:** se ordenan las secciones por renta y se cortan por población acumulada de la
Comunidad, de modo que cada quintil reúne en torno al 20 % de la población (Q1 = renta más
baja). Como la unidad de corte es la sección, los quintiles no son exactamente del 20 %.
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd

from .manifiestos import sha256_archivo

ARCHIVO_ADRH = ("ine_adrh_2024", "adrh_madrid_2024_completo.json")
INDICADOR = "dato1"  # renta neta media por persona (euros)
NOTAS = {"por encima de la cota superior": "cota_superior", "por debajo de la cota inferior": "cota_inferior",
         "comarca agraria": "media_comarca"}


def ruta_adrh(raiz: Path) -> Path:
    """Ruta del ADRH en `crudos/`."""
    return raiz / "crudos" / ARCHIVO_ADRH[0] / ARCHIVO_ADRH[1]


def comprobar_manifiesto(ruta: Path) -> str:
    """SHA-256 del archivo; falla si no coincide con el de su manifiesto `.source.json`."""
    esperado = json.loads(ruta.with_name(ruta.name + ".source.json").read_text(encoding="utf-8"))["sha256"]
    real = sha256_archivo(ruta)
    if real != esperado:
        raise ValueError(f"El SHA-256 de {ruta.name} no coincide con su manifiesto.")
    return real


def calidad(nota) -> str:
    """Clase de calidad del dato a partir de la nota del INE (vacía o NaN = dato publicado)."""
    if not isinstance(nota, str) or not nota.strip():
        return "dato"
    return next((clase for texto, clase in NOTAS.items() if texto in nota), "otra_nota")


def leer_adrh(ruta: Path) -> pd.DataFrame:
    """Renta neta media por persona por sección, con la calidad del dato."""
    rasgos = json.loads(ruta.read_text(encoding="utf-8"))["features"]
    tabla = pd.DataFrame(rasgos)[["cusec", INDICADOR, "nota1"]]
    return pd.DataFrame({"cusec": tabla["cusec"].astype(str), "renta_neta_persona": tabla[INDICADOR].astype(float),
                         "calidad_renta": tabla["nota1"].map(calidad)})


def quintiles_poblacion(renta: pd.Series, poblacion: pd.Series) -> pd.Series:
    """Quintil de renta (1 = más baja) de cada sección, cortando por población acumulada."""
    orden = np.argsort(renta.to_numpy(), kind="stable")
    acumulada = np.cumsum(poblacion.to_numpy()[orden])
    # Población acumulada en el punto medio de cada sección, para no castigar a la última.
    centro = (acumulada - poblacion.to_numpy()[orden] / 2) / acumulada[-1]
    quintil = np.empty(len(renta), dtype=int)
    quintil[orden] = np.clip(np.floor(centro * 5).astype(int) + 1, 1, 5)
    return pd.Series(quintil, index=renta.index, name="quintil_renta")


def quintiles_seccion(adrh: pd.DataFrame, unidades: pd.DataFrame) -> pd.DataFrame:
    """Quintil de renta por sección, ponderado por la población de las unidades de demanda.

    Falla si alguna sección con población no tiene renta: no se imputa.
    """
    poblacion = unidades.groupby("cusec")["poblacion_total"].sum()
    tabla = adrh.set_index("cusec").reindex(poblacion.index)
    if tabla["renta_neta_persona"].isna().any():
        faltan = tabla.index[tabla["renta_neta_persona"].isna()].tolist()[:5]
        raise ValueError(f"Secciones sin renta en el ADRH (p. ej. {faltan}); no se imputan.")
    tabla["quintil_renta"] = quintiles_poblacion(tabla["renta_neta_persona"], poblacion)
    return tabla.reset_index()


def por_quintil(unidades: pd.DataFrame, estados: pd.Series, columna: str, valores: tuple[str, ...]) -> list[dict]:
    """Población de un grupo por quintil de renta y estado (A, B o C).

    `unidades`: con `quintil_renta` y la columna de población; `estados`: mismo índice.
    """
    filas = []
    for quintil, grupo in unidades.groupby("quintil_renta"):
        cuentas = grupo[columna].groupby(estados.loc[grupo.index]).sum()
        filas.append({"quintil_renta": int(quintil), **{v: float(cuentas.get(v, 0.0)) for v in valores},
                      "denominador": float(grupo[columna].sum())})
    return filas
