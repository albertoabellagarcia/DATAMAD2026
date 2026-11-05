#!/usr/bin/env python3
"""
caso_accidentes.py · DATAMAD 2026, diapositiva 63

Dataset: «Accidentes de circulación con víctimas por ubicación y resultado
del accidente» (Comunidad de Madrid, fuente original: DGT)
https://datos.comunidad.madrid/dataset/1908061

Hace lo que pide el «Pruébalo» de la diapositiva:
  1. Lee la ficha del dataset con la API CKAN (package_show?id=1908061).
  2. Descarga el recurso CSV (o JSON si no hay CSV).
  3. Detecta las columnas de ubicación, resultado y valor.
  4. Resume los accidentes con víctimas por ubicación y resultado.

Uso:
  python caso_accidentes.py
  python caso_accidentes.py --ubicacion "Zona" --resultado "Lesividad" --valor "Valor"
      (para indicar las columnas a mano si la detección automática falla)

Salida: accidentes_datos.csv (datos descargados) y accidentes_resumen.json
Requisitos: pip install requests
"""

import csv
import io
import json
import sys
import unicodedata
from collections import Counter, defaultdict

import requests

DATASET = "1908061"
CKAN_BASES = ["https://datos.comunidad.madrid/api/3/action",
              "https://datos.comunidad.madrid/catalogo/api/3/action"]
TIMEOUT = 60

PISTAS_UBICACION = ("ubicacion", "zona", "via", "lugar", "municipio", "territorio",
                    "tipo de via", "carretera", "urbana", "interurbana")
PISTAS_RESULTADO = ("resultado", "lesividad", "gravedad", "victima", "fallecid",
                    "herid", "muert")
PISTAS_VALOR = ("valor", "numero", "total", "accidentes", "cantidad", "n.")


def sin_tildes(texto):
    t = unicodedata.normalize("NFD", str(texto).lower())
    return "".join(c for c in t if unicodedata.category(c) != "Mn")


def argumento(nombre):
    if nombre in sys.argv:
        i = sys.argv.index(nombre)
        if i + 1 < len(sys.argv):
            return sys.argv[i + 1]
    return None


# ---------------------------------------------------------------- CKAN
def ficha_dataset(id_dataset):
    for base in CKAN_BASES:
        try:
            r = requests.get(f"{base}/package_show", params={"id": id_dataset},
                             timeout=TIMEOUT)
            datos = r.json()
            if datos.get("success"):
                return datos["result"]
        except (requests.RequestException, ValueError):
            continue
    sys.exit(f"No se pudo leer el dataset {id_dataset} en la API CKAN.")


def elegir_recurso(recursos):
    for formato in ("CSV", "JSON"):
        for r in recursos:
            if (r.get("format") or "").upper() == formato:
                return r
    return recursos[0] if recursos else None


# ---------------------------------------------------------------- lectura
def descargar_filas(recurso):
    r = requests.get(recurso["url"], timeout=TIMEOUT)
    r.raise_for_status()
    contenido = r.content
    for codificacion in ("utf-8-sig", "latin-1"):
        try:
            texto = contenido.decode(codificacion)
            break
        except UnicodeDecodeError:
            continue

    if (recurso.get("format") or "").upper() == "JSON" or texto.lstrip()[:1] in "[{":
        datos = json.loads(texto)
        if isinstance(datos, dict):
            for clave in ("data", "datos", "records", "result", "items"):
                if isinstance(datos.get(clave), list):
                    datos = datos[clave]
                    break
        return [d for d in datos if isinstance(d, dict)]

    try:
        dialecto = csv.Sniffer().sniff(texto[:5000], delimiters=";,\t|")
    except csv.Error:
        dialecto = csv.excel
        dialecto.delimiter = ";"
    return list(csv.DictReader(io.StringIO(texto), dialect=dialecto))


def numero(valor):
    """'1.234' -> 1234 ; '12,5' -> 12.5 ; vacío o texto -> None"""
    if valor is None:
        return None
    if isinstance(valor, (int, float)):
        return valor
    t = str(valor).strip()
    if not t:
        return None
    if "," in t:
        t = t.replace(".", "").replace(",", ".")
    elif t.count(".") >= 1 and all(len(p) == 3 for p in t.split(".")[1:]):
        t = t.replace(".", "")
    try:
        n = float(t)
        return int(n) if n.is_integer() else n
    except ValueError:
        return None


def detectar_columna(columnas, pistas, excluir=()):
    for pista in pistas:
        for c in columnas:
            if c not in excluir and pista in sin_tildes(c):
                return c
    return None


def es_numerica(filas, columna):
    valores = [f.get(columna) for f in filas[:200] if str(f.get(columna, "")).strip()]
    return bool(valores) and sum(numero(v) is not None for v in valores) / len(valores) > 0.9


