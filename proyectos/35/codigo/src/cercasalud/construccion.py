"""Etapas de cálculo sin red sobre una versión existente (`build`).

Cada etapa escribe en una carpeta temporal y solo al terminar la renombra a su nombre
final (R-OPS-01). Etapas, en orden: atención primaria, población, demanda, tiempos a pie
(`acceso_pie`, con R5 y Java) y estados de acceso a primaria (`acceso`, H3).

La matriz de transporte no se calcula aquí: es un cálculo de horas que se lanza aparte
(fases/noches/ejecutor_nocturno.py) y que `acceso` lee de `noches/`.
"""

import json
import os
import shutil
from pathlib import Path

import numpy as np
import pandas as pd

from . import acceso, demanda, poblacion, primaria
from .ingesta import ahora_utc, leer_snapshot, ruta_en_snapshot
from .manifiestos import SUFIJO_TEMPORAL, escribir_json_atomico, sha256_archivo
from .rutas import carpeta_procesados

ARCHIVO_SANIDAD = ("sanidad", "centros_servicios_establecimientos_sanitarios.csv")
ARCHIVO_POBLACION = ("ine_69213", "69213.csv")
ARCHIVO_SECCIONES = ("ine_secciones_2025", "secciones_2025_madrid.geojson")
ARCHIVO_OSM = ("osm", "madrid-261112.osm.pbf")
TOLERANCIA_TOTALES = 1e-6  # R-DEM-01
BLOQUE_PIE = 10_000
# Matriz de transporte de 9 a 13 h: noche 1 (414 centros) y los 8 centros curados del 14/11.
CARPETAS_TRANSPORTE = ("transporte_9_13", "transporte_9_13_centros_nuevos")
# Por franja de D-17. La de 16 a 20 h (noche 2) se calcula ya con los 422 centros.
CARPETAS_TRANSPORTE_FRANJA = {"9_13": CARPETAS_TRANSPORTE, "16_20": ("transporte_16_20",)}
CARPETA_INVENTARIO_AMPLIADO = "sensibilidad_inventario_ampliado"
# Refugios de la situación inicial de B: los 43 mercados de Madrid (D-28) y la coordenada de OSM que falta.
UMBRAL_MAX_REFUGIOS = 15  # el mayor umbral de sensibilidad de B (D-20); más allá no hace falta el par
GRUPOS_C = acceso.GRUPOS_EDAD
CARPETA_CURADO = Path(__file__).resolve().parents[2] / "curado"
ARCHIVO_REFUGIOS_MERCADOS = CARPETA_CURADO / "refugios_mercados_madrid.csv"
ARCHIVO_REFUGIOS_COORDENADAS = CARPETA_CURADO / "refugios_coordenadas_osm.csv"
# Coordenadas curadas de los centros que el registro publica sin ellas (curado/README.md).
ARCHIVO_COORDENADAS_CURADAS = Path(__file__).resolve().parents[2] / "curado" / "primaria_coordenadas_osm.csv"


def preparar_temporal(destino: Path) -> Path:
    """Crea vacía la carpeta temporal de una etapa (borra la de un intento anterior interrumpido)."""
    temporal = destino.with_name(destino.name + SUFIJO_TEMPORAL)
    if temporal.exists():
        shutil.rmtree(temporal)
    temporal.mkdir(parents=True)
    return temporal


def publicar_carpeta(temporal: Path, destino: Path) -> None:
    """Sustituye la carpeta final por la temporal ya completa."""
    if destino.exists():
        shutil.rmtree(destino)
    os.replace(temporal, destino)


def etapa_primaria(raiz: Path, id_snapshot: str) -> dict:
    """Filtra la primaria pública de la versión y guarda centros, excluidos, discrepancias y conteos."""
    snapshot = leer_snapshot(raiz, id_snapshot)
    origen = ruta_en_snapshot(raiz, snapshot, *ARCHIVO_SANIDAD)
    curadas = primaria.leer_coordenadas_curadas(ARCHIVO_COORDENADAS_CURADAS)
    resultado = primaria.filtrar_primaria(primaria.leer_registro(origen), curadas)
    destino = carpeta_procesados(raiz, id_snapshot) / "primaria"
    temporal = preparar_temporal(destino)
    resultado["incluidos"].to_parquet(temporal / "centros_primaria.parquet", index=False)
    resultado["excluidos"].to_csv(temporal / "excluidos.csv", index=False, encoding="utf-8")
    resultado["discrepancias"].to_csv(temporal / "discrepancias.csv", index=False, encoding="utf-8")
    resumen = {
        "etapa": "primaria", "snapshot": id_snapshot, "creado_utc": ahora_utc().isoformat(),
        "origen": origen.relative_to(raiz).as_posix(), "origen_sha256": sha256_archivo(origen),
        "columnas_personales_eliminadas": list(primaria.COLUMNAS_PERSONALES),
        "criterio": {"tipos": list(primaria.TIPOS_PRIMARIA), "dependencia": primaria.DEPENDENCIA_PUBLICA,
                     "dependencia_patrimonial_alternativa": primaria.PATRIMONIAL_PUBLICA,
                     "regla_dependencias": "funcional autonómica O patrimonial SERMAS",
                     "x_minima": primaria.X_MINIMA, "y_minima": primaria.Y_MINIMA,
                     "crs": "EPSG:25830 (inferido y validado; el origen no lo declara)"},
        "coordenadas_curadas": {"archivo": "curado/primaria_coordenadas_osm.csv",
                                "sha256": sha256_archivo(ARCHIVO_COORDENADAS_CURADAS),
                                "licencia": "ODbL (derivado de OpenStreetMap)",
                                "regla": "solo rellenan coordenadas vacías del registro"},
        "conteos": resultado["conteos"],
    }
    escribir_json_atomico(temporal / "resumen.json", resumen)
    publicar_carpeta(temporal, destino)
    return resumen


def etapa_demanda(raiz: Path, id_snapshot: str, config: dict | None = None) -> dict:
    """Unidades de demanda (malla de 100 m con soporte OSM) y secciones pendientes de localizar.

    Usa la salida de la etapa `poblacion` de la misma versión. Falla sin publicar si la suma
    de las unidades no reproduce el INE por sección y edad con tolerancia 10⁻⁶ (R-DEM-01).
    """
    snapshot = leer_snapshot(raiz, id_snapshot)
    pbf = ruta_en_snapshot(raiz, snapshot, *ARCHIVO_OSM)
    capa = ruta_en_snapshot(raiz, snapshot, *ARCHIVO_SECCIONES)
    por_edad = pd.read_parquet(carpeta_procesados(raiz, id_snapshot) / "poblacion" / "poblacion_seccion_edad.parquet")
    edificios, usos = demanda.leer_soporte_osm(pbf)
    secciones = demanda.leer_secciones(capa)
    excluir = tuple((config or {}).get("demanda", {}).get("excluir_usos", []))
    resultado = demanda.construir_unidades(edificios, usos, secciones, por_edad, excluir)
    diferencia = demanda.diferencia_maxima_con_ine(resultado["unidades"], demanda.poblacion_ancha(por_edad))
    destino = carpeta_procesados(raiz, id_snapshot) / "demanda"
    temporal = preparar_temporal(destino)
    resultado["unidades"].to_parquet(temporal / "unidades_demanda.parquet", index=False)
    resultado["pendientes"].to_csv(temporal / "secciones_pendiente_localizar.csv", index=False, encoding="utf-8")
    interiores = demanda.puntos_interiores(secciones)
    interiores.assign(x=interiores.geometry.x, y=interiores.geometry.y).drop(columns="geometry").to_parquet(
        temporal / "puntos_interiores_seccion.parquet", index=False)
    resumen = {
        "etapa": "demanda", "snapshot": id_snapshot, "creado_utc": ahora_utc().isoformat(),
        "pbf": pbf.relative_to(raiz).as_posix(), "pbf_sha256": sha256_archivo(pbf),
        "capa_secciones": capa.relative_to(raiz).as_posix(),
        "criterio": {"lado_celda_m": demanda.LADO_CELDA_M, "crs": demanda.CRS_CALCULO,
                     "tipos_vivienda": list(demanda.TIPOS_VIVIENDA),
                     "building_yes": "solo si su punto interior cae en landuse=residential",
                     "respaldo": "landuse=residential si la sección no tiene edificios de vivienda",
                     "peso": "superficie de planta (edificios) o de suelo residencial (respaldo)",
                     "excluir_usos": list(excluir)},
        "diferencia_maxima_con_ine": diferencia,
        "conteos": resultado["conteos"],
    }
    escribir_json_atomico(temporal / "resumen.json", resumen)
    if diferencia > TOLERANCIA_TOTALES:
        raise ValueError(f"Las unidades no conservan el INE (diferencia {diferencia}); no se publica.")
    publicar_carpeta(temporal, destino)
    return resumen


def puntos(tabla: pd.DataFrame, id_col: str):
    """GeoDataFrame de puntos EPSG:25830 con columna id, a partir de columnas x, y."""
    import geopandas as gpd
    return gpd.GeoDataFrame({"id": tabla[id_col].astype(str).to_numpy()},
                            geometry=gpd.points_from_xy(tabla["x"], tabla["y"]), crs="EPSG:25830")


def tiempos_pie_por_velocidad(redr5, origenes, destinos, velocidad_kmh: float, radio_min: int) -> pd.DataFrame:
    """Tiempo al centro más cercano de cada origen a una velocidad, por bloques de 10.000."""
    import datetime

    from . import red
    partes = []
    for inicio in range(0, len(origenes), BLOQUE_PIE):
        tiempos = red.matriz(redr5, origenes.iloc[inicio:inicio + BLOQUE_PIE], destinos, modos=["WALK"],
                             velocidad_kmh=velocidad_kmh, max_min=radio_min,
                             salida=datetime.datetime(2026, 11, 17, 10, 0))  # a pie no depende de la hora
        partes.append(red.minimo_por_origen(tiempos))
    minimos = pd.concat(partes, ignore_index=True)
    return minimos.rename(columns={"id": "unidad", "travel_time": acceso.columna_pie(velocidad_kmh),
                                   "to_id": f"centro_{velocidad_kmh:.1f}"})


