"""Download the approved files into a dated snapshot. Uses the network: run only with Andrea's approval.

Usage: python3 -I pipeline/download.py            first snapshot
       python3 -I pipeline/download.py contours   outlines in their native reference system
       python3 -I pipeline/download.py province   rent, services, transport and terrain for the whole region
       python3 -I pipeline/download.py dogs       dog areas and veterinary centres
Existing files are never overwritten.
"""

import datetime
import hashlib
import json
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

SNAPSHOT = Path(__file__).resolve().parent.parent / "datos/snapshots/2026-11-25-municipal"
CKAN = "https://datos.comunidad.madrid/api/3/action/package_show?id="
DATASETS = (
    "alquiler_medio_mensual_viviendas_arrendadas_valor_catastral_municipios_mas_20000",
    "perceptores_salarios_por_edad_nacionalidad_y_sexo",
    "perceptores_asalariados_por_edad_nacionalidad_y_sexo",
    "spacm_bono_alquiler_joven_2022",
    "centros_educativos",
    "spacm_listado_bibliotecas_servicios_lectura",
    "poblacion_censada_por_edad_nacionalidad_y_sexo",
)
BOUNDARIES = "idem-unid-admin"
BOUNDARIES_URL = (
    "https://idem.comunidad.madrid/geoidem/ows?service=WFS&version=2.0.0&request=GetFeature"
    "&typeNames=UnidadesAdministrativas:IDEM_CM_UNID_ADMIN&outputFormat=application/json&srsName=EPSG:4326"
)
BOUNDARIES_META = {
    "title": "Divisiones Administrativas de la Comunidad de Madrid (IDEM)",
    "license": "CC BY 4.0",
}


CONTOURS = Path(__file__).resolve().parent.parent / "datos/snapshots/2026-11-25-contornos-25830"
NATIVE_URL = BOUNDARIES_URL.replace("EPSG:4326", "EPSG:25830")
CAPABILITIES_URL = "https://idem.comunidad.madrid/geoidem/ows?service=WFS&version=2.0.0&request=GetCapabilities"


def fetch(url):
    for attempt in (1, 2):
        try:
            request = urllib.request.Request(url, headers={"User-Agent": "DataMad2026-UDIT/1.0"})
            with urllib.request.urlopen(request, timeout=180) as response:
                return response.read()
        except OSError as error:
            print(f"attempt {attempt} failed: {url}: {error}")
            if attempt == 2:
                raise


