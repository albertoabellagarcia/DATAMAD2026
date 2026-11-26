"""Formato del mapa de minutos de la app (pantalla 2; SPEC P-27). No calcula resultados (R-UI-01).

Solo convierte lo que prepara `capas_mapa.py` en colores, textos, encuadres y la leyenda con
barras. No importa Streamlit, para poder probarlo.

Paletas de ColorBrewer (decisión del usuario del 15/11/2026; `docs/referencias_producto_20261115/
INFORME.md`, «Paleta cartográfica»):
- minutos: RdYlBu de 7 clases invertida (azul = cerca, rojo = lejos);
- porcentaje sin opción por municipio: YlOrRd de 7 clases (más es peor);
- quintil de renta: RdBu de 5 clases (divergente; rojo = renta más baja).
La interfaz es casi monocroma: el mapa es lo único con color.
"""

import html
import json
import math

import pandas as pd

AZUL_ROJO = ("#4575B4", "#91BFDB", "#E0F3F8", "#FFFFBF", "#FEE090", "#FC8D59", "#D73027")
AMARILLO_ROJO = ("#FFFFB2", "#FED976", "#FEB24C", "#FD8D3C", "#FC4E2A", "#E31A1C", "#B10026")
ROJO_AZUL_5 = ("#CA0020", "#F4A582", "#F7F7F7", "#92C5DE", "#0571B0")
NO_EVALUABLE = "#9E9E9E"
TERRITORIO = "#EEEEEE"  # suelo sin población residencial
TEXTO, TEXTO_SECUNDARIO, BORDE = "#1A1A1A", "#4D4D4D", "#BDBDBD"


NOTAS_MAPA = {
    "minutos": ("Cada color es la parte de una celda de 100 m donde vive gente (población del INE repartida por los "
                "edificios residenciales de OpenStreetMap). Minutos al centro de atención primaria pública más "
                "cercano por la red; no mide citas ni capacidad."),
    "transporte": ("En transporte cuenta también ir andando, con la mediana de las salidas de la franja (martes "
                   "laborable). Todas las celdas de una sección comparten el tiempo en transporte. Donde todos llegan "
                   "a pie en 20 min o menos no se calculó el transporte y vale el tiempo a pie, así que las clases "
                   "por debajo de 20 min pueden ser algo pesimistas."),
    "quintil_renta": ("Quintiles de la Comunidad con cerca del 20 % de la población cada uno. Es estratificación, no "
                      "causa: la renta no interviene en ningún cálculo de acceso."),
    "municipios": ("Porcentaje de toda la población del municipio sin un centro dentro del umbral. «Sin opción "
                   "verificada» no significa «sin centro»: el umbral es un supuesto del análisis."),
}


def nota_mapa(variable: str) -> str:
    """Cómo leer el mapa de la variable elegida (lo usan la app de Streamlit y la página web)."""
    if variable.startswith("pct_sin"):
        return NOTAS_MAPA["municipios"]
    if variable == "quintil_renta":
        return NOTAS_MAPA["quintil_renta"]
    return NOTAS_MAPA["minutos"] + (" " + NOTAS_MAPA["transporte"] if variable.startswith("min_tp") else "")


def rgb(hexadecimal: str) -> list[int]:
    """«#4575B4» → [69, 117, 180]."""
    return [int(hexadecimal[i:i + 2], 16) for i in (1, 3, 5)]


def colores(clases: pd.Series, paleta: tuple) -> pd.Series:
    """Color RGB de cada clase (0 = primera de la paleta); gris para -1 (no evaluable o sin dato)."""
    tabla = {i: rgb(c) for i, c in enumerate(paleta)} | {-1: rgb(NO_EVALUABLE)}
    return clases.astype(int).map(tabla)


def zoom_para(lon_min: float, lat_min: float, lon_max: float, lat_max: float, ancho_px: int, alto_px: int) -> float:
    """Zoom de Web Mercator con el que el rectángulo cabe en `ancho_px` × `alto_px`, con un pequeño margen.

    deck.gl mide el mundo en teselas de 512 px: a zoom z, 360° de longitud ocupan 512 · 2^z px.
    """
    ancho = max(lon_max - lon_min, 1e-4)
    lat_media = math.radians((lat_min + lat_max) / 2)
    alto = max(lat_max - lat_min, 1e-4) / math.cos(lat_media)
    zoom = min(math.log2(ancho_px * 360 / (512 * ancho)), math.log2(alto_px * 360 / (512 * alto)))
    return round(min(zoom - 0.15, 15.0), 2)


def rotulos_sin_solape(candidatos: pd.DataFrame, zoom: float, margen_px: float = 6) -> pd.DataFrame:
    """Quita los rótulos que se pisarían con otro ya colocado, en el orden de `candidatos` (prioridad).

    Calcula la caja de cada rótulo en píxeles con el zoom de la vista: ancho ≈ 0,6 × tamaño por
    carácter (fuente sin serifa en negrita) y alto ≈ tamaño. Se queda con un rótulo si su caja no
    se cruza con la de ninguno de los anteriores. Así, en la vista de la Comunidad no se amontonan
    los municipios del área metropolitana (visto en la captura del 16/11/2026).
    """
    px_grado_lon = 512 * 2 ** zoom / 360
    colocados, quedan = [], []
    for indice, fila in candidatos.iterrows():
        # En Web Mercator, un grado de latitud ocupa 1 / cos(lat) veces lo que uno de longitud.
        x = fila["lon"] * px_grado_lon
        y = fila["lat"] * px_grado_lon / math.cos(math.radians(fila["lat"]))
        medio_ancho = 0.6 * fila["tamano"] * len(str(fila["nombre"])) / 2 + margen_px
        medio_alto = fila["tamano"] / 2 + margen_px
        if all(abs(x - cx) >= medio_ancho + cw or abs(y - cy) >= medio_alto + ch for cx, cy, cw, ch in colocados):
            colocados.append((x, y, medio_ancho, medio_alto))
            quedan.append(indice)
    return candidatos.loc[quedan]