def etapa_acceso_pie(raiz: Path, id_snapshot: str, config: dict) -> dict:
    """Tiempos a pie de cada unidad al centro de primaria más cercano, a las tres velocidades (R5).

    Engancha unidades y centros a la red (R-RED-02); los centros que no enganchan no se usan.
    Es la etapa lenta de `build` (unos 45 min, sin medir con 422 centros): necesita Java.
    """
    import time

    from . import red
    snapshot = leer_snapshot(raiz, id_snapshot)
    pbf = ruta_en_snapshot(raiz, snapshot, *ARCHIVO_OSM)
    proc = carpeta_procesados(raiz, id_snapshot)
    unidades = pd.read_parquet(proc / "demanda" / "unidades_demanda.parquet", columns=["unidad", "x", "y"])
    centros = pd.read_parquet(proc / "primaria" / "centros_primaria.parquet")
    pie = config["primaria"]["pie"]
    velocidades = [pie["velocidad_kmh"], *pie["velocidades_sensibilidad_kmh"]]
    inicio = time.monotonic()
    redr5 = red.construir_red(pbf)
    radio_enganche = red.radio_enganche_r5()
    origenes, destinos = puntos(unidades, "unidad"), puntos(centros, "centro_nro_registro")
    enganche_unidades = red.enganche(redr5, origenes, radio_enganche)
    enganche_centros = red.enganche(redr5, destinos, radio_enganche)
    destinos_ok = destinos[destinos["id"].isin(enganche_centros.loc[enganche_centros["enganchado"], "id"])]
    tabla = enganche_unidades.rename(columns={"id": "unidad"})
    tabla["recta_m"] = red.recta_al_mas_cercano_m(origenes, destinos_ok)
    segundos = {}
    for velocidad in velocidades:
        t0 = time.monotonic()
        tabla = tabla.merge(tiempos_pie_por_velocidad(redr5, origenes, destinos_ok, velocidad,
                                                      pie["radio_calculo_min"]), on="unidad", how="left")
        segundos[f"{velocidad:.1f}"] = round(time.monotonic() - t0, 1)
    destino = proc / "acceso_pie"
    temporal = preparar_temporal(destino)
    tabla.to_parquet(temporal / "tiempos_pie.parquet", index=False)
    enganche_centros.to_csv(temporal / "enganche_centros.csv", index=False, encoding="utf-8")
    resumen = {
        "etapa": "acceso_pie", "snapshot": id_snapshot, "creado_utc": ahora_utc().isoformat(),
        "manifiesto_motor": red.manifiesto_motor(pbf, [], {
            "modo": "WALK", "velocidades_kmh": velocidades, "radio_calculo_min": pie["radio_calculo_min"],
            "radio_enganche_m": radio_enganche, "snap_to_network_en_matriz": False}),
        "conteos": {"unidades": len(tabla), "unidades_sin_enganche": int((~tabla["enganchado"]).sum()),
                    "centros": len(destinos), "centros_enganchados": len(destinos_ok)},
        "segundos": {"total": round(time.monotonic() - inicio, 1), "por_velocidad": segundos},
    }
    escribir_json_atomico(temporal / "resumen.json", resumen)
    publicar_carpeta(temporal, destino)
    return resumen


def leer_matriz_transporte(proc: Path, franja: str = "9_13") -> pd.DataFrame | None:
    """Matriz de transporte de una franja (9 a 13 h: noche 1 más los centros curados), o None
    si no existe.

    Falla si alguna de sus carpetas existe pero no está completa: una matriz a medias daría
    estados falsos.
    """
    partes = []
    for nombre in CARPETAS_TRANSPORTE_FRANJA[franja]:
        carpeta = proc / "noches" / nombre
        if not carpeta.exists():
            continue
        estado = json.loads((carpeta / "estado.json").read_text(encoding="utf-8"))
        if not estado.get("completa"):
            raise ValueError(f"La matriz de transporte de {carpeta} no está completa.")
        partes += [pd.read_parquet(a) for a in sorted(carpeta.glob("bloque_*.parquet"))]
    return pd.concat(partes, ignore_index=True) if partes else None


def escenario_inventario_ampliado(proc: Path, unidades: pd.DataFrame, matriz: pd.DataFrame | None,
                                  config: dict) -> list[dict]:
    """Escenario base más los centros públicos que R-DAT-02 excluye por la dependencia funcional
    (los de `resumen.json`; cinco desde el 15/11, antes tres).

    Solo si existe `sensibilidad_inventario_ampliado/` (fases/H3_situacion_inicial_A/
    inventario_ampliado.py) y hay matriz de transporte. El escenario base no cambia.
    """
    carpeta = proc / CARPETA_INVENTARIO_AMPLIADO
    if matriz is None or not (carpeta / "resumen.json").exists():
        return []
    extra = json.loads((carpeta / "resumen.json").read_text(encoding="utf-8"))
    ampliadas = acceso.con_centros_extra(unidades, pd.read_parquet(carpeta / "tiempos_pie.parquet"))
    matriz_ampliada = pd.concat([matriz, pd.read_parquet(carpeta / "transporte.parquet")], ignore_index=True)
    base = acceso.escenarios(config)[0]
    escenario = {**base, "nombre": "inventario_ampliado", "centros_extra": extra["centros"]}
    por_modo = acceso.estados_escenario(ampliadas, acceso.mejor_por_seccion(matriz_ampliada), escenario, config)
    return acceso.resumir(ampliadas, por_modo, escenario)


def escenarios_franja_tarde(proc: Path, unidades: pd.DataFrame, matriz: pd.DataFrame | None, centros: set,
                            config: dict) -> dict:
    """Escenarios `franja_16_20` y `ambas_franjas` (D-17), o {} si no hay matriz de 16 a 20 h.

    El escenario base sigue siendo el de 9 a 13 h, para no cambiar las cifras ya verificadas.
    Supuesto declarado: los centros están abiertos en las dos franjas (SPEC §7, F-05).
    """
    tarde = leer_matriz_transporte(proc, "16_20")
    if matriz is None or tarde is None:
        return {}
    if not set(tarde["to_id"]) <= centros:
        raise ValueError("La matriz de 16 a 20 h usa centros que ya no están en primaria.")
    por_seccion = {"9_13": acceso.mejor_por_seccion(matriz), "16_20": acceso.mejor_por_seccion(tarde)}
    todos = acceso.estados_franjas(unidades, por_seccion, config)
    return {nombre: por_modo for nombre, por_modo in todos.items() if nombre != "franja_9_13"}


def etapa_acceso(raiz: Path, id_snapshot: str, config: dict) -> dict:
    """Estados de acceso a primaria por unidad y modo, y resumen por escenario (H3, sin red)."""
    proc = carpeta_procesados(raiz, id_snapshot)
    unidades = pd.read_parquet(proc / "demanda" / "unidades_demanda.parquet").merge(
        pd.read_parquet(proc / "acceso_pie" / "tiempos_pie.parquet"), on="unidad", how="left", validate="one_to_one")
    matriz = leer_matriz_transporte(proc)
    por_seccion = None if matriz is None else acceso.mejor_por_seccion(matriz)
    centros = set(pd.read_parquet(proc / "primaria" / "centros_primaria.parquet")["centro_nro_registro"])
    if matriz is not None and not set(matriz["to_id"]) <= centros:
        raise ValueError("La matriz de transporte usa centros que ya no están en primaria.")
    filas, base = [], None
    for escenario in acceso.escenarios(config):
        por_modo = acceso.estados_escenario(unidades, por_seccion, escenario, config)
        filas += acceso.resumir(unidades, por_modo, escenario)
        if escenario["nombre"] == "base":
            base = por_modo
    filas += escenario_inventario_ampliado(proc, unidades, matriz, config)
    tarde = escenarios_franja_tarde(proc, unidades, matriz, centros, config)
    for nombre, por_modo in tarde.items():
        filas += acceso.resumir(unidades, por_modo, {**acceso.escenarios(config)[0], "nombre": nombre})
    destino = proc / "acceso"
    temporal = preparar_temporal(destino)
    pd.DataFrame(filas).to_csv(temporal / "resumen_acceso.csv", index=False, encoding="utf-8")
    estados = unidades[["unidad", "cusec"]].copy()
    for modo, tabla in base.items():
        estados[f"estado_{modo}"], estados[f"motivo_{modo}"] = tabla["estado"], tabla["motivo"]
    # Columnas de la franja de tarde y de las dos franjas, solo si existe la matriz de 16 a 20 h.
    for nombre, sufijo in (("franja_16_20", "16_20"), ("ambas_franjas", "ambas")):
        if nombre in tarde:
            for modo in ("transporte", "al_menos_uno"):
                estados[f"estado_{modo}_{sufijo}"] = tarde[nombre][modo]["estado"]
                estados[f"motivo_{modo}_{sufijo}"] = tarde[nombre][modo]["motivo"]
    estados.to_parquet(temporal / "estados_base.parquet", index=False)
    acceso.por_municipio(unidades, base).to_csv(temporal / "por_municipio_base.csv", index=False, encoding="utf-8")
    comunidad = [f for f in filas if f["escenario"] == "base" and f["territorio"] == "comunidad"
                 and f["grupo_edad"] == "total"]
    resumen = {
        "etapa": "acceso", "snapshot": id_snapshot, "creado_utc": ahora_utc().isoformat(),
        "config": config, "transporte": "matriz" if matriz is not None else "sin motor (R-RED-05)",
        "carpetas_transporte": [n for c in CARPETAS_TRANSPORTE_FRANJA.values() for n in c
                                if (proc / "noches" / n).exists()],
        "franjas_transporte": ["9_13"] + (["16_20"] if tarde else []),
        "base_comunidad_total": {f["modo"]: {e: round(f[e]) for e in acceso.ESTADOS} for f in comunidad},
    }
    escribir_json_atomico(temporal / "resumen.json", resumen)
    publicar_carpeta(temporal, destino)
    return resumen


