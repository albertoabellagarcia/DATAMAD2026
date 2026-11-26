"""Adquisición explícita de datos (`fetch`), versiones fechadas (snapshots) y verificación.

Portado del patrón de historico/decision_audit/scripts/audit_downloads.py:10-21 (retrieve):
URL, URL final, estado HTTP, tipo de contenido, bytes, SHA-256 y fecha de descarga en un
manifiesto <archivo>.source.json. Cambios respecto al original:
- la descarga va en streaming a un temporal y se renombra al terminar (escritura atómica);
- cada descarga va a una carpeta con el ID de la versión, y nunca sobrescribe otra;
- si el contenido es idéntico a una versión ya guardada, se reutiliza esa versión.
"""

import datetime
import hashlib
import os
import urllib.request
from pathlib import Path

from .catalogo import CATALOGO, ArchivoFuente
from .manifiestos import (
    SUFIJO_MANIFIESTO,
    SUFIJO_TEMPORAL,
    TAMANO_BLOQUE,
    escribir_json_atomico,
    leer_json,
    ruta_manifiesto,
    sha256_archivo,
)
from .rutas import carpeta_crudos, carpeta_snapshots

AGENTE_HTTP = "cercasalud-mad/0.1 (herramienta local de datos abiertos)"
TIEMPO_ESPERA_S = 120


def ahora_utc() -> datetime.datetime:
    """Momento actual en UTC."""
    return datetime.datetime.now(datetime.UTC)


def nuevo_id_snapshot(momento: datetime.datetime | None = None) -> str:
    """Identificador de versión a partir de la fecha y hora UTC, p. ej. 20261113T190000Z."""
    return (momento or ahora_utc()).strftime("%Y%m%dT%H%M%SZ")


def descargar_a_temporal(archivo: ArchivoFuente, carpeta: Path) -> tuple[Path, dict]:
    """Descarga la URL en streaming a <carpeta>/<nombre>.parcial y devuelve (temporal, metadatos)."""
    carpeta.mkdir(parents=True, exist_ok=True)
    temporal = carpeta / (archivo.nombre + SUFIJO_TEMPORAL)
    peticion = urllib.request.Request(archivo.url, headers={"User-Agent": AGENTE_HTTP})
    resumen, total = hashlib.sha256(), 0
    try:
        with urllib.request.urlopen(peticion, timeout=TIEMPO_ESPERA_S) as respuesta, temporal.open("wb") as salida:
            for bloque in iter(lambda: respuesta.read(TAMANO_BLOQUE), b""):
                salida.write(bloque)
                resumen.update(bloque)
                total += len(bloque)
            metadatos = {
                "url": archivo.url,
                "final_url": respuesta.geturl(),
                "status": getattr(respuesta, "status", None),
                "content_type": respuesta.headers.get("Content-Type"),
                "bytes": total,
                "sha256": resumen.hexdigest(),
                "retrieved_at_utc": ahora_utc().isoformat(),
            }
    except BaseException:
        if temporal.exists():
            temporal.unlink()
        raise
    return temporal, metadatos


def fecha_adquisicion(manifiesto: dict) -> str:
    """Fecha con la que se ordenan las versiones: descarga, inventario o copia, por ese orden."""
    return (manifiesto.get("retrieved_at_utc") or manifiesto.get("fecha_inventario_utc")
            or manifiesto.get("copiado_utc") or "")


def versiones_locales(raiz: Path, archivo: ArchivoFuente) -> list[tuple[Path, dict]]:
    """Versiones guardadas de un archivo: las que tienen manifiesto con la misma URL."""
    carpeta = carpeta_crudos(raiz) / archivo.fuente
    versiones = []
    for manifiesto in carpeta.rglob("*" + SUFIJO_MANIFIESTO):
        datos = leer_json(manifiesto)
        if (datos.get("url") or datos.get("source_url")) == archivo.url:
            ruta = manifiesto.with_name(manifiesto.name[: -len(SUFIJO_MANIFIESTO)])
            if ruta.exists():
                versiones.append((ruta, datos))
    return sorted(versiones, key=lambda par: fecha_adquisicion(par[1]))


