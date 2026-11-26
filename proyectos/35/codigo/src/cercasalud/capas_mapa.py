"""Capas del mapa de minutos de la app (H6; SPEC P-27, propuesta del 15/11/2026).

Prepara en `build` (etapa `capas_app`) todo lo que dibuja el mapa de la pantalla de primaria,
para que la app no calcule (R-UI-01). Pasa a la app el boceto v2 de
`fases/H6_app/boceto_mapa_20261115/` (modelo WikiBarrio, decisiones del usuario del 15/11).

**Minutos de una unidad de demanda**, con los mismos datos y reglas que la etapa `acceso`:
- a pie: su tiempo de R5 a la velocidad base (3,0 km/h) al centro de primaria más cercano;
- a pie o en transporte, por franja: el menor entre ese tiempo y el de su sección en la matriz
  (`acceso.tiempo_transporte`, percentil del estado, P-18). En las secciones sin matriz, todas
  las unidades llegan a pie en 20 min o menos y su tiempo es el de ir andando: el transporte
  podría acortarlo, así que las clases por debajo de 20 min pueden quedar algo pesimistas.
- Sin tiempo dentro del radio de cálculo: última clase («más de …»).
- Las unidades no evaluables van aparte (clase -1), nunca como «lejos».

**Comprobación:** en las unidades evaluables, «minutos ≤ umbral» tiene que coincidir con el
estado `con_acceso` de `acceso`. Si no coincide en una sola unidad, la etapa falla: el mapa no
puede contradecir las cifras.

**Clases:** siete, de un tercio del umbral cada una, para que el paso del azul al cálido caiga en
el umbral (≤ 10, 10–20, 20–30 | 30–40 … > 60 en transporte; de 5 en 5 a pie).

**Dónde se pinta:** solo donde vive gente. Cada unidad es la parte de su celda de 100 m que cae
dentro de su sección (`demanda.py`), así que se dibuja la intersección de la celda con la
sección: una celda partida entre dos secciones lleva dos colores, uno por unidad.

**Vista por municipio:** porcentaje de la población total del municipio sin opción verificada.

**Referencias sin internet:** límites de municipio (secciones del INE), límites y nombres de los
21 distritos de Madrid (nombres de la tabla IGUALA del Ayuntamiento), autopistas y autovías de
OpenStreetMap y, en Madrid capital, sus vías principales. La capa de barrios no se usa: su
licencia no está confirmada.

Cálculo en EPSG:25830; las coordenadas se guardan en WGS84 (texto JSON) para dibujarlas.
"""

import itertools
import json
import re
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import pyogrio
import shapely

from . import acceso

LADO_CELDA_M = 100  # malla de las unidades de demanda (demanda.py)
CRS_CALCULO, CRS_DIBUJO = "EPSG:25830", "EPSG:4326"
DECIMALES_GRADOS = 5  # unos 1 m: de sobra para dibujar
TOLERANCIA_PIEZAS_M = 2
TOLERANCIA_LIMITES_M = 25
TOLERANCIA_VIAS_M = 15
VIAS_COMUNIDAD = ("motorway", "trunk")
VIAS_CAPITAL = ("primary",)
LIMITES_PCT_SIN = (0.0, 1.0, 5.0, 10.0, 25.0, 50.0)
ETIQUETAS_PCT_SIN = ("0 %", "hasta 1 %", "1–5 %", "5–10 %", "10–25 %", "25–50 %", "> 50 %")
ETIQUETAS_QUINTIL = ("Q1 (renta más baja)", "Q2", "Q3", "Q4", "Q5 (renta más alta)")
SIN_CLASE = -1
NOMBRE_COMUNIDAD = "Comunidad de Madrid"


def nombre_legible(nmun: str) -> str:
    """«Rozas de Madrid, Las» → «Las Rozas de Madrid»."""
    coincidencia = re.match(r"^(.*), (La|El|Los|Las)$", nmun)
    return f"{coincidencia.group(2)} {coincidencia.group(1)}" if coincidencia else nmun


