#!/usr/bin/env python3
"""
caso_carreteras.py · DATAMAD 2026, diapositiva 64

Hace lo que pide el «Pruébalo» de la diapositiva:
  1. Muestra el dataset «Indicadores de red y motorización» (901007).
  2. Busca en datos.comunidad.madrid todos los datasets sobre carreteras.
  3. Indica cuáles tienen datos geográficos (GeoJSON, WMS, WFS, SHP, KML…).
  4. Con --mapa, descarga el primer GeoJSON encontrado y genera un mapa HTML
     (la nota de la diapositiva: «pedir a la IA que pinte en un mapa…»).

Uso:
  python caso_carreteras.py
  python caso_carreteras.py --mapa
  python caso_carreteras.py --buscar "red viaria"

Salida: carreteras_datasets.csv  (y mapa_carreteras.html con --mapa)
Requisitos: pip install requests
"""

import csv
import json
import sys

import requests

CKAN_BASES = ["https://datos.comunidad.madrid/api/3/action",
              "https://datos.comunidad.madrid/catalogo/api/3/action"]
DATASET_INDICADORES = "901007"
TIMEOUT = 60
POR_PAGINA = 100

# Formatos geográficos: seguro / posible (un ZIP puede llevar un SHP dentro)
GEO_SEGURO = {"GEOJSON", "WMS", "WFS", "SHP", "SHAPEFILE", "KML", "KMZ", "GML",
              "GPKG", "GEOPACKAGE", "WMTS", "ESRI REST", "GEOJSON-LD"}
GEO_POSIBLE = {"ZIP", "JSON"}


def argumento(nombre, defecto=None):
    if nombre in sys.argv:
        i = sys.argv.index(nombre)
        if i + 1 < len(sys.argv) and not sys.argv[i + 1].startswith("--"):
            return sys.argv[i + 1]
    return defecto


def ckan(accion, **params):
    ultimo_error = None
    for base in CKAN_BASES:
        try:
            r = requests.get(f"{base}/{accion}", params=params, timeout=TIMEOUT)
            datos = r.json()
            if datos.get("success"):
                return datos["result"]
            ultimo_error = datos.get("error")
        except (requests.RequestException, ValueError) as e:
            ultimo_error = e
    raise RuntimeError(f"{accion} falló: {ultimo_error}")


def buscar_todos(consulta):
    """package_search paginado: devuelve todos los resultados."""
    datasets, inicio = [], 0
    while True:
        r = ckan("package_search", q=consulta, rows=POR_PAGINA, start=inicio)
        datasets += r["results"]
        inicio += POR_PAGINA
        if inicio >= r["count"] or not r["results"]:
            return datasets, r["count"]


def formato(recurso):
    f = (recurso.get("format") or "").upper().strip()
    url = (recurso.get("url") or "").lower()
    if not f:
        for ext, nombre in ((".geojson", "GEOJSON"), (".kml", "KML"), (".kmz", "KMZ"),
                            (".shp", "SHP"), (".zip", "ZIP"), (".csv", "CSV"),
                            (".json", "JSON"), (".xlsx", "XLSX")):
            if url.split("?")[0].endswith(ext):
                return nombre
    if "service=wms" in url or "/wms" in url:
        return "WMS"
    if "service=wfs" in url or "/wfs" in url:
        return "WFS"
    if "geojson" in url or "geojson" in (recurso.get("name") or "").lower():
        return "GEOJSON"
    return f or "?"


def clasificar(dataset):
    formatos = sorted({formato(r) for r in dataset.get("resources", [])})
    seguros = [f for f in formatos if f in GEO_SEGURO]
    posibles = [f for f in formatos if f in GEO_POSIBLE]
    if seguros:
        return "sí", formatos, seguros
    if posibles:
        return "posible", formatos, posibles
    return "no", formatos, []


