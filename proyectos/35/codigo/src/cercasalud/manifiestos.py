"""Huellas SHA-256 y escritura atómica.

Escritura atómica (R-OPS-01): se escribe en un archivo temporal y solo al terminar bien
se renombra al nombre final. Si el proceso se corta, nunca queda un archivo a medias
con el nombre definitivo.
"""

import hashlib
import json
import os
from pathlib import Path

TAMANO_BLOQUE = 1 << 20  # 1 MiB: lee archivos grandes sin cargarlos enteros en memoria
SUFIJO_TEMPORAL = ".parcial"
SUFIJO_MANIFIESTO = ".source.json"


def sha256_archivo(ruta: Path) -> str:
    """Calcula el SHA-256 de un archivo leyéndolo por bloques."""
    resumen = hashlib.sha256()
    with ruta.open("rb") as fichero:
        for bloque in iter(lambda: fichero.read(TAMANO_BLOQUE), b""):
            resumen.update(bloque)
    return resumen.hexdigest()


def escribir_atomico(destino: Path, contenido: bytes) -> None:
    """Escribe bytes en un temporal y lo renombra al destino; si falla, borra el temporal."""
    destino.parent.mkdir(parents=True, exist_ok=True)
    temporal = destino.with_name(destino.name + SUFIJO_TEMPORAL)
    try:
        temporal.write_bytes(contenido)
        os.replace(temporal, destino)
    finally:
        if temporal.exists():
            temporal.unlink()


def escribir_json_atomico(destino: Path, datos) -> None:
    """Escribe un JSON legible (UTF-8, sin BOM) de forma atómica."""
    texto = json.dumps(datos, ensure_ascii=False, indent=2) + "\n"
    escribir_atomico(destino, texto.encode("utf-8"))


def leer_json(ruta: Path):
    """Lee un JSON tolerando la marca BOM que añaden algunas herramientas de Windows."""
    return json.loads(ruta.read_text(encoding="utf-8-sig"))


def ruta_manifiesto(archivo: Path) -> Path:
    """Devuelve la ruta del manifiesto de un archivo: <archivo>.source.json."""
    return archivo.with_name(archivo.name + SUFIJO_MANIFIESTO)