def texto_minutos(minutos: float, ultimo_limite: float) -> str:
    """«23 min»; por encima del último límite o sin ruta, «más de 60 min»."""
    if minutos is None or not math.isfinite(minutos) or minutos > ultimo_limite:
        return f"más de {ultimo_limite:g} min"
    return f"{minutos:.0f} min"


def personas(valor: float) -> str:
    """Número de personas con punto de miles: 289239.7 → «289.240»."""
    return f"{valor:,.0f}".replace(",", ".")


def porcentaje(valor: float, decimales: int = 1) -> str:
    """«4,1 %»."""
    return f"{valor:.{decimales}f} %".replace(".", ",")


def caracteres(textos) -> str:
    """Caracteres que dibujan los rótulos: ASCII imprimible más los de los propios textos (tildes, eñes).

    deck.gl solo dibuja los caracteres de esta lista; su opción «auto» no los recogió (15/11/2026).
    """
    return "".join(sorted({chr(i) for i in range(32, 127)} | set("".join(textos))))


def contornos_listas(textos: pd.Series) -> list:
    """Contornos guardados como texto JSON → listas de [lon, lat] para pydeck."""
    return [json.loads(t) for t in textos]


def fila_leyenda(etiqueta: str, color: str, pct: float | None, ancho_max_px: int = 110) -> str:
    """Una fila de la leyenda: muestra de color, etiqueta y barra con el porcentaje (si lo hay)."""
    muestra = (f"<span style='display:inline-block;width:22px;height:18px;background:{color};"
               f"border:1px solid {BORDE};vertical-align:middle'></span>")
    barra = ""
    if pct is not None:
        largo = max(1, round(ancho_max_px * pct / 100))
        barra = (f"<span style='display:inline-block;width:{largo}px;height:12px;background:{color};"
                 f"border:1px solid {BORDE};vertical-align:middle;margin-left:auto'></span>"
                 f"<span style='width:56px;text-align:right;color:{TEXTO}'>{porcentaje(pct)}</span>")
    return (f"<div style='display:flex;align-items:center;gap:8px;margin:3px 0'>{muestra}"
            f"<span style='min-width:118px;color:{TEXTO}'>{html.escape(etiqueta)}</span>{barra}</div>")


def leyenda_html(titulo: str, subtitulo: str, filas: list[tuple], umbral_tras: int | None,
                 extra: list[tuple] = ()) -> str:
    """Leyenda con barras de población por clase (idea de HeiGIT), con el umbral marcado.

    `filas`: (etiqueta, color, porcentaje o None). `umbral_tras`: índice de la fila tras la que se
    dibuja la raya del umbral. `extra`: filas sin barra o con su propio porcentaje (no evaluable,
    sin población).
    """
    partes = [(f"<div style='font-size:1rem;line-height:1.35'><div style='font-weight:700;color:{TEXTO}'>"
              f"{html.escape(titulo)}</div><div style='color:{TEXTO_SECUNDARIO};margin-bottom:6px'>"
              f"{html.escape(subtitulo)}</div>")]
    for i, (etiqueta, color, pct) in enumerate(filas):
        partes.append(fila_leyenda(etiqueta, color, pct))
        if umbral_tras is not None and i == umbral_tras:
            partes.append(f"<div style='border-top:2px solid {TEXTO};margin:4px 0;text-align:right;font-size:.8rem;"
                          f"font-weight:700;color:{TEXTO}'>umbral</div>")
    partes.append("<div style='height:6px'></div>")
    partes += [fila_leyenda(etiqueta, color, pct) for etiqueta, color, pct in extra]
    partes.append("</div>")
    return "".join(partes)


def filas_tramos(tramos: pd.DataFrame, etiquetas: list[str], paleta: tuple) -> tuple[list[tuple], float]:
    """Filas de la leyenda de una variable y un territorio, y porcentaje no evaluable (sobre el total)."""
    pct = tramos.set_index("clase")["pct"]
    filas = [(etiqueta, color, float(pct.get(i, 0.0))) for i, (etiqueta, color) in enumerate(zip(etiquetas, paleta,
                                                                                              strict=True))]
    return filas, float(pct.get(-1, 0.0))


def lineas_estado(fila: dict, modo: str, etiqueta_modo: str) -> str:
    """Una línea de la tarjeta: con acceso, sin opción verificada y no evaluable de un modo."""
    con, sin, no_eval = (fila[f"{modo}_{e}"] for e in ("con_acceso", "sin_opcion_verificada", "no_evaluable"))
    total = con + sin + no_eval
    texto = (f"**{etiqueta_modo}:** con acceso {porcentaje(100 * con / total)} · sin opción verificada "
             f"{personas(sin)} ({porcentaje(100 * sin / total)})")
    return texto + (f" · no evaluable {personas(no_eval)}" if no_eval >= 0.5 else "")


def tarjeta(fila: dict, modos: list[tuple[str, str]]) -> str:
    """Tarjeta de un territorio en Markdown: nombre, población y estados por modo."""
    lineas = [f"### {fila['nombre']}", f"{personas(fila['poblacion'])} habitantes (INE 2025)"]
    lineas += [lineas_estado(fila, modo, etiqueta) for modo, etiqueta in modos if f"{modo}_con_acceso" in fila]
    return "\n\n".join(lineas)