def numero(valor: float) -> str:
    """Número sin decimales sobrantes: 10.0 → «10», 7.5 → «7,5»."""
    return f"{valor:g}".replace(".", ",")


def limites_clases(umbral: float) -> list[float]:
    """Seis límites de clase, de un tercio del umbral cada uno: el umbral es el tercero."""
    paso = umbral / 3
    return [paso * i for i in range(1, 7)]


def etiquetas_minutos(limites: list[float]) -> list[str]:
    """Etiquetas de las siete clases de minutos."""
    tramos = [f"{numero(a)}–{numero(b)}" for a, b in itertools.pairwise(limites)]
    return [f"≤ {numero(limites[0])} min", *tramos, f"> {numero(limites[-1])}"]


def clase(valores: pd.Series, limites: tuple | list, evaluable: pd.Series) -> pd.Series:
    """Índice de clase de cada valor (0 = primera; sin valor = última); -1 si no es evaluable.

    La clase i reúne los valores mayores que el límite i-1 y menores o iguales que el límite i.
    """
    numeros = pd.to_numeric(valores, errors="coerce").to_numpy(dtype=float)
    numeros = np.where(np.isnan(numeros), np.inf, numeros)
    indice = np.searchsorted(np.asarray(limites, dtype=float), numeros, side="left")
    return pd.Series(np.where(np.asarray(evaluable, dtype=bool), indice, SIN_CLASE), index=valores.index)


def variables_minutos(config: dict, franjas: list[str]) -> dict:
    """Catálogo de las variables de minutos: título, umbral, columna de estado, límites y etiquetas."""
    pie, tp = config["primaria"]["pie"], config["primaria"]["transporte"]
    catalogo = {"min_pie": {"titulo": f"Minutos a pie ({pie['velocidad_kmh']:.1f} km/h)".replace(".", ","),
                            "umbral": pie["umbral_min"], "estado": "estado_pie"}}
    for franja in franjas:
        desde, hasta = franja.split("_")
        sufijo = "" if franja == "9_13" else f"_{franja}"
        catalogo[f"min_tp_{franja}"] = {
            "titulo": f"Minutos a pie o en transporte público, de {desde} a {hasta} h",
            "umbral": tp["umbral_min"], "estado": f"estado_transporte{sufijo}"}
    for variable in catalogo.values():
        variable["limites"] = limites_clases(variable["umbral"])
        variable["etiquetas"] = etiquetas_minutos(variable["limites"])
    return catalogo


def minutos_unidades(unidades: pd.DataFrame, por_seccion: dict[str, pd.DataFrame], config: dict) -> pd.DataFrame:
    """Minutos a pie y, por franja, a pie o en transporte de cada unidad (reglas de `acceso`).

    `unidades` lleva `cusec` y las columnas de tiempo a pie; `por_seccion[franja]` es la salida de
    `acceso.mejor_por_seccion` para la matriz de esa franja.
    """
    pie, tp = config["primaria"]["pie"], config["primaria"]["transporte"]
    tabla = pd.DataFrame({"unidad": unidades["unidad"],
                          "min_pie": unidades[acceso.columna_pie(pie["velocidad_kmh"])].astype(float)})
    for franja, mejores in por_seccion.items():
        tabla[f"min_tp_{franja}"] = acceso.tiempo_transporte(unidades, mejores[f"p{tp['percentil_estado']}"],
                                                             pie["velocidad_kmh"])
    return tabla


def incoherencias(tabla: pd.DataFrame, catalogo: dict) -> dict[str, int]:
    """Unidades evaluables en las que «minutos ≤ umbral» no coincide con `con_acceso`, por variable."""
    resultado = {}
    for nombre, variable in catalogo.items():
        estado = tabla[variable["estado"]]
        evaluable = estado != acceso.NO_EVAL
        dentro = tabla[nombre].fillna(np.inf) <= variable["umbral"]
        resultado[nombre] = int((evaluable & (dentro != (estado == acceso.CON))).sum())
    return resultado


