"""Datos que lee la app (H6): capa del mapa precalculada, tablas de resultados y atribuciones.

La app no calcula (R-UI-01): todo lo que muestra sale de `build`. Esta capa solo une estados
ya calculados y pasa coordenadas a WGS84 para dibujarlas (cálculo en EPSG:25830, visualización
en WGS84).
"""

from pathlib import Path

import pandas as pd
from pyproj import Transformer

# Textos literales de fases/H0_candidatura/agente_b/LICENCIAS.md (líneas 35-38) y crédito de OSM.
ATRIBUCIONES = (
    ("Mapa y red viaria: © colaboradores de OpenStreetMap, datos bajo la Open Database License (ODbL): "
     "https://www.openstreetmap.org/copyright"),
    "Powered by CRTM (http://www.crtm.es/). Horarios GTFS explotados para calcular tiempos de viaje.",
    "Elaboración propia con datos extraídos del sitio web del INE: www.ine.es",
    "Fuente de los datos: Comunidad de Madrid (http://datos.comunidad.madrid)",
    "Origen de los datos: Ayuntamiento de Madrid",
)
COLUMNAS_PERSONALES = ("NIF", "TITULARES_NOMBRE", "telefono", "email")


def capa_mapa(proc: Path) -> pd.DataFrame:
    """Unidades con población, estados de A (base), de B (franja de referencia) y de C, en WGS84."""
    unidades = pd.read_parquet(proc / "demanda" / "unidades_demanda.parquet",
                               columns=["unidad", "cusec", "x", "y", "poblacion_total", "poblacion_65_mas",
                                        "poblacion_75_mas"])
    tabla = unidades.merge(pd.read_parquet(proc / "acceso" / "estados_base.parquet").drop(columns="cusec"),
                           on="unidad", how="left", validate="one_to_one")
    b = proc / "refugios" / "b_estados_base_central.parquet"
    if b.exists():
        import json
        franja = json.loads((proc / "refugios" / "resumen.json").read_text(encoding="utf-8"))["franja_referencia_c"]
        estados_b = pd.read_parquet(b)
        ref = estados_b[(estados_b["tipo_dia"] == "laborable_julio") & (estados_b["hora"] == franja)]
        tabla = tabla.merge(ref[["unidad", "estado", "motivo"]].rename(
            columns={"estado": "estado_b", "motivo": "motivo_b"}), on="unidad", how="left", validate="one_to_one")
        # C por unidad con cada modo de A y B en la franja de referencia (mismo cálculo que `refugios`).
        from .refugios import estados_c
        for modo in ("pie", "transporte"):
            a = tabla[["unidad", f"estado_{modo}", f"motivo_{modo}"]].rename(
                columns={f"estado_{modo}": "estado", f"motivo_{modo}": "motivo"})
            c = estados_c(a, ref[["unidad", "estado", "motivo"]]).set_index("unidad")["estado"]
            tabla[f"estado_c_{modo}"] = tabla["unidad"].map(c)
    lon, lat = Transformer.from_crs("EPSG:25830", "EPSG:4326", always_xy=True).transform(
        tabla["x"].to_numpy(), tabla["y"].to_numpy())
    return tabla.drop(columns=["x", "y"]).assign(lon=lon, lat=lat)


def ordenar_versiones(nombres: list[str]) -> list[str]:
    """Versiones de datos para el selector: primero las descargadas y después los escenarios.

    Una versión descargada tiene el identificador de `fetch` sin sufijo (`20261113T190802Z`); un
    escenario de sensibilidad lleva sufijo (`20261113T190802Z-sin-claros`). Dentro de cada grupo,
    la más reciente primero. Así la app abre siempre la base y no un escenario (hasta el 15/11,
    el orden alfabético inverso abría `-sin-claros-ambiguos`).
    """
    descargadas = sorted((n for n in nombres if "-" not in n), reverse=True)
    escenarios = sorted((n for n in nombres if "-" in n), reverse=True)
    return descargadas + escenarios


ESCENARIOS_VERSION = {
    "sin-claros": "edificios S1 (sin los claramente no residenciales)",
    "sin-claros-ambiguos": "edificios S2 (sin los no residenciales y los ambiguos)",
    "base-s1-427": "S1 con 427 centros (preparado, sin recalcular)",
}


def fecha_version(identificador: str) -> str:
    """«20261113T190802Z» → «13/11/2026»; si no tiene ese formato, lo devuelve tal cual."""
    fecha = identificador.split("T")[0]
    return f"{fecha[6:8]}/{fecha[4:6]}/{fecha[0:4]}" if len(fecha) == 8 and fecha.isdigit() else identificador


def etiqueta_version(nombre: str) -> str:
    """Rótulo del selector de versión.

    «20261113T190802Z» → «Base: datos del 13/11/2026»;
    «20261113T190802Z-sin-claros» → «Escenario: edificios S1 (…) · datos del 13/11/2026».
    El identificador completo sigue al pie de cada pantalla.
    """
    identificador, _, sufijo = nombre.partition("-")
    if not sufijo:
        return f"Base: datos del {fecha_version(identificador)}"
    return f"Escenario: {ESCENARIOS_VERSION.get(sufijo, sufijo)} · datos del {fecha_version(identificador)}"


