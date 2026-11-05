#!/usr/bin/env python3
"""
caso_turismo.py · DATAMAD 2026, diapositiva 66

Hace lo que pide el «Pruébalo» de la diapositiva:
  1. Busca en datos.comunidad.madrid datasets de «turismo» y «alojamientos».
  2. Revisa sus recursos y lista los que incluyen coordenadas
     (formatos geográficos o columnas tipo latitud/longitud, UTM X/Y…).
  3. Con --poi, convierte el primer dataset con latitud/longitud al modelo
     PointOfInterest de Smart Data Models (la nota de la diapositiva) y, si
     está instalado pysmartdatamodels, valida las primeras entidades.

Uso:
  python caso_turismo.py
  python caso_turismo.py --poi
  python caso_turismo.py --buscar "museos" --poi

Salida: turismo_datasets.csv  (y turismo_PointOfInterest.json con --poi)
Requisitos: pip install requests
Opcional:   pip install pysmartdatamodels   (validación con --poi)
"""

import csv
import io
import json
import re
import sys
import unicodedata

import requests

CKAN_BASES = ["https://datos.comunidad.madrid/api/3/action",
              "https://datos.comunidad.madrid/catalogo/api/3/action"]
CONSULTAS = ["turismo", "alojamientos"]
TIMEOUT = 60
MAX_DATASETS = 60          # cuántos datasets revisar como máximo
BYTES_MUESTRA = 64 * 1024  # solo se descarga el principio de cada fichero
VALIDAR = 5

GEO_FORMATOS = {"GEOJSON", "KML", "KMZ", "SHP", "WMS", "WFS", "GML", "GPKG"}
TABULARES = {"CSV", "JSON", "XLS", "XLSX", "TSV"}
LAT = ("latitud", "latitude", "lat", "coordenada_y", "y_wgs84")
LON = ("longitud", "longitude", "lon", "lng", "long", "coordenada_x", "x_wgs84")
UTM = ("utm_x", "utm_y", "coordenada x", "coordenada y", "x_utm", "y_utm", "xutm",
       "yutm", "x_etrs89", "y_etrs89", "coord_x", "coord_y")


def normal(texto):
    t = unicodedata.normalize("NFD", str(texto).lower().strip())
    return "".join(c for c in t if unicodedata.category(c) != "Mn")


def argumento(nombre, defecto=None):
    if nombre in sys.argv:
        i = sys.argv.index(nombre)
        if i + 1 < len(sys.argv) and not sys.argv[i + 1].startswith("--"):
            return sys.argv[i + 1]
    return defecto


def ckan(accion, **params):
    for base in CKAN_BASES:
        try:
            datos = requests.get(f"{base}/{accion}", params=params, timeout=TIMEOUT).json()
            if datos.get("success"):
                return datos["result"]
        except (requests.RequestException, ValueError):
            continue
    raise RuntimeError(f"La API CKAN no respondió a {accion}")


# ---------------------------------------------------------------- inspección
def muestra(url):
    """Primeros KB de un fichero (sin descargarlo entero)."""
    try:
        with requests.get(url, stream=True, timeout=TIMEOUT) as r:
            r.raise_for_status()
            datos = b""
            for trozo in r.iter_content(8192):
                datos += trozo
                if len(datos) >= BYTES_MUESTRA:
                    break
    except requests.RequestException:
        return None
    for cod in ("utf-8-sig", "latin-1"):
        try:
            return datos.decode(cod)
        except UnicodeDecodeError:
            continue
    return None


def columnas_de(texto):
    """Nombres de columna de un CSV o de los objetos de un JSON."""
    t = texto.lstrip()
    if t[:1] in "[{":
        nombres = set(re.findall(r'"([^"\\]{1,60})"\s*:', t[:20000]))
        return sorted(nombres)
    primera = t.splitlines()[0] if t else ""
    sep = max(";,\t|", key=primera.count)
    return [c.strip().strip('"') for c in primera.split(sep)]