def anadir_clases(tabla: pd.DataFrame, catalogo: dict) -> pd.DataFrame:
    """Columnas `clase_<variable>` de minutos y `clase_quintil_renta` (0 a 4; -1 sin dato)."""
    tabla = tabla.copy()
    for nombre, variable in catalogo.items():
        tabla[f"clase_{nombre}"] = clase(tabla[nombre], variable["limites"], tabla[variable["estado"]] != acceso.NO_EVAL)
    quintil = pd.to_numeric(tabla["quintil_renta"], errors="coerce")
    tabla["clase_quintil_renta"] = np.where(quintil.notna(), quintil.fillna(0) - 1, SIN_CLASE).astype(int)
    return tabla


# ------------------------------ geometría ------------------------------------------------------

def piezas_unidades(unidades: pd.DataFrame, secciones: gpd.GeoDataFrame) -> gpd.GeoSeries:
    """Polígono de cada unidad: su celda de 100 m recortada por su sección (EPSG:25830).

    Si el recorte sale vacío (la sección no está en la capa o un error numérico), se usa la celda
    entera. Índice: el de `unidades`.
    """
    esquina = unidades["celda"].str.split("_", expand=True).astype(int).to_numpy() * LADO_CELDA_M
    cajas = shapely.box(esquina[:, 0], esquina[:, 1], esquina[:, 0] + LADO_CELDA_M, esquina[:, 1] + LADO_CELDA_M)
    seccion = secciones.set_index("CUSEC").geometry.reindex(unidades["cusec"]).to_numpy()
    recorte = shapely.intersection(cajas, seccion)
    vacio = shapely.is_missing(recorte) | shapely.is_empty(recorte) | (shapely.area(recorte) == 0)
    piezas = np.where(vacio, cajas, recorte)
    return gpd.GeoSeries(shapely.simplify(piezas, TOLERANCIA_PIEZAS_M, preserve_topology=True),
                         index=unidades.index, crs=CRS_CALCULO)


def contornos(geometrias: gpd.GeoSeries) -> pd.DataFrame:
    """Anillo exterior de cada polígono, en WGS84 y como texto JSON; una fila por parte.

    Los anillos interiores se omiten: un hueco dentro de una celda es otra unidad, que se dibuja
    encima porque las piezas se ordenan de mayor a menor superficie. La columna `fila` es el
    índice de origen.
    """
    partes = geometrias.explode(index_parts=False)
    partes = partes[partes.geom_type == "Polygon"]
    superficie = partes.area.to_numpy()
    wgs = partes.to_crs(CRS_DIBUJO)
    anillos = shapely.get_exterior_ring(wgs.to_numpy())
    coordenadas, cual = shapely.get_coordinates(anillos, return_index=True)
    cortes = np.flatnonzero(np.diff(cual)) + 1
    textos = [json.dumps(np.round(trozo, DECIMALES_GRADOS).tolist(), separators=(",", ":"))
              for trozo in np.split(coordenadas, cortes)]
    tabla = pd.DataFrame({"fila": partes.index.to_numpy(), "superficie_m2": superficie, "contorno": textos})
    return tabla.sort_values("superficie_m2", ascending=False, kind="stable").reset_index(drop=True)


def caminos(geometrias: gpd.GeoSeries, tipo: str, con_codigo: bool = True) -> pd.DataFrame:
    """Líneas en WGS84 como texto JSON (una fila por tramo), con su tipo y el código de su territorio.

    De un polígono se toma su contorno. `codigo` es el índice de `geometrias` (municipio o
    distrito), o vacío si `con_codigo` es falso (vías).
    """
    lineas = geometrias.boundary if geometrias.geom_type.isin(["Polygon", "MultiPolygon"]).any() else geometrias
    partes = lineas.explode(index_parts=False)
    partes = partes[partes.geom_type.isin(["LineString", "LinearRing"]) & ~partes.is_empty].to_crs(CRS_DIBUJO)
    textos = [json.dumps(np.round(np.asarray(g.coords)[:, :2], DECIMALES_GRADOS).tolist(), separators=(",", ":"))
              for g in partes]
    codigos = partes.index.astype(str) if con_codigo else [""] * len(partes)
    return pd.DataFrame({"tipo": tipo, "codigo": list(codigos), "camino": textos})