def leer_refugios() -> pd.DataFrame:
    """Los 43 mercados curados con coordenadas (EPSG:25830); la que falta sale del archivo de OSM."""
    mercados = pd.read_csv(ARCHIVO_REFUGIOS_MERCADOS, dtype=str, keep_default_na=False)
    osm = pd.read_csv(ARCHIVO_REFUGIOS_COORDENADAS, dtype=str, keep_default_na=False).set_index("pk")
    for eje in ("x", "y"):
        columna = f"coordenada_{eje}"
        mercados[eje] = pd.to_numeric(mercados[columna].where(mercados[columna] != "", mercados["pk"].map(osm[columna])))
    if mercados[["x", "y"]].isna().any().any():
        raise ValueError("Hay refugios sin coordenadas.")
    return mercados


def etapa_refugios_pie(raiz: Path, id_snapshot: str, config: dict) -> dict:
    """Pares unidad-refugio a pie (R5) a `UMBRAL_MAX_REFUGIOS` min o menos, a las tres velocidades.

    Solo unidades del territorio con lista oficial verificada (hoy, Madrid capital).
    """
    import datetime
    import time

    from . import red, refugios
    snapshot = leer_snapshot(raiz, id_snapshot)
    pbf = ruta_en_snapshot(raiz, snapshot, *ARCHIVO_OSM)
    proc = carpeta_procesados(raiz, id_snapshot)
    unidades = pd.read_parquet(proc / "demanda" / "unidades_demanda.parquet", columns=["unidad", "cusec", "x", "y"])
    unidades = unidades[refugios.territorio_b(unidades)]
    mercados = leer_refugios()
    pie = config["primaria"]["pie"]
    velocidades = [pie["velocidad_kmh"], *pie["velocidades_sensibilidad_kmh"]]
    inicio = time.monotonic()
    redr5 = red.construir_red(pbf)
    enganche = red.enganche(redr5, puntos(mercados, "pk"), red.radio_enganche_r5())
    partes = []
    for velocidad in velocidades:
        for desde in range(0, len(unidades), BLOQUE_PIE):
            tiempos = red.matriz(redr5, puntos(unidades.iloc[desde:desde + BLOQUE_PIE], "unidad"),
                                 puntos(mercados, "pk"), modos=["WALK"], velocidad_kmh=velocidad,
                                 max_min=UMBRAL_MAX_REFUGIOS, salida=datetime.datetime(2026, 7, 14, 12, 0))
            cerca = tiempos.dropna(subset=["travel_time"])
            partes.append(pd.DataFrame({"unidad": cerca["from_id"], "refugio": cerca["to_id"],
                                        "minutos": cerca["travel_time"], "velocidad_kmh": velocidad}))
    pares = pd.concat(partes, ignore_index=True)
    destino = proc / "refugios_pie"
    temporal = preparar_temporal(destino)
    pares.to_parquet(temporal / "pares.parquet", index=False)
    enganche.to_csv(temporal / "enganche_refugios.csv", index=False, encoding="utf-8")
    resumen = {
        "etapa": "refugios_pie", "snapshot": id_snapshot, "creado_utc": ahora_utc().isoformat(),
        "refugios": {"archivo": "curado/refugios_mercados_madrid.csv", "sha256": sha256_archivo(ARCHIVO_REFUGIOS_MERCADOS),
                     "coordenadas_osm": "curado/refugios_coordenadas_osm.csv"},
        "manifiesto_motor": red.manifiesto_motor(pbf, [], {"modo": "WALK", "velocidades_kmh": velocidades,
                                                           "max_min": UMBRAL_MAX_REFUGIOS}),
        "conteos": {"unidades": len(unidades), "refugios": len(mercados),
                    "refugios_enganchados": int(enganche["enganchado"].sum()), "pares": len(pares)},
        "segundos": round(time.monotonic() - inicio, 1),
    }
    escribir_json_atomico(temporal / "resumen.json", resumen)
    publicar_carpeta(temporal, destino)
    return resumen


def escenarios_b(config: dict) -> list[dict]:
    """Base (3,0 km/h, 10 min) con sus cuatro cotas y sensibilidades de umbral y velocidad (cota central)."""
    pie = config["primaria"]["pie"]
    b = config["refugios"]
    base = {"velocidad_kmh": pie["velocidad_kmh"], "umbral_min": b["umbral_min"]}
    lista = [{"nombre": f"base_{cota}", "cota": cota, **base} for cota in ("acreditable", "inferior", "central", "superior")]
    lista += [{"nombre": f"umbral_{u}", "cota": "central", **base, "umbral_min": u} for u in b["umbrales_sensibilidad_min"]]
    lista += [{"nombre": f"velocidad_{v}", "cota": "central", **base, "velocidad_kmh": v}
              for v in pie["velocidades_sensibilidad_kmh"]]
    return lista


def etapa_refugios(raiz: Path, id_snapshot: str, config: dict) -> dict:
    """B por unidad, tipo de día y hora con cotas; métricas de D-24; C con A (H4, sin red)."""
    from . import horarios, refugios
    proc = carpeta_procesados(raiz, id_snapshot)
    # «Sin conexión» con el mismo criterio que A: sin enganche o con fallo de enlace a pie (R-RED-02).
    estados_a_base = pd.read_parquet(proc / "acceso" / "estados_base.parquet")[["unidad", "estado_pie"]]
    unidades = pd.read_parquet(proc / "demanda" / "unidades_demanda.parquet").merge(
        estados_a_base, on="unidad", validate="one_to_one")
    unidades["enganchado"] = unidades["estado_pie"] != acceso.NO_EVAL
    pares = pd.read_parquet(proc / "refugios_pie" / "pares.parquet")
    estados_ref = horarios.tabla_estados(leer_refugios()).assign(acceso_verificado=False)  # D-33: no_consta
    territorio = refugios.territorio_b(unidades)
    por_hora, resumen, central = [], [], None
    for esc in escenarios_b(config):
        pares_v = pares[pares["velocidad_kmh"] == esc["velocidad_kmh"]]
        tabla = refugios.estados_b(unidades, pares_v, estados_ref, esc["umbral_min"], esc["cota"], territorio)
        # Denominadores por territorio: la Comunidad (con lo no evaluable por inventario) y Madrid capital.
        for nombre_territorio, mascara in acceso.territorios(unidades).items():
            if nombre_territorio == "resto":
                continue
            subconjunto = unidades[mascara.to_numpy()]
            filas_hora, filas_resumen = refugios.metricas_b(tabla[tabla["unidad"].isin(subconjunto["unidad"])],
                                                            subconjunto, {**esc, "territorio": nombre_territorio})
            por_hora += filas_hora
            resumen += filas_resumen
        if esc["nombre"] == "base_central":
            central = tabla
    # Franja de referencia de C: la peor hora del laborable de julio, cota central, población total.
    ref = next(f for f in resumen if f["nombre"] == "base_central" and f["grupo_edad"] == "total"
               and f["tipo_dia"] == "laborable_julio" and f["territorio"] == "madrid_capital")
    b_ref = central[(central["tipo_dia"] == "laborable_julio") & (central["hora"] == ref["peor_hora"])][
        ["unidad", "estado", "motivo"]]
    estados_a = pd.read_parquet(proc / "acceso" / "estados_base.parquet")
    filas_c, filas_c_hora = [], []
    for modo in ("pie", "transporte"):
        a = estados_a[["unidad", f"estado_{modo}", f"motivo_{modo}"]].rename(
            columns={f"estado_{modo}": "estado", f"motivo_{modo}": "motivo"})
        c = refugios.estados_c(a, b_ref).merge(unidades, on="unidad")
        union = refugios.union_con_acceso(a, b_ref).reindex(unidades["unidad"]).to_numpy()
        for grupo, columna in GRUPOS_C.items():
            por_estado = c.groupby("estado")[columna].sum()
            filas_c.append({"modo_a": modo, "grupo_edad": grupo, "franja_b": f"laborable_julio {ref['peor_hora']}-{ref['peor_hora'] + 1} h",
                            **{e: float(por_estado.get(e, 0.0)) for e in ("carencia_coincidente", "sin_coincidencia", "no_evaluable")},
                            "con_acceso_a_o_b": float(unidades.loc[union, columna].sum()),
                            "denominador": float(unidades[columna].sum()), "unidad_medida": "personas"})
        # Sensibilidad de C a la franja de B: cada tipo de día y hora (cota central).
        filas_c_hora += [{"modo_a": modo, **f} for f in refugios.c_por_hora(a, central, unidades, GRUPOS_C)]
    destino = proc / "refugios"
    temporal = preparar_temporal(destino)
    pd.DataFrame(filas_c_hora).to_csv(temporal / "c_por_hora.csv", index=False, encoding="utf-8")
    pd.DataFrame(por_hora).to_csv(temporal / "b_por_hora.csv", index=False, encoding="utf-8")
    pd.DataFrame(resumen).to_csv(temporal / "b_resumen.csv", index=False, encoding="utf-8")
    pd.DataFrame(filas_c).to_csv(temporal / "c_resumen.csv", index=False, encoding="utf-8")
    central.to_parquet(temporal / "b_estados_base_central.parquet", index=False)
    resumen_json = {
        "etapa": "refugios", "snapshot": id_snapshot, "creado_utc": ahora_utc().isoformat(),
        "territorio_b": "Madrid capital (D-28); Coslada fuera del cálculo público (D-30)",
        "supuesto_acceso": "D-33: acceso estimado dentro del horario comercial; acceso_zona_climatizada = no_consta",
        "franja_referencia_c": ref["peor_hora"], "config_refugios": config["refugios"],
    }
    escribir_json_atomico(temporal / "resumen.json", resumen_json)
    publicar_carpeta(temporal, destino)
    return resumen_json


