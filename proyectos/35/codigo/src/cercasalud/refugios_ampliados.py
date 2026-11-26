"""Refugios ampliados: más espacios frente al calor, cada uno con su tipo y su nivel de evidencia.

Decisión del usuario del 22/11/2026 (`fases/PLAN_ENTREGA_20261114.md`, tabla de decisiones; cambia el alcance de
D-12). Además de los 43 mercados, se señalan bibliotecas, museos, centros de mayores, centros culturales, salas de
estudio, centros deportivos, servicios sociales, juntas de distrito, centros comerciales y cines. Solo en Madrid
capital, el único municipio con una lista oficial verificada (D-28).

**Niveles de evidencia** (nunca se mezclan en una cifra):
- `verificado`: los 43 mercados de la lista municipal (la base de B, sin cambios);
- `respaldo_oficial`: una fuente oficial acredita la climatización: las bibliotecas municipales y los cinco museos
  municipales (CALORMAD 2026, p. 86 del PDF) y los recursos del Anexo VIII con climatización «Sí»;
- `potencial`: sin fuente oficial de climatización, horario o acceso libre (OpenStreetMap, el Anexo VIII con
  climatización parcial o en blanco, servicios sociales y juntas de distrito por su horario administrativo, y las
  bibliotecas de la Comunidad de Madrid, a las que no se refiere el plan municipal).

**Tres líneas de cobertura** (B a pie, el umbral y la velocidad de la base):
1. `verificados`: los 43 mercados, como en la etapa `refugios` (debe dar lo mismo; se comprueba);
2. `respaldo_oficial`: los mercados y los espacios con respaldo oficial. Solo cuentan como abiertos los que tienen
   horario de verano curado (hoy, las 36 bibliotecas municipales); el resto queda `pendiente` y su entorno, si no
   hay otro abierto, `no_evaluable` (lo desconocido no se da por cerrado ni por abierto);
3. `maximo_posible`: todos los espacios de los tres niveles, abiertos todas las horas. Es un techo, no un dato.

Las **capas aparte** no son refugio y no entran en ninguna cifra: parques y zonas verdes de toda la Comunidad (OSM;
decisión del usuario del 23/11/2026: parques, jardines públicos, áreas recreativas y monte o bosque, cada uno con su
`clase`; el CALORMAD, §3.3, cuenta los parques entre las «zonas especialmente sensibles» al calor) y refresco e
hidratación en Madrid capital (fuentes de agua y piscinas municipales al aire libre, a las que remiten los anexos V
y V-A del CALORMAD).
"""

import re
import unicodedata
from pathlib import Path

import numpy as np
import pandas as pd

from . import horarios, refugios
from .acceso import territorios
from .catalogo import CATALOGO
from .ingesta import versiones_locales
from .manifiestos import leer_json, ruta_manifiesto, sha256_archivo

CURADO = Path(__file__).resolve().parents[2] / "curado"
HORARIOS_CURADOS = CURADO / "refugios_ampliados_horarios.csv"
ANEXO_CURADO = CURADO / "anexo_viii_calormad_2026.csv"
EQUIPAMIENTOS = {"bibliotecas": "equipamientos_bibliotecas.csv", "mayores": "centros_mayores.csv",
                 "culturales": "centros_culturales.csv"}
CAPAS_PROTECCION_CIVIL = ("RECURSOS_PROTECCION_CIVIL/ALBERGUES_EMERGENCIA_REFUGIOS_CLIMATICOS.shp",
                          "RECURSOS_PROTECCION_CIVIL/ALBERGUES_EMERGENCIA_REFUGIOS_CLIMATICOS_GRAN_CAPACIDAD.shp")

VERIFICADO, RESPALDO, POTENCIAL = "verificado", "respaldo_oficial", "potencial"
NIVELES = {VERIFICADO: "Verificado", RESPALDO: "Con respaldo oficial", POTENCIAL: "Potencial, no verificado"}
TIPOS = {
    "mercado": "Mercado municipal (zonas comunes climatizadas)", "biblioteca": "Biblioteca pública",
    "museo": "Museo", "centro_mayores": "Centro de mayores", "centro_cultural": "Centro cultural",
    "sala_estudio": "Sala de estudio", "centro_deportivo": "Centro deportivo municipal",
    "servicios_sociales": "Centro de servicios sociales", "junta_distrito": "Junta municipal de distrito",
    "centro_comercial": "Centro comercial", "cine": "Cine",
}
# Servicios del Anexo VIII que entran (los demás —centros de día, enseñanzas artísticas, espacios de igualdad,
# información juvenil y el recinto ferial— no estaban en la lista aceptada por el usuario).
SERVICIO_ANEXO = {"Centro Municipal de Mayores": "centro_mayores", "Centro Cultural": "centro_cultural",
                  "CENTRO CULTURAL": "centro_cultural", "Centro Deportivo Municipal": "centro_deportivo",
                  "Centros Espacio Deporte": "centro_deportivo", "Sala de Estudio y Lectura": "sala_estudio",
                  "Biblioteca": "biblioteca", "Centro de Servicios Sociales": "servicios_sociales",
                  "Junta Municipal de Distrito": "junta_distrito"}
SOLO_POTENCIAL = {"servicios_sociales", "junta_distrito"}   # horario administrativo
TIPO_CSV = {"bibliotecas": "biblioteca", "mayores": "centro_mayores", "culturales": "centro_cultural",
            "salas": "sala_estudio", "deportivos": "centro_deportivo"}
# CSV de datos.madrid.es descargados con `fetch` (23/11/2026). Las salas de estudio aportan horario y salas nuevas;
# los polideportivos, solo el horario de los centros que ya están (el CSV mezcla campos de fútbol, piscinas de verano
# y otras instalaciones al aire libre, que no son espacios cerrados).
CSV_CATALOGO = {"salas": "madrid_salas_estudio", "deportivos": "madrid_polideportivos"}
SOLO_HORARIO = {"deportivos"}
TIPO_CSV_ADMITIDO = {"culturales": "/CentrosCulturales", "salas": "/SalasEstudioLectura"}
# Los cinco museos del «listado de espacios climatizados» de la S. G. de Museos y Exposiciones (CALORMAD, p. 86):
# nombre oficial → fragmentos que debe contener el nombre en OSM (sin tildes ni mayúsculas).
MUSEOS_MUNICIPALES = {
    "Museo de San Isidro. Los Orígenes de Madrid": ("museo", "san isidro"),
    "Museo de Historia de Madrid": ("museo", "historia de madrid"),
    "Museo de Arte Contemporáneo": ("museo de arte contemporaneo",),
    "Planetario de Madrid": ("planetario",),
    "Imprenta Municipal - Artes del Libro": ("imprenta municipal",),
}
CAJA_MADRID = (-3.90, 40.30, -3.51, 40.65)   # lon/lat; contiene Madrid capital (solo para leer menos OSM)
# Etiquetas de OSM de los espacios de Madrid capital que se leen: tipo → (clave, valor).
BUSCADOS_OSM = {"museo": ("tourism", "museum"), "cine": ("amenity", "cinema"), "centro_comercial": ("shop", "mall")}
TIPOS_OSM_ESPACIO = ("museo", "cine", "centro_comercial")