def generar_mapa(datasets):
    """Descarga el primer GeoJSON y crea un mapa Leaflet en HTML."""
    for d in datasets:
        for r in d.get("resources", []):
            if formato(r) != "GEOJSON":
                continue
            try:
                geo = requests.get(r["url"], timeout=TIMEOUT).json()
                if geo.get("type") not in ("FeatureCollection", "Feature"):
                    continue
            except (requests.RequestException, ValueError):
                continue
            n = len(geo.get("features", [])) if geo.get("type") == "FeatureCollection" else 1
            html = f"""<!doctype html><html lang="es"><head><meta charset="utf-8">
<title>{d.get('title')}</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<style>html,body,#mapa{{height:100%;margin:0}}
#titulo{{position:absolute;z-index:1000;top:10px;left:50px;background:#fff;padding:6px 10px;
font:14px sans-serif;border-radius:6px;box-shadow:0 1px 4px #0004}}</style></head>
<body><div id="titulo">{d.get('title')} · {n} elementos</div><div id="mapa"></div><script>
const mapa = L.map('mapa').setView([40.42, -3.70], 9);
L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png',
  {{attribution: '© OpenStreetMap'}}).addTo(mapa);
const capa = L.geoJSON({json.dumps(geo, ensure_ascii=False)}, {{
  onEachFeature: (f, l) => l.bindPopup('<pre>' +
     JSON.stringify(f.properties, null, 1).slice(0, 800) + '</pre>')
}}).addTo(mapa);
try {{ mapa.fitBounds(capa.getBounds()); }} catch (e) {{}}
</script></body></html>"""
            with open("mapa_carreteras.html", "w", encoding="utf-8") as f:
                f.write(html)
            print(f"\nMapa: mapa_carreteras.html ({n} elementos de «{d.get('title')}»)")
            print("Ábrelo en el navegador.")
            return
    print("\nNo se encontró ningún GeoJSON descargable para el mapa.")
    print("Prueba con los recursos WMS/SHP en un SIG (p. ej. QGIS).")


def main():
    consulta = argumento("--buscar", "carreteras")

    print("=== Dataset de la diapositiva")
    try:
        d = ckan("package_show", id=DATASET_INDICADORES)
        print(f"{d.get('title')}  ·  licencia: {d.get('license_title')}")
        print((d.get("notes") or "")[:300])
        for r in d.get("resources", []):
            print(f"  - [{formato(r)}] {r.get('name')}")
    except RuntimeError as e:
        print(f"No disponible: {e}")

    print(f"\n=== Búsqueda «{consulta}» en datos.comunidad.madrid")
    datasets, total = buscar_todos(consulta)
    print(f"{total} datasets encontrados\n")

    filas = []
    for d in datasets:
        geo, formatos, geo_formatos = clasificar(d)
        filas.append({"geografico": geo, "titulo": d.get("title"), "id": d.get("name"),
                      "formatos_geo": ", ".join(geo_formatos),
                      "todos_los_formatos": ", ".join(formatos),
                      "url": f"https://datos.comunidad.madrid/dataset/{d.get('name')}"})
    orden = {"sí": 0, "posible": 1, "no": 2}
    filas.sort(key=lambda f: (orden[f["geografico"]], f["titulo"] or ""))

    for f in filas:
        marca = {"sí": "🗺 ", "posible": "? ", "no": "  "}[f["geografico"]]
        extra = f"  [{f['formatos_geo']}]" if f["formatos_geo"] else ""
        print(f"{marca}{(f['titulo'] or '')[:80]}{extra}")

    n_si = sum(f["geografico"] == "sí" for f in filas)
    n_pos = sum(f["geografico"] == "posible" for f in filas)
    print(f"\nCon datos geográficos: {n_si} · posibles (ZIP/JSON, revisar): {n_pos} "
          f"· sin datos geográficos: {len(filas) - n_si - n_pos}")

    with open("carreteras_datasets.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(filas[0].keys()) if filas else ["titulo"],
                           delimiter=";")
        w.writeheader()
        w.writerows(filas)
    print("Guardado: carreteras_datasets.csv")

    if "--mapa" in sys.argv:
        generar_mapa([d for d in datasets if clasificar(d)[0] == "sí"])


if __name__ == "__main__":
    main()