def etapa_refugios_ampliados(raiz: Path, id_snapshot: str, config: dict) -> dict:
    """Refugios ampliados (decisión del usuario del 22/11/2026; módulo `refugios_ampliados`).

    Reúne los espacios con su tipo, nivel de evidencia y fuente; calcula a pie (R5, velocidad y umbral de la base de
    B) los pares unidad-espacio de Madrid capital y las tres líneas de cobertura; prepara las capas aparte de parques
    y de refresco. Escribe solo en `refugios_ampliados/`: no toca ninguna otra etapa.
    """
    import datetime
    import time

    from pyproj import Transformer

    from . import horarios, red, refugios
    from . import refugios_ampliados as ra
    inicio = time.monotonic()
    snapshot = leer_snapshot(raiz, id_snapshot)
    pbf = ruta_en_snapshot(raiz, snapshot, *ARCHIVO_OSM)
    proc = carpeta_procesados(raiz, id_snapshot)
    contorno = ra.contorno_madrid(ruta_en_snapshot(raiz, snapshot, *ARCHIVO_SECCIONES))
    anexo = pd.read_csv(ra.ANEXO_CURADO, dtype=str, keep_default_na=False)
    zip_pc = ruta_en_snapshot(raiz, snapshot, "madrid_proteccion_civil", "RECURSOS_PROTECCION_CIVIL.zip")
    csvs = {clave: ra.leer_csv_madrid(ra.ruta_equipamientos(raiz, clave)) for clave in ra.EQUIPAMIENTOS}
    csvs.update({clave: ra.leer_csv_madrid(ra.ruta_catalogo(raiz, fuente)) for clave, fuente in ra.CSV_CATALOGO.items()})
    osm = ra.leer_osm(pbf, contorno, ra.BUSCADOS_OSM)
    mercados = leer_refugios()
    tabla = ra.espacios(mercados, anexo, ra.coordenadas_proteccion_civil(zip_pc), csvs,
                        osm[osm["tipo"].isin(ra.TIPOS_OSM_ESPACIO)], ra.espacios_museos_por_nombre(pbf, contorno))
    a_wgs84 = Transformer.from_crs("EPSG:25830", "EPSG:4326", always_xy=True)
    tabla["lon"], tabla["lat"] = a_wgs84.transform(tabla["x"].to_numpy(), tabla["y"].to_numpy())
    agua = ra.refresco(ra.leer_csv_madrid(ra.ruta_catalogo(raiz, "madrid_fuentes"), "utf-8-sig"),
                       ra.leer_csv_madrid(ra.ruta_catalogo(raiz, "madrid_piscinas")))
    agua["lon"], agua["lat"] = a_wgs84.transform(agua["x"].to_numpy(), agua["y"].to_numpy())
    # Zonas verdes de toda la Comunidad (decisión del usuario del 23/11/2026): lectura aparte del PBF completo.
    contorno_comunidad = ra.contorno_comunidad(ruta_en_snapshot(raiz, snapshot, *ARCHIVO_SECCIONES))
    verdes = ra.zonas_verdes(ra.leer_verdes_osm(pbf, contorno_comunidad), contorno_comunidad)
    # Bibliotecas públicas del resto de la Comunidad (usuario, 23/11/2026): solo mapa; no son destino de R5.
    municipios = ra.municipios_comunidad(ruta_en_snapshot(raiz, snapshot, *ARCHIVO_SECCIONES))
    bibliotecas_cm, bibliotecas_sin_ubicar = ra.casar_bibliotecas(
        ra.bibliotecas_publicas_cm(ra.leer_csv_madrid(ra.ruta_catalogo(raiz, "cm_bibliotecas"))),
        ra.leer_bibliotecas_osm(pbf, municipios), municipios)
    bibliotecas_cm["lon"], bibliotecas_cm["lat"] = a_wgs84.transform(bibliotecas_cm["x"].to_numpy(),
                                                                     bibliotecas_cm["y"].to_numpy())
    # Unidades y «sin conexión» con el mismo criterio que la etapa `refugios`.
    estados_a_base = pd.read_parquet(proc / "acceso" / "estados_base.parquet")[["unidad", "estado_pie"]]
    unidades = pd.read_parquet(proc / "demanda" / "unidades_demanda.parquet").merge(
        estados_a_base, on="unidad", validate="one_to_one")
    unidades["enganchado"] = unidades["estado_pie"] != acceso.NO_EVAL
    origenes = unidades[refugios.territorio_b(unidades)]
    umbral, velocidad = config["refugios"]["umbral_min"], config["primaria"]["pie"]["velocidad_kmh"]
    redr5 = red.construir_red(pbf)
    destinos = puntos(tabla, "id")
    enganche = red.enganche(redr5, destinos, red.radio_enganche_r5())
    partes = []
    for desde in range(0, len(origenes), BLOQUE_PIE):
        # Mismo tope que `refugios_pie`: con el tope igual al umbral (10), R5 perdía pares de 10 min justos y la
        # línea «verificados» no reproducía la base (REGISTRO-FALLOS 49). El umbral se aplica después, al contar.
        tiempos = red.matriz(redr5, puntos(origenes.iloc[desde:desde + BLOQUE_PIE], "unidad"), destinos,
                             modos=["WALK"], velocidad_kmh=velocidad, max_min=UMBRAL_MAX_REFUGIOS,
                             salida=datetime.datetime(2026, 7, 14, 12, 0))
        cerca = tiempos.dropna(subset=["travel_time"])
        partes.append(pd.DataFrame({"unidad": cerca["from_id"], "refugio": cerca["to_id"],
                                    "minutos": cerca["travel_time"]}))
    pares = pd.concat(partes, ignore_index=True)
    curados = pd.read_csv(ra.HORARIOS_CURADOS, dtype=str, keep_default_na=False)
    estados_mercados = horarios.tabla_estados(mercados).assign(acceso_verificado=False)   # D-33
    lineas, _ = ra.lineas_cobertura(unidades, pares, ra.estados_por_linea(tabla, estados_mercados, curados), umbral)
    comprobacion = comprobar_linea_verificados(proc, lineas)
    destino = proc / "refugios_ampliados"
    temporal = preparar_temporal(destino)
    tabla.to_parquet(temporal / "espacios.parquet", index=False)
    agua.to_parquet(temporal / "refresco.parquet", index=False)
    verdes.to_parquet(temporal / "parques.parquet", index=False)
    bibliotecas_cm.to_parquet(temporal / "bibliotecas_comunidad.parquet", index=False)
    bibliotecas_sin_ubicar.to_csv(temporal / "bibliotecas_comunidad_sin_ubicar.csv", index=False, encoding="utf-8")
    pares.to_parquet(temporal / "pares.parquet", index=False)
    enganche.to_csv(temporal / "enganche_espacios.csv", index=False, encoding="utf-8")
    pd.DataFrame(lineas).to_csv(temporal / "lineas.csv", index=False, encoding="utf-8")
    resumen = {
        "etapa": "refugios_ampliados", "snapshot": id_snapshot, "creado_utc": ahora_utc().isoformat(),
        "decision": "Usuario, 22/11/2026 (fases/PLAN_ENTREGA_20261114.md, tabla de decisiones; amplía D-12)",
        "territorio": "Madrid capital", "umbral_min": umbral, "velocidad_kmh": velocidad,
        "conteos": {"espacios": len(tabla), "por_tipo_y_nivel": ra.conteos(tabla),
                    "refresco": {k: int(v) for k, v in agua["tipo"].value_counts().items()},
                    "parques": len(verdes),
                    "parques_por_clase": {k: int(v) for k, v in verdes["clase"].value_counts().items()},
                    "territorio_parques": "Comunidad de Madrid",
                    "bibliotecas_comunidad": {"ubicadas_por_calidad": {k: int(v) for k, v in
                                                                       bibliotecas_cm["calidad"].value_counts().items()},
                                              "sin_ubicar_por_motivo": {k: int(v) for k, v in
                                                                        bibliotecas_sin_ubicar["motivo"].value_counts().items()}},
                    "pares": len(pares), "unidades_origen": len(origenes),
                    "espacios_enganchados": int(enganche["enganchado"].sum()), "horarios_curados": len(curados)},
        "comprobacion_verificados": comprobacion,
        "fuentes": {"curado": {p.name: sha256_archivo(p) for p in (ra.HORARIOS_CURADOS, ra.ANEXO_CURADO)},
                    "crudos": {p.name: sha256_archivo(p) for p in ra.archivos_externos(raiz)}},
        "manifiesto_motor": red.manifiesto_motor(pbf, [], {"modo": "WALK", "velocidad_kmh": velocidad, "umbral_min": umbral,
                                                           "max_min": UMBRAL_MAX_REFUGIOS}),
        "segundos": round(time.monotonic() - inicio, 1),
    }
    escribir_json_atomico(temporal / "resumen.json", resumen)
    publicar_carpeta(temporal, destino)
    return resumen


def comprobar_linea_verificados(proc: Path, lineas: list[dict]) -> dict:
    """La línea «verificados» debe reproducir la base de B (etapa `refugios`): peor hora, laborable de julio, total."""
    base = pd.read_csv(proc / "refugios" / "b_resumen.csv")
    fila = base[(base["nombre"] == "base_central") & (base["territorio"] == "madrid_capital")
                & (base["grupo_edad"] == "total") & (base["tipo_dia"] == "laborable_julio")].iloc[0]
    nueva = next(f for f in lineas if f["linea"] == "verificados" and f["cota"] == "central"
                 and f["grupo_edad"] == "total" and f["tipo_dia"] == "laborable_julio")
    anterior = float(fila["con_acceso_peor_hora"])
    return {"refugios_b_resumen": anterior, "linea_verificados": nueva["con_acceso_peor_hora"],
            "coincide": abs(anterior - nueva["con_acceso_peor_hora"]) < 0.5}