# Zonas verdes de toda la Comunidad (decisión del usuario del 23/11/2026: «parques y jardines públicos, y además
# monte o bosque»; el césped urbano, `landuse=grass`, queda fuera). Capa aparte: no es refugio ni entra en cifras.
CLASES_VERDES = {"parque": "Parque", "jardin": "Jardín público", "area_recreativa": "Área recreativa",
                 "monte_bosque": "Monte o bosque"}
# Si dos polígonos se solapan, se dibuja el de la clase más concreta (número menor).
PRIORIDAD_VERDES = {"parque": 0, "jardin": 1, "area_recreativa": 2, "monte_bosque": 3}
ACCESO_NO_PUBLICO = ("private", "no", "customers", "permit", "residents")
JARDIN_TIPO_PRIVADO = ("residential", "private", "kitchen", "school")
JARDIN_TIPO_PUBLICO = ("public", "municipal", "botanical", "arboretum")
NOMBRE_PRIVADO = re.compile(r"urbanizaci[oó]n|residencial|\bresidencia\b|comunidad de propietarios",
                                   re.IGNORECASE)
# Recintos cerrados en los que un jardín sin acceso declarado se da por no público (los campus universitarios no
# están: en Madrid se pasean libremente).
RECINTOS_CERRADOS = ("school", "kindergarten", "college", "hospital", "clinic", "place_of_worship", "monastery",
                     "social_facility", "prison")
# Deportes de motor: un `recreation_ground` con ellos es un circuito, no un área recreativa.
DEPORTES_MOTOR = ("motocross", "karting", "motor")
# Espacios de OSM cuyo monte no es de libre acceso (se recorta el monte o bosque que cae dentro).
ZONAS_ACCESO_RESTRINGIDO = {
    "r20243902": ("Monte de El Pardo (Patrimonio Nacional): la mayor parte es zona reservada sin acceso libre; OSM no "
                  "delimita la parte abierta, así que se excluye entero."),
}
AREA_MIN_PARQUE_M2 = 1000
AREA_MIN_JARDIN_SIN_NOMBRE_M2 = 5000
AREA_MIN_MONTE_M2 = 10000
SOLAPE_MAXIMO = 0.9   # fracción de un polígono dentro de otro de igual o más prioridad a partir de la cual se quita
# Tolerancia de simplificación (m): 4 m en las zonas urbanas, como la capa de la capital; 25 m en el monte, que a
# escala de la Comunidad pesa más de la mitad del archivo de la página (medido el 23/11/2026).
SIMPLIFICAR_VERDES_M = {"parque": 4, "jardin": 4, "area_recreativa": 4, "monte_bosque": 25}
CONDICION_VERDES = (
    "leisure IN ('park', 'garden', 'recreation_ground') OR landuse IN ('forest', 'recreation_ground', 'residential') "
    "OR \"natural\" = 'wood' OR boundary = 'protected_area' OR amenity IN ("
    + ", ".join(f"'{a}'" for a in RECINTOS_CERRADOS) + ")"
)
COLUMNAS_VERDES = ["osm_id", "osm_way_id", "name", "leisure", "landuse", "natural", "boundary", "amenity", "sport",
                   "other_tags"]

CALORMAD = "CALORMAD 2026"
EVIDENCIA = {
    "mercado": ("Lista municipal de 43 mercados con aire acondicionado en sus zonas comunes (madrid.es; nota del "
                "Ayuntamiento del 28/05/2026). Horario comercial curado; el acceso a la zona climatizada no consta "
                "(D-33)."),
    "biblioteca_municipal": (f"{CALORMAD}, p. 86 del PDF: las bibliotecas públicas municipales «cuentan todas con "
                             "climatización» y ofrecen espacios donde la ciudadanía se puede «refugiar»."),
    "biblioteca_comunidad": ("Biblioteca de la Comunidad de Madrid (datos.madrid.es): la declaración del plan "
                             "municipal no la cubre; la climatización no consta."),
    "museo_municipal": (f"{CALORMAD}, p. 86 del PDF: listado de espacios climatizados de la Subdirección General de "
                        "Museos y Exposiciones. Su horario de verano no está curado."),
    "anexo_si": (f"{CALORMAD}, Anexo VIII (p. {{pagina}} del PDF): climatización «Sí». El anexo es un inventario "
                 "potencial de emergencia, no una red abierta a diario; su horario de verano no está curado."),
    "anexo_parcial": f"{CALORMAD}, Anexo VIII (p. {{pagina}} del PDF): climatización «Parcial».",
    "anexo_vacio": f"{CALORMAD}, Anexo VIII (p. {{pagina}} del PDF): la climatización no consta.",
    "anexo_gran_capacidad": (f"{CALORMAD}, Anexo VIII (p. {{pagina}} del PDF), gran capacidad: la nota 12 dice "
                             "«climatizados total o parcialmente», sin precisar cuál."),
    "anexo_administrativo": (f"{CALORMAD}, Anexo VIII (p. {{pagina}} del PDF), con horario administrativo: no se "
                             "cuenta como espacio de refugio."),
    "csv_sin_anexo": "Equipamiento municipal (datos.madrid.es) fuera del Anexo VIII: la climatización no consta.",
    "osm": ("OpenStreetMap: ubicación aportada por sus colaboradores; no hay fuente oficial de climatización, "
            "horario ni acceso libre."),
    "osm_cine": ("OpenStreetMap: ubicación aportada por sus colaboradores. Según la nota municipal del 28/05/2026, "
                 "los cines ofrecen descuentos de 15 a 17 h: el acceso es de pago."),
}
LICENCIA = {"ayuntamiento": "CC BY 4.0 (Ayuntamiento de Madrid)", "calormad": "Documento público del Ayuntamiento",
            "osm": "ODbL 1.0 (© colaboradores de OpenStreetMap)"}


# ------------------------------------------------------------------ lectura de fuentes


def sin_tildes(texto: str) -> str:
    """Minúsculas sin tildes ni signos combinados, para comparar nombres."""
    return "".join(c for c in unicodedata.normalize("NFD", str(texto).lower()) if unicodedata.category(c) != "Mn")


def copia_verificada(ruta: Path) -> Path:
    """La ruta, si su SHA-256 coincide con el de su manifiesto `.source.json`; si no, error."""
    manifiesto = leer_json(ruta_manifiesto(ruta))
    if sha256_archivo(ruta) != manifiesto.get("sha256"):
        raise ValueError(f"{ruta}: el SHA-256 no coincide con su manifiesto.")
    return ruta


def ruta_equipamientos(raiz: Path, clave: str) -> Path:
    """CSV municipal de equipamientos ya adquirido (fuera del catálogo de `fetch`), con su SHA-256 comprobado."""
    return copia_verificada(raiz / "crudos" / "madrid_equipamientos" / EQUIPAMIENTOS[clave])


def ruta_catalogo(raiz: Path, fuente: str) -> Path:
    """Última copia local de una fuente del catálogo, con su SHA-256 comprobado."""
    archivo = next(a for a in CATALOGO if a.fuente == fuente)
    versiones = versiones_locales(raiz, archivo)
    if not versiones:
        raise FileNotFoundError(f"Falta {fuente}: `uv run cercasalud fetch --fuente {fuente}`.")
    ruta, manifiesto = versiones[-1]
    if sha256_archivo(ruta) != manifiesto.get("sha256"):
        raise ValueError(f"{ruta}: el SHA-256 no coincide con su manifiesto.")
    return ruta