def vias(pbf: Path, tipos: tuple, recorte) -> gpd.GeoSeries:
    """Vías de OSM de esos tipos, recortadas a un territorio y simplificadas (EPSG:25830)."""
    lista = ", ".join(f"'{t}'" for t in tipos)
    lineas = pyogrio.read_dataframe(pbf, layer="lines", columns=["highway"], where=f"highway IN ({lista})")
    lineas = lineas.set_crs(CRS_DIBUJO).to_crs(CRS_CALCULO)
    xmin, ymin, xmax, ymax = recorte.bounds
    dentro = lineas.cx[xmin:xmax, ymin:ymax].geometry.intersection(recorte)
    return dentro[~dentro.is_empty].simplify(TOLERANCIA_VIAS_M).reset_index(drop=True)


def lineas_referencia(municipios: gpd.GeoDataFrame, distritos: gpd.GeoDataFrame, pbf: Path) -> pd.DataFrame:
    """Límites de municipio y de distrito, autopistas y autovías, y vías principales de la capital."""
    region = municipios.union_all()
    capital = municipios.loc[municipios["cumun"] == acceso.MADRID_CAPITAL].union_all()
    return pd.concat([caminos(municipios.set_index("cumun").geometry, "limite_municipio"),
                      caminos(distritos.set_index("cdis").geometry, "limite_distrito"),
                      caminos(vias(pbf, VIAS_COMUNIDAD, region), "via_principal", False),
                      caminos(vias(pbf, VIAS_CAPITAL, capital), "via_capital", False)], ignore_index=True)


def poligonos_territorio(secciones: gpd.GeoDataFrame) -> tuple[gpd.GeoDataFrame, gpd.GeoDataFrame]:
    """Municipios (179) y distritos de Madrid capital (21), disueltos de las secciones y simplificados."""
    municipios = secciones.dissolve(by="CUMUN", aggfunc={"NMUN": "first"}).reset_index()
    municipios = municipios.rename(columns={"CUMUN": "cumun", "NMUN": "nombre"})
    municipios["nombre"] = municipios["nombre"].map(nombre_legible)
    capital = secciones[secciones["CUMUN"] == acceso.MADRID_CAPITAL]
    distritos = capital.dissolve(by="CDIS").reset_index().rename(columns={"CDIS": "cdis"})[["cdis", "geometry"]]
    for capa in (municipios, distritos):
        capa["geometry"] = capa.geometry.simplify(TOLERANCIA_LIMITES_M)
    return municipios, distritos


# ------------------------------ territorios, tramos y vista por municipio ---------------------

def modos_estado(tabla: pd.DataFrame) -> list[str]:
    """Modos de A con estado por unidad: a pie, en transporte (9 a 13 h) y, si existe, de 16 a 20 h."""
    return [m for m in ("pie", "transporte", "transporte_16_20") if f"estado_{m}" in tabla.columns]


def recuentos_estado(tabla: pd.DataFrame, clave: pd.Series) -> pd.DataFrame:
    """Población por estado de A (escenario base, cada modo y franja) para cada grupo de `clave`."""
    columnas = {}
    for modo in modos_estado(tabla):
        suma = tabla.pivot_table(index=clave, columns=f"estado_{modo}", values="poblacion_total", aggfunc="sum",
                                 fill_value=0.0).reindex(columns=list(acceso.ESTADOS), fill_value=0.0)
        for estado in acceso.ESTADOS:
            columnas[f"{modo}_{estado}"] = suma[estado]
    return pd.DataFrame(columnas)


def centro_poblado(tabla: pd.DataFrame, clave: pd.Series) -> pd.DataFrame:
    """Centro ponderado por población de cada grupo (EPSG:25830): donde va su rótulo."""
    pesos = tabla["poblacion_total"]
    suma = pd.DataFrame({"xp": tabla["x"] * pesos, "yp": tabla["y"] * pesos, "poblacion": pesos}).groupby(clave).sum()
    return pd.DataFrame({"x": suma["xp"] / suma["poblacion"], "y": suma["yp"] / suma["poblacion"],
                         "poblacion": suma["poblacion"]})