def etapa_renta(raiz: Path, id_snapshot: str) -> dict:
    """A y C por quintil de renta de la sección (ADRH 2024; D-16), sin índice compuesto.

    A: Comunidad, por modo (escenario base). C: con A en cada modo y B en la franja de
    referencia, por quintil, en la población total, 65+ y 75+.
    """
    from . import refugios, renta
    proc = carpeta_procesados(raiz, id_snapshot)
    ruta = renta.ruta_adrh(raiz)
    sha = renta.comprobar_manifiesto(ruta)
    unidades = pd.read_parquet(proc / "demanda" / "unidades_demanda.parquet")
    secciones = renta.quintiles_seccion(renta.leer_adrh(ruta), unidades)
    unidades = unidades.merge(secciones[["cusec", "quintil_renta"]], on="cusec", validate="many_to_one")
    estados = unidades[["unidad"]].merge(pd.read_parquet(proc / "acceso" / "estados_base.parquet"), on="unidad",
                                         validate="one_to_one")
    grupos = {"total": "poblacion_total", "65+": "poblacion_65_mas", "75+": "poblacion_75_mas"}
    filas_a = [{"modo": modo, "grupo_edad": grupo, **fila}
               for modo in acceso.MODOS for grupo, columna in grupos.items()
               for fila in renta.por_quintil(unidades, estados[f"estado_{modo}"], columna, acceso.ESTADOS)]
    filas_c = []
    resumen_b = json.loads((proc / "refugios" / "resumen.json").read_text(encoding="utf-8"))
    central = pd.read_parquet(proc / "refugios" / "b_estados_base_central.parquet")
    ref = central[(central["tipo_dia"] == "laborable_julio") & (central["hora"] == resumen_b["franja_referencia_c"])]
    for modo in ("pie", "transporte"):
        a = estados[["unidad", f"estado_{modo}", f"motivo_{modo}"]].rename(
            columns={f"estado_{modo}": "estado", f"motivo_{modo}": "motivo"})
        c = refugios.estados_c(a, ref[["unidad", "estado", "motivo"]]).set_index("unidad")["estado"]
        estado_c = unidades["unidad"].map(c)
        filas_c += [{"modo_a": modo, "grupo_edad": grupo, **fila} for grupo, columna in grupos.items()
                    for fila in renta.por_quintil(unidades, estado_c, columna,
                                                  ("carencia_coincidente", "sin_coincidencia", acceso.NO_EVAL))]
    destino = proc / "renta"
    temporal = preparar_temporal(destino)
    secciones.to_csv(temporal / "quintiles_seccion.csv", index=False, encoding="utf-8")
    pd.DataFrame(filas_a).to_csv(temporal / "a_por_renta.csv", index=False, encoding="utf-8")
    pd.DataFrame(filas_c).to_csv(temporal / "c_por_renta.csv", index=False, encoding="utf-8")
    resumen = {"etapa": "renta", "snapshot": id_snapshot, "creado_utc": ahora_utc().isoformat(),
               "fuente": {"archivo": "crudos/ine_adrh_2024/adrh_madrid_2024_completo.json", "sha256": sha,
                          "indicador": "dato1, renta neta media por persona (euros)", "licencia": "CC BY 4.0 (INE)"},
               "conteos": {"secciones": len(secciones),
                           "calidad": secciones["calidad_renta"].value_counts().to_dict(),
                           "poblacion_por_quintil": unidades.groupby("quintil_renta")["poblacion_total"].sum()
                           .round(0).to_dict()}}
    escribir_json_atomico(temporal / "resumen.json", resumen)
    publicar_carpeta(temporal, destino)
    return resumen


def etapa_contexto(raiz: Path, id_snapshot: str) -> dict:
    """Capas de contexto de Madrid capital (D-16): personas solas por barrio e IGUALA por distrito.

    Lee de `crudos/` con comprobación del SHA-256 contra su manifiesto (no están en la versión de
    datos) y la capa de la app (`app/`) para poner al lado las cifras de A y C de cada barrio.
    """
    import geopandas as gpd

    from . import contexto, renta
    proc = carpeta_procesados(raiz, id_snapshot)
    rutas = {n: raiz / "crudos" / a / b for n, (a, b) in
             (("solas", contexto.ARCHIVO_SOLAS), ("iguala", contexto.ARCHIVO_IGUALA), ("barrios", contexto.ARCHIVO_BARRIOS))}
    hashes = {n: renta.comprobar_manifiesto(r) for n, r in rutas.items()}
    capa = pd.read_parquet(proc / "app" / "unidades_mapa.parquet")
    capital = capa[capa["cusec"].str.startswith(acceso.MADRID_CAPITAL)]
    unidades = pd.read_parquet(proc / "demanda" / "unidades_demanda.parquet", columns=["unidad", "x", "y"])
    unidades = unidades[unidades["unidad"].isin(capital["unidad"])]
    estados = capital[["unidad", "poblacion_total", "poblacion_65_mas", "estado_pie", "estado_transporte",
                       "estado_b", "estado_c_pie", "estado_c_transporte"]]
    barrios = gpd.read_file(f"zip://{rutas['barrios']}")
    tabla = contexto.tabla_barrios(unidades, estados, contexto.personas_solas(rutas["solas"]), barrios)
    iguala = contexto.iguala_distritos(rutas["iguala"])
    destino = proc / "contexto"
    temporal = preparar_temporal(destino)
    tabla.to_csv(temporal / "barrios.csv", index=False, encoding="utf-8")
    iguala.to_csv(temporal / "iguala_distritos.csv", index=False, encoding="utf-8")
    contexto.prueba_integracion(tabla).to_csv(temporal / "prueba_integracion.csv", index=False, encoding="utf-8")
    resumen = {"etapa": "contexto", "snapshot": id_snapshot, "creado_utc": ahora_utc().isoformat(),
               "fuentes_sha256": hashes, "uso": "solo contexto (D-16); no interviene en ningún cálculo",
               "conteos": {"barrios": len(tabla), "barrios_con_personas_solas": int(tabla["solas_total"].notna().sum()),
                           "poblacion_capital_asignada": round(float(tabla["poblacion_total"].sum())),
                           "poblacion_capital": round(float(capital["poblacion_total"].sum())),
                           "iguala_anio": int(iguala["Fecha datos"].iloc[0]), "distritos_iguala": len(iguala)}}
    escribir_json_atomico(temporal / "resumen.json", resumen)
    publicar_carpeta(temporal, destino)
    return resumen


def etapa_candidatos_pie(raiz: Path, id_snapshot: str, config: dict) -> dict:
    """Candidatos de A (D-15) y pares unidad-candidato a pie (R5) para las unidades sin opción a pie.

    Fila 6 de PLAN_CALCULOS.md. Orígenes: unidades `sin_opcion_verificada` a pie en el escenario
    base. Destinos: los candidatos. Se guardan los pares hasta `max_pares_candidatos_min`.
    """
    import datetime
    import time

    from . import actuaciones, red
    snapshot = leer_snapshot(raiz, id_snapshot)
    pbf = ruta_en_snapshot(raiz, snapshot, *ARCHIVO_OSM)
    proc = carpeta_procesados(raiz, id_snapshot)
    unidades = pd.read_parquet(proc / "demanda" / "unidades_demanda.parquet")
    estados = pd.read_parquet(proc / "acceso" / "estados_base.parquet")
    estado_pie = unidades[["unidad"]].merge(estados, on="unidad", how="left")["estado_pie"]
    tabla_candidatos = actuaciones.candidatos(unidades, estado_pie)
    sin = unidades[(estado_pie == acceso.SIN).to_numpy()]
    maximo = config["actuaciones"]["max_pares_candidatos_min"]
    inicio = time.monotonic()
    redr5 = red.construir_red(pbf)
    partes = []
    for desde in range(0, len(sin), BLOQUE_PIE):
        tiempos = red.matriz(redr5, puntos(sin.iloc[desde:desde + BLOQUE_PIE], "unidad"),
                             puntos(tabla_candidatos, "candidato"), modos=["WALK"],
                             velocidad_kmh=config["primaria"]["pie"]["velocidad_kmh"], max_min=maximo,
                             salida=datetime.datetime(2026, 11, 17, 10, 0))
        cerca = tiempos.dropna(subset=["travel_time"])
        partes.append(pd.DataFrame({"unidad": cerca["from_id"], "candidato": cerca["to_id"],
                                    "minutos": cerca["travel_time"]}))
    pares = pd.concat(partes, ignore_index=True)
    destino = proc / "candidatos_pie"
    temporal = preparar_temporal(destino)
    tabla_candidatos.to_parquet(temporal / "candidatos.parquet", index=False)
    pares.to_parquet(temporal / "pares.parquet", index=False)
    resumen = {"etapa": "candidatos_pie", "snapshot": id_snapshot, "creado_utc": ahora_utc().isoformat(),
               "manifiesto_motor": red.manifiesto_motor(pbf, [], {"modo": "WALK", "max_min": maximo,
                                                                  "velocidad_kmh": config["primaria"]["pie"]["velocidad_kmh"]}),
               "conteos": {"candidatos": len(tabla_candidatos), "unidades_sin_opcion_pie": len(sin), "pares": len(pares)},
               "segundos": round(time.monotonic() - inicio, 1)}
    escribir_json_atomico(temporal / "resumen.json", resumen)
    publicar_carpeta(temporal, destino)
    return resumen