def archivos_externos(raiz: Path) -> list[Path]:
    """Archivos de `crudos/` que lee la etapa fuera de la versión de datos (para su huella, R-ARQ-03)."""
    return [raiz / "crudos" / "madrid_equipamientos" / n for n in EQUIPAMIENTOS.values()] + \
        [ruta_catalogo(raiz, f) for f in ("madrid_fuentes", "madrid_piscinas", *CSV_CATALOGO.values(), "cm_bibliotecas")]


def leer_csv_madrid(ruta: Path, codificacion: str = "cp1252") -> pd.DataFrame:
    """CSV de datos.madrid.es (separador «;»), todo como texto."""
    return pd.read_csv(ruta, sep=";", encoding=codificacion, dtype=str, keep_default_na=False)


def contorno_madrid(ruta_secciones: Path):
    """Contorno de Madrid capital (EPSG:25830): unión de sus secciones censales del INE."""
    import pyogrio
    import shapely
    secciones = pyogrio.read_dataframe(ruta_secciones, columns=["CUSEC"])
    capital = secciones[secciones["CUSEC"].str.startswith("28079")].to_crs("EPSG:25830")
    return shapely.union_all(capital.geometry.buffer(0.5)).buffer(-0.5)


def contorno_comunidad(ruta_secciones: Path):
    """Contorno de la Comunidad de Madrid (EPSG:25830): unión de todas sus secciones censales (CUSEC «28…»)."""
    import pyogrio
    import shapely
    secciones = pyogrio.read_dataframe(ruta_secciones, columns=["CUSEC"])
    comunidad = secciones[secciones["CUSEC"].str.startswith("28")].to_crs("EPSG:25830")
    return shapely.union_all(comunidad.geometry.buffer(0.5)).buffer(-0.5)


# ------------------------------------------------------------------ espacios oficiales


def fila_espacio(id_: str, nombre: str, tipo: str, nivel: str, evidencia: str, fuente: str, licencia: str,
                 x: float, y: float, horario: str = "", url: str = "") -> dict:
    """Un espacio con todos sus campos (coordenadas en EPSG:25830)."""
    return {"id": id_, "nombre": " ".join(str(nombre).split()), "tipo": tipo, "nivel": nivel, "evidencia": evidencia,
            "fuente": fuente, "licencia": licencia, "x": float(x), "y": float(y),
            "horario_texto": " ".join(str(horario).split()), "url": url}


def espacios_mercados(mercados: pd.DataFrame) -> list[dict]:
    """Los 43 mercados de la base, nivel verificado (`construccion.leer_refugios`)."""
    return [fila_espacio(f"mercado:{m['pk']}", m.get("nombre", m["pk"]), "mercado", VERIFICADO, EVIDENCIA["mercado"],
                         "Ayuntamiento de Madrid (madrid.es) y curación propia", LICENCIA["ayuntamiento"], m["x"], m["y"])
            for _, m in mercados.iterrows()]


def nivel_anexo(tipo: str, climatizacion: str, grupo: str, pagina: str) -> tuple[str, str]:
    """(nivel, evidencia) de un recurso del Anexo VIII según su servicio y su climatización."""
    if tipo == "biblioteca":
        return RESPALDO, EVIDENCIA["biblioteca_municipal"]
    if tipo in SOLO_POTENCIAL:
        return POTENCIAL, EVIDENCIA["anexo_administrativo"].format(pagina=pagina)
    if grupo == "gran_capacidad":
        return POTENCIAL, EVIDENCIA["anexo_gran_capacidad"].format(pagina=pagina)
    if climatizacion == "Sí":
        return RESPALDO, EVIDENCIA["anexo_si"].format(pagina=pagina)
    clave = "anexo_parcial" if climatizacion == "Parcial" else "anexo_vacio"
    return POTENCIAL, EVIDENCIA[clave].format(pagina=pagina)


def coordenadas_proteccion_civil(ruta_zip: Path) -> pd.DataFrame:
    """PK y coordenadas (EPSG:25830) de los 260 recursos del Anexo VIII en la capa de Protección Civil.

    Solo se usan la geometría y el PK: los demás campos de la capa no se interpretan (R-TMP-05).
    """
    import pyogrio
    partes = []
    for capa in CAPAS_PROTECCION_CIVIL:
        datos = pyogrio.read_dataframe(f"/vsizip/{ruta_zip.as_posix()}/{capa}", columns=["PK"]).to_crs("EPSG:25830")
        partes.append(pd.DataFrame({"pk": datos["PK"].astype(str).str.strip(), "x": datos.geometry.x,
                                    "y": datos.geometry.y}))
    return pd.concat(partes, ignore_index=True).drop_duplicates("pk")


LLAMADA_NOTA = re.compile(r"(?<=\))\s*\d+$")   # «(Barajas) 2», «(Latina)11»: llamadas a nota del PDF del anexo


def nombre_anexo(nombre: str, nombres_csv: dict[str, str], pk: str) -> str:
    """Nombre del recurso: el del CSV municipal si está (limpio); si no, el del anexo sin la llamada a nota final."""
    return nombres_csv.get(pk) or LLAMADA_NOTA.sub("", nombre)


def espacios_anexo(anexo: pd.DataFrame, coordenadas: pd.DataFrame, horarios_csv: dict[str, str],
                   nombres_csv: dict[str, str] | None = None) -> list[dict]:
    """Recursos del Anexo VIII de los servicios aceptados, con su nivel según la climatización del anexo."""
    tabla = anexo[anexo["servicio"].isin(SERVICIO_ANEXO)].merge(coordenadas, on="pk", how="left", validate="one_to_one")
    if tabla[["x", "y"]].isna().any().any():
        raise ValueError(f"Recursos del Anexo VIII sin coordenadas: {tabla.loc[tabla['x'].isna(), 'pk'].tolist()}")
    filas = []
    for _, r in tabla.iterrows():
        tipo = SERVICIO_ANEXO[r["servicio"]]
        nivel, evidencia = nivel_anexo(tipo, r["climatizacion"], r["grupo_anexo"], r["pagina_pdf"])
        filas.append(fila_espacio(f"eq:{r['pk']}", nombre_anexo(r["nombre"], nombres_csv or {}, r["pk"]), tipo, nivel,
                                  evidencia,
                                  f"Ayuntamiento de Madrid, {CALORMAD} (Anexo VIII) y capa de Protección Civil",
                                  LICENCIA["ayuntamiento"], r["x"], r["y"], horarios_csv.get(r["pk"], "")))
    return filas