def save(name, url, folder=SNAPSHOT):
    path = folder / name
    if not path.exists():
        path.write_bytes(fetch(url))
    data = path.read_bytes()
    stamp = datetime.datetime.fromtimestamp(path.stat().st_mtime).astimezone().isoformat(timespec="seconds")
    print(f"{name}: {len(data)} bytes")
    return {"file": name, "url": url, "downloaded": stamp, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def contours():
    """One new folder. The licence terms are copied from the capabilities document, which is not stored."""
    CONTOURS.mkdir(parents=True, exist_ok=True)
    manifest = CONTOURS / "MANIFIESTO.json"
    if manifest.exists():
        raise SystemExit("MANIFIESTO.json already exists, left untouched")
    entry = save(f"{BOUNDARIES}.geojson", NATIVE_URL, CONTOURS)
    if not json.loads((CONTOURS / entry["file"]).read_bytes())["crs"]["properties"]["name"].endswith("25830"):
        raise SystemExit("unexpected reference system")
    capabilities = fetch(CAPABILITIES_URL)
    declared = {}
    for tag in ("Fees", "AccessConstraints"):
        declared[tag] = re.search(rf"<ows:{tag}[^>]*>(.*?)</ows:{tag}>", capabilities.decode("utf-8"), re.S)[1].strip()
    terms = {"url": CAPABILITIES_URL, "read": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
             "sha256": hashlib.sha256(capabilities).hexdigest(), **declared}
    record = {"id": BOUNDARIES, **BOUNDARIES_META, **entry, "crs": "EPSG:25830", "declared_by_service": terms}
    manifest.write_text(json.dumps({"files": [record]}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(declared, ensure_ascii=False))


PROVINCE = Path(__file__).resolve().parent.parent / "datos/snapshots/2026-11-26-provincia"
PORTAL = "https://datos.comunidad.madrid/dataset/"
CRTM = "https://services5.arcgis.com/UxADft6QPcvFyDU1/arcgis/rest/services/{}/FeatureServer/0"
CRTM_QUERY = ("/query?where=1%3D1&outFields=CODIGOMUNICIPIO%2CCODIGOPROVINCIA%2CDENOMINACION"
              "&outSR=25830&geometryPrecision=0&f=geojson")
IDEM = ("https://idem.comunidad.madrid/geoidem/ows?service=WFS&version=2.0.0&request=GetFeature"
        "&typeNames={}&outputFormat=application/json&srsName=EPSG:25830")
WCS = "https://servicios.idee.es/wcs-inspire/mdt?service=WCS&version=2.0.1&request="
TERRAIN_URL = (WCS + "GetCoverage&CoverageId=Elevacion25830_200&subset=x(365000,496000)"
               "&subset=y(4415000,4558000)&format=image/tiff")
RENT_LICENSE = ("Reutilización con las condiciones del artículo 7 y el anexo del RD 1495/2011 (deducida de su "
                "artículo 8.1; el conjunto no trae licencia escrita)")


def declared(url):
    """Terms and dates read from the service itself. The answer is hashed, not stored."""
    answer = fetch(url)
    record = {"url": url, "read": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
              "sha256": hashlib.sha256(answer).hexdigest()}
    text = answer.decode("utf-8")
    if "api/3/action" in url:
        package = json.loads(text)["result"]
        record.update({k: package.get(k) for k in ("title", "license_id", "license_title", "metadata_modified")})
        record["resources"] = [{k: r.get(k) for k in ("url", "last_modified")} for r in package["resources"]]
    elif "arcgis" in url:
        layer = json.loads(text)
        record.update({k: layer.get(k) for k in ("name", "copyrightText", "maxRecordCount", "editingInfo")})
        record["count"] = json.loads(fetch(url.split("?")[0] + "/query?where=1%3D1&returnCountOnly=true&f=json"))["count"]
    else:
        for tag in ("Fees", "AccessConstraints"):
            found = re.search(rf"<(?:\w+:)?{tag}[^>]*>(.*?)</(?:\w+:)?{tag}>", text, re.S)
            record[tag] = found[1].strip() if found else None
    return record


def province():
    """The eleven files Andrea approved on 26 November. Nothing else is saved."""
    PROVINCE.mkdir(parents=True, exist_ok=True)
    manifest = PROVINCE / "MANIFIESTO.json"
    if manifest.exists():
        raise SystemExit("MANIFIESTO.json already exists, left untouched")
    wanted = [("alquiler-mivau", "VDP001_01.csv", "https://cdn.mivau.gob.es/portal-web-mivau/Datos_MIVAU/CSV/VDP001_01.csv",
               "Alquiler por municipio 2011 a 2024 (VDP001_01, Ministerio de Vivienda y Agenda Urbana)", RENT_LICENSE, None),
              ("relieve-ign-200", "relieve-ign-200.tif", TERRAIN_URL, "Modelo digital del terreno a 200 m (IGN)",
               "CC BY 4.0 scne.es", WCS + "GetCapabilities")]
    for ident, package, resource, name, title in (
            ("registro-sanitario", "d8a0a444-adf5-4c04-8999-0eac3de52cb7", "2948b4da-8b39-42b7-b667-779a5284f39d",
             "centros_servicios_establecimientos_sanitarios.csv", "Registro de centros, servicios y establecimientos sanitarios"),
            ("oficinas-farmacia", "2d682b1d-e2e8-4c6f-b902-7a3f108e2fb9", "904a161b-f339-4296-be61-1ae914494c89",
             "oficinas_farmacia.csv", "Oficinas de farmacia")):
        wanted.append((ident, name, f"{PORTAL}{package}/resource/{resource}/download/{name}", title, "cc-by",
                       CKAN + package))
    for ident, service, title in (("crtm-bus-interurbano", "M8_Red", "Paradas de autobús interurbano"),
                                  ("crtm-metro", "M4_Red", "Estaciones de metro"),
                                  ("crtm-cercanias", "M5_Red", "Estaciones de cercanías"),
                                  ("crtm-metro-ligero", "M10_Red", "Paradas de metro ligero")):
        wanted.append((ident, f"{ident}.geojson", CRTM.format(service) + CRTM_QUERY, f"{title} (CRTM)",
                       "Licencia de uso del CRTM, https://www.crtm.es/licencia-de-uso",
                       CRTM.format(service) + "?f=json"))
    for ident, layer, title in (
            ("idem-deporte", "ServiciosPublicos:IDEM_EIEL_INSTAL_DEPORTIVA_23", "Instalaciones deportivas, EIEL 2023"),
            ("idem-parques", "CubiertaTerrestre:IDEM_EIEL_PARQUE_23", "Parques, EIEL 2023"),
            ("idem-cultura", "ServiciosPublicos:IDEM_EIEL_CENT_CULTURAL_23", "Centros culturales, EIEL 2023")):
        wanted.append((ident, f"{ident}.geojson", IDEM.format(layer), f"{title} (IDEM)",
                       "CC BY 4.0 Comunidad de Madrid", CAPABILITIES_URL))
    assert len(wanted) == 11
    files, failed = [], []
    for ident, name, url, title, license_text, terms in wanted:
        try:
            record = {"id": ident, "title": title, "license": license_text, **save(name, url, PROVINCE)}
            if terms:
                record["declared_by_service"] = declared(terms)
            files.append(record)
        except (OSError, ValueError, KeyError) as error:
            failed.append(ident)
            print(f"FAILED {ident}: {error}")
    if failed:
        raise SystemExit(f"manifest not written, missing: {failed}")
    manifest.write_text(json.dumps({"files": files}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    for record in files:
        print(record["id"], json.dumps(record.get("declared_by_service"), ensure_ascii=False)[:700])
    print(f"manifest: {len(files)} files")


DOGS = Path(__file__).resolve().parent.parent / "datos/snapshots/2026-11-26-perro"
MADRID = "https://datos.madrid.es/api/3/action/package_show?id=300094-0-areas-caninas"
OVERPASS = "https://overpass-api.de/api/"
# Only the tags the map shows: no telephone, e-mail, web or owner is ever asked for.
OVERPASS_QUERY = ('[out:csv(::type,::id,::lat,::lon,"amenity","leisure","access","name","addr:street",'
                  '"addr:housenumber";true;"\\t")][timeout:150];'
                  'area["ISO3166-2"="ES-MD"]["boundary"="administrative"]->.region;'
                  '(nwr["leisure"="dog_park"](area.region);nwr["amenity"="veterinary"](area.region););out center;')


def dogs():
    """Dog areas and veterinary centres from open sources, approved by Andrea on 26 November."""
    DOGS.mkdir(parents=True, exist_ok=True)
    manifest = DOGS / "MANIFIESTO.json"
    if manifest.exists():
        raise SystemExit("MANIFIESTO.json already exists, left untouched")
    answer = fetch(MADRID)
    package = json.loads(answer)["result"]
    resource = next(r for r in package["resources"] if r["name"] == "300094-2-areas-caninas" and r["format"] == "CSV")
    terms = {"url": MADRID, "read": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
             "sha256": hashlib.sha256(answer).hexdigest(),
             **{k: package.get(k) for k in ("title", "license_id", "license_title", "license_url", "metadata_modified")}}
    madrid = {"id": "ayto-areas-caninas", "title": "Áreas caninas (Ayuntamiento de Madrid)",
              "license": package["license_title"],
              **save("areas-caninas.csv", resource["url"], DOGS),
              "page": "https://datos.madrid.es/dataset/300094-0-areas-caninas", "declared_by_service": terms}
    query = urllib.parse.urlencode({"data": OVERPASS_QUERY})
    osm = {"id": "osm-perro", "title": "Zonas caninas y veterinarios de la Comunidad de Madrid (OpenStreetMap)",
           "license": "ODbL 1.0, © OpenStreetMap",
           **save("osm-perro.tsv", f"{OVERPASS}interpreter?{query}", DOGS),
           "page": "https://www.openstreetmap.org/copyright", "query": OVERPASS_QUERY,
           "declared_by_service": {"url": OVERPASS + "timestamp", "data_until": fetch(OVERPASS + "timestamp").decode().strip()}}
    manifest.write_text(json.dumps({"files": [madrid, osm]}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def main():
    SNAPSHOT.mkdir(parents=True, exist_ok=True)
    files, failed = [], []
    for ident in DATASETS + (BOUNDARIES,):
        try:
            if ident == BOUNDARIES:
                entry = save(f"{ident}.geojson", BOUNDARIES_URL)
                json.loads((SNAPSHOT / entry["file"]).read_bytes())
                files.append({"id": ident, **BOUNDARIES_META, **entry})
                continue
            meta_entry = save(f"{ident}.meta.json", CKAN + ident)
            package = json.loads((SNAPSHOT / meta_entry["file"]).read_bytes())["result"]
            resources = [r for r in package["resources"] if (r.get("format") or "").upper() == "CSV"]
            if len(resources) != 1:
                raise ValueError(f"{ident}: expected one CSV resource, found {len(resources)}")
            entry = save(f"{ident}.csv", resources[0]["url"])
            common = {"id": ident, "title": package["title"], "license": package["license_id"],
                      "page": f"https://datos.comunidad.madrid/dataset/{ident}"}
            files += [{**common, **entry}, {**common, **meta_entry}]
        except (OSError, ValueError, KeyError) as error:
            failed.append(ident)
            print(f"FAILED {ident}: {error}")
    manifest = SNAPSHOT / "MANIFIESTO.json"
    if failed:
        raise SystemExit(f"manifest not written, missing: {failed}")
    if manifest.exists():
        raise SystemExit("MANIFIESTO.json already exists, left untouched")
    manifest.write_text(json.dumps({"files": files}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"manifest: {len(files)} files")


if __name__ == "__main__":
    {"contours": contours, "province": province, "dogs": dogs}.get(" ".join(sys.argv[1:]), main)()