def adquirir(raiz: Path, archivo: ArchivoFuente, id_version: str) -> dict:
    """Descarga un archivo; lo guarda como versión nueva o reutiliza una idéntica ya guardada."""
    carpeta = carpeta_crudos(raiz) / archivo.fuente / id_version
    temporal, metadatos = descargar_a_temporal(archivo, carpeta)
    for ruta, datos in versiones_locales(raiz, archivo):
        if datos.get("sha256") == metadatos["sha256"]:
            temporal.unlink()
            _borrar_si_vacia(carpeta)
            return {"fuente": archivo.fuente, "nombre": archivo.nombre, "accion": "reutilizada_identica",
                    "ruta": ruta.relative_to(raiz).as_posix(), "sha256": metadatos["sha256"]}
    destino = carpeta / archivo.nombre
    os.replace(temporal, destino)
    escribir_json_atomico(ruta_manifiesto(destino), {
        **metadatos, "fuente": archivo.fuente, "file": archivo.nombre,
        "organismo": archivo.organismo, "licencia": archivo.licencia})
    return {"fuente": archivo.fuente, "nombre": archivo.nombre, "accion": "descargada",
            "ruta": destino.relative_to(raiz).as_posix(), "sha256": metadatos["sha256"]}


def _borrar_si_vacia(carpeta: Path) -> None:
    """Elimina una carpeta de versión si se quedó vacía tras reutilizar una copia idéntica."""
    if carpeta.exists() and not any(carpeta.iterdir()):
        carpeta.rmdir()


def entrada_snapshot(raiz: Path, archivo: ArchivoFuente) -> dict:
    """Elige la versión local más reciente de un archivo y comprueba su SHA-256."""
    versiones = versiones_locales(raiz, archivo)
    if not versiones:
        return {"fuente": archivo.fuente, "nombre": archivo.nombre, "url": archivo.url, "estado": "sin_version_local"}
    ruta, datos = versiones[-1]
    calculado = sha256_archivo(ruta)
    return {
        "fuente": archivo.fuente, "nombre": archivo.nombre, "url": archivo.url,
        "estado": "ok" if calculado == datos.get("sha256") else "sha256_no_coincide_con_manifiesto",
        "ruta": ruta.relative_to(raiz).as_posix(), "bytes": ruta.stat().st_size, "sha256": calculado,
        "fecha_adquisicion": fecha_adquisicion(datos), "organismo": archivo.organismo,
        "licencia": archivo.licencia,
    }


def crear_snapshot(raiz: Path, id_version: str, descargas: list[dict] | None = None) -> Path:
    """Escribe datos/snapshots/<ID>.json con la versión vigente de cada archivo del catálogo."""
    entradas = [entrada_snapshot(raiz, archivo) for archivo in CATALOGO]
    destino = carpeta_snapshots(raiz) / f"{id_version}.json"
    if destino.exists():
        raise FileExistsError(f"La versión {id_version} ya existe; una versión no se sobrescribe.")
    escribir_json_atomico(destino, {
        "id": id_version, "creado_utc": ahora_utc().isoformat(),
        "descargas_de_esta_orden": descargas or [], "archivos": entradas,
    })
    return destino


def leer_snapshot(raiz: Path, id_version: str) -> dict:
    """Lee una versión fechada; falla con un mensaje claro si no existe."""
    ruta = carpeta_snapshots(raiz) / f"{id_version}.json"
    if not ruta.exists():
        raise FileNotFoundError(f"No existe la versión {id_version} en {ruta.parent}")
    return leer_json(ruta)


def verificar_snapshot(raiz: Path, id_version: str) -> list[str]:
    """Recalcula el SHA-256 de cada archivo de la versión y devuelve los problemas encontrados."""
    problemas = []
    for entrada in leer_snapshot(raiz, id_version)["archivos"]:
        if entrada["estado"] != "ok":
            problemas.append(f"{entrada['fuente']}/{entrada['nombre']}: {entrada['estado']}")
            continue
        ruta = raiz / entrada["ruta"]
        if not ruta.exists():
            problemas.append(f"{entrada['ruta']}: no existe")
        elif sha256_archivo(ruta) != entrada["sha256"]:
            problemas.append(f"{entrada['ruta']}: el SHA-256 ya no coincide")
    return problemas


def ruta_en_snapshot(raiz: Path, snapshot: dict, fuente: str, nombre: str) -> Path:
    """Ruta local del archivo de una fuente dentro de una versión; falla si no está disponible."""
    for entrada in snapshot["archivos"]:
        if entrada["fuente"] == fuente and entrada["nombre"] == nombre and entrada["estado"] == "ok":
            return raiz / entrada["ruta"]
    raise LookupError(f"La versión {snapshot['id']} no tiene {fuente}/{nombre} verificado.")