def espacios_csv(clave: str, tabla: pd.DataFrame, ya_incluidos: set[str]) -> list[dict]:
    """Equipamientos municipales de un CSV que no están ya en el Anexo VIII (sus PK)."""
    filas = []
    for _, r in tabla.iterrows():
        pk = r["PK"].strip()
        if f"eq:{pk}" in ya_incluidos:
            continue
        tipo = TIPO_CSV[clave]
        if clave in TIPO_CSV_ADMITIDO and not r["TIPO"].endswith(TIPO_CSV_ADMITIDO[clave]):
            continue   # los CSV mezclan auditorios, teatros, oficinas juveniles…: solo entra el tipo buscado
        if clave == "bibliotecas":
            municipal = r["EMAIL"].strip().lower().endswith("@madrid.es")
            nivel = RESPALDO if municipal else POTENCIAL
            evidencia = EVIDENCIA["biblioteca_municipal" if municipal else "biblioteca_comunidad"]
        else:
            nivel, evidencia = POTENCIAL, EVIDENCIA["csv_sin_anexo"]
        filas.append(fila_espacio(f"eq:{pk}", r["NOMBRE"], tipo, nivel, evidencia,
                                  "Ayuntamiento de Madrid (datos.madrid.es)", LICENCIA["ayuntamiento"],
                                  r["COORDENADA-X"], r["COORDENADA-Y"], r["HORARIO"], r["CONTENT-URL"]))
    return filas


# ------------------------------------------------------------------ OpenStreetMap


def etiqueta_osm(fila, clave: str, propias: set):
    """Valor de una clave OSM: de su columna o de `other_tags` (REGISTRO-FALLOS 30)."""
    if clave in propias:
        valor = fila.get(clave)
        return valor if isinstance(valor, str) else None
    otras = fila.get("other_tags")
    m = re.search(rf'"{clave}"=>"([^"]*)"', otras if isinstance(otras, str) else "")
    return m.group(1) if m else None


def leer_osm(pbf: Path, contorno, buscados: dict[str, tuple[str, str]]):
    """Elementos de OSM con alguna de las etiquetas buscadas dentro de Madrid capital (EPSG:25830).

    Devuelve un GeoDataFrame con `tipo`, `nombre`, `osm`, `capa` y la geometría (puntos y polígonos).
    """
    import geopandas as gpd
    import pyogrio
    partes = []
    for capa in ("points", "multipolygons"):
        propias = set(pyogrio.read_info(pbf, layer=capa)["fields"])
        condiciones = [f"{c} = '{v}'" if c in propias else f"other_tags LIKE '%\"{c}\"=>\"{v}\"%'"
                       for c, v in buscados.values()]
        datos = pyogrio.read_dataframe(pbf, layer=capa, bbox=CAJA_MADRID, where=" OR ".join(condiciones))
        if datos.empty:
            continue
        datos = datos.to_crs("EPSG:25830")
        datos = datos[datos.geometry.representative_point().within(contorno)]
        for tipo, (clave, valor) in buscados.items():
            sel = datos[datos.apply(lambda f, c=clave, p=propias: etiqueta_osm(f, c, p), axis=1) == valor]
            if capa == "points":
                ident = "n" + sel["osm_id"].astype(str)
            else:
                ident = np.where(sel["osm_way_id"].notna(), "w" + sel["osm_way_id"].astype(str),
                                 "r" + sel["osm_id"].astype(str))
            acceso = sel.apply(lambda f, p=propias: etiqueta_osm(f, "access", p), axis=1)
            # Horario general declarado en OSM (`opening_hours`), solo para mostrarlo: no entra en ninguna cifra.
            horario = sel.apply(lambda f, p=propias: etiqueta_osm(f, "opening_hours", p) or "", axis=1)
            partes.append(gpd.GeoDataFrame({"tipo": tipo, "nombre": sel["name"].fillna(""), "osm": ident,
                                            "acceso": acceso, "horario": horario, "capa": capa},
                                           geometry=sel.geometry, crs="EPSG:25830"))
    return pd.concat(partes, ignore_index=True) if partes else gpd.GeoDataFrame()


def sin_duplicar_puntos(elementos):
    """Quita los puntos que caen dentro de un polígono del mismo tipo (el mismo sitio mapeado dos veces)."""
    poligonos = elementos[elementos["capa"] == "multipolygons"]
    quitar = []
    for i, fila in elementos[elementos["capa"] == "points"].iterrows():
        mismos = poligonos[poligonos["tipo"] == fila["tipo"]]
        if len(mismos) and mismos.geometry.buffer(30).contains(fila.geometry).any():
            quitar.append(i)
    return elementos.drop(index=quitar)


def es_museo_municipal(nombre: str) -> str | None:
    """Nombre oficial del museo municipal climatizado (CALORMAD, p. 86) al que corresponde un nombre de OSM."""
    plano = sin_tildes(nombre)
    for oficial, fragmentos in MUSEOS_MUNICIPALES.items():
        if all(f in plano for f in fragmentos):
            return oficial
    return None


def espacios_osm(elementos) -> list[dict]:
    """Museos, cines y centros comerciales de OSM. Los cinco museos municipales suben a respaldo oficial."""
    filas = []
    for _, e in sin_duplicar_puntos(elementos).iterrows():
        punto = e.geometry.representative_point()
        oficial = es_museo_municipal(e["nombre"]) if e["tipo"] == "museo" else None
        nivel = RESPALDO if oficial else POTENCIAL
        evidencia = EVIDENCIA["museo_municipal"] if oficial else EVIDENCIA["osm_cine" if e["tipo"] == "cine" else "osm"]
        filas.append(fila_espacio(f"osm:{e['osm']}", oficial or e["nombre"] or TIPOS[e["tipo"]], e["tipo"], nivel,
                                  evidencia, "OpenStreetMap (extracto de Geofabrik)", LICENCIA["osm"],
                                  punto.x, punto.y, e.get("horario", "") or ""))
    return filas


def espacios_museos_por_nombre(pbf: Path, contorno) -> pd.DataFrame:
    """Los museos municipales que OSM no etiqueta como museo (p. ej. un planetario), buscados por su nombre."""
    import pyogrio
    filas = []
    for capa in ("points", "multipolygons"):
        condiciones = " OR ".join(f"name LIKE '%{f}%'" for f in ("Planetario", "Imprenta Municipal", "San Isidro",
                                                                   "Historia de Madrid", "Arte Contempor"))
        datos = pyogrio.read_dataframe(pbf, layer=capa, bbox=CAJA_MADRID, where=condiciones)
        if datos.empty:
            continue
        datos = datos.to_crs("EPSG:25830")
        datos = datos[datos.geometry.representative_point().within(contorno)]
        for _, d in datos.iterrows():
            oficial = es_museo_municipal(d["name"])
            if oficial:
                p = d.geometry.representative_point()
                filas.append({"oficial": oficial, "nombre_osm": d["name"], "x": p.x, "y": p.y, "capa": capa,
                              "area": d.geometry.area})
    tabla = pd.DataFrame(filas)
    if tabla.empty:
        return tabla
    # Si el museo está como punto y como polígono, se queda el polígono (el edificio).
    return tabla.sort_values(["oficial", "area"], ascending=[True, False]).drop_duplicates("oficial")


# ------------------------------------------------------------------ todos los espacios