def texto_objetivo(objetivo: str) -> str:
    """«total» → «Población total»; «75+» → «Personas de 75 años o más»."""
    if objetivo == "total":
        return "Población total"
    return f"Personas de {objetivo[:-1]} años o más" if objetivo.endswith("+") else objetivo


def ordenar_objetivos(objetivos) -> list[str]:
    """Objetivos de una cartera con «total» primero y después los grupos de edad (65+, 75+…)."""
    return sorted(set(objetivos), key=lambda o: (o != "total", o))


def sin_campos_personales(tabla: pd.DataFrame) -> pd.DataFrame:
    """Quita cualquier columna personal antes de exportar (R-UI-03)."""
    return tabla.drop(columns=[c for c in tabla.columns if c in COLUMNAS_PERSONALES])


# ------------------------------ ficha de decisión y exportación (R-UI-03) ----------------------
# Solo dan formato a resultados ya calculados por `build`; no calculan nada (R-UI-01).

RESPONSABLES = {
    "a_pie": ("Consejería de Sanidad de la Comunidad de Madrid (Servicio Madrileño de Salud), como titular de la "
              "red pública de atención primaria. Propuesta sin consultar con el organismo."),
    "a_transporte": ("Consejería de Sanidad de la Comunidad de Madrid (Servicio Madrileño de Salud); la mejora del "
                     "transporte depende además del Consorcio Regional de Transportes. Propuesta sin consultar con el organismo."),
    "b1": "Ayuntamiento de Madrid, titular de la red de mercados municipales. Propuesta sin consultar con el organismo.",
}
CONDICIONES = {
    "a_pie": ("Una zona de búsqueda es una celda de 250 m con población residente, no un solar ni un edificio. La "
              "ganancia supone un centro abierto en esa zona y mide proximidad física potencial, no capacidad ni citas."),
    "a_transporte": ("Igual que a pie, con transporte público de 9 a 13 h en un martes laborable (mediana de las "
                     "salidas de la franja). Supone el centro abierto en la franja."),
    "b1": ("Abrir al público la zona climatizada del mercado en esas horas. El acceso a la zona climatizada no "
           "consta en ninguna ficha (D-33): la ganancia es bajo el supuesto de acceso dentro del horario abierto."),
}


def geojson_zonas(detalle: pd.DataFrame) -> dict:
    """GeoJSON (WGS84) de las zonas elegidas de una cartera, sin campos personales."""
    rasgos = []
    for fila in sin_campos_personales(detalle).to_dict("records"):
        propiedades = {k: v for k, v in fila.items() if k not in ("lon", "lat")}
        rasgos.append({"type": "Feature", "geometry": {"type": "Point", "coordinates": [fila["lon"], fila["lat"]]},
                       "properties": propiedades})
    return {"type": "FeatureCollection", "features": rasgos}


def manifiesto_escenario(version: str, componente: str, fila: dict, supuestos: dict, no_evaluable: dict) -> dict:
    """Manifiesto JSON de una actuación: versión de datos, restricciones, supuestos, solver,
    población no evaluable y atribuciones (PLAN §7.3)."""
    import json

    solver = {k[len("milp_"):]: v for k, v in fila.items() if k.startswith("milp_")}
    manifiesto = {"version_datos": version, "componente": componente, "objetivo": fila.get("objetivo"),
                  "restricciones": {k: fila[k] for k in ("k", "max_centros", "max_centro_horas") if k in fila},
                  "supuestos": supuestos, "solver": solver, "no_evaluable": no_evaluable,
                  "responsable_propuesto": RESPONSABLES[componente], "condiciones": CONDICIONES[componente],
                  "atribuciones": list(ATRIBUCIONES)}
    if isinstance(fila.get("alternativas_sin_mercado"), str):
        manifiesto["alternativas_sin_mercado"] = json.loads(fila["alternativas_sin_mercado"])
    return manifiesto


TEXTO_ALTERNATIVAS_B1 = (
    "Mejor cartera posible sin cada mercado elegido. «Pérdida» es el porcentaje de la ganancia en la peor hora "
    "que se pierde al excluirlo: si es pequeña, ese mercado y el que entra en su lugar están prácticamente "
    "empatados y la elección entre ellos es casi indiferente; si es grande, la elección es firme.")