def carteras_a(unidades: pd.DataFrame, estado_pie: pd.Series, pares: pd.DataFrame, cand: pd.DataFrame,
               config: dict) -> list[dict]:
    """MILP de A a pie y regla simple, por objetivo (total y 65+) y tamaño de cartera; con robustez."""
    from . import actuaciones, optimizacion
    cfg, pie = config["actuaciones"], config["primaria"]["pie"]
    sin = unidades[(estado_pie == acceso.SIN).to_numpy()]
    filas = []
    for objetivo, columna, local in (("total", "poblacion_total", "sin_opcion_pie_total"),
                                     ("65+", "poblacion_65_mas", "sin_opcion_pie_65")):
        cubre = actuaciones.conjuntos_cobertura(pares, sin["unidad"], pie["umbral_min"])
        pesos = sin[columna].to_numpy()
        for k in cfg["carteras_a"]:
            milp_a = optimizacion.cobertura_maxima(cubre, pesos, k, cfg["limite_solver_s"])
            regla = optimizacion.regla_simple(dict(zip(cand["candidato"], cand[local], strict=True)), k)
            fila = {"objetivo": objetivo, "k": k, **{f"milp_{c}": v for c, v in milp_a.items()},
                    "regla_simple_elegidos": regla, "regla_simple_ganancia": optimizacion.ganancia_de(cubre, pesos, regla)}
            for velocidad in pie["velocidades_sensibilidad_kmh"]:
                fila[f"robustez_ganancia_{velocidad}"] = ganancia_a_velocidad(
                    unidades, pares, milp_a["elegidos"], velocidad, pie, columna)
            problemas = {"base": (cubre, pesos)}
            problemas.update({f"velocidad_{v}": problema_a_pie_velocidad(unidades, pares, v, pie, columna)
                              for v in pie["velocidades_sensibilidad_kmh"]})
            fila.update(robustez_completa(problemas, milp_a["elegidos"], k, cfg["limite_solver_s"]))
            filas.append(fila)
    return filas


def problema_a_pie_velocidad(unidades: pd.DataFrame, pares: pd.DataFrame, velocidad: float, pie: dict,
                             columna: str) -> tuple[list[frozenset], np.ndarray]:
    """Conjuntos de cobertura y pesos de A a pie a otra velocidad (tiempos reescalados desde 3,0 km/h,
    como `ganancia_a_velocidad`; a 2,4 km/h es una cota inferior)."""
    from . import actuaciones
    sin_v = unidades[(unidades[acceso.columna_pie(velocidad)].isna()
                      | (unidades[acceso.columna_pie(velocidad)] > pie["umbral_min"])).to_numpy()]
    escalados = pares.assign(minutos=pares["minutos"] * pie["velocidad_kmh"] / velocidad)
    return actuaciones.conjuntos_cobertura(escalados, sin_v["unidad"], pie["umbral_min"]), sin_v[columna].to_numpy()


def ganancia_a_velocidad(unidades: pd.DataFrame, pares: pd.DataFrame, elegidos: list, velocidad: float, pie: dict,
                         columna: str) -> float:
    """Ganancia de una cartera fija a otra velocidad (robustez, SPEC §9).

    El estado sin la cartera es el de esa velocidad. El tiempo a un candidato se reescala desde
    3,0 km/h (R5: distancia / velocidad; aproximación por el redondeo a minutos). Solo se conocen
    los pares de las unidades sin opción a 3,0 km/h, que incluyen a todas las sin opción a 3,6.
    A 2,4 km/h, las unidades que pierden el acceso base no tienen pares y no se cuentan: la
    ganancia es una cota inferior.
    """
    sin_v = unidades[(unidades[acceso.columna_pie(velocidad)].isna()
                      | (unidades[acceso.columna_pie(velocidad)] > pie["umbral_min"])).to_numpy()]
    factor = pie["velocidad_kmh"] / velocidad
    cerca = pares[pares["candidato"].isin(elegidos) & (pares["minutos"] * factor <= pie["umbral_min"])]
    return float(sin_v.loc[sin_v["unidad"].isin(cerca["unidad"]), columna].sum())


def leer_candidatos_tp(proc: Path, franja: str) -> pd.DataFrame | None:
    """Pares sección-candidato en transporte de una franja (noche 2), o None si no existen.
    Falla si la carpeta existe pero no está completa."""
    carpeta = proc / "noches" / f"candidatos_tp_{franja}"
    if not (carpeta / "estado.json").exists():
        return None
    if not json.loads((carpeta / "estado.json").read_text(encoding="utf-8")).get("completa"):
        raise ValueError(f"Los candidatos en transporte de {carpeta} no están completos.")
    return pd.concat([pd.read_parquet(a) for a in sorted(carpeta.glob("bloque_*.parquet"))], ignore_index=True)


def escenarios_tp_actuaciones(config: dict, hay_tarde: bool) -> list[dict]:
    """Escenarios en los que se evalúa la cartera de A en transporte (robustez, SPEC §9).

    El base (9 a 13 h, p50, sin margen) es el que optimiza el MILP. Los demás solo evalúan las
    carteras ya elegidas: p80, márgenes de sesgo de la matriz urbana y, si está calculada, la
    franja de 16 a 20 h.
    """
    base = {**acceso.escenarios(config)[0], "nombre": "base", "franja": "9_13"}
    lista = [base, {**base, "nombre": "tp_p80", "percentil_tp": 80}]
    lista += [{**base, "nombre": f"tp_margen_{m}", "margen_tp_min": m}
              for m in config["primaria"]["transporte"]["margenes_sesgo_min"]]
    if hay_tarde:
        lista.append({**base, "nombre": "franja_16_20", "franja": "16_20"})
    return lista


def problema_a_transporte(unidades: pd.DataFrame, matrices: dict, pares_pie: pd.DataFrame, pares_tp: dict,
                          escenario: dict, config: dict) -> tuple[pd.DataFrame, list[frozenset]]:
    """Unidades sin opción en transporte en un escenario y sus conjuntos de candidatos."""
    from . import actuaciones
    franja = escenario["franja"]
    por_modo = acceso.estados_escenario(unidades, acceso.mejor_por_seccion(matrices[franja]), escenario, config)
    sin = unidades[(por_modo["transporte"]["estado"] == acceso.SIN).to_numpy()]
    cubre = actuaciones.conjuntos_cobertura_transporte(sin, pares_pie, pares_tp[franja], escenario["umbral_tp_min"],
                                                       escenario["percentil_tp"], escenario["margen_tp_min"])
    return sin, cubre


def carteras_a_transporte(proc: Path, unidades: pd.DataFrame, estado_pie: pd.Series, pares_pie: pd.DataFrame,
                          cand: pd.DataFrame, carteras_pie: list[dict], config: dict) -> list[dict]:
    """MILP de A en transporte (9 a 13 h), con regla simple, cartera a pie y robustez.

    Devuelve [] si no están los pares en transporte de la noche 2 (`candidatos_tp_9_13`).
    Para cada objetivo (total y 65+) y tamaño k:
    - el MILP elige la cartera en el escenario base (candidatos equivalentes fusionados);
    - la regla simple toma los k candidatos con más población sin opción en transporte en su celda;
    - la cartera óptima a pie (misma k y objetivo) se evalúa en transporte, y la de transporte a pie;
    - la cartera de transporte se evalúa en los escenarios de robustez.
    """
    from . import actuaciones, optimizacion
    pares_tp = {f: leer_candidatos_tp(proc, f) for f in ("9_13", "16_20")}
    if pares_tp["9_13"] is None:
        return []
    matrices = {"9_13": leer_matriz_transporte(proc)}
    hay_tarde = pares_tp["16_20"] is not None and (proc / "noches" / "transporte_16_20").exists()
    if hay_tarde:
        matrices["16_20"] = leer_matriz_transporte(proc, "16_20")
    cfg, pie = config["actuaciones"], config["primaria"]["pie"]
    escenarios = escenarios_tp_actuaciones(config, hay_tarde)
    problemas = {e["nombre"]: problema_a_transporte(unidades, matrices, pares_pie, pares_tp, e, config)
                 for e in escenarios}
    # Robustez frente al inventario: con los centros de la vía patrimonial del SERMAS que R-DAT-02
    # excluye (si están calculados), parte de la población deja de estar sin opción (p. ej.
    # Sevilla la Nueva) y una zona elegida allí deja de aportar.
    carpeta = proc / CARPETA_INVENTARIO_AMPLIADO
    if (carpeta / "resumen.json").exists():
        ampliadas = acceso.con_centros_extra(unidades, pd.read_parquet(carpeta / "tiempos_pie.parquet"))
        matrices_amp = {"9_13": pd.concat([matrices["9_13"], pd.read_parquet(carpeta / "transporte.parquet")],
                                          ignore_index=True)}
        problemas["inventario_ampliado"] = problema_a_transporte(ampliadas, matrices_amp, pares_pie, pares_tp,
                                                                 escenarios[0], config)
    sin, cubre = problemas["base"]
    sin_pie = unidades[(estado_pie == acceso.SIN).to_numpy()]
    cubre_pie = actuaciones.conjuntos_cobertura(pares_pie, sin_pie["unidad"], pie["umbral_min"])
    filas = []
    for objetivo, columna in (("total", "poblacion_total"), ("65+", "poblacion_65_mas")):
        pesos = sin[columna].to_numpy()
        # Regla simple: población sin opción en transporte dentro de la celda de cada candidato.
        celda = actuaciones.celda_candidato(sin)
        poblacion_celda = sin.groupby(celda)[columna].sum().to_dict()
        prioridad = dict(zip(cand["candidato"], cand["poblacion"], strict=True))
        reducido, equivalentes = actuaciones.fusionar_equivalentes(cubre, prioridad)
        for k in cfg["carteras_a"]:
            milp_tp = optimizacion.cobertura_maxima(reducido, pesos, k, cfg["limite_solver_s"])
            regla = optimizacion.regla_simple(poblacion_celda, k)
            de_pie = next(f["milp_elegidos"] for f in carteras_pie if f["objetivo"] == objetivo and f["k"] == k)
            fila = {"objetivo": objetivo, "k": k, "franja": "9_13", **{f"milp_{c}": v for c, v in milp_tp.items()},
                    "milp_candidatos_sin_fusionar": len({c for s in cubre for c in s}),
                    "milp_equivalentes": json.dumps({c: equivalentes.get(c, []) for c in milp_tp["elegidos"]}),
                    "regla_simple_elegidos": regla,
                    "regla_simple_ganancia": optimizacion.ganancia_de(cubre, pesos, regla),
                    "cartera_pie_elegidos": de_pie,
                    "cartera_pie_ganancia_en_transporte": optimizacion.ganancia_de(cubre, pesos, de_pie),
                    "cartera_tp_ganancia_a_pie": optimizacion.ganancia_de(
                        cubre_pie, sin_pie[columna].to_numpy(), milp_tp["elegidos"]),
                    "sin_opcion_base": float(pesos.sum())}
            for nombre, (sin_e, cubre_e) in problemas.items():
                if nombre != "base":
                    fila[f"robustez_ganancia_{nombre}"] = optimizacion.ganancia_de(
                        cubre_e, sin_e[columna].to_numpy(), milp_tp["elegidos"])
                    fila[f"robustez_sin_opcion_{nombre}"] = float(sin_e[columna].sum())
            fila.update(robustez_completa({n: (c, s[columna].to_numpy()) for n, (s, c) in problemas.items()},
                                          milp_tp["elegidos"], k, cfg["limite_solver_s"]))
            filas.append(fila)
    return filas