def espacios(mercados: pd.DataFrame, anexo: pd.DataFrame, coordenadas: pd.DataFrame,
             csv_equipamientos: dict[str, pd.DataFrame], osm, museos_nombre: pd.DataFrame) -> pd.DataFrame:
    """Tabla única de espacios (uno por fila) con tipo, nivel, evidencia, fuente, licencia y coordenadas."""
    horarios_csv = {r["PK"].strip(): r["HORARIO"] for t in csv_equipamientos.values() for _, r in t.iterrows()}
    nombres_csv = {r["PK"].strip(): " ".join(r["NOMBRE"].split()) for t in csv_equipamientos.values()
                   for _, r in t.iterrows()}
    filas = espacios_mercados(mercados) + espacios_anexo(anexo, coordenadas, horarios_csv, nombres_csv)
    for clave, tabla in csv_equipamientos.items():
        if clave in SOLO_HORARIO:
            continue   # solo da el horario y el nombre de los espacios que ya están
        filas += espacios_csv(clave, tabla, {f["id"] for f in filas})
    filas += espacios_osm(osm)
    tabla = pd.DataFrame(filas)
    # Museos municipales que OSM no etiqueta como museo: se añaden por su nombre si no están ya.
    ya = set(tabla.loc[tabla["nivel"].eq(RESPALDO) & tabla["tipo"].eq("museo"), "nombre"])
    extra = [fila_espacio(f"museo:{sin_tildes(m['oficial'])[:24].replace(' ', '_')}", m["oficial"], "museo", RESPALDO,
                          EVIDENCIA["museo_municipal"], "OpenStreetMap (ubicación) y CALORMAD 2026", LICENCIA["osm"],
                          m["x"], m["y"])
             for _, m in museos_nombre.iterrows() if m["oficial"] not in ya]
    tabla = pd.concat([tabla, pd.DataFrame(extra)], ignore_index=True) if extra else tabla
    if tabla["id"].duplicated().any():
        raise ValueError(f"Espacios repetidos: {tabla.loc[tabla['id'].duplicated(), 'id'].tolist()}")
    return tabla


# ------------------------------------------------------------------ bibliotecas del resto de la Comunidad (solo mapa)
#
# Decisión del usuario del 23/11/2026 (propuesta 3 de `docs/investigacion_iniciativas_20261123/INFORME.md`): las
# bibliotecas públicas de punto fijo del directorio de la Comunidad de Madrid **fuera de Madrid capital**, en el mapa,
# como «potencial». No son destino de R5 ni entran en ninguna línea: fuera de la capital, B sigue no evaluable. El
# directorio no trae coordenadas: cada biblioteca se casa con una biblioteca de OpenStreetMap de su mismo municipio.

TIPO_BIBLIOTECA_PUBLICA = "biblioteca publica  punto fijo"   # «Biblioteca Pública. Punto fijo», normalizado
# Errata sistemática del CSV de la Comunidad (perfil del 23/11/2026): «l A» aparece como «L-» («RafaeL-lberti»,
# «deL-rroyo», «CentraL-lmudena»). Se deshace con esta regla explícita, que solo toca ese patrón.
ERRATA_L_A = re.compile(r"(?<=[A-Za-zÁÉÍÓÚáéíóúñÑ])L-(?=[a-záéíóúñ])")
# Localidades del CSV que no son el nombre INE del municipio (revisadas una a una el 23/11/2026).
LOCALIDAD_A_MUNICIPIO = {
    "cerceda": "el boalo",                                   # núcleo del municipio de El Boalo
    "pozuelo de alarconpozuelo de alarcon": "pozuelo de alarcon",   # nombre repetido sin separador
    "san agustin de guadalix": "san agustin del guadalix",   # nombre INE
}
PALABRAS_GENERICAS = {"biblioteca", "bibliotecas", "publica", "publicas", "municipal", "municipales", "de", "del", "la",
                      "las", "el", "los", "y", "e", "en", "a", "sala", "lectura", "punto", "fijo", "bpm", "centro",
                      "cultural", "casa", "cultura", "servicio"}
# Bibliotecas de OSM que no son públicas de punto fijo: no sirven para casar (sobre todo en la regla «única del
# municipio», donde un nombre distinto no lo delataría).
NO_PUBLICA_OSM = re.compile(r"universi|urjc|uc3m|college|school|colegio|instituto|\bies\b|academia|deposito|"
                            r"facultad|campus|escuela|seminario|archivo hist|ludoteca", re.IGNORECASE)
UMBRAL_NOMBRE = 0.5   # coincidencia de palabras propias (Jaccard) para un casamiento «seguro»
EVIDENCIA_CM = ("Directorio de bibliotecas de la Comunidad de Madrid (datos.comunidad.madrid, CC BY 4.0): biblioteca "
                "pública de punto fijo. La climatización no consta y su horario de verano no está curado. Ubicación "
                "tomada de OpenStreetMap ({calidad}).")
CALIDAD_CASAMIENTO = {"seguro": "el nombre coincide con el de OSM en su municipio",
                      "probable": "es la única biblioteca pública del municipio en las dos fuentes, con nombres distintos"}


def corregir_errata(texto: str) -> str:
    """Deshace la errata «L-» → «l A» del directorio de la Comunidad («RafaeL-lberti» → «Rafael Alberti»)."""
    return ERRATA_L_A.sub("l A", str(texto))


def plano(texto: str) -> str:
    """Minúsculas sin tildes y sin signos (solo letras, números y espacios)."""
    return re.sub(r"[^a-z0-9ñ ]", " ", sin_tildes(texto))


def palabras_propias(nombre: str) -> set[str]:
    """Palabras que distinguen una biblioteca de otra (sin «biblioteca», «municipal», artículos...)."""
    return {p for p in plano(nombre).split() if p not in PALABRAS_GENERICAS and len(p) > 1}


def municipio_normalizado(nombre: str) -> str:
    """Nombre de municipio comparable: «Boalo (El)» y «El Boalo» → «el boalo»."""
    texto = " ".join(plano(nombre).split())
    pospuesto = re.match(r"^(.*?) (el|la|los|las)$", texto)
    texto = f"{pospuesto.group(2)} {pospuesto.group(1)}" if pospuesto else texto
    return LOCALIDAD_A_MUNICIPIO.get(texto, texto)


def bibliotecas_publicas_cm(tabla: pd.DataFrame) -> pd.DataFrame:
    """Bibliotecas públicas de punto fijo fuera de Madrid capital, con la errata corregida."""
    tabla = tabla.assign(nombre=tabla["nombre_biblioteca"].map(corregir_errata),
                         localidad=tabla["localidad"].map(corregir_errata).str.strip())
    publica = tabla["tipo_biblioteca"].map(plano).str.startswith(TIPO_BIBLIOTECA_PUBLICA)
    fuera = tabla["localidad"].map(municipio_normalizado) != "madrid"
    return tabla[publica & fuera].reset_index(drop=True)


def municipios_comunidad(ruta_secciones: Path):
    """Polígonos de los 179 municipios (EPSG:25830) con su código (`CUMUN`) y nombre INE (`NMUN`)."""
    import pyogrio
    secciones = pyogrio.read_dataframe(ruta_secciones, columns=["CUMUN", "NMUN"]).to_crs("EPSG:25830")
    return secciones.dissolve("CUMUN", as_index=False, aggfunc="first")


