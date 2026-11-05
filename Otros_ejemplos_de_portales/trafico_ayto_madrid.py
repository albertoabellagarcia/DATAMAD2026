#!/usr/bin/env python3
"""
Madrid real-time traffic data (Ayuntamiento de Madrid).

Dataset: "Tráfico. Datos del tráfico en tiempo real"
Catalogue: https://datos.gob.es/es/catalogo/l01280796-trafico-datos-del-trafico-en-tiempo-real

How it works:
  1. Asks the datos.gob.es API (apidata) for the dataset's distributions
     and finds the URL of the real-time XML file.
  2. Downloads the XML (updated about every 5 minutes) and parses every
     measuring point (<pm>).
  3. Saves the data as JSON and CSV, with a timestamp in the file name.

Usage:
  python trafico_madrid_tiempo_real.py            # one snapshot
  python trafico_madrid_tiempo_real.py --loop     # new snapshot every 5 min
  python trafico_madrid_tiempo_real.py --loop 600 # every 600 seconds

Requirements: pip install requests
Optional:     pip install pyproj   (adds latitude/longitude to each point)
"""

import csv
import json
import sys
import time
import xml.etree.ElementTree as ET
from datetime import datetime

import requests

DATASET_ID = "l01280796-trafico-datos-del-trafico-en-tiempo-real"
APIDATA_URL = f"https://datos.gob.es/apidata/catalog/dataset/{DATASET_ID}.json"

# Used only if the catalogue API is unavailable
FALLBACK_XML_URL = "https://informo.madrid.es/informo/tmadrid/pm.xml"

DEFAULT_INTERVAL = 300  # seconds (the source updates every ~5 minutes)
TIMEOUT = 60

SERVICE_LEVELS = {0: "fluido", 1: "lento", 2: "retenciones", 3: "congestión"}
NUMERIC_FIELDS = {"intensidad", "ocupacion", "carga", "nivelServicio",
                  "intensidadSat", "velocidad", "st_x", "st_y"}

session = requests.Session()
session.headers.update({"User-Agent": "datamad-trafico/1.0",
                        "Accept": "application/json"})


# ---------------------------------------------------------------- 1. catalogue API
def find_urls(obj):
    """Collect every accessURL / downloadURL in the API response."""
    urls = []
    if isinstance(obj, dict):
        for key, value in obj.items():
            if key in ("accessURL", "downloadURL"):
                values = value if isinstance(value, list) else [value]
                for v in values:
                    if isinstance(v, dict):
                        v = v.get("_about") or v.get("value")
                    if isinstance(v, str):
                        urls.append(v)
            else:
                urls.extend(find_urls(value))
    elif isinstance(obj, list):
        for item in obj:
            urls.extend(find_urls(item))
    return urls


def get_xml_url():
    """Return the real-time XML URL published in the catalogue."""
    try:
        r = session.get(APIDATA_URL, timeout=TIMEOUT)
        r.raise_for_status()
        urls = find_urls(r.json())
        print(f"Catalogue API: {len(urls)} distribution URL(s) found")
        for u in urls:
            print(f"  - {u}")
        # Prefer an XML file; skip documentation PDFs and web pages
        for u in urls:
            if u.lower().endswith(".xml"):
                return u
    except (requests.RequestException, ValueError) as e:
        print(f"Catalogue API unavailable ({e})")
    print(f"Using known data URL: {FALLBACK_XML_URL}")
    return FALLBACK_XML_URL


# ---------------------------------------------------------------- 2. download + parse
def to_number(text):
    """'436008,175' -> 436008.175 ; '80' -> 80 ; otherwise the original text."""
    if text is None:
        return None
    t = text.strip().replace(",", ".")
    try:
        n = float(t)
        return int(n) if n.is_integer() and "." not in t else n
    except ValueError:
        return text.strip()


def parse_xml(content):
    root = ET.fromstring(content)  # respects the encoding declared in the XML
    timestamp = root.findtext("fecha_hora")
    points = []
    for pm in root.iter("pm"):
        point = {}
        for child in pm:
            value = child.text.strip() if child.text else None
            point[child.tag] = to_number(value) if child.tag in NUMERIC_FIELDS else value
        level = point.get("nivelServicio")
        if isinstance(level, int):
            point["nivelServicio_texto"] = SERVICE_LEVELS.get(level, "desconocido")
        point["fecha_hora"] = timestamp
        points.append(point)
    return timestamp, points


def add_lat_lon(points):
    """Convert UTM (EPSG:25830) coordinates to lat/lon if pyproj is installed."""
    try:
        from pyproj import Transformer
    except ImportError:
        return False
    tr = Transformer.from_crs("EPSG:25830", "EPSG:4326", always_xy=True)
    for p in points:
        x, y = p.get("st_x"), p.get("st_y")
        if isinstance(x, (int, float)) and isinstance(y, (int, float)):
            lon, lat = tr.transform(x, y)
            p["longitud"], p["latitud"] = round(lon, 6), round(lat, 6)
    return True


# ---------------------------------------------------------------- 3. save
def save(points, timestamp):
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base = f"trafico_madrid_{stamp}"

    with open(f"{base}.json", "w", encoding="utf-8") as f:
        json.dump({"fecha_hora": timestamp, "total": len(points), "puntos": points},
                  f, ensure_ascii=False, indent=2)

    fields = sorted({k for p in points for k in p})
    with open(f"{base}.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fields, delimiter=";")
        w.writeheader()
        w.writerows(points)

    return base


def summary(points):
    levels = {}
    for p in points:
        name = p.get("nivelServicio_texto", "sin dato")
        levels[name] = levels.get(name, 0) + 1
    errors = sum(1 for p in points if p.get("error") == "S")
    print("  Service level:", ", ".join(f"{k}: {v}" for k, v in sorted(levels.items())))
    print(f"  Points reporting an error: {errors}")


def snapshot(xml_url):
    r = session.get(xml_url, timeout=TIMEOUT)
    r.raise_for_status()
    timestamp, points = parse_xml(r.content)
    coords = add_lat_lon(points)
    base = save(points, timestamp)
    print(f"\n[{datetime.now():%H:%M:%S}] Data time: {timestamp} | "
          f"{len(points)} measuring points")
    summary(points)
    print(f"  Saved: {base}.json and {base}.csv"
          + ("" if coords else "  (install pyproj to add lat/lon)"))


# ---------------------------------------------------------------- main
def main():
    loop = "--loop" in sys.argv
    interval = DEFAULT_INTERVAL
    if loop:
        i = sys.argv.index("--loop")
        if i + 1 < len(sys.argv) and sys.argv[i + 1].isdigit():
            interval = int(sys.argv[i + 1])

    xml_url = get_xml_url()

    while True:
        try:
            snapshot(xml_url)
        except (requests.RequestException, ET.ParseError) as e:
            print(f"Error getting data: {e}")
        if not loop:
            break
        print(f"  Next update in {interval} s (Ctrl+C to stop)")
        try:
            time.sleep(interval)
        except KeyboardInterrupt:
            print("\nStopped.")
            break


if __name__ == "__main__":
    main()