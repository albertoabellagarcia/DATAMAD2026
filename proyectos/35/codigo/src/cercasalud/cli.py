"""Órdenes de la línea de comandos: `uv run cercasalud <orden>` (SPEC §12).

- fetch: adquisición explícita y nueva versión fechada (la única orden que usa la red).
- build: cálculo sin red sobre una versión existente.
- verify: recalcula los SHA-256 de una versión.
- app: app local de Streamlit, solo en 127.0.0.1 (R-ARQ-02).
- web: página web al estilo WikiBarrio (P-28), desde resultados guardados; solo en 127.0.0.1.
- scenario: prevista, todavía sin implementar.
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

from . import construccion, huellas, ingesta
from .catalogo import archivos_de, fuentes_disponibles
from .configuracion import leer_config
from .rutas import carpeta_procesados, raiz_datos


def orden_fetch(argumentos) -> int:
    """Descarga las fuentes pedidas (o ninguna con --solo-registrar) y crea una versión."""
    raiz, id_version = raiz_datos(), ingesta.nuevo_id_snapshot()
    descargas = []
    if not argumentos.solo_registrar:
        for archivo in archivos_de(argumentos.fuente):
            try:
                descargas.append(ingesta.adquirir(raiz, archivo, id_version))
            except (OSError, ValueError) as error:  # red, HTTP, disco o URL: se registra y se sigue
                descargas.append({"fuente": archivo.fuente, "nombre": archivo.nombre,
                                  "accion": "error", "detalle": repr(error)})
    destino = ingesta.crear_snapshot(raiz, id_version, descargas)
    estados = [entrada["estado"] for entrada in ingesta.leer_snapshot(raiz, id_version)["archivos"]]
    print(json.dumps({"snapshot": id_version, "archivo": str(destino), "descargas": descargas,
                      "estados": {e: estados.count(e) for e in set(estados)}}, ensure_ascii=False, indent=2))
    errores = any(d["accion"] == "error" for d in descargas) or any(e != "ok" for e in estados)
    return 1 if errores else 0


def orden_verify(argumentos) -> int:
    """Comprueba que cada archivo de la versión sigue teniendo su SHA-256."""
    problemas = ingesta.verificar_snapshot(raiz_datos(), argumentos.snapshot)
    print("Sin problemas." if not problemas else "\n".join(problemas))
    return 1 if problemas else 0


ETAPAS = ("primaria", "poblacion", "demanda", "acceso_pie", "acceso", "refugios_pie", "refugios", "refugios_ampliados",
          "renta",
          "candidatos_pie", "actuaciones", "capas_app", "contexto")
CARPETA_DE_ETAPA = {"capas_app": "app"}  # carpeta de resultados cuando no se llama como la etapa


def orden_build(argumentos) -> int:
    """Ejecuta, en orden, las etapas pedidas (por defecto, todas) sobre una versión existente."""
    raiz, config = raiz_datos(), leer_config()
    pedidas = argumentos.etapa or list(ETAPAS)
    funciones = {
        "primaria": lambda: construccion.etapa_primaria(raiz, argumentos.snapshot)["conteos"],
        "poblacion": lambda: construccion.etapa_poblacion(raiz, argumentos.snapshot)["conteos"],
        "demanda": lambda: construccion.etapa_demanda(raiz, argumentos.snapshot, config)["conteos"],
        "acceso_pie": lambda: construccion.etapa_acceso_pie(raiz, argumentos.snapshot, config)["conteos"],
        "acceso": lambda: construccion.etapa_acceso(raiz, argumentos.snapshot, config)["base_comunidad_total"],
        "refugios_pie": lambda: construccion.etapa_refugios_pie(raiz, argumentos.snapshot, config)["conteos"],
        "refugios": lambda: construccion.etapa_refugios(raiz, argumentos.snapshot, config)["franja_referencia_c"],
        "refugios_ampliados": lambda: construccion.etapa_refugios_ampliados(raiz, argumentos.snapshot,
                                                                            config)["comprobacion_verificados"],
        "renta": lambda: construccion.etapa_renta(raiz, argumentos.snapshot)["conteos"],
        "candidatos_pie": lambda: construccion.etapa_candidatos_pie(raiz, argumentos.snapshot, config)["conteos"],
        "actuaciones": lambda: construccion.etapa_actuaciones(raiz, argumentos.snapshot, config)["estados_a"],
        "capas_app": lambda: construccion.etapa_capas_app(raiz, argumentos.snapshot, config)["comprobaciones_mapa"],
        "contexto": lambda: construccion.etapa_contexto(raiz, argumentos.snapshot)["conteos"],
    }
    resultados = {}
    for etapa in [e for e in ETAPAS if e in pedidas]:
        # R-ARQ-03: se omite si sus entradas, el código y la configuración no cambiaron.
        destino = carpeta_procesados(raiz, argumentos.snapshot) / CARPETA_DE_ETAPA.get(etapa, etapa)
        valor = huellas.huella(raiz, argumentos.snapshot, etapa)
        if not argumentos.forzar and huellas.sin_cambios(destino, valor):
            resultados[etapa] = "omitida: sin cambios en sus entradas (usa --forzar para recalcularla)"
            continue
        resultados[etapa] = funciones[etapa]()
        huellas.guardar(destino, valor)
    print(json.dumps(resultados, ensure_ascii=False, indent=2, default=str))
    return 0


APP = Path(__file__).resolve().parents[2] / "app" / "streamlit_app.py"


def opciones_app() -> list[str]:
    """Opciones de Streamlit de la app: local, sin telemetría, sin enlaces a servicios y con el tema propio."""
    return ["--server.address", "127.0.0.1", "--server.headless", "true", "--browser.gatherUsageStats", "false",
            "--server.enableStaticServing", "true",  # estilo de mapa y capas locales (app/static/)
            # Sin el botón «Deploy» ni el menú de desarrollo: enlazan con servicios de Streamlit en internet.
            "--client.toolbarMode", "minimal",
            # Interfaz casi monocroma: el mapa es lo único con color (decisión del usuario, 15/11/2026).
            "--theme.base", "light", "--theme.primaryColor", "#1A1A1A", "--theme.textColor", "#1A1A1A",
            "--theme.backgroundColor", "#FFFFFF", "--theme.secondaryBackgroundColor", "#F2F2F2",
            # Tema del 16/11 (plan de la app, punto 5): esquinas pequeñas, bordes grises visibles, enlaces
            # subrayados en negro y cifras en negrita. La fuente es la que trae Streamlit, servida en local.
            "--theme.baseRadius", "small", "--theme.buttonRadius", "small", "--theme.borderColor", "#BDBDBD",
            "--theme.showWidgetBorder", "true", "--theme.dataframeHeaderBackgroundColor", "#F2F2F2",
            "--theme.linkColor", "#1A1A1A", "--theme.linkUnderline", "true", "--theme.metricValueFontWeight", "700",
            "--theme.headingFontWeights", "700", "--theme.paddingTop", "2.5rem"]


def orden_app(argumentos) -> int:
    """Arranca la app local: solo en 127.0.0.1, sin abrir el navegador y sin telemetría (R-ARQ-02)."""
    orden = [sys.executable, "-m", "streamlit", "run", str(APP), *opciones_app()]
    return subprocess.run(orden, check=False).returncode


def orden_web(argumentos) -> int:
    """Prepara los datos de la página web desde resultados guardados y la sirve en 127.0.0.1 (SPEC P-28).

    No calcula nada de `build`: solo lee `datos/procesados/<versión>/`. Con `--exportar CARPETA`
    copia la página con sus datos a una carpeta vacía que se puede publicar tal cual.
    """
    from . import web
    if not argumentos.solo_servir:
        resumen = web.exportar(raiz_datos(), argumentos.snapshot, web.CARPETA_WEB / "datos", leer_config())
        print(json.dumps({"version": resumen["version_datos"], "pesos_bytes": resumen["pesos_bytes"]},
                         ensure_ascii=False, indent=2))
    if argumentos.exportar:
        copiados = web.exportar_paquete(web.CARPETA_WEB, Path(argumentos.exportar))
        print(f"Paquete en {argumentos.exportar}: {', '.join(copiados)}")
        return 0
    web.servir(web.CARPETA_WEB, argumentos.puerto, abrir=not argumentos.no_abrir)
    return 0


def orden_no_implementada(argumentos) -> int:
    """Informa de que la orden está prevista pero no existe todavía."""
    print(f"La orden '{argumentos.orden}' está prevista en la SPEC §12, pero todavía no está implementada.",
          file=sys.stderr)
    return 2


def construir_parser() -> argparse.ArgumentParser:
    """Define las órdenes y sus opciones."""
    parser = argparse.ArgumentParser(prog="cercasalud", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    ordenes = parser.add_subparsers(dest="orden", required=True)
    fetch = ordenes.add_parser("fetch", help="descarga y crea una versión fechada")
    fetch.add_argument("--fuente", action="append", choices=fuentes_disponibles(),
                       help="fuente que se descarga (repetible); por defecto, todas")
    fetch.add_argument("--solo-registrar", action="store_true",
                       help="no descarga nada: crea la versión con lo ya adquirido")
    fetch.set_defaults(funcion=orden_fetch)
    for nombre, funcion in (("build", orden_build), ("verify", orden_verify)):
        sub = ordenes.add_parser(nombre)
        sub.add_argument("--snapshot", required=True, help="ID de la versión, p. ej. 20261113T190000Z")
        sub.set_defaults(funcion=funcion)
        if nombre == "build":
            sub.add_argument("--etapa", action="append", choices=ETAPAS,
                             help="etapa que se ejecuta (repetible); por defecto, todas en orden")
            sub.add_argument("--forzar", action="store_true",
                             help="recalcula aunque sus entradas no hayan cambiado (R-ARQ-03)")
    ordenes.add_parser("app", help="app local en 127.0.0.1").set_defaults(funcion=orden_app)
    pagina = ordenes.add_parser("web", help="página web: prepara sus datos y la sirve en 127.0.0.1")
    pagina.add_argument("--snapshot", default="20261113T190802Z",
                        help="versión de datos (por defecto, la base vigente de la demo)")
    pagina.add_argument("--puerto", type=int, default=8765)
    pagina.add_argument("--no-abrir", action="store_true", help="no abre el navegador")
    pagina.add_argument("--solo-servir", action="store_true", help="sirve los datos ya preparados sin regenerarlos")
    pagina.add_argument("--exportar", metavar="CARPETA", help="copia la página y sus datos a una carpeta vacía")
    pagina.set_defaults(funcion=orden_web)
    ordenes.add_parser("scenario").set_defaults(funcion=orden_no_implementada)
    return parser


def main(argv: list[str] | None = None) -> int:
    """Punto de entrada de `uv run cercasalud`."""
    argumentos = construir_parser().parse_args(argv)
    return argumentos.funcion(argumentos)


if __name__ == "__main__":
    sys.exit(main())