def leer_bibliotecas_osm(pbf: Path, municipios):
    """Bibliotecas de OSM (`amenity=library`) fuera de Madrid capital, como punto, con su municipio."""
    import geopandas as gpd
    import pyogrio
    partes = []
    for capa in ("points", "multipolygons"):
        propias = set(pyogrio.read_info(pbf, layer=capa)["fields"])
        condicion = "amenity = 'library'" if "amenity" in propias else "other_tags LIKE '%\"amenity\"=>\"library\"%'"
        datos = pyogrio.read_dataframe(pbf, layer=capa, where=condicion)
        if datos.empty:
            continue
        datos = datos.to_crs("EPSG:25830")
        ident = ("n" + datos["osm_id"].astype(str) if capa == "points" else
                 np.where(datos["osm_way_id"].notna(), "w" + datos["osm_way_id"].astype(str), "r" + datos["osm_id"].astype(str)))
        partes.append(gpd.GeoDataFrame({"osm": ident, "nombre_osm": datos["name"].fillna("")},
                                       geometry=datos.geometry.representative_point(), crs="EPSG:25830"))
    osm = gpd.GeoDataFrame(pd.concat(partes, ignore_index=True), crs="EPSG:25830")
    osm = gpd.sjoin(osm, municipios[["CUMUN", "geometry"]], predicate="within").drop(columns="index_right")
    osm = osm[(osm["CUMUN"] != "28079") & ~osm["nombre_osm"].str.contains(NO_PUBLICA_OSM)]
    return osm.reset_index(drop=True)


def parecido(nombre_a: str, nombre_b: str) -> float:
    """Coincidencia (Jaccard) de las palabras propias de dos nombres; 0 si ninguno tiene palabras propias."""
    a, b = palabras_propias(nombre_a), palabras_propias(nombre_b)
    return len(a & b) / len(a | b) if a | b else 0.0