def robustez_completa(problemas: dict[str, tuple[list[frozenset], np.ndarray]], elegidos: list, k: int,
                      limite_s: float) -> dict:
    """SPEC §9: en cada escenario, la nueva cartera preferida (reoptimizada) y, entre todos, la
    alternativa max-min (la de mayor ganancia en su peor escenario), con la peor ganancia de la
    cartera base para compararlas.

    `problemas`: {escenario: (conjuntos de cobertura, pesos)}, con el escenario `base` incluido.
    """
    from . import optimizacion
    fila = {}
    for nombre, (cubre, pesos) in problemas.items():
        if nombre == "base":
            continue
        nueva = optimizacion.cobertura_maxima(cubre, pesos, k, limite_s)
        fila[f"reoptimo_ganancia_{nombre}"] = nueva["ganancia"]
        fila[f"reoptimo_estado_{nombre}"] = nueva["estado"]
        fila[f"reoptimo_elegidos_{nombre}"] = nueva["elegidos"]
    maxmin = optimizacion.cobertura_max_min(list(problemas.values()), k, limite_s)
    ganancias_base = [optimizacion.ganancia_de(c, p, elegidos) for c, p in problemas.values()]
    ganancias_maxmin = {n: optimizacion.ganancia_de(c, p, maxmin["elegidos"]) for n, (c, p) in problemas.items()}
    return {**fila, "maxmin_estado": maxmin["estado"], "maxmin_elegidos": maxmin["elegidos"],
            "maxmin_peor_ganancia": maxmin["peor_ganancia"], "maxmin_ganancia_base": ganancias_maxmin["base"],
            "maxmin_escenarios": list(problemas), "cartera_base_peor_ganancia": min(ganancias_base),
            "maxmin_segundos": maxmin["segundos"]}


def carteras_b1(proc: Path, unidades: pd.DataFrame, config: dict) -> list[dict]:
    """B1 (MILP en dos etapas), regla simple y cota «todos abiertos», para total y 75+."""
    from . import actuaciones, horarios, optimizacion
    cfg = config["actuaciones"]
    tipo, umbral = cfg["b1_tipo_dia"], config["refugios"]["umbral_min"]
    estados_b = pd.read_parquet(proc / "refugios" / "b_estados_base_central.parquet")
    pares = pd.read_parquet(proc / "refugios_pie" / "pares.parquet")
    pares = pares[pares["velocidad_kmh"] == config["primaria"]["pie"]["velocidad_kmh"]]
    mercados = leer_refugios()
    nombres = dict(zip(mercados["pk"], mercados["nombre"], strict=True))
    estados_ref = horarios.tabla_estados(mercados)
    limites = [(cfg["b1_max_centros"], cfg["b1_max_centro_horas"])]
    limites += [(c, cfg["b1_max_centro_horas"]) for c in cfg["b1_sensibilidad_centros"]]
    limites += [(cfg["b1_max_centros"], h) for h in cfg["b1_sensibilidad_centro_horas"]]
    filas = []
    for objetivo, columna in (("total", "poblacion_total"), ("75+", "poblacion_75_mas")):
        demanda, cubiertos, bloques = actuaciones.demanda_b1(estados_b, pares, estados_ref, unidades, tipo, umbral, columna)
        cerca = pares[pares["minutos"] <= umbral].merge(unidades[["unidad", columna]], on="unidad")
        poblacion_cerca = cerca.groupby("refugio")[columna].sum().to_dict()
        todos = optimizacion.evaluar_b1(demanda, cubiertos, bloques)
        # Robustez (SPEC §9): la misma cartera, evaluada en los otros tipos de día.
        otros = {t: actuaciones.demanda_b1(estados_b, pares, estados_ref, unidades, t, umbral, columna)
                 for t in config["refugios"]["tipos_dia"] if t != tipo}
        for max_c, max_h in limites:
            resultado = optimizacion.ampliar_horas(demanda, cubiertos, bloques, max_c, max_h, cfg["limite_solver_s"])
            regla = optimizacion.regla_simple_b1(demanda, cubiertos, bloques, poblacion_cerca, max_c, max_h)
            evaluada = optimizacion.evaluar_b1(demanda, cubiertos, regla)
            alternativas = optimizacion.alternativas_b1(demanda, cubiertos, bloques, resultado.get("bloques", []),
                                                        max_c, max_h, cfg["limite_solver_s"])
            filas.append({"objetivo": objetivo, "tipo_dia": tipo, "max_centros": max_c, "max_centro_horas": max_h,
                          **{f"milp_{c}": v for c, v in resultado.items() if c not in ("max_centros", "max_centro_horas")},
                          # Para la ficha de decisión: nombre del mercado y hora de inicio de cada bloque abierto.
                          "milp_bloques_detalle": json.dumps([{"mercado": nombres.get(r, r), "hora_inicio": h}
                                                              for r, h in resultado.get("bloques", [])],
                                                             ensure_ascii=False),
                          # Empate o elección firme: la mejor cartera sin cada mercado elegido.
                          "alternativas_sin_mercado": json.dumps(alternativas_con_nombres(alternativas, nombres),
                                                                 ensure_ascii=False),
                          "regla_simple_bloques": regla, "regla_simple_peor_hora": evaluada["peor_hora"],
                          "regla_simple_personas_hora": evaluada["personas_hora_ganadas"],
                          "cota_todos_abiertos_peor_hora": todos["peor_hora"],
                          "cota_todos_abiertos_personas_hora": todos["personas_hora_ganadas"],
                          "cubiertos_hoy_por_hora": json.dumps(cubiertos),
                          **robustez_b1_tipos_dia(otros, resultado.get("bloques", []))})
    return filas


def alternativas_con_nombres(alternativas: list[dict], nombres: dict) -> list[dict]:
    """Cambia los identificadores de refugio por el nombre del mercado para la ficha de decisión."""
    return [{"excluido": nombres.get(a["excluido"], a["excluido"]),
             "mercados": [nombres.get(r, r) for r in a["refugios"]],
             **{k: v for k, v in a.items() if k not in ("excluido", "refugios")}} for a in alternativas]


def robustez_b1_tipos_dia(otros: dict[str, tuple], bloques_abiertos: list) -> dict:
    """Peor hora antes y después y personas-hora ganadas de una cartera de B1 en otros tipos de día.

    Un bloque (refugio, hora) que ese tipo de día ya está abierto no añade nada: `evaluar_b1` solo
    cuenta como ganancia la población sin acceso en esa hora.
    """
    from . import optimizacion
    fila = {}
    for tipo_dia, (demanda_dia, cubiertos, _bloques) in otros.items():
        evaluada = optimizacion.evaluar_b1(demanda_dia, cubiertos, [tuple(b) for b in bloques_abiertos])
        fila[f"robustez_{tipo_dia}_peor_hora_antes"] = min(cubiertos.values())
        fila[f"robustez_{tipo_dia}_peor_hora_despues"] = evaluada["peor_hora"]
        fila[f"robustez_{tipo_dia}_personas_hora"] = evaluada["personas_hora_ganadas"]
    return fila


def anadir_antes_despues(filas: list[dict], sin_opcion: dict[str, float]) -> list[dict]:
    """Añade a cada cartera la población sin opción antes y después, y la ganancia incremental
    respecto a la cartera anterior del mismo objetivo (k = 1 → 3 → 5), para la pantalla de
    resultados (la app no calcula: R-UI-01)."""
    anterior: dict[str, float] = {}
    for fila in sorted(filas, key=lambda f: (f["objetivo"], f["k"])):
        antes = fila.get("sin_opcion_base", sin_opcion[fila["objetivo"]])
        fila.update({"sin_opcion_antes": antes, "sin_opcion_despues": antes - fila["milp_ganancia"],
                     "ganancia_incremental": fila["milp_ganancia"] - anterior.get(fila["objetivo"], 0.0)})
        anterior[fila["objetivo"]] = fila["milp_ganancia"]
    return filas


