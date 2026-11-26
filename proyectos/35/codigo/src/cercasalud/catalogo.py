"""Catálogo de archivos que la orden `fetch` sabe descargar.

Cada URL procede de los manifiestos de adquisición del 11 al 13/11/2026 (copiados a
DATAMAD26/datos/crudos/<fuente>/*.source.json). Las licencias son las confirmadas en
fases/H0_candidatura/agente_b/LICENCIAS.md. Las fuentes que no se descargan con una URL
directa (extracción del MITECO, páginas municipales, CALORMAD, que exige otra herramienta)
no están aquí: se documentan como adquisición manual.
"""

from dataclasses import dataclass

ARCGIS = "https://www.arcgis.com/sharing/rest/content/items/{}/data"
LICENCIA_CRTM = "Licencia de datos abiertos del CRTM; actualización exigida pendiente (SPEC F-17)"

WFS_SECCIONES_2025 = (
    "https://www.ine.es/geoserver/wfs?service=WFS&version=2.0.0&request=GetFeature"
    "&typeNames=WMS_INE_SECCIONES_G01%3ASecciones_2025&outputFormat=application%2Fjson"
    "&srsName=EPSG%3A25830&CQL_FILTER=CPRO%3D%2728%27&count=10000"
)


@dataclass(frozen=True)
class ArchivoFuente:
    """Un archivo descargable de una fuente, con su procedencia y licencia."""

    fuente: str
    nombre: str
    url: str
    organismo: str
    licencia: str


def _gtfs(red: str, item: str) -> ArchivoFuente:
    """Construye la entrada de un GTFS publicado por el CRTM en ArcGIS."""
    return ArchivoFuente("crtm_gtfs", f"gtfs_{red}.zip", ARCGIS.format(item),
                         "Consorcio Regional de Transportes de Madrid", LICENCIA_CRTM)