def casar_bibliotecas(publicas: pd.DataFrame, osm, municipios) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Casa cada biblioteca del directorio con una de OSM de su municipio, sin repetir ninguna de las dos.

    - `seguro`: palabras propias del nombre con coincidencia ≥ `UMBRAL_NOMBRE`;
    - `probable`: es la única biblioteca pública del municipio en el directorio y en OSM.
    Se asignan los pares de mayor coincidencia primero. Devuelve (ubicadas, sin ubicar con su motivo).
    """
    codigo = {municipio_normalizado(n): c for c, n in zip(municipios["CUMUN"], municipios["NMUN"], strict=True)}
    publicas = publicas.assign(cumun=publicas["localidad"].map(lambda x: codigo.get(municipio_normalizado(x))))
    n_csv = publicas["cumun"].value_counts()
    n_osm = osm["CUMUN"].value_counts()
    pares = [(i, j, parecido(b["nombre"], o["nombre_osm"]))
             for i, b in publicas.iterrows() if pd.notna(b["cumun"])
             for j, o in osm[osm["CUMUN"] == b["cumun"]].iterrows()]
    pares.sort(key=lambda p: -p[2])
    usadas_b, usadas_o, filas = set(), set(), []
    for i, j, valor in pares:
        if i in usadas_b or j in usadas_o:
            continue
        cumun = publicas.at[i, "cumun"]
        if valor >= UMBRAL_NOMBRE:
            calidad = "seguro"
        elif n_csv.get(cumun, 0) == 1 and n_osm.get(cumun, 0) == 1:
            calidad = "probable"
        else:
            continue
        usadas_b.add(i)
        usadas_o.add(j)
        b, o = publicas.loc[i], osm.loc[j]
        filas.append({"nombre": " ".join(b["nombre"].split()), "localidad": b["localidad"], "cumun": cumun,
                      "horario_texto": " ".join(str(b["horario"]).split()), "calidad": calidad,
                      "coincidencia": round(valor, 2), "osm": o["osm"], "nombre_osm": o["nombre_osm"],
                      "x": o.geometry.x, "y": o.geometry.y})
    sin = publicas.loc[[i for i in publicas.index if i not in usadas_b]]
    motivo = np.where(sin["cumun"].isna(), "localidad sin municipio INE",
                      np.where(sin["cumun"].map(n_osm).fillna(0) == 0, "su municipio no tiene bibliotecas públicas en OSM",
                               "sin biblioteca de OSM con nombre coincidente"))
    sin_ubicar = pd.DataFrame({"nombre": sin["nombre"], "localidad": sin["localidad"], "motivo": motivo})
    return pd.DataFrame(filas), sin_ubicar.reset_index(drop=True)


# ------------------------------------------------------------------ capas aparte (no son refugio)


def columna_osm(datos, clave: str, propias: set) -> pd.Series:
    """Una clave de OSM para todas las filas: de su columna o de `other_tags` (REGISTRO-FALLOS 30)."""
    if clave in propias:
        return datos[clave].astype(object).where(datos[clave].notna(), None)
    valores = datos["other_tags"].fillna("").str.extract(rf'"{re.escape(clave)}"=>"([^"]*)"')[0]
    return valores.astype(object).where(valores.notna(), None)


def leer_verdes_osm(pbf: Path, contorno):
    """Polígonos de OSM que usa la capa de zonas verdes, en toda la Comunidad (EPSG:25830), en una sola lectura.

    Trae los candidatos (parques, jardines, áreas recreativas, monte y bosque) y lo que sirve para decidir sobre
    ellos: parcelas residenciales, recintos cerrados y espacios protegidos (zonas de acceso restringido). Quedan los
    que tocan el contorno. Columnas: `osm`, `nombre`, las claves de `COLUMNAS_VERDES`, `acceso` y `tipo_jardin`.
    """
    import geopandas as gpd
    import pyogrio
    import shapely
    propias = set(pyogrio.read_info(pbf, layer="multipolygons")["fields"])
    datos = pyogrio.read_dataframe(pbf, layer="multipolygons", where=CONDICION_VERDES, columns=COLUMNAS_VERDES)
    datos = datos.to_crs("EPSG:25830")
    geometrias = datos.geometry.values.copy()
    invalidas = ~shapely.is_valid(geometrias)
    geometrias[invalidas] = shapely.buffer(geometrias[invalidas], 0)   # anillos que se cruzan: se rehacen
    shapely.prepare(contorno)
    toca = shapely.intersects(geometrias, contorno)
    datos = datos[toca]
    tabla = {"osm": np.where(datos["osm_way_id"].notna(), "w" + datos["osm_way_id"].astype(str),
                             "r" + datos["osm_id"].astype(str)),
             "nombre": datos["name"].fillna("").astype(str)}
    for clave in ("leisure", "landuse", "natural", "boundary", "amenity", "sport"):
        tabla[clave] = columna_osm(datos, clave, propias)
    tabla["acceso"] = columna_osm(datos, "access", propias)
    tabla["tipo_jardin"] = columna_osm(datos, "garden:type", propias)
    return gpd.GeoDataFrame(tabla, geometry=geometrias[toca], crs="EPSG:25830").reset_index(drop=True)


def clase_verde(elementos) -> pd.Series:
    """Clase de cada elemento («» si no es zona verde), en este orden: parque, jardín, área recreativa, monte."""
    e = elementos
    condiciones = [e["leisure"].eq("park"), e["leisure"].eq("garden"),
                   e["leisure"].eq("recreation_ground") | e["landuse"].eq("recreation_ground"),
                   e["landuse"].eq("forest") | e["natural"].eq("wood")]
    return pd.Series(np.select(condiciones, list(CLASES_VERDES), default=""), index=e.index)


def dentro_de(elementos, zonas) -> np.ndarray:
    """Si el punto representativo de cada elemento cae dentro de alguna de las zonas."""
    import shapely
    marca = np.zeros(len(elementos), dtype=bool)
    if len(elementos) == 0 or len(zonas) == 0:
        return marca
    puntos = shapely.point_on_surface(elementos.geometry.values)
    dentro, _ = shapely.STRtree(zonas.geometry.values).query(puntos, predicate="within")
    marca[np.unique(dentro)] = True
    return marca


def nombre_privado(nombres: pd.Series) -> pd.Series:
    """Nombres de urbanización, residencial o residencia: indican un espacio de una comunidad privada."""
    return nombres.str.contains(NOMBRE_PRIVADO)


def jardines_publicos(jardines, residencial, recintos) -> pd.Series:
    """Qué jardines (`leisure=garden`) se toman por públicos (decisión del 23/11/2026).

    La mayoría de los jardines de OSM son patios y jardines privados sin `access`. Fuera: acceso no público, tipo
    privado (`garden:type`) o menos de 1000 m². De lo que queda, entran: (a) los que declaran acceso o tipo
    público; (b) los que tienen nombre (de al menos tres letras), salvo el de una urbanización o residencia y los
    que caen en un recinto cerrado; (c) los que sin nombre miden 5000 m² o más y no caen en una parcela residencial
    ni en un recinto cerrado.
    """
    j = jardines
    area = j.geometry.area
    en_residencial, en_recinto = dentro_de(j, residencial), dentro_de(j, recintos)
    nombre = j["nombre"].str.strip()
    base = (~j["acceso"].isin(ACCESO_NO_PUBLICO) & ~j["tipo_jardin"].isin(JARDIN_TIPO_PRIVADO)
            & (area >= AREA_MIN_PARQUE_M2))
    declarado = j["acceso"].isin(["yes", "permissive"]) | j["tipo_jardin"].isin(JARDIN_TIPO_PUBLICO)
    con_nombre = (nombre.str.count(r"\w") >= 3) & ~nombre_privado(nombre) & ~en_recinto
    grande_sin_nombre = (nombre == "") & (area >= AREA_MIN_JARDIN_SIN_NOMBRE_M2) & ~en_residencial & ~en_recinto
    return base & (declarado | con_nombre | grande_sin_nombre)


def areas_recreativas_publicas(areas) -> pd.Series:
    """Áreas recreativas (`recreation_ground`) de libre uso.

    Fuera: acceso no público, las que tienen otro uso de ocio (`leisure` de centro deportivo, parque acuático…), las
    de deportes de motor (circuitos) y las de una urbanización o residencia (piscinas comunitarias).
    """
    otro_ocio = areas["leisure"].notna() & ~areas["leisure"].isin(["park", "garden", "recreation_ground"])
    motor = areas["sport"].fillna("").str.contains("|".join(DEPORTES_MOTOR))
    return ~areas["acceso"].isin(ACCESO_NO_PUBLICO) & ~otro_ocio & ~motor & ~nombre_privado(areas["nombre"])


def seleccion_verdes(elementos):
    """Elementos que entran en la capa de zonas verdes, con su `clase` (aún sin recortar ni quitar solapes).

    Parques y monte o bosque entran salvo acceso no público; jardines y áreas recreativas, con sus reglas. Los
    espacios protegidos (`leisure=nature_reserve`, `boundary=protected_area`) no entran por sí mismos: son límites
    administrativos de miles de hectáreas, no zonas verdes de uso diario.
    """
    e = elementos.assign(clase=clase_verde(elementos))
    residencial = e[e["landuse"].eq("residential") & e["clase"].eq("")]
    recintos = e[e["amenity"].isin(RECINTOS_CERRADOS) & e["clase"].eq("")]
    entra = e["clase"].isin(["parque", "monte_bosque"]) & ~e["acceso"].isin(ACCESO_NO_PUBLICO)
    jardin, recreativa = e["clase"].eq("jardin"), e["clase"].eq("area_recreativa")
    entra[jardin] = jardines_publicos(e[jardin], residencial, recintos)
    entra[recreativa] = areas_recreativas_publicas(e[recreativa])
    return e[entra]


def recortar_verdes(verdes, contorno, restringida):
    """Recorta los polígonos al contorno y quita del monte o bosque la zona de acceso restringido (si la hay)."""
    import shapely
    geometrias = verdes.geometry.values.copy()
    fuera = ~shapely.within(geometrias, contorno)
    geometrias[fuera] = shapely.intersection(geometrias[fuera], contorno)
    if restringida is not None:
        monte = verdes["clase"].eq("monte_bosque").to_numpy() & shapely.intersects(geometrias, restringida)
        geometrias[monte] = shapely.difference(geometrias[monte], restringida)
    return con_geometria(verdes, solo_poligonos(geometrias))


def con_geometria(tabla, geometrias):
    """La tabla con otra geometría (mismo índice y sistema de coordenadas)."""
    import geopandas as gpd
    return tabla.set_geometry(gpd.GeoSeries(geometrias, index=tabla.index, crs=tabla.crs))


def solo_poligonos(geometrias) -> np.ndarray:
    """Quita las líneas y los puntos sueltos de las colecciones que deja un recorte; quedan sus polígonos."""
    import shapely
    resultado = np.array(geometrias, dtype=object)
    for k in np.flatnonzero(shapely.get_type_id(resultado) == 7):   # 7 = GeometryCollection
        partes = [p for p in shapely.get_parts(resultado[k]) if shapely.get_type_id(p) in (3, 6)]
        resultado[k] = shapely.union_all(partes) if partes else shapely.Polygon()
    return resultado


def sin_solapes(verdes):
    """Quita los polígonos que caen casi enteros (`SOLAPE_MAXIMO`) dentro de otro mayor de igual o más prioridad.

    Así un jardín dentro de un parque, o un bosque dentro de un parque, no se pintan dos veces (con relleno
    translúcido, el solape se vería más oscuro). Un parque dentro de un monte sí se conserva: es más concreto.
    """
    import shapely
    geometrias = verdes.geometry.values
    area = shapely.area(geometrias)
    prioridad = verdes["clase"].map(PRIORIDAD_VERDES).to_numpy()
    i, j = shapely.STRtree(geometrias).query(geometrias, predicate="intersects")
    mayor = (area[j] > area[i]) | ((area[j] == area[i]) & (j < i))
    candidatos = (i != j) & mayor & (prioridad[j] <= prioridad[i])
    i, j = i[candidatos], j[candidatos]
    dentro = shapely.area(shapely.intersection(geometrias[i], geometrias[j])) >= SOLAPE_MAXIMO * area[i]
    return verdes[~np.isin(np.arange(len(verdes)), i[dentro])]


def zonas_verdes(elementos, contorno):
    """Capa de parques y zonas verdes de toda la Comunidad, simplificada, en EPSG:4326.

    `elementos`: la salida de `leer_verdes_osm`. Devuelve `nombre`, `osm`, `clase` (`CLASES_VERDES`) y geometría.
    """
    import shapely
    seleccion = seleccion_verdes(elementos)
    restringidas = elementos[elementos["osm"].isin(ZONAS_ACCESO_RESTRINGIDO)]
    restringida = shapely.union_all(restringidas.geometry.values) if len(restringidas) else None
    verdes = recortar_verdes(seleccion, contorno, restringida)
    minimo = np.where(verdes["clase"].eq("monte_bosque"), AREA_MIN_MONTE_M2, AREA_MIN_PARQUE_M2)
    verdes = sin_solapes(verdes[verdes.geometry.area >= minimo])
    tolerancia = verdes["clase"].map(SIMPLIFICAR_VERDES_M).to_numpy(dtype=float)
    verdes = con_geometria(verdes, shapely.simplify(verdes.geometry.values, tolerancia, preserve_topology=True))
    return verdes[["nombre", "osm", "clase", "geometry"]].to_crs("EPSG:4326").reset_index(drop=True)


SECCION_AIRE_LIBRE = re.compile(r"al aire libre\s*:([^.]*)", re.IGNORECASE)
PISCINA_DIRECTA = re.compile(r"piscinas? (?:de verano|al aire libre|aire libre|descubiertas?)", re.IGNORECASE)


def tiene_piscina_al_aire_libre(equipamiento: str) -> bool:
    """«Piscina de verano / al aire libre», o una piscina dentro de la lista «… al aire libre: …» (hasta el punto)."""
    texto = " ".join(str(equipamiento).split())
    seccion = " ".join(m.group(1) for m in SECCION_AIRE_LIBRE.finditer(texto))
    return bool(PISCINA_DIRECTA.search(texto) or re.search(r"piscina", seccion, re.IGNORECASE))


def refresco(fuentes: pd.DataFrame, piscinas: pd.DataFrame) -> pd.DataFrame:
    """Fuentes de agua operativas (para personas) y piscinas municipales al aire libre, en EPSG:25830."""
    f = fuentes[(fuentes["ESTADO"] == "OPERATIVO") & fuentes["USO"].isin(["PERSONAS", "PERSONAS_Y_MASCOTAS"])]
    filas = [{"id": f"fuente:{r['ID']}", "tipo": "fuente", "nombre": "Fuente de agua para beber",
              "detalle": " ".join(f"{r['TIPO_VIA']} {r['NOM_VIA']} {r['NUM_VIA']}".split()),
              "x": float(r["COORD_GIS_X"]), "y": float(r["COORD_GIS_Y"])} for _, r in f.iterrows()]
    p = piscinas[piscinas["EQUIPAMIENTO"].map(tiene_piscina_al_aire_libre)]
    filas += [{"id": f"piscina:{r['PK']}", "tipo": "piscina", "nombre": " ".join(r["NOMBRE"].split()),
               "detalle": "Piscina municipal al aire libre (temporada de verano; de pago)",
               "x": float(r["COORDENADA-X"]), "y": float(r["COORDENADA-Y"])} for _, r in p.iterrows()]
    return pd.DataFrame(filas)


# ------------------------------------------------------------------ horarios y estados


def estado_texto(texto: str, hora: int) -> str:
    """Estado en la franja [hora, hora+1) de un texto curado: «cerrado», «pendiente» o tramos «HH:MM-HH:MM»."""
    if texto == "cerrado":
        return horarios.CERRADO
    if texto == "pendiente":
        return horarios.PENDIENTE
    return horarios.abierto_en(horarios.tramos(texto), hora)


def estados_curados(curados: pd.DataFrame) -> pd.DataFrame:
    """Estado de cada espacio con fila en el archivo curado, en cada tipo de día y hora.

    `acceso_verificado` sale de su columna: «sí» solo en las bibliotecas municipales (el CALORMAD acredita su uso
    como refugio); en los demás, el acceso dentro del horario es un supuesto, como en los mercados (D-33).
    """
    filas = []
    for _, c in curados.iterrows():
        acceso = str(c.get("acceso_verificado", "sí")).strip().lower() in ("sí", "si", "true")
        for hora in horarios.HORAS:
            fin = horarios.combinar([estado_texto(c["sabado"], hora), estado_texto(c["domingo"], hora)])
            for tipo, estado in (("laborable_julio", estado_texto(c["laborables_julio"], hora)),
                                 ("laborable_agosto", estado_texto(c["laborables_agosto"], hora)),
                                 ("fin_de_semana", fin)):
                filas.append({"refugio": c["id"], "tipo_dia": tipo, "hora": hora, "estado": estado,
                              "acceso_verificado": acceso})
    return pd.DataFrame(filas)


def todas_las_horas(ids: list[str], estado: str, acceso: bool) -> pd.DataFrame:
    """El mismo estado para unos espacios en todos los tipos de día y horas."""
    rejilla = pd.MultiIndex.from_product([ids, horarios.TIPOS_DIA, horarios.HORAS],
                                         names=["refugio", "tipo_dia", "hora"]).to_frame(index=False)
    return rejilla.assign(estado=estado, acceso_verificado=acceso)


def estados_por_linea(tabla_espacios: pd.DataFrame, estados_mercados: pd.DataFrame,
                      curados: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Estados de los espacios que cuentan en cada línea (ver el docstring del módulo)."""
    mercados = estados_mercados.assign(refugio="mercado:" + estados_mercados["refugio"].astype(str))
    curado = estados_curados(curados)
    respaldo = tabla_espacios.loc[tabla_espacios["nivel"] == RESPALDO, "id"]
    sin_horario = sorted(set(respaldo) - set(curado["refugio"]))
    con_respaldo = pd.concat([mercados, curado[curado["refugio"].isin(respaldo)],
                              todas_las_horas(sin_horario, horarios.PENDIENTE, False)], ignore_index=True)
    maximo = todas_las_horas(tabla_espacios["id"].tolist(), horarios.ABIERTO, True)
    return {"verificados": mercados, "respaldo_oficial": con_respaldo, "maximo_posible": maximo}


