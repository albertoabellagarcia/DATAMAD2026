"""Motor de rutas r5py/R5 a pie y en transporte público (H2; P-14, R-RED-01, R-RED-02).

r5py arranca una máquina virtual de Java (JDK 21) al importarse, así que se importa dentro
de cada función: el resto del paquete y los tests no necesitan Java.

Clasificación del resultado de ruta de cada origen (R-RED-02):
- `fallo_conexion`: el origen no engancha a ninguna calle transitable a pie dentro del radio
  de enganche de R5.
- `dentro_umbral`: llega a algún destino en el umbral o menos.
- `fuera_umbral`: el destino más cercano está entre el umbral y el radio de cálculo.
- `fallo_enlace`: R5 no llega a ningún destino dentro del radio de cálculo, pero hay uno a
  distancia en línea recta alcanzable dentro del umbral. Un rodeo así no es creíble: se trata
  como fallo de enlace con la red (por ejemplo, una isla de calles) y no como carencia. Solo
  se aplica a pie, si se da la distancia en línea recta.
- `fuera_radio`: R5 no llega a ningún destino dentro del radio de cálculo.

Correspondencia con los estados de la SPEC §7 (`ESTADO_SEGUN_CLASE`): los dos fallos son
`no_evaluable` (`conexion`); fuera de umbral y fuera de radio son `sin_opcion_verificada`.
"""

import csv
import datetime
import io
import os
import shutil
import subprocess
import zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
from scipy.spatial import cKDTree

from .manifiestos import SUFIJO_TEMPORAL, sha256_archivo

TABLAS_OPCIONALES = ("fare_attributes.txt", "fare_rules.txt", "transfers.txt", "frequencies.txt",
                     "feed_info.txt", "shapes.txt")
FECHA_FIJA_ZIP = (2026, 1, 1, 0, 0, 0)
CLASES = ("dentro_umbral", "fuera_umbral", "fuera_radio", "fallo_conexion", "fallo_enlace")
ESTADO_SEGUN_CLASE = {
    "dentro_umbral": ("con_acceso", ""),
    "fuera_umbral": ("sin_opcion_verificada", ""),
    "fuera_radio": ("sin_opcion_verificada", ""),
    "fallo_conexion": ("no_evaluable", "conexion"),
    "fallo_enlace": ("no_evaluable", "conexion"),
}


def version_java() -> str:
    """Primera línea de `java -version` del JDK que verá r5py; falla si no hay ninguno."""
    java_home = os.environ.get("JAVA_HOME")
    ejecutable = str(Path(java_home) / "bin" / "java") if java_home else shutil.which("java")
    if not ejecutable:
        raise RuntimeError("No hay JDK visible para r5py: define JAVA_HOME o pon java en el PATH.")
    salida = subprocess.run([ejecutable, "-version"], capture_output=True, text=True, check=True)
    return (salida.stderr or salida.stdout).splitlines()[0].strip()


def filas_de_datos(contenido: bytes) -> int:
    """Filas de datos de un archivo GTFS (sin contar la cabecera ni las líneas en blanco)."""
    lineas = [linea for linea in contenido.decode("utf-8-sig", errors="replace").splitlines() if linea.strip()]
    return max(len(lineas) - 1, 0)


def motivo_para_omitir(nombre: str, contenido: bytes) -> str:
    """Por qué se omite una tabla opcional que R5 rechaza, o '' si se conserva."""
    if nombre not in TABLAS_OPCIONALES:
        return ""
    filas = filas_de_datos(contenido)
    if filas == 0:
        return f"omitida tabla opcional vacía {nombre}"
    if nombre == "feed_info.txt" and filas > 1:
        return f"omitido {nombre} con {filas} registros (el estándar GTFS admite uno)"
    return ""


def extender_calendario(contenido: bytes, hasta: datetime.date) -> tuple[bytes, list[str]]:
    """calendar.txt con la fecha de fin de cada servicio llevada a `hasta` si terminaba antes.

    Es un SUPUESTO, no un arreglo de forma: aplica el horario publicado a fechas posteriores a
    su vigencia. Solo se usa cuando no hay un feed vigente y debe declararse (decisión del
    usuario del 13/11/2026 para Metro). No toca días de la semana, viajes ni frecuencias.
    """
    filas = list(csv.DictReader(io.StringIO(contenido.decode("utf-8-sig"))))
    fecha = hasta.strftime("%Y%m%d")
    cambios = []
    for fila in filas:
        if fila["end_date"] < fecha:
            cambios.append(f"SUPUESTO: servicio {fila['service_id']} extendido de {fila['end_date']} a {fecha}")
            fila["end_date"] = fecha
    salida = io.StringIO()
    escritor = csv.DictWriter(salida, fieldnames=list(filas[0]) if filas else [], lineterminator=chr(10))
    escritor.writeheader()
    escritor.writerows(filas)
    return salida.getvalue().encode("utf-8"), cambios