CATALOGO: tuple[ArchivoFuente, ...] = (
    ArchivoFuente(
        "sanidad", "centros_servicios_establecimientos_sanitarios.csv",
        "https://datos.comunidad.madrid/dataset/d8a0a444-adf5-4c04-8999-0eac3de52cb7/resource/"
        "2948b4da-8b39-42b7-b667-779a5284f39d/download/centros_servicios_establecimientos_sanitarios.csv",
        "Comunidad de Madrid", "CC BY 4.0; la columna NIF se elimina en la ingesta"),
    ArchivoFuente(
        "zonas_basicas_salud", "zonas_basicas_salud.zip",
        "https://datos.comunidad.madrid/dataset/924044d0-b75e-402c-8c13-96ace11da0ff/resource/"
        "79a88736-b7c9-44e9-aca4-3b1d145ec5f0/download/zonas_basicas_salud.zip",
        "Comunidad de Madrid, DG de Salud Pública", "CC BY 4.0"),
    ArchivoFuente(
        "ine_69213", "69213.csv", "https://www.ine.es/jaxiT3/files/t/es/csv_bdsc/69213.csv",
        "INE", "CC BY 4.0"),
    ArchivoFuente(
        "ine_secciones_2025", "secciones_2025_madrid.geojson", WFS_SECCIONES_2025,
        "INE", "CC BY 4.0"),
    ArchivoFuente(
        "madrid_proteccion_civil", "RECURSOS_PROTECCION_CIVIL.zip",
        "https://geoportal.madrid.es/fsdescargas/IDEAM_WBGEOPORTAL/PROTECCION_CIVIL/RECURSOS_PROTECCION_CIVIL.zip",
        "Ayuntamiento de Madrid", "Condiciones generales de reutilización del Ayuntamiento de Madrid"),
    _gtfs("metro", "5c7f2951962540d69ffe8f640d94c246"),
    _gtfs("emt", "868df0e58fca47e79b942902dffd7da0"),
    _gtfs("interurbanos", "885399f83408473c8d815e40c5e702b7"),
    _gtfs("urbanos", "357e63c2904f43aeb5d8a267a64346d8"),
    _gtfs("ligero", "aaed26cc0ff64b0c947ac0bc3e033196"),
    _gtfs("cercanias", "1a25440bf66f499bae2657ec7fb40144"),
    ArchivoFuente(
        "osm", "madrid-261112.osm.pbf",
        "https://download.geofabrik.de/europe/spain/madrid-261112.osm.pbf",
        "OpenStreetMap contributors (extracto de Geofabrik GmbH)", "ODbL 1.0"),
    # Refugios ampliados (decisión del usuario del 22/11/2026): las dos fuentes oficiales a las que remiten los
    # anexos V y V-A del CALORMAD 2026. Solo capa de «refresco e hidratación»; no son refugios climatizados.
    ArchivoFuente(
        "madrid_piscinas", "210227-0-piscinas-publicas-csv.csv",
        "https://datos.madrid.es/dataset/210227-0-piscinas-publicas/resource/210227-0-piscinas-publicas-csv/"
        "download/210227-0-piscinas-publicas-csv.csv",
        "Ayuntamiento de Madrid", "CC BY 4.0"),
    ArchivoFuente(
        "madrid_fuentes", "300051-26-fuentes.csv",
        "https://datos.madrid.es/dataset/300051-0-fuentes/resource/300051-26-fuentes/download/300051-26-fuentes.csv",
        "Ayuntamiento de Madrid", "CC BY 4.0"),
    # Horario general publicado de los centros deportivos y las salas de estudio de la ampliación de B (23/11/2026):
    # los del Anexo VIII solo traían el horario de taquilla o el de la revisión del 13/11.
    ArchivoFuente(
        "madrid_polideportivos", "200186-0-polideportivos-csv.csv",
        "https://datos.madrid.es/dataset/200186-0-polideportivos/resource/200186-0-polideportivos-csv/"
        "download/200186-0-polideportivos-csv.csv",
        "Ayuntamiento de Madrid", "CC BY 4.0"),
    ArchivoFuente(
        "madrid_salas_estudio", "217921-1-salas-estudio-csv.csv",
        "https://datos.madrid.es/dataset/217921-0-salas-estudio/resource/217921-1-salas-estudio-csv/"
        "download/217921-1-salas-estudio-csv.csv",
        "Ayuntamiento de Madrid", "CC BY 4.0"),
    # Directorio de bibliotecas de la Comunidad de Madrid (decisión del usuario del 23/11/2026, propuesta 3 de
    # `docs/investigacion_iniciativas_20261123/INFORME.md`): solo en el mapa, fuera de Madrid capital, como
    # «potencial». No trae coordenadas: se ubican casándolas con OpenStreetMap.
    ArchivoFuente(
        "cm_bibliotecas", "spacm_listado_bibliotecas_servicios_lectura.csv",
        "https://datos.comunidad.madrid/dataset/e6a74331-d329-4ba2-8bb9-6be2669417a2/resource/"
        "c7a913c5-5bdf-4ba6-b3a9-4c14c89d555a/download/spacm_listado_bibliotecas_servicios_lectura.csv",
        "Comunidad de Madrid", "CC BY 4.0 (ficha CKAN: cc-by, legalcode 4.0)"),
    # Solo fondo de contexto de la página web (resto de España y países vecinos, sin datos):
    # provincias y regiones de primer nivel a escala 1:10 millones.
    ArchivoFuente(
        "natural_earth", "ne_10m_admin_1_states_provinces.zip",
        "https://naciscdn.org/naturalearth/10m/cultural/ne_10m_admin_1_states_provinces.zip",
        "Natural Earth", "Dominio público (https://www.naturalearthdata.com/about/terms-of-use/)"),
)


def fuentes_disponibles() -> list[str]:
    """Nombres de las fuentes del catálogo, sin repetir y en orden."""
    return list(dict.fromkeys(archivo.fuente for archivo in CATALOGO))


def archivos_de(fuentes: list[str] | None) -> list[ArchivoFuente]:
    """Archivos del catálogo de las fuentes pedidas (todas si no se pide ninguna)."""
    if not fuentes:
        return list(CATALOGO)
    desconocidas = set(fuentes) - set(fuentes_disponibles())
    if desconocidas:
        raise ValueError(f"Fuentes desconocidas: {sorted(desconocidas)}")
    return [archivo for archivo in CATALOGO if archivo.fuente in fuentes]