def detalle_carteras(filas_a: list[dict], filas_tp: list[dict], cand: pd.DataFrame, unidades: pd.DataFrame,
                     sin_pie: dict[str, float]) -> pd.DataFrame:
    """Una fila por zona elegida en cada cartera de A, con coordenadas WGS84 y municipio, para
    la ficha de decisión y la exportación GeoJSON de la app (que no calcula: R-UI-01).

    `sin_pie`: población sin opción a pie por objetivo (el «antes» de las carteras a pie).
    Municipio de una zona: el de la unidad más poblada de su celda.
    """
    from pyproj import Transformer

    from . import actuaciones
    celdas = unidades.assign(candidato=actuaciones.celda_candidato(unidades)).sort_values(
        "poblacion_total", ascending=False).drop_duplicates("candidato").set_index("candidato")["cusec"].str[:5]
    lon, lat = Transformer.from_crs("EPSG:25830", "EPSG:4326", always_xy=True).transform(
        cand["x"].to_numpy(), cand["y"].to_numpy())
    zonas = cand.assign(lon=lon, lat=lat, municipio=cand["candidato"].map(celdas)).set_index("candidato")
    filas = []
    for componente, lista in (("a_pie", filas_a), ("a_transporte", filas_tp)):
        for f in lista:
            antes = f.get("sin_opcion_base", sin_pie[f["objetivo"]])
            for orden, zona in enumerate(f["milp_elegidos"], start=1):
                filas.append({"componente": componente, "objetivo": f["objetivo"], "k": f["k"], "orden": orden,
                              "zona": zona, "lon": zonas.at[zona, "lon"], "lat": zonas.at[zona, "lat"],
                              "municipio": zonas.at[zona, "municipio"], "poblacion_celda": zonas.at[zona, "poblacion"],
                              "estado_solver": f["milp_estado"], "ganancia_cartera": f["milp_ganancia"],
                              "sin_opcion_antes": antes, "sin_opcion_despues": antes - f["milp_ganancia"]})
    return pd.DataFrame(filas)


def etapa_actuaciones(raiz: Path, id_snapshot: str, config: dict) -> dict:
    """H5: carteras de A a pie y B1, con regla simple, robustez y registro del solver."""
    proc = carpeta_procesados(raiz, id_snapshot)
    unidades = pd.read_parquet(proc / "demanda" / "unidades_demanda.parquet").merge(
        pd.read_parquet(proc / "acceso_pie" / "tiempos_pie.parquet"), on="unidad", validate="one_to_one")
    estados = pd.read_parquet(proc / "acceso" / "estados_base.parquet")
    estado_pie = unidades[["unidad"]].merge(estados, on="unidad", how="left")["estado_pie"]
    pares = pd.read_parquet(proc / "candidatos_pie" / "pares.parquet")
    cand = pd.read_parquet(proc / "candidatos_pie" / "candidatos.parquet")
    sin_pie = {o: float(unidades.loc[(estado_pie == acceso.SIN).to_numpy(), c].sum())
               for o, c in (("total", "poblacion_total"), ("65+", "poblacion_65_mas"))}
    filas_a = anadir_antes_despues(carteras_a(unidades, estado_pie, pares, cand, config), sin_pie)
    filas_tp = anadir_antes_despues(carteras_a_transporte(proc, unidades, estado_pie, pares, cand, filas_a, config),
                                    sin_pie)
    filas_b1 = carteras_b1(proc, unidades, config)
    destino = proc / "actuaciones"
    temporal = preparar_temporal(destino)
    pd.DataFrame(filas_a).to_csv(temporal / "carteras_a_pie.csv", index=False, encoding="utf-8")
    if filas_tp:
        pd.DataFrame(filas_tp).to_csv(temporal / "carteras_a_transporte.csv", index=False, encoding="utf-8")
    detalle_carteras(filas_a, filas_tp, cand, unidades, sin_pie).to_csv(
        temporal / "carteras_detalle.csv", index=False, encoding="utf-8")
    pd.DataFrame(filas_b1).to_csv(temporal / "b1_ampliar_horas.csv", index=False, encoding="utf-8")
    resumen = {"etapa": "actuaciones", "snapshot": id_snapshot, "creado_utc": ahora_utc().isoformat(),
               "config": config["actuaciones"],
               "estados_a": sorted({f["milp_estado"] for f in filas_a}),
               "estados_a_transporte": sorted({f["milp_estado"] for f in filas_tp}) or "sin pares en transporte",
               "estados_b1": sorted({f["milp_estado"] for f in filas_b1})}
    escribir_json_atomico(temporal / "resumen.json", resumen)
    publicar_carpeta(temporal, destino)
    return resumen


def capas_mapa_minutos(raiz: Path, id_snapshot: str, config: dict) -> dict:
    """Capas del mapa de minutos (SPEC P-27): lee las entradas y llama a `capas_mapa.preparar`."""
    import geopandas as gpd

    from . import capas_mapa, contexto, renta
    proc = carpeta_procesados(raiz, id_snapshot)
    snapshot = leer_snapshot(raiz, id_snapshot)
    unidades = pd.read_parquet(proc / "demanda" / "unidades_demanda.parquet").merge(
        pd.read_parquet(proc / "acceso_pie" / "tiempos_pie.parquet"), on="unidad", how="left", validate="one_to_one")
    por_seccion = {franja: acceso.mejor_por_seccion(matriz) for franja in CARPETAS_TRANSPORTE_FRANJA
                   if (matriz := leer_matriz_transporte(proc, franja)) is not None}
    iguala = raiz / "crudos" / contexto.ARCHIVO_IGUALA[0] / contexto.ARCHIVO_IGUALA[1]
    renta.comprobar_manifiesto(iguala)
    distritos = contexto.iguala_distritos(iguala)
    nombres = dict(zip(distritos["cod_distrito"].map("{:02d}".format), distritos["Nombre distrito"], strict=True))
    return capas_mapa.preparar(
        unidades, pd.read_parquet(proc / "acceso" / "estados_base.parquet"), por_seccion,
        pd.read_csv(proc / "renta" / "quintiles_seccion.csv", dtype={"cusec": str}),
        gpd.read_file(ruta_en_snapshot(raiz, snapshot, *ARCHIVO_SECCIONES)), nombres,
        ruta_en_snapshot(raiz, snapshot, *ARCHIVO_OSM), config)


def etapa_capas_app(raiz: Path, id_snapshot: str, config: dict) -> dict:
    """Capas de la app (H6), precalculadas para que la app no calcule (R-UI-01).

    `unidades_mapa.parquet`: estados de A, B y C por unidad (pantallas 3 y 4). Mapa de minutos de
    la pantalla 2 (`capas_mapa.py`): `celdas_mapa.parquet`, `municipios_mapa.parquet`,
    `lineas_mapa.parquet`, `territorios_mapa.csv` y `tramos_mapa.csv`, y las mismas capas listas para
    deck.gl en `deck/*.json` (`capas_deck.py`); el catálogo de variables va en `resumen.json`.
    """
    from . import app_datos, capas_deck
    proc = carpeta_procesados(raiz, id_snapshot)
    capa = app_datos.capa_mapa(proc)
    minutos = capas_mapa_minutos(raiz, id_snapshot, config)
    destino = proc / "app"
    temporal = preparar_temporal(destino)
    capa.to_parquet(temporal / "unidades_mapa.parquet", index=False)
    for nombre in ("celdas", "municipios", "lineas"):
        minutos[nombre].to_parquet(temporal / f"{nombre}_mapa.parquet", index=False)
    for nombre in ("territorios", "tramos"):
        minutos[nombre].to_csv(temporal / f"{nombre}_mapa.csv", index=False, encoding="utf-8")
    filas_deck = capas_deck.escribir(temporal / "deck", minutos)
    resumen = {"etapa": "capas_app", "snapshot": id_snapshot, "creado_utc": ahora_utc().isoformat(),
               "conteos": {"unidades": len(capa), "con_estado_b": int(capa.get("estado_b", pd.Series()).notna().sum())},
               "variables_minutos": minutos["catalogo"], "comprobaciones_mapa": minutos["comprobaciones"],
               "filas_deck": filas_deck}
    escribir_json_atomico(temporal / "resumen.json", resumen)
    publicar_carpeta(temporal, destino)
    return resumen


def etapa_poblacion(raiz: Path, id_snapshot: str) -> dict:
    """Normaliza la población INE por sección y edad, y documenta los códigos sin dato ni polígono.

    Si las sumas de las secciones no reproducen los agregados del INE, la etapa falla y no
    publica nada (R-DEM-01): la carpeta temporal queda para inspeccionarla.
    """
    snapshot = leer_snapshot(raiz, id_snapshot)
    origen = ruta_en_snapshot(raiz, snapshot, *ARCHIVO_POBLACION)
    capa = ruta_en_snapshot(raiz, snapshot, *ARCHIVO_SECCIONES)
    resultado = poblacion.normalizar(poblacion.leer_tabla(origen), poblacion.leer_poligonos(capa))
    destino = carpeta_procesados(raiz, id_snapshot) / "poblacion"
    temporal = preparar_temporal(destino)
    resultado["por_edad"].to_parquet(temporal / "poblacion_seccion_edad.parquet", index=False)
    resultado["por_seccion"].to_parquet(temporal / "poblacion_seccion.parquet", index=False)
    resultado["codigos_sin_dato"].to_csv(temporal / "codigos_sin_dato_ni_poligono.csv",
                                         index=False, encoding="utf-8")
    resumen = {
        "etapa": "poblacion", "snapshot": id_snapshot, "creado_utc": ahora_utc().isoformat(),
        "origen": origen.relative_to(raiz).as_posix(), "origen_sha256": sha256_archivo(origen),
        "capa_secciones": capa.relative_to(raiz).as_posix(), "capa_sha256": sha256_archivo(capa),
        "criterio": {"periodo": poblacion.PERIODO, "sexo": poblacion.SEXO_TOTAL,
                     "umbrales_mayores": list(poblacion.UMBRALES_MAYORES),
                     "tipo_poligono_seccion": poblacion.TIPO_POLIGONO_SECCION},
        "descuadres_con_agregados_ine": resultado["descuadres"],
        "cruce_poligonos": resultado["cruce_poligonos"],
        "conteos": resultado["conteos"],
    }
    escribir_json_atomico(temporal / "resumen.json", resumen)
    if resultado["descuadres"]:
        raise ValueError(f"{len(resultado['descuadres'])} descuadres con los agregados del INE; "
                         f"no se publica. Detalle en {temporal / 'resumen.json'}")
    publicar_carpeta(temporal, destino)
    return resumen