def preparar_gtfs(origen: Path, carpeta: Path,
                  extender_hasta: datetime.date | None = None) -> tuple[Path, list[str]]:
    """Devuelve un GTFS legible por R5 y la lista de cambios hechos para conseguirlo.

    Con `extender_hasta`, además, alarga el calendario con `extender_calendario` (supuesto
    declarado: cada cambio empieza por «SUPUESTO»).

    Arreglos de forma, que no tocan horarios, viajes ni paradas:
    - si los archivos están dentro de una única subcarpeta del zip, se sacan a la raíz;
    - se omiten las tablas opcionales (`TABLAS_OPCIONALES`) que R5 rechaza: las vacías y un
      feed_info.txt con más de un registro.
    Siempre devuelve una copia en `carpeta` cuyo nombre lleva los 12 primeros caracteres del
    SHA-256 de la propia copia (`gtfs_metro_<huella>.zip`). Motivo: r5py guarda su copia de
    trabajo de cada entrada por nombre de archivo y no la renueva si ya existe
    (r5py/util/working_copy.py:46-53), así que un contenido nuevo con un nombre ya usado se
    ignoraría. La copia se escribe de forma determinista (fecha fija en cada entrada): el mismo
    origen y las mismas reglas dan el mismo archivo y la misma huella, y R5 reutiliza su red.
    El original nunca se modifica.
    """
    with zipfile.ZipFile(origen) as zip_origen:
        archivos = [n for n in zip_origen.namelist() if not n.endswith("/")]
        carpetas = {n.split("/")[0] for n in archivos if "/" in n}
        if carpetas and (len(carpetas) != 1 or any(n.count("/") != 1 for n in archivos)):
            raise ValueError(f"{origen.name}: estructura no prevista ({sorted(carpetas)})")
        base = {n: n.split("/", 1)[-1] for n in archivos}
        motivos = {n: motivo_para_omitir(base[n], zip_origen.read(n)) for n in archivos}
        omitidos = [n for n in archivos if motivos[n]]
        cambios = ([f"archivos sacados de la subcarpeta {min(carpetas)}"] if carpetas else []) + [
            motivos[n] for n in omitidos]
        carpeta.mkdir(parents=True, exist_ok=True)
        temporal = carpeta / f"{origen.stem}{SUFIJO_TEMPORAL}"
        with zipfile.ZipFile(temporal, "w", zipfile.ZIP_DEFLATED) as zip_destino:
            for nombre in sorted(set(archivos) - set(omitidos)):
                contenido = zip_origen.read(nombre)
                if extender_hasta and base[nombre] == "calendar.txt":
                    contenido, extendidos = extender_calendario(contenido, extender_hasta)
                    cambios += extendidos
                entrada = zipfile.ZipInfo(base[nombre], date_time=FECHA_FIJA_ZIP)
                entrada.compress_type = zipfile.ZIP_DEFLATED
                zip_destino.writestr(entrada, contenido)
    destino = carpeta / f"{origen.stem}_{sha256_archivo(temporal)[:12]}.zip"
    os.replace(temporal, destino)
    return destino, cambios


def construir_red(pbf: Path, gtfs: list[Path] | None = None):
    """Red de R5 con la red viaria del PBF y, si se dan, los GTFS."""
    import r5py
    return r5py.TransportNetwork(pbf, [str(g) for g in (gtfs or [])])


def radio_enganche_r5() -> float:
    """Radio de enganche por defecto de R5 (StreetLayer.LINK_RADIUS_METERS), en metros."""
    import jpype
    import r5py  # noqa: F401  (al importarse arranca la JVM, necesaria para JClass)
    return float(jpype.JClass("com.conveyal.r5.streets.StreetLayer").LINK_RADIUS_METERS)


def enganche(red, puntos: gpd.GeoDataFrame, radio_m: float) -> pd.DataFrame:
    """Para cada punto: si engancha a una calle transitable a pie y a qué distancia."""
    enganchados = red.snap_to_network(puntos.geometry, radius=radio_m)
    vacio = enganchados.is_empty.to_numpy()
    distancia = np.where(vacio, np.nan, puntos.geometry.distance(enganchados).to_numpy())
    return pd.DataFrame({"id": puntos["id"].to_numpy(), "enganchado": ~vacio, "distancia_enganche_m": distancia})