def tabla_alternativas_b1(fila: dict) -> pd.DataFrame:
    """Alternativas de una cartera de B1 (ya calculadas por `build`) en una tabla legible."""
    import json

    alternativas = json.loads(fila.get("alternativas_sin_mercado") or "[]")
    if not alternativas:
        return pd.DataFrame()
    tabla = pd.DataFrame(alternativas)
    tabla["excluido"] = tabla["excluido"].map(nombre_mercado_corto)
    tabla["mercados"] = tabla["mercados"].map(lambda lista: ", ".join(nombre_mercado_corto(m) for m in lista))
    # La pérdida va justo después del mercado: es lo que dice si la elección es firme o un empate.
    orden = ["excluido", "perdida_peor_hora_pct", "peor_hora_despues", "personas_hora_ganadas", "mercados", "estado"]
    return tabla[[c for c in orden if c in tabla.columns]].rename(
        columns={"excluido": "Sin este mercado", "mercados": "Mejor cartera sin él", "peor_hora_despues": "Peor hora",
                 "personas_hora_ganadas": "Personas-hora ganadas", "perdida_peor_hora_pct": "Pérdida (% de la ganancia)",
                 "estado": "Estado del solver"}).round({"Peor hora": 0, "Personas-hora ganadas": 0,
                                                        "Pérdida (% de la ganancia)": 1}).astype(
        {"Peor hora": "Int64", "Personas-hora ganadas": "Int64"})


def nombre_mercado_corto(nombre: str) -> str:
    """«Mercado municipal de Pacífico» → «Pacífico» (el prefijo se repite en los 43)."""
    return nombre.removeprefix("Mercado municipal de ").removeprefix("Mercado Municipal de ")


def resumen_html(resumen: list[tuple[str, str]]) -> str:
    """Resumen «concepto: valor» de la ficha para la app: concepto en gris, valor en negrita."""
    import html

    filas = "".join(
        "<div style='display:flex;gap:16px;padding:9px 0;border-bottom:1px solid #BDBDBD'>"
        f"<span style='flex:0 0 46%;color:#4D4D4D'>{html.escape(c)}</span>"
        f"<span style='font-weight:700;color:#1A1A1A'>{html.escape(v)}</span></div>" for c, v in resumen)
    return f"<div style='font-size:1rem;line-height:1.4'>{filas}</div>"


def ficha_html(titulo: str, manifiesto: dict, tabla: pd.DataFrame, alternativas: pd.DataFrame | None = None,
               resumen: list[tuple[str, str]] | None = None, limites: str | None = None) -> str:
    """Ficha de decisión en HTML legible y autónomo (sin recursos externos).

    Arriba, el resumen «concepto: valor» y los límites; después, zonas o bloques, alternativas y,
    al final, el manifiesto técnico completo (versión, supuestos y solver) para reproducirla.
    """
    import html
    import json

    def tabla_html(datos: pd.DataFrame) -> str:
        return datos.to_html(index=False, border=0, classes="datos", na_rep="—")

    filas = "".join(f"<tr><th>{html.escape(str(k))}</th><td>{html.escape(json.dumps(v, ensure_ascii=False, default=str))}"
                    "</td></tr>" for k, v in manifiesto.items() if k not in ("atribuciones", "alternativas_sin_mercado"))
    atribuciones = "".join(f"<li>{html.escape(a)}</li>" for a in manifiesto["atribuciones"])
    bloque_resumen = "" if not resumen else ("<table class='resumen'>" + "".join(
        f"<tr><th>{html.escape(c)}</th><td>{html.escape(v)}</td></tr>" for c, v in resumen) + "</table>")
    bloque_limites = "" if not limites else (f"<div class='limites'><h2>Límites que acompañan</h2><p>{html.escape(limites)}"
                                             "</p></div>")
    bloque_alternativas = "" if alternativas is None or alternativas.empty else (
        "<h2>Alternativas: ¿elección firme o empate?</h2><p>" + html.escape(TEXTO_ALTERNATIVAS_B1) + "</p>"
        + tabla_html(alternativas))
    estilo = ("body{font-family:'Segoe UI',Arial,sans-serif;color:#1A1A1A;max-width:60rem;margin:2rem auto;"
              "padding:0 1rem;line-height:1.45}h1{margin-bottom:.2rem}.sub{color:#4D4D4D;margin-top:0}"
              "table{border-collapse:collapse;margin:.6rem 0 1.2rem}th,td{padding:.45rem .6rem;text-align:left;"
              "vertical-align:top;border-bottom:1px solid #BDBDBD}table.resumen th{font-weight:400;color:#4D4D4D;"
              "width:22rem}table.resumen td{font-weight:700}table.datos th{background:#F2F2F2}"
              ".limites{background:#F2F2F2;padding:.2rem 1rem;border-left:4px solid #1A1A1A}"
              "details{margin-top:1.5rem}small{color:#4D4D4D}")
    return ("<!doctype html><html lang='es'><head><meta charset='utf-8'><title>" + html.escape(titulo) + "</title>"
            "<style>" + estilo + "</style></head><body><h1>" + html.escape(titulo) + "</h1>"
            f"<p class='sub'>Versión de datos {html.escape(str(manifiesto.get('version_datos', '')))} · resultados "
            "precalculados por CercaSalud MAD</p>" + bloque_resumen + bloque_limites
            + "<h2>Zonas o bloques</h2>" + tabla_html(sin_campos_personales(tabla))
            + bloque_alternativas
            + "<h2>Manifiesto técnico (para reproducir)</h2><table>" + filas + "</table>"
            + "<h2>Atribuciones</h2><ul>" + atribuciones + "</ul>"
            "<p><small>Mide proximidad física potencial. No mide citas, capacidad ni efectos sobre la salud.</small></p>"
            "</body></html>")
