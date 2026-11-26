"""Omisión de etapas cuyas entradas no cambiaron (R-ARQ-03).

Cada etapa de `build` tiene una «huella»: el SHA-256 de
- su nombre;
- el código del paquete (`src/cercasalud/*.py`) y la configuración (`config/base.toml`);
- el manifiesto de la versión de datos, que ya lleva el SHA-256 de cada descarga;
- las carpetas de resultados que lee (todas sus archivos, con nombre y contenido);
- los archivos curados o externos que lee (`curado/`, el ADRH de `crudos/`).

Al terminar bien una etapa se guarda su huella en `<etapa>/.huella.json`. En la siguiente
ejecución, si la huella calculada coincide con la guardada, la etapa se omite. `--forzar` la
recalcula igualmente. Una etapa que falla no guarda huella, así que siempre se repite.

Cualquier cambio de código cambia la huella de todas las etapas: es deliberado (prudente), aunque
recalcule algo que no hacía falta.
"""

import hashlib
import json
from pathlib import Path

from .manifiestos import escribir_json_atomico, sha256_archivo

PAQUETE = Path(__file__).resolve().parent
REPOSITORIO = PAQUETE.parents[1]
ARCHIVO_HUELLA = ".huella.json"

# Carpetas de `procesados/<versión>/` que lee cada etapa (las de `noches/` incluidas).
CARPETAS_LEIDAS = {
    "primaria": [],
    "poblacion": [],
    "demanda": ["poblacion"],
    "acceso_pie": ["demanda", "primaria"],
    "acceso": ["demanda", "acceso_pie", "primaria", "noches/transporte_9_13", "noches/transporte_9_13_centros_nuevos",
               "noches/transporte_16_20", "sensibilidad_inventario_ampliado"],
    "refugios_pie": ["demanda"],
    "refugios": ["demanda", "acceso", "refugios_pie"],
    "refugios_ampliados": ["demanda", "acceso", "refugios"],
    "renta": ["demanda", "acceso", "refugios"],
    "candidatos_pie": ["demanda", "acceso"],
    "actuaciones": ["demanda", "acceso_pie", "acceso", "candidatos_pie", "refugios", "refugios_pie",
                    "noches/transporte_9_13", "noches/transporte_9_13_centros_nuevos", "noches/transporte_16_20",
                    "noches/candidatos_tp_9_13", "noches/candidatos_tp_16_20"],
    "capas_app": ["demanda", "acceso_pie", "acceso", "refugios", "renta", "noches/transporte_9_13",
                  "noches/transporte_9_13_centros_nuevos", "noches/transporte_16_20"],
    "contexto": ["demanda", "app"],
}
# Archivos fuera de la versión de datos que lee cada etapa (relativos a la raíz de datos o al repositorio).
EXTERNOS_DATOS = {"renta": ["crudos/ine_adrh_2024/adrh_madrid_2024_completo.json"],
                  "capas_app": ["crudos/madrid_iguala/informe_globales.xlsx"],  # nombres de los distritos
                  "contexto": ["crudos/madrid_personas_solas/personas_solas.xlsx",
                               "crudos/madrid_iguala/informe_globales.xlsx", "crudos/madrid_barrios/barrios.zip"]}
CURADO = sorted((REPOSITORIO / "curado").glob("*.csv"))


def huella_carpeta(carpeta: Path, resumen) -> None:
    """Añade al resumen el nombre y el SHA-256 de cada archivo de una carpeta (si existe)."""
    if not carpeta.exists():
        resumen.update(f"ausente:{carpeta.name}".encode())
        return
    for archivo in sorted(p for p in carpeta.rglob("*") if p.is_file() and p.name != ARCHIVO_HUELLA):
        resumen.update(archivo.relative_to(carpeta).as_posix().encode())
        resumen.update(sha256_archivo(archivo).encode())


def huella(raiz: Path, id_snapshot: str, etapa: str) -> str:
    """Huella de las entradas, el código y la configuración de una etapa."""
    resumen = hashlib.sha256(etapa.encode())
    import os

    from .configuracion import CONFIG_BASE, VARIABLE_CONFIG
    config = Path(os.environ.get(VARIABLE_CONFIG, CONFIG_BASE))  # la configuración en uso, no siempre la base
    for archivo in [*sorted(PAQUETE.glob("*.py")), config, *CURADO,
                    raiz / "snapshots" / f"{id_snapshot}.json"]:
        resumen.update(archivo.name.encode())
        resumen.update(sha256_archivo(archivo).encode())
    for relativo in EXTERNOS_DATOS.get(etapa, []):
        resumen.update(relativo.encode())
        resumen.update(sha256_archivo(raiz / relativo).encode())
    if etapa == "refugios_ampliados":   # sus CSV de crudos dependen de la última descarga verificada
        from .refugios_ampliados import archivos_externos
        for ruta in archivos_externos(raiz):
            resumen.update(ruta.name.encode())
            resumen.update(sha256_archivo(ruta).encode())
    proc = raiz / "procesados" / id_snapshot
    for relativa in CARPETAS_LEIDAS[etapa]:
        resumen.update(relativa.encode())
        huella_carpeta(proc / relativa, resumen)
    return resumen.hexdigest()


def sin_cambios(destino: Path, valor: str) -> bool:
    """True si la etapa ya existe con la misma huella."""
    archivo = destino / ARCHIVO_HUELLA
    return archivo.exists() and json.loads(archivo.read_text(encoding="utf-8")).get("huella") == valor


def guardar(destino: Path, valor: str) -> None:
    """Guarda la huella de una etapa terminada."""
    escribir_json_atomico(destino / ARCHIVO_HUELLA, {"huella": valor})