LINEAS = (("verificados", "central"), ("verificados", "acreditable"), ("respaldo_oficial", "central"),
          ("respaldo_oficial", "acreditable"), ("maximo_posible", "central"))


def lineas_cobertura(unidades: pd.DataFrame, pares: pd.DataFrame, estados_linea: dict[str, pd.DataFrame],
                     umbral_min: float) -> tuple[list[dict], dict[str, pd.DataFrame]]:
    """Métricas de B por línea y cota en Madrid capital, y estados por unidad de cada línea (cota central).

    `unidades`: con `enganchado` y las columnas de población; `pares`: unidad, refugio (id del espacio) y minutos.
    """
    territorio = refugios.territorio_b(unidades)
    capital = unidades[territorios(unidades)["madrid_capital"].to_numpy()]
    resumen, tablas = [], {}
    for linea, cota in LINEAS:
        estados = estados_linea[linea]
        pares_linea = pares[pares["refugio"].isin(estados["refugio"])]
        tabla = refugios.estados_b(unidades, pares_linea, estados, umbral_min, cota, territorio)
        tabla = tabla[tabla["unidad"].isin(capital["unidad"])]
        _, filas = refugios.metricas_b(tabla, capital, {"linea": linea, "cota": cota, "umbral_min": umbral_min})
        resumen += filas
        if cota == "central":
            tablas[linea] = tabla
    return resumen, tablas


def conteos(tabla_espacios: pd.DataFrame) -> dict:
    """Número de espacios por tipo y nivel (para el resumen y la página)."""
    return {f"{t}|{n}": int(c) for (t, n), c in tabla_espacios.groupby(["tipo", "nivel"]).size().items()}

