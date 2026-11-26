"""00 · Descarga reproducible de los datos desde la API CKAN del Portal de Datos Abiertos de la Comunidad de Madrid.

Para cada fichero: package_show?id=<dataset> -> recurso (por id) -> URL -> descarga.
No necesita clave. Por seguridad NO sobrescribe ficheros existentes salvo con --forzar.

Uso:
    python Codigo/00_descarga_ckan.py                     # descarga a Datos/ y Mapa/ lo que falte
    python Codigo/00_descarga_ckan.py --destino otra/ruta # todo a otra carpeta (p. ej. para comparar)

La población del INE (tabla 68535) no está en CKAN: ver README («Datos del INE»).
"""
import argparse
import hashlib
from pathlib import Path

import requests

API = "https://datos.comunidad.madrid/api/3/action/package_show"
RAIZ = Path(__file__).resolve().parents[1]

# fichero local -> (carpeta, dataset CKAN, id del recurso)
RECURSOS = {
    "paro_registrado_municipios.csv": ("Datos", "paro_por_nacionalidad_sector_y_sexo_09", "0858e9d5-726f-4587-b934-5efb6a3b5409"),
    "afiliados_residencia_rama.csv": ("Datos", "afiliados_por_residencia_y_rama", "7198bd4a-adf3-4d4e-a79e-158dc7c29b45"),
    "afiliados_centro_trabajo_rama.csv": ("Datos", "afiliados_por_ubicacion_y_rama", "21e8facc-98a8-43c7-a177-9746860c2498"),
    "afiliados_residencia_grupo_cotizacion.csv": ("Datos", "afiliados_por_residencia_y_grupo", "5730a9c8-6b98-4b98-8761-05afe7e0e101"),
    "afiliados_residencia_contrato.csv": ("Datos", "afiliados_por_residencia_y_contrato", "6328dfff-92f8-4628-87c1-09cf755a055f"),
    "cursos_formacion_empleo.csv": ("Datos", "cursos_formacion_profesional_empleo", "212f0191-919f-4932-a810-8ca90498676a"),
    "limites_secciones_censales_2019.zip": ("Mapa", "secciones_censales", "b53b766c-e013-444c-b3b0-0992c4a0dbfc"),
}


def url_recurso(dataset: str, recurso_id: str) -> str:
    r = requests.get(API, params={"id": dataset}, timeout=60)
    r.raise_for_status()
    for res in r.json()["result"]["resources"]:
        if res["id"] == recurso_id:
            return res["url"]
    raise KeyError(f"Recurso {recurso_id} no encontrado en {dataset}")


def md5(ruta: Path) -> str:
    return hashlib.md5(ruta.read_bytes()).hexdigest()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--destino", type=Path, help="carpeta única de destino (por defecto Datos/ y Mapa/)")
    ap.add_argument("--forzar", action="store_true", help="sobrescribir ficheros existentes")
    args = ap.parse_args()

    for nombre, (carpeta, dataset, rid) in RECURSOS.items():
        dest = (args.destino or RAIZ / carpeta) / nombre
        dest.parent.mkdir(parents=True, exist_ok=True)
        if dest.exists() and not args.forzar:
            print(f"= {nombre}: ya existe, no se toca")
            continue
        url = url_recurso(dataset, rid)
        with requests.get(url, timeout=300, stream=True) as r:
            r.raise_for_status()
            with open(dest, "wb") as f:
                for trozo in r.iter_content(1 << 20):
                    f.write(trozo)
        print(f"+ {nombre}: {dest.stat().st_size / 1e6:.1f} MB  md5 {md5(dest)}  <- {dataset}")


if __name__ == "__main__":
    main()