def tipo_coordenadas(columnas):
    norm = {normal(c): c for c in columnas}
    lat = next((norm[n] for n in norm if n in LAT or n.startswith("latitud")), None)
    lon = next((norm[n] for n in norm if n in LON or n.startswith("longitud")), None)
    if lat and lon:
        return "lat/lon", [lat, lon]
    utm = [norm[n] for n in norm if n in UTM or re.fullmatch(r"(coordenada|coord)?[ _]?[xy]", n)]
    if len(utm) >= 2:
        return "UTM/XY", utm[:2]
    geo = [norm[n] for n in norm if n in ("geometry", "geometria", "geo", "coordinates",
                                          "coordenadas", "geom", "wkt")]
    if geo:
        return "geometría", geo[:1]
    return None, []


def analizar(dataset):
    """Devuelve (coordenadas, detalle, recurso con lat/lon, columnas)."""
    recursos = dataset.get("resources", [])
    formatos = sorted({(r.get("format") or "?").upper() for r in recursos})
    geo = [f for f in formatos if f in GEO_FORMATOS]
    for r in recursos:
        if (r.get("format") or "").upper() not in ("CSV", "JSON"):
            continue
        texto = muestra(r.get("url", ""))
        if not texto:
            continue
        tipo, cols = tipo_coordenadas(columnas_de(texto))
        if tipo:
            return "sí", f"{tipo}: {', '.join(cols)}", (r if tipo == "lat/lon" else None), cols
    if geo:
        return "sí", f"formato {', '.join(geo)}", None, []
    if any(f in TABULARES for f in formatos):
        return "no", "sin columnas de coordenadas", None, []
    return "?", f"formatos {', '.join(formatos)}", None, []


# ---------------------------------------------------------------- PointOfInterest
def leer_csv_json(url):
    r = requests.get(url, timeout=TIMEOUT)
    r.raise_for_status()
    for cod in ("utf-8-sig", "latin-1"):
        try:
            texto = r.content.decode(cod)
            break
        except UnicodeDecodeError:
            continue
    if texto.lstrip()[:1] in "[{":
        datos = json.loads(texto)
        if isinstance(datos, dict):
            datos = next((v for v in datos.values() if isinstance(v, list)), [])
        return [d for d in datos if isinstance(d, dict)]
    primera = texto.splitlines()[0]
    sep = max(";,\t|", key=primera.count)
    return list(csv.DictReader(io.StringIO(texto), delimiter=sep))


def num(v):
    try:
        return float(str(v).replace(",", "."))
    except (TypeError, ValueError):
        return None


def a_point_of_interest(fila, i, col_lat, col_lon, dataset):
    norm = {normal(k): k for k in fila}

    def campo(*pistas):
        for p in pistas:
            for n, k in norm.items():
                if p in n and str(fila.get(k, "")).strip():
                    return str(fila[k]).strip()
        return None

    lat, lon = num(fila.get(col_lat)), num(fila.get(col_lon))
    if lat is None or lon is None or not (-90 <= lat <= 90 and -180 <= lon <= 180):
        return None
    entidad = {
        "id": f"urn:ngsi-ld:PointOfInterest:madrid-{dataset.get('name')}-{i}",
        "type": "PointOfInterest",
        "name": campo("nombre", "denominacion", "titulo", "name") or f"Punto {i}",
        "category": ["tourism"],
        "location": {"type": "Point", "coordinates": [round(lon, 6), round(lat, 6)]},
        "dataProvider": "Comunidad de Madrid",
        "source": f"https://datos.comunidad.madrid/dataset/{dataset.get('name')}",
    }
    direccion = {k: v for k, v in {
        "streetAddress": campo("direccion", "domicilio", "calle", "via"),
        "addressLocality": campo("municipio", "localidad", "poblacion"),
        "postalCode": campo("codigo postal", "cod_postal", "cp", "postal"),
        "addressRegion": "Comunidad de Madrid", "addressCountry": "ES"}.items() if v}
    if len(direccion) > 2:
        entidad["address"] = direccion
    descripcion = campo("descripcion", "tipo", "categoria", "clase")
    if descripcion:
        entidad["description"] = descripcion[:500]
    web = campo("web", "url", "pagina")
    if web and web.startswith("http"):
        entidad["contactPoint"] = {"url": web}
    return entidad