def a_grados(x: np.ndarray, y: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """EPSG:25830 → longitud y latitud."""
    puntos = gpd.GeoSeries(gpd.points_from_xy(x, y), crs=CRS_CALCULO).to_crs(CRS_DIBUJO)
    return puntos.x.to_numpy(), puntos.y.to_numpy()


def territorios(tabla: pd.DataFrame, municipios: gpd.GeoDataFrame, distritos: gpd.GeoDataFrame,
                nombres_distritos: dict[str, str]) -> pd.DataFrame:
    """Comunidad, municipios y distritos de la capital: nombre, rótulo, encuadre, población y estados."""
    grupos = {"comunidad": pd.Series("28", index=tabla.index), "municipio": tabla["cusec"].str[:5]}
    capital = tabla[tabla["cusec"].str.startswith(acceso.MADRID_CAPITAL)]
    filas = []
    for tipo, clave in grupos.items():
        filas.append(centro_poblado(tabla, clave).join(recuentos_estado(tabla, clave)).assign(tipo=tipo))
    clave_distrito = capital["cusec"].str[5:7]
    filas.append(centro_poblado(capital, clave_distrito).join(recuentos_estado(capital, clave_distrito))
                 .assign(tipo="distrito"))
    resultado = pd.concat(filas).rename_axis("codigo").reset_index()
    nombres = {"28": NOMBRE_COMUNIDAD, **dict(zip(municipios["cumun"], municipios["nombre"], strict=True))}
    resultado["nombre"] = [nombres_distritos.get(c, c) if t == "distrito" else nombres.get(c, c)
                           for t, c in zip(resultado["tipo"], resultado["codigo"], strict=True)]
    resultado["lon"], resultado["lat"] = a_grados(resultado["x"].to_numpy(), resultado["y"].to_numpy())
    return anadir_encuadre(resultado, municipios, distritos).drop(columns=["x", "y"])


def anadir_encuadre(resultado: pd.DataFrame, municipios: gpd.GeoDataFrame, distritos: gpd.GeoDataFrame) -> pd.DataFrame:
    """Rectángulo envolvente en grados de cada territorio (para centrar el mapa al buscarlo)."""
    capas = {"comunidad": gpd.GeoSeries([municipios.union_all()], index=["28"], crs=CRS_CALCULO),
             "municipio": municipios.set_index("cumun").geometry, "distrito": distritos.set_index("cdis").geometry}
    cajas = []
    for tipo, geometrias in capas.items():
        limites = geometrias.to_crs(CRS_DIBUJO).bounds.rename(
            columns={"minx": "lon_min", "miny": "lat_min", "maxx": "lon_max", "maxy": "lat_max"})
        cajas.append(limites.assign(tipo=tipo).rename_axis("codigo").reset_index())
    return resultado.merge(pd.concat(cajas), on=["tipo", "codigo"], how="left", validate="one_to_one")


def porcentajes_sin_opcion(territorio: pd.DataFrame) -> pd.DataFrame:
    """Porcentaje de la población total sin opción verificada (a pie y en transporte) y su clase."""
    territorio = territorio.copy()
    total = territorio[[f"pie_{e}" for e in acceso.ESTADOS]].sum(axis=1)
    for modo in [m for m in ("pie", "transporte", "transporte_16_20") if f"{m}_{acceso.SIN}" in territorio]:
        territorio[f"pct_sin_{modo}"] = 100 * territorio[f"{modo}_{acceso.SIN}"] / total
        territorio[f"clase_pct_sin_{modo}"] = clase(territorio[f"pct_sin_{modo}"], LIMITES_PCT_SIN,
                                                    pd.Series(True, index=territorio.index))
    return territorio


def tramos(tabla: pd.DataFrame, columnas_clase: list[str]) -> pd.DataFrame:
    """Población y porcentaje por clase, por territorio (Comunidad, municipio y distrito) y variable.

    El porcentaje de cada clase es sobre la población evaluable de esa variable; la fila de clase
    -1 (no evaluable o sin dato) lleva su porcentaje sobre la población total.
    """
    capital = tabla["cusec"].str.startswith(acceso.MADRID_CAPITAL)
    claves = [("comunidad", tabla.index, pd.Series("28", index=tabla.index)),
              ("municipio", tabla.index, tabla["cusec"].str[:5]),
              ("distrito", tabla.index[capital], tabla.loc[capital, "cusec"].str[5:7])]
    filas = []
    for tipo, indice, clave in claves:
        for columna in columnas_clase:
            suma = tabla.loc[indice].groupby([clave, tabla.loc[indice, columna]])["poblacion_total"].sum()
            suma = suma.rename_axis(["codigo", "clase"]).rename("poblacion").reset_index()
            total = suma.groupby("codigo")["poblacion"].transform("sum")
            evaluable = suma["poblacion"].where(suma["clase"] != SIN_CLASE, 0).groupby(suma["codigo"]).transform("sum")
            suma["pct"] = np.where(suma["clase"] == SIN_CLASE, 100 * suma["poblacion"] / total,
                                   100 * suma["poblacion"] / evaluable.replace(0, np.nan))
            filas.append(suma.assign(tipo=tipo, variable=columna.removeprefix("clase_")))
    return pd.concat(filas, ignore_index=True)[["tipo", "codigo", "variable", "clase", "poblacion", "pct"]]


# ------------------------------ ensamblado ----------------------------------------------------

def preparar(unidades: pd.DataFrame, estados: pd.DataFrame, por_seccion: dict[str, pd.DataFrame],
             quintiles: pd.DataFrame, secciones: gpd.GeoDataFrame, nombres_distritos: dict[str, str], pbf: Path,
             config: dict) -> dict:
    """Todas las capas del mapa de minutos. Falla si los minutos contradicen algún estado.

    Devuelve las tablas `celdas`, `municipios`, `lineas`, `territorios` y `tramos`, el catálogo de
    variables y las comprobaciones hechas.
    """
    catalogo = variables_minutos(config, list(por_seccion))
    tabla = (unidades[["unidad", "cusec", "celda", "x", "y", "poblacion_total"]]
             .merge(minutos_unidades(unidades, por_seccion, config), on="unidad", validate="one_to_one")
             .merge(estados.drop(columns="cusec"), on="unidad", how="left", validate="one_to_one")
             .merge(quintiles[["cusec", "quintil_renta", "calidad_renta"]], on="cusec", how="left",
                    validate="many_to_one"))
    errores = incoherencias(tabla, catalogo)
    if any(errores.values()):
        raise ValueError(f"Los minutos contradicen los estados de acceso en estas unidades: {errores}")
    tabla = anadir_clases(tabla, catalogo)
    secciones = secciones[secciones["TIPO"] == "SECCIONADO"]
    municipios, distritos = poligonos_territorio(secciones)
    piezas = contornos(piezas_unidades(tabla, secciones))
    columnas = ["unidad", "cusec", "poblacion_total", *catalogo, *[f"clase_{v}" for v in catalogo],
                "quintil_renta", "calidad_renta", "clase_quintil_renta",
                *[c for c in estados.columns if c.startswith("estado_")]]
    celdas = piezas.join(tabla[columnas], on="fila").drop(columns="fila")
    territorio = porcentajes_sin_opcion(territorios(tabla, municipios, distritos, nombres_distritos))
    contornos_municipio = contornos(municipios.geometry).join(municipios[["cumun"]], on="fila").drop(columns="fila")
    columnas_clase = [f"clase_{v}" for v in catalogo] + ["clase_quintil_renta"]
    return {"celdas": celdas, "municipios": contornos_municipio, "lineas": lineas_referencia(municipios, distritos, pbf),
            "territorios": territorio, "tramos": tramos(tabla, columnas_clase), "catalogo": catalogo,
            "comprobaciones": {"incoherencias_minutos_estado": errores,
                               "unidades_sin_quintil": int(tabla["quintil_renta"].isna().sum()),
                               "piezas_dibujadas": len(celdas), "unidades": len(tabla)}}
