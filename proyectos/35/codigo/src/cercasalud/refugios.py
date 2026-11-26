"""Situación inicial de B (refugios, a pie) y C (carencias coincidentes) por unidad de demanda (H4).

**B por unidad, tipo de día y hora** (SPEC D-20, P-06, R-TMP-03, R-TMP-04, D-29, D-33):
- `con_acceso`: algún refugio a `umbral` minutos o menos está abierto toda la hora;
- `no_evaluable` (`horario`): ninguno abierto, pero alguno en estado pendiente;
- `sin_opcion_verificada`: ningún refugio en el umbral, o todos cerrados.

Fuera de los municipios con lista oficial verificada (hoy, solo Madrid capital), B es
`no_evaluable` (`inventario`). Una unidad sin conexión a la red a pie es `no_evaluable` (`conexion`).

**Cotas:**
- **central:** horario comercial con el supuesto de acceso de D-33; pendiente queda pendiente;
- **inferior:** pendiente como cerrado;
- **superior:** pendiente como abierto;
- **acreditable:** sin el supuesto de D-33. Sin acceso verificado a la zona climatizada, nada
  cuenta como abierto: lo abierto pasa a pendiente.

Se cumple acreditable ≤ inferior ≤ central ≤ superior en `con_acceso` (R-TMP-04).

**Métricas por tipo de día** (D-24, §8 de la SPEC):
- cobertura por hora;
- la de la peor hora;
- personas-hora;
- personas únicas con alguna hora (nunca se suman horas como personas).

**C** (P-21, R-CMP-02, R-CMP-03): en cada unidad donde A y B son evaluables, carencia
coincidente = A `sin_opcion_verificada` y B `sin_opcion_verificada` en la franja de referencia.
La franja es la peor hora del laborable de julio en la cota central, para la población total.
Fuera, C es `no_evaluable`.
"""

import json

import numpy as np
import pandas as pd

from .acceso import CON, ESTADOS, GRUPOS_EDAD, MADRID_CAPITAL, NO_EVAL, SIN
from .horarios import ABIERTO, CERRADO, HORAS, PENDIENTE, TIPOS_DIA

COTAS = ("acreditable", "inferior", "central", "superior")


def aplicar_cota(estados: pd.DataFrame, cota: str) -> pd.Series:
    """Estado de cada refugio-hora según la cota (ver el docstring del módulo)."""
    estado = estados["estado"]
    if cota == "inferior":
        return estado.replace(PENDIENTE, CERRADO)
    if cota == "superior":
        return estado.replace(PENDIENTE, ABIERTO)
    if cota == "acreditable":
        return estado.where(estados["acceso_verificado"] | (estado != ABIERTO), PENDIENTE)
    return estado


def estados_b(unidades: pd.DataFrame, pares: pd.DataFrame, estados_refugio: pd.DataFrame, umbral_min: float,
              cota: str, territorio_b: pd.Series) -> pd.DataFrame:
    """Estado de B por unidad, tipo de día y hora (filas: unidades × tipos de día × horas).

    `pares`: unidad, refugio y minutos a pie (solo pares cercanos). `estados_refugio`: refugio,
    tipo_dia, hora, estado y acceso_verificado. `territorio_b`: máscara de unidades con lista
    oficial verificada.
    """
    rejilla = pd.MultiIndex.from_product([unidades["unidad"], TIPOS_DIA, HORAS], names=["unidad", "tipo_dia", "hora"])
    cerca = pares[pares["minutos"] <= umbral_min][["unidad", "refugio"]]
    cruce = cerca.merge(estados_refugio.assign(estado=aplicar_cota(estados_refugio, cota)), on="refugio")
    hay = cruce.assign(abierto=cruce["estado"] == ABIERTO, pendiente=cruce["estado"] == PENDIENTE) \
        .groupby(["unidad", "tipo_dia", "hora"])[["abierto", "pendiente"]].any().reindex(rejilla, fill_value=False)
    estado = np.where(hay["abierto"], CON, np.where(hay["pendiente"], NO_EVAL, SIN))
    motivo = np.where(estado == NO_EVAL, "horario", "")
    tabla = pd.DataFrame({"estado": estado, "motivo": motivo}, index=rejilla).reset_index()
    fuera = tabla["unidad"].isin(unidades.loc[~territorio_b.to_numpy(), "unidad"])
    sin_red = tabla["unidad"].isin(unidades.loc[~unidades["enganchado"].to_numpy(dtype=bool), "unidad"])
    tabla.loc[sin_red, ["estado", "motivo"]] = [NO_EVAL, "conexion"]
    tabla.loc[fuera, ["estado", "motivo"]] = [NO_EVAL, "inventario"]
    return tabla


def poblacion_por_estado(tabla: pd.DataFrame, unidades: pd.DataFrame, columna: str) -> pd.DataFrame:
    """Población de un grupo de edad por tipo de día, hora y estado."""
    con_pob = tabla.merge(unidades[["unidad", columna]], on="unidad")
    return con_pob.pivot_table(index=["tipo_dia", "hora"], columns="estado", values=columna, aggfunc="sum",
                               fill_value=0.0).reindex(columns=list(ESTADOS), fill_value=0.0)