# ---------------------------------------------------------------- main
def main():
    ficha = ficha_dataset(DATASET)
    print(f"Dataset: {ficha.get('title')}")
    print(f"Organización: {(ficha.get('organization') or {}).get('title')}")
    print("Recursos:")
    for r in ficha.get("resources", []):
        print(f"  - [{r.get('format')}] {r.get('name')}  {r.get('url')}")

    recurso = elegir_recurso(ficha.get("resources", []))
    if not recurso:
        sys.exit("El dataset no tiene recursos descargables.")
    print(f"\nDescargando: {recurso.get('url')}")
    filas = descargar_filas(recurso)
    if not filas:
        sys.exit("El recurso no contiene filas.")
    columnas = list(filas[0].keys())
    print(f"{len(filas)} filas · columnas: {columnas}")

    with open("accidentes_datos.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=columnas, delimiter=";")
        w.writeheader()
        w.writerows(filas)

    # Columnas: las indicadas a mano o detectadas automáticamente
    numericas = [c for c in columnas if es_numerica(filas, c)]
    texto = [c for c in columnas if c not in numericas]
    col_ubic = argumento("--ubicacion") or detectar_columna(texto, PISTAS_UBICACION)
    col_res = argumento("--resultado") or detectar_columna(texto, PISTAS_RESULTADO,
                                                           excluir=(col_ubic,))
    col_val = argumento("--valor") or detectar_columna(numericas, PISTAS_VALOR)
    if not col_val:
        anyos = [c for c in numericas if "ano" in sin_tildes(c) or "año" in c.lower()]
        candidatas = [c for c in numericas if c not in anyos]
        col_val = candidatas[-1] if candidatas else None

    print("\nColumnas usadas:")
    print(f"  ubicación: {col_ubic}")
    print(f"  resultado: {col_res}")
    print(f"  valor:     {col_val or '(ninguna: se cuentan filas)'}")
    if not col_ubic and not col_res:
        print("\nNo se detectaron ubicación ni resultado. Valores de las columnas de texto:")
        for c in texto:
            print(f"  {c}: {sorted({str(f.get(c)) for f in filas})[:10]}")
        print("Indica las columnas con --ubicacion y --resultado.")
        return

    def cantidad(fila):
        return (numero(fila.get(col_val)) or 0) if col_val else 1

    # Si hay columna de año, resumen del último año y evolución anual
    col_anyo = next((c for c in columnas if sin_tildes(c) in ("ano", "anyo", "año", "periodo")
                     or sin_tildes(c).startswith("ano")), None)
    ultimo = None
    if col_anyo:
        anyos = sorted({str(f.get(col_anyo)) for f in filas})
        ultimo = anyos[-1]
        print(f"\nAños disponibles: {anyos[0]} – {ultimo}")

    resumen = {"dataset": ficha.get("title"), "fuente": recurso.get("url"),
               "columnas": {"ubicacion": col_ubic, "resultado": col_res,
                            "valor": col_val, "año": col_anyo}}

    def tabla(filas_sel, titulo):
        por_ubic, por_res, cruce = Counter(), Counter(), defaultdict(Counter)
        for f in filas_sel:
            u = str(f.get(col_ubic)) if col_ubic else "Total"
            r = str(f.get(col_res)) if col_res else "Total"
            n = cantidad(f)
            por_ubic[u] += n
            por_res[r] += n
            cruce[u][r] += n
        print(f"\n=== {titulo}")
        print("\nPor ubicación:")
        for k, v in por_ubic.most_common():
            print(f"  {k:<45} {v:>10,}".replace(",", "."))
        print("\nPor resultado:")
        for k, v in por_res.most_common():
            print(f"  {k:<45} {v:>10,}".replace(",", "."))
        resultados = [k for k, _ in por_res.most_common()]
        print("\nUbicación × resultado:")
        print("  " + " " * 30 + "".join(f"{r[:14]:>16}" for r in resultados))
        for u, _ in por_ubic.most_common():
            print(f"  {u[:30]:<30}" + "".join(f"{cruce[u][r]:>16,}".replace(",", ".")
                                               for r in resultados))
        return {"por_ubicacion": dict(por_ubic), "por_resultado": dict(por_res),
                "cruce": {u: dict(v) for u, v in cruce.items()}}

    if ultimo:
        resumen[f"año_{ultimo}"] = tabla([f for f in filas if str(f.get(col_anyo)) == ultimo],
                                         f"ÚLTIMO AÑO ({ultimo})")
        evolucion = Counter()
        for f in filas:
            evolucion[str(f.get(col_anyo))] += cantidad(f)
        print("\nEvolución anual (total):")
        for a in sorted(evolucion):
            print(f"  {a}: {evolucion[a]:,}".replace(",", "."))
        resumen["evolucion_anual"] = dict(sorted(evolucion.items()))
    resumen["todos_los_años"] = tabla(filas, "TODOS LOS DATOS")

    with open("accidentes_resumen.json", "w", encoding="utf-8") as f:
        json.dump(resumen, f, ensure_ascii=False, indent=2)
    print("\nGuardado: accidentes_datos.csv y accidentes_resumen.json")


if __name__ == "__main__":
    main()
