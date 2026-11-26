"""Lector mínimo de hojas XLSX con la biblioteca estándar (zipfile y XML).

Sirve para las capas de contexto por barrio (D-16) sin añadir `openpyxl` a las dependencias
(CLAUDE.md: no se añaden dependencias fuera de la lista sin justificarlo en la SPEC). Lee los
valores guardados de una hoja: números, textos compartidos y textos en línea. No calcula
fórmulas ni interpreta formatos de fecha; las celdas combinadas solo tienen valor en la primera.
"""

import re
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

import pandas as pd

NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
      "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships"}
REL_NS = "{http://schemas.openxmlformats.org/package/2006/relationships}"


def columna_a_indice(referencia: str) -> int:
    """'A1' → 0, 'AB7' → 27."""
    letras = re.match(r"[A-Z]+", referencia).group(0)
    indice = 0
    for letra in letras:
        indice = indice * 26 + (ord(letra) - 64)
    return indice - 1


def textos_compartidos(libro: zipfile.ZipFile) -> list[str]:
    """Tabla de textos compartidos del libro (vacía si no hay)."""
    if "xl/sharedStrings.xml" not in libro.namelist():
        return []
    raiz = ET.fromstring(libro.read("xl/sharedStrings.xml"))
    return ["".join(t.text or "" for t in si.iter(f"{{{NS['m']}}}t")) for si in raiz.findall("m:si", NS)]


def ruta_hoja(libro: zipfile.ZipFile, nombre: str) -> str:
    """Ruta interna del XML de la hoja con ese nombre."""
    hojas = ET.fromstring(libro.read("xl/workbook.xml"))
    relaciones = ET.fromstring(libro.read("xl/_rels/workbook.xml.rels"))
    destinos = {r.get("Id"): r.get("Target") for r in relaciones.iter(f"{REL_NS}Relationship")}
    for hoja in hojas.iter(f"{{{NS['m']}}}sheet"):
        if hoja.get("name") == nombre:
            destino = destinos[hoja.get(f"{{{NS['r']}}}id")].lstrip("/")
            return destino if destino.startswith("xl/") else f"xl/{destino}"
    raise KeyError(f"No existe la hoja {nombre!r}.")


def valor_celda(celda: ET.Element, compartidos: list[str]):
    """Valor guardado de una celda: número, texto o None."""
    tipo = celda.get("t")
    if tipo == "inlineStr":
        return "".join(t.text or "" for t in celda.iter(f"{{{NS['m']}}}t"))
    v = celda.find("m:v", NS)
    if v is None or v.text is None:
        return None
    if tipo == "s":
        return compartidos[int(v.text)]
    if tipo in ("str", "e"):
        return v.text
    return float(v.text)


def leer_hoja(ruta: Path, nombre: str) -> pd.DataFrame:
    """Hoja como tabla sin cabecera (filas y columnas en su posición de Excel, empezando en 0)."""
    with zipfile.ZipFile(ruta) as libro:
        compartidos = textos_compartidos(libro)
        raiz = ET.fromstring(libro.read(ruta_hoja(libro, nombre)))
    filas: dict[int, dict[int, object]] = {}
    for fila in raiz.iter(f"{{{NS['m']}}}row"):
        numero = int(fila.get("r")) - 1
        for celda in fila.findall("m:c", NS):
            filas.setdefault(numero, {})[columna_a_indice(celda.get("r"))] = valor_celda(celda, compartidos)
    if not filas:
        return pd.DataFrame()
    ancho = max(max(c) for c in filas.values()) + 1
    return pd.DataFrame([[filas.get(i, {}).get(j) for j in range(ancho)] for i in range(max(filas) + 1)])