def convertir_poi(dataset, recurso, cols):
    print(f"\n=== PointOfInterest a partir de «{dataset.get('title')}»")
    filas = leer_csv_json(recurso["url"])
    col_lat, col_lon = cols
    entidades = [e for i, f in enumerate(filas, 1)
                 if (e := a_point_of_interest(f, i, col_lat, col_lon, dataset))]
    print(f"{len(filas)} filas -> {len(entidades)} entidades PointOfInterest")
    if not entidades:
        return
    with open("turismo_PointOfInterest.json", "w", encoding="utf-8") as f:
        json.dump(entidades, f, ensure_ascii=False, indent=2)
    print("Primera entidad:")
    print(json.dumps(entidades[0], ensure_ascii=False, indent=2))
    print("Guardado: turismo_PointOfInterest.json")

    try:
        from pysmartdatamodels import pysmartdatamodels as sdm
    except ImportError:
        print("(instala pysmartdatamodels para validarlas contra el modelo)")
        return
    print(f"\nValidación con pysmartdatamodels (primeras {VALIDAR}):")
    for e in entidades[:VALIDAR]:
        try:
            r = sdm.validate_payload("PointOfInterest", "dataModel.PointOfInterest", e)
            ok = r.get("result") if isinstance(r, dict) else r
            print(f"  {'✔' if ok else '✘'} {e['name'][:50]}: "
                  f"{r.get('details') if isinstance(r, dict) else r}")
        except Exception as ex:
            print(f"  ✘ {e['name'][:50]}: {ex}")


# ---------------------------------------------------------------- main
def main():
    consultas = [argumento("--buscar")] if argumento("--buscar") else CONSULTAS
    vistos = {}
    for q in consultas:
        r = ckan("package_search", q=q, rows=MAX_DATASETS)
        print(f"Búsqueda «{q}»: {r['count']} datasets")
        for d in r["results"]:
            vistos.setdefault(d["id"], d)
    datasets = list(vistos.values())[:MAX_DATASETS]
    print(f"Revisando {len(datasets)} datasets (solo el principio de cada fichero)…\n")

    filas, candidato = [], None
    for d in datasets:
        coord, detalle, recurso, cols = analizar(d)
        marca = {"sí": "📍", "no": "  ", "?": "? "}[coord]
        print(f"{marca} {(d.get('title') or '')[:75]:<75} {detalle}")
        filas.append({"coordenadas": coord, "titulo": d.get("title"), "detalle": detalle,
                      "url": f"https://datos.comunidad.madrid/dataset/{d.get('name')}"})
        if recurso and not candidato:
            candidato = (d, recurso, cols)

    con = [f for f in filas if f["coordenadas"] == "sí"]
    print(f"\nCon coordenadas: {len(con)} de {len(filas)}")
    sin = [f for f in filas if f["coordenadas"] == "no"]
    if sin:
        print(f"Sin coordenadas: {len(sin)} (se podrían geocodificar por dirección)")

    filas.sort(key=lambda f: {"sí": 0, "?": 1, "no": 2}[f["coordenadas"]])
    with open("turismo_datasets.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=["coordenadas", "titulo", "detalle", "url"],
                           delimiter=";")
        w.writeheader()
        w.writerows(filas)
    print("Guardado: turismo_datasets.csv")

    if "--poi" in sys.argv:
        if candidato:
            convertir_poi(*candidato)
        else:
            print("\nNingún dataset tiene columnas de latitud/longitud para --poi.")


if __name__ == "__main__":
    main()