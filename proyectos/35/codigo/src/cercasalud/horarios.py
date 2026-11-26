"""Horarios curados de refugios: estado de cada hora por tipo de día (H4; SPEC D-20, D-29, D-33).

Estados de un refugio en una hora: `abierto`, `cerrado` o `pendiente` (no consta).
- «Abierto en una hora» significa abierto durante toda esa hora (SPEC §7).
- Horas del perfil: de 12 a 21 h, es decir, las franjas que empiezan a las 12, 13, …, 20 (D-20).
- **Laborable:** abierta solo si abre esa hora de lunes a viernes. Si el horario cambia según el
  día, manda el día más restrictivo (supuesto declarado, análogo a la regla del fin de semana).
- **Fin de semana:** abierta solo si abre esa hora el sábado y el domingo (D-20). Si algún día
  está cerrado, cerrada; si no, pendiente cuando falta el dato de algún día.
- **Laborable de julio y de agosto:** las fichas dan el horario de verano y ningún cierre de
  agosto («sin cierres declarados en la ficha (no consta)»). Los dos tipos usan el mismo horario,
  y así se declara.

Textos de domingo de los 43 mercados (`curado/refugios_mercados_madrid.csv`):
- «no figura» o «no figura (mercado); …» → pendiente: la ficha no lo dice;
- «… solo el primer domingo …» → cerrado un domingo cualquiera de verano;
- un tramo horario («11:00-16:30», «11:00-17:00, solo ocio y restauración») → esos tramos.
"""

import re

import pandas as pd

ABIERTO, CERRADO, PENDIENTE = "abierto", "cerrado", "pendiente"
HORAS = tuple(range(12, 21))  # franjas de 12-13 a 20-21
TIPOS_DIA = ("laborable_julio", "laborable_agosto", "fin_de_semana")
DIAS_LABORABLES = ("lunes", "martes", "miercoles", "jueves", "viernes")
TRAMO = re.compile(r"(\d{1,2}):(\d{2})-(\d{1,2}):(\d{2})")


def tramos(texto: str) -> list[tuple[int, int]]:
    """Tramos «HH:MM-HH:MM» de un texto, en minutos desde medianoche."""
    return [(int(a) * 60 + int(b), int(c) * 60 + int(d)) for a, b, c, d in TRAMO.findall(texto)]


def sin_tildes(texto: str) -> str:
    """Minúsculas sin tildes, para reconocer los nombres de los días."""
    return texto.lower().translate(str.maketrans("áéíóú", "aeiou"))


def dias_de(prefijo: str) -> list[str]:
    """Días laborables que nombra un prefijo («lunes», «martes a jueves», «viernes»…)."""
    prefijo = sin_tildes(prefijo)
    rango = re.search(r"(lunes|martes|miercoles|jueves|viernes) a (lunes|martes|miercoles|jueves|viernes)", prefijo)
    if rango:
        inicio, fin = DIAS_LABORABLES.index(rango.group(1)), DIAS_LABORABLES.index(rango.group(2))
        return list(DIAS_LABORABLES[inicio:fin + 1])
    return [d for d in DIAS_LABORABLES if d in prefijo]


def laborables_por_dia(texto: str) -> dict[str, list[tuple[int, int]]]:
    """Tramos de cada día de lunes a viernes. Sin nombres de día, el mismo horario para todos."""
    if not any(d in sin_tildes(texto) for d in DIAS_LABORABLES):
        return {d: tramos(texto) for d in DIAS_LABORABLES}
    por_dia: dict[str, list[tuple[int, int]]] = {}
    for parte in texto.split(";"):
        primer_tramo = TRAMO.search(parte)
        if not primer_tramo:
            continue
        for dia in dias_de(parte[:primer_tramo.start()]):
            por_dia[dia] = tramos(parte)
    faltan = [d for d in DIAS_LABORABLES if d not in por_dia]
    if faltan:
        raise ValueError(f"Horario laborable sin los días {faltan}: {texto!r}")
    return por_dia


def domingo(texto: str) -> list[tuple[int, int]] | str:
    """Tramos del domingo, o PENDIENTE / CERRADO según el texto curado."""
    plano = sin_tildes(texto)
    if "solo el primer domingo" in plano:
        return CERRADO
    if plano.startswith("no figura"):
        return PENDIENTE
    encontrados = tramos(texto)
    if not encontrados:
        raise ValueError(f"Texto de domingo no reconocido: {texto!r}")
    return encontrados


def abierto_en(tramos_dia: list[tuple[int, int]] | str, hora: int) -> str:
    """Estado en la franja [hora, hora+1): abierto si algún tramo la cubre entera."""
    if isinstance(tramos_dia, str):
        return tramos_dia
    inicio, fin = hora * 60, (hora + 1) * 60
    return ABIERTO if any(a <= inicio and fin <= b for a, b in tramos_dia) else CERRADO


def combinar(estados: list[str]) -> str:
    """Todos los días deben abrir: cerrado si alguno cierra; pendiente si falta algún dato."""
    if CERRADO in estados:
        return CERRADO
    return PENDIENTE if PENDIENTE in estados else ABIERTO


def estados_refugio(fila: pd.Series) -> list[dict]:
    """Filas (tipo de día, hora, estado) de un mercado curado."""
    laborables = laborables_por_dia(fila["laborables_comercial"])
    sabado, dom = tramos(fila["sabado_comercial"]), domingo(fila["domingo_comercial"])
    filas = []
    for hora in HORAS:
        laborable = combinar([abierto_en(laborables[d], hora) for d in DIAS_LABORABLES])
        fin_de_semana = combinar([abierto_en(sabado, hora), abierto_en(dom, hora)])
        for tipo, estado in (("laborable_julio", laborable), ("laborable_agosto", laborable),
                             ("fin_de_semana", fin_de_semana)):
            filas.append({"refugio": str(fila["pk"]), "tipo_dia": tipo, "hora": hora, "estado": estado})
    return filas


def tabla_estados(mercados: pd.DataFrame) -> pd.DataFrame:
    """Estado de cada mercado en cada tipo de día y hora."""
    return pd.DataFrame([f for _, fila in mercados.iterrows() for f in estados_refugio(fila)])
