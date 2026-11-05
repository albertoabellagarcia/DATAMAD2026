#!/usr/bin/env python3
"""
caso_gasolineras.py · DATAMAD 2026, diapositiva 65

API REST de precios de carburantes del Ministerio:
https://sedeaplicaciones.minetur.gob.es/ServiciosRESTCarburantes/PreciosCarburantes/

Sigue los tres pasos de la diapositiva:
  1. /Listados/Provincias/                      -> ID de la provincia
  2. /Listados/MunicipiosPorProvincia/[ID]      -> ID del municipio
  3. /EstacionesTerrestres/FiltroMunicipio/[ID] -> gasolineras con ubicación,
                                                   horario y precios
Pide JSON con la cabecera «Accept: application/json» (sin ella responde XML).

Uso:
  python caso_gasolineras.py                          # Madrid capital
  python caso_gasolineras.py --municipio "Alcalá de Henares"
  python caso_gasolineras.py --provincia Madrid --toda-la-provincia

Salida: gasolineras_<lugar>.csv y gasolineras_<lugar>.geojson
        (el GeoJSON se abre en geojson.io o QGIS)
Requisitos: pip install requests
"""

import csv
import json
import re
import sys
import unicodedata

import requests

BASE = "https://sedeaplicaciones.minetur.gob.es/ServiciosRESTCarburantes/PreciosCarburantes"
HEADERS = {"Accept": "application/json", "User-Agent": "datamad-gasolineras/1.0"}
TIMEOUT = 90

CARBURANTES = {
    "Gasolina 95": "Precio Gasolina 95 E5",
    "Gasolina 98": "Precio Gasolina 98 E5",
    "Gasóleo A": "Precio Gasoleo A",
    "Gasóleo Premium": "Precio Gasoleo Premium",
    "GLP": "Precio Gases licuados del petróleo",
}
TOP = 10


def argumento(nombre, defecto=None):
    if nombre in sys.argv:
        i = sys.argv.index(nombre)
        if i + 1 < len(sys.argv):
            return sys.argv[i + 1]
    return defecto


def normal(texto):
    t = unicodedata.normalize("NFD", str(texto).lower().strip())
    return "".join(c for c in t if unicodedata.category(c) != "Mn")


def get(ruta):
    r = requests.get(f"{BASE}/{ruta}", headers=HEADERS, timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()


def clave(registro, *pistas):
    """Nombre real de un campo (la API tiene erratas, p. ej. «IDPovincia»)."""
    for pista in pistas:
        for k in registro:
            if normal(k) == normal(pista):
                return k
    for pista in pistas:
        for k in registro:
            if normal(pista) in normal(k):
                return k
    return None


def buscar(lista, nombre, campo_nombre, campo_id):
    objetivo = normal(nombre)
    exactos = [x for x in lista if normal(x[campo_nombre]) == objetivo]
    if exactos:
        return exactos[0]
    parecidos = [x for x in lista if objetivo in normal(x[campo_nombre])]
    if len(parecidos) == 1:
        return parecidos[0]
    nombres = ", ".join(x[campo_nombre] for x in (parecidos or lista)[:15])
    sys.exit(f"No encuentro «{nombre}». ¿Quizá: {nombres}?")


def numero(texto):
    """'1,489' -> 1.489 ; '' -> None"""
    try:
        return float(str(texto).replace(",", "."))
    except (TypeError, ValueError):
        return None


def main():
    nom_provincia = argumento("--provincia", "Madrid")
    nom_municipio = argumento("--municipio", "Madrid")
    toda = "--toda-la-provincia" in sys.argv

    # Paso 1: provincias
    provincias = get("Listados/Provincias/")
    k_id = clave(provincias[0], "IDPovincia", "IDProvincia", "ID")
    k_nom = clave(provincias[0], "Provincia")
    prov = buscar(provincias, nom_provincia, k_nom, k_id)
    print(f"Paso 1 · /Listados/Provincias/ -> {prov[k_nom]} (ID {prov[k_id]})")

    if toda:
        lugar = prov[k_nom]
        ruta = f"EstacionesTerrestres/FiltroProvincia/{prov[k_id]}"
    else:
        # Paso 2: municipios de la provincia
        municipios = get(f"Listados/MunicipiosPorProvincia/{prov[k_id]}")
        m_id = clave(municipios[0], "IDMunicipio")
        m_nom = clave(municipios[0], "Municipio")
        mun = buscar(municipios, nom_municipio, m_nom, m_id)
        print(f"Paso 2 · /Listados/MunicipiosPorProvincia/{prov[k_id]} -> "
              f"{mun[m_nom]} (ID {mun[m_id]}) · {len(municipios)} municipios")
        lugar = mun[m_nom]
        ruta = f"EstacionesTerrestres/FiltroMunicipio/{mun[m_id]}"

    # Paso 3: gasolineras
    datos = get(ruta)
    estaciones = datos.get("ListaEESSPrecio", [])
    print(f"Paso 3 · /{ruta} -> {len(estaciones)} gasolineras "
          f"(precios de {datos.get('Fecha')}, resultado: {datos.get('ResultadoConsulta')})")
    if not estaciones:
        return

    # Ranking de precios por carburante
    for nombre, campo in CARBURANTES.items():
        con_precio = [(numero(e.get(campo)), e) for e in estaciones if numero(e.get(campo))]
        if not con_precio:
            continue
        con_precio.sort(key=lambda x: x[0])
        precios = [p for p, _ in con_precio]
        media = sum(precios) / len(precios)
        print(f"\n=== {nombre}: {len(precios)} gasolineras · mín {precios[0]:.3f} € · "
              f"media {media:.3f} € · máx {precios[-1]:.3f} €")
        for precio, e in con_precio[:TOP]:
            print(f"  {precio:.3f} €  {e.get('Rótulo', '')[:22]:<22} "
                  f"{e.get('Dirección', '')[:38]:<38} {e.get('Localidad', '')[:18]}")

    # Guardar CSV y GeoJSON
    base = "gasolineras_" + re.sub(r"[^a-z0-9]+", "_", normal(lugar)).strip("_")
    campos = list(estaciones[0].keys())
    with open(f"{base}.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=campos, delimiter=";", extrasaction="ignore")
        w.writeheader()
        w.writerows(estaciones)

    features = []
    for e in estaciones:
        lat = numero(e.get("Latitud"))
        lon = numero(e.get("Longitud (WGS84)") or e.get(clave(e, "Longitud") or ""))
        if lat is None or lon is None:
            continue
        props = {"rotulo": e.get("Rótulo"), "direccion": e.get("Dirección"),
                 "localidad": e.get("Localidad"), "horario": e.get("Horario")}
        for nombre, campo in CARBURANTES.items():
            props[nombre] = numero(e.get(campo))
        features.append({"type": "Feature",
                         "geometry": {"type": "Point", "coordinates": [lon, lat]},
                         "properties": props})
    with open(f"{base}.geojson", "w", encoding="utf-8") as f:
        json.dump({"type": "FeatureCollection", "features": features},
                  f, ensure_ascii=False)
    print(f"\nGuardado: {base}.csv y {base}.geojson ({len(features)} puntos)")


if __name__ == "__main__":
    main()