def metricas_b(tabla: pd.DataFrame, unidades: pd.DataFrame, escenario: dict) -> tuple[list[dict], list[dict]]:
    """Filas por hora y filas resumen (peor hora, personas-hora, personas únicas) por tipo de día y edad."""
    por_hora, resumen = [], []
    supuestos = json.dumps(escenario, ensure_ascii=False)
    for grupo, columna in GRUPOS_EDAD.items():
        poblacion = poblacion_por_estado(tabla, unidades, columna)
        for (tipo, hora), fila in poblacion.iterrows():
            por_hora.append({**escenario, "grupo_edad": grupo, "tipo_dia": tipo, "hora": hora,
                             **{e: float(fila[e]) for e in ESTADOS}, "unidad_medida": "personas"})
        con_pob = tabla.merge(unidades[["unidad", columna]], on="unidad")
        for tipo in TIPOS_DIA:
            horas = poblacion.loc[tipo]
            peor = horas[CON].idxmin()
            unicas = con_pob[(con_pob["tipo_dia"] == tipo) & (con_pob["estado"] == CON)] \
                .drop_duplicates("unidad")[columna].sum()
            resumen.append({**escenario, "grupo_edad": grupo, "tipo_dia": tipo, "peor_hora": int(peor),
                            "con_acceso_peor_hora": float(horas.loc[peor, CON]),
                            "sin_opcion_peor_hora": float(horas.loc[peor, SIN]),
                            "no_evaluable_peor_hora": float(horas.loc[peor, NO_EVAL]),
                            "personas_hora_con_acceso": float(horas[CON].sum()),
                            "personas_unicas_con_alguna_hora": float(unicas),
                            "denominador": float(unidades[columna].sum()), "supuestos": supuestos})
    return por_hora, resumen


def estados_c(estado_a: pd.DataFrame, estado_b_ref: pd.DataFrame) -> pd.DataFrame:
    """C por unidad: coincidencia de carencias donde A y B son evaluables (P-21).

    `estado_a` y `estado_b_ref`: columnas unidad, estado y motivo (B en la franja de referencia).
    """
    tabla = estado_a.merge(estado_b_ref, on="unidad", suffixes=("_a", "_b"), validate="one_to_one")
    evaluable = (tabla["estado_a"] != NO_EVAL) & (tabla["estado_b"] != NO_EVAL)
    coincide = evaluable & (tabla["estado_a"] == SIN) & (tabla["estado_b"] == SIN)
    estado = np.where(~evaluable, NO_EVAL, np.where(coincide, "carencia_coincidente", "sin_coincidencia"))
    motivo = np.where(~evaluable, np.where(tabla["estado_b"] == NO_EVAL, "b_" + tabla["motivo_b"],
                                           "a_" + tabla["motivo_a"]), "")
    return pd.DataFrame({"unidad": tabla["unidad"], "estado": estado, "motivo": motivo})


def c_por_hora(estado_a: pd.DataFrame, estados_b: pd.DataFrame, unidades: pd.DataFrame,
               grupos: dict[str, str]) -> list[dict]:
    """C en cada tipo de día y hora de B (comprobación de cuánto depende C de la franja elegida).

    La franja de referencia de C sigue siendo la peor hora (escenario declarado); esta tabla
    repite C con B en cada hora para ver cuánto cambia. `estados_b`: B por unidad, tipo de día y
    hora (una cota). `grupos`: {nombre del grupo de edad: columna de población}.
    """
    filas = []
    for (tipo, hora), b in estados_b.groupby(["tipo_dia", "hora"]):
        c = estados_c(estado_a, b[["unidad", "estado", "motivo"]]).merge(unidades, on="unidad")
        for grupo, columna in grupos.items():
            por_estado = c.groupby("estado")[columna].sum()
            filas.append({"tipo_dia": tipo, "hora": int(hora), "grupo_edad": grupo,
                          **{e: float(por_estado.get(e, 0.0)) for e in ("carencia_coincidente", "sin_coincidencia",
                                                                        NO_EVAL)},
                          "unidad_medida": "personas"})
    return filas


def union_con_acceso(estado_a: pd.DataFrame, estado_b_ref: pd.DataFrame) -> pd.Series:
    """Unidades con acceso en A o en B (sin duplicar personas; R-MET-02)."""
    tabla = estado_a.merge(estado_b_ref, on="unidad", suffixes=("_a", "_b"), validate="one_to_one")
    return pd.Series(((tabla["estado_a"] == CON) | (tabla["estado_b"] == CON)).to_numpy(), index=tabla["unidad"])


def territorio_b(unidades: pd.DataFrame) -> pd.Series:
    """Unidades en municipios con lista oficial verificada de refugios: hoy, Madrid capital (D-28, D-30)."""
    return unidades["cusec"].str.startswith(MADRID_CAPITAL)