def matriz(red, origenes: gpd.GeoDataFrame, destinos: gpd.GeoDataFrame, *, modos: list[str],
           velocidad_kmh: float, max_min: int, salida: datetime.datetime, ventana_min: int = 1,
           percentiles: tuple[int, ...] = (50,)) -> pd.DataFrame:
    """Matriz de tiempos (min) de R5. `modos`: nombres de r5py.TransportMode, p. ej. ['WALK'].

    Con transporte, R5 calcula una salida por minuto dentro de la ventana y devuelve los
    percentiles pedidos (P-18: mediana y p80). Un par sin ruta en `max_min` queda en NaN.
    """
    import r5py
    resultado = r5py.TravelTimeMatrix(
        red, origins=origenes[["id", "geometry"]], destinations=destinos[["id", "geometry"]],
        transport_modes=[getattr(r5py.TransportMode, m) for m in modos], departure=salida,
        departure_time_window=datetime.timedelta(minutes=ventana_min), percentiles=list(percentiles),
        speed_walking=velocidad_kmh, max_time=datetime.timedelta(minutes=max_min),
        max_time_walking=datetime.timedelta(minutes=max_min))
    return pd.DataFrame(resultado)


def matriz_en_paralelo(red, origenes: gpd.GeoDataFrame, destinos: gpd.GeoDataFrame, hilos: int,
                       **parametros) -> pd.DataFrame:
    """`matriz` con los orígenes repartidos en `hilos` bloques que se calculan a la vez.

    r5py 1.1.7 recorre los orígenes uno a uno (r5py/r5/travel_time_matrix.py:98) y, en
    transporte, usa en la práctica un solo núcleo. La red de R5 se comparte entre hilos; cada
    bloque crea su propia petición. Devuelve lo mismo que `matriz`.
    """
    bloques = [b for b in np.array_split(np.arange(len(origenes)), hilos) if len(b)]
    with ThreadPoolExecutor(max_workers=len(bloques)) as ejecutor:
        partes = list(ejecutor.map(lambda idx: matriz(red, origenes.iloc[idx], destinos, **parametros), bloques))
    return pd.concat(partes, ignore_index=True)


def minimo_por_origen(tiempos: pd.DataFrame, columna: str = "travel_time") -> pd.DataFrame:
    """Tiempo al destino más cercano de cada origen y qué destino es (NaN si ninguno)."""
    validos = tiempos.dropna(subset=[columna])
    fila_minima = validos.loc[validos.groupby("from_id")[columna].idxmin()]
    minimos = fila_minima.set_index("from_id")[[columna, "to_id"]]
    return minimos.reindex(tiempos["from_id"].unique()).rename_axis("id").reset_index()


def recta_al_mas_cercano_m(origenes: gpd.GeoDataFrame, destinos: gpd.GeoDataFrame) -> np.ndarray:
    """Distancia en línea recta (m) de cada origen al destino más cercano; ambos en EPSG:25830."""
    arbol = cKDTree(np.column_stack([destinos.geometry.x, destinos.geometry.y]))
    distancia, _ = arbol.query(np.column_stack([origenes.geometry.x, origenes.geometry.y]))
    return distancia


def clasificar(tiempo_min: pd.Series, enganchado: pd.Series, umbral_min: float, radio_min: float,
               recta_min: pd.Series | None = None) -> pd.Series:
    """Clase de R-RED-02 de cada origen (ver el docstring del módulo)."""
    if radio_min <= umbral_min:
        raise ValueError("El radio de cálculo debe ser mayor que el umbral.")
    tiempo = pd.to_numeric(tiempo_min, errors="coerce").to_numpy(dtype=float)
    enganchado = np.asarray(enganchado, dtype=bool)
    recta = np.full(len(tiempo), np.inf) if recta_min is None else np.asarray(recta_min, dtype=float)
    sin_tiempo = np.isnan(tiempo)
    condiciones = [~enganchado, ~sin_tiempo & (tiempo <= umbral_min), ~sin_tiempo, recta <= umbral_min]
    clases = np.select(condiciones, ["fallo_conexion", "dentro_umbral", "fuera_umbral", "fallo_enlace"],
                       default="fuera_radio")
    return pd.Series(clases, index=tiempo_min.index, name="clase")


def manifiesto_motor(pbf: Path, gtfs: list[Path], parametros: dict) -> dict:
    """Entradas exactas, versiones y parámetros del motor (R-RED-01)."""
    import r5py
    from r5py.util.classpath import R5_JAR_SHA256, R5_JAR_URL
    return {
        "creado_utc": datetime.datetime.now(datetime.UTC).isoformat(),
        "pbf": {"archivo": pbf.name, "sha256": sha256_archivo(pbf), "bytes": pbf.stat().st_size},
        "gtfs": [{"archivo": g.name, "sha256": sha256_archivo(g), "bytes": g.stat().st_size} for g in gtfs],
        "r5py": r5py.__version__,
        "r5_jar": {"url": R5_JAR_URL, "sha256_esperado": R5_JAR_SHA256},
        "java": version_java(),
        "parametros": parametros,
    }

