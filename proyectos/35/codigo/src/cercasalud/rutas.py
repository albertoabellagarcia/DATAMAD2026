"""Ubicación de los datos del proyecto, que viven fuera del repositorio (nunca van a git)."""

import os
from pathlib import Path

VARIABLE_ENTORNO = "CERCASALUD_DATOS"


def raiz_datos() -> Path:
    """Devuelve la carpeta de datos.

    Usa la variable de entorno CERCASALUD_DATOS si existe; si no, la carpeta `datos/`
    hermana del repositorio (DATAMAD26/datos), que es donde están los crudos unificados.
    """
    valor = os.environ.get(VARIABLE_ENTORNO)
    if valor:
        return Path(valor).resolve()
    repositorio = Path(__file__).resolve().parents[2]
    return (repositorio.parent / "datos").resolve()


def carpeta_crudos(raiz: Path) -> Path:
    """Carpeta de descargas originales: datos/crudos/<fuente>/."""
    return raiz / "crudos"


def carpeta_snapshots(raiz: Path) -> Path:
    """Carpeta de versiones fechadas: datos/snapshots/<ID>.json."""
    return raiz / "snapshots"


def carpeta_procesados(raiz: Path, id_snapshot: str) -> Path:
    """Carpeta de salidas calculadas a partir de una versión: datos/procesados/<ID>/."""
    return raiz / "procesados" / id_snapshot
