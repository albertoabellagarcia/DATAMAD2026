"""App (H6): exportación sin campos personales (R-UI-03), atribuciones obligatorias y etiquetas
prohibidas (R-MET-04). No arranca Streamlit: revisa los textos y las funciones de datos.
"""

import json
from pathlib import Path

import pandas as pd

from cercasalud import app_datos

RAIZ = Path(__file__).resolve().parents[1]
ETIQUETAS_PROHIBIDAS = ("pacientes atendidos", "salud ganada", "muertes evitadas", "sin refugios")


def test_la_app_abre_la_base_y_no_un_escenario():
    """Las versiones descargadas van antes que los escenarios de sensibilidad, que se rotulan como tales."""
    nombres = ["20261113T190802Z-sin-claros", "20261113T190802Z", "20261113T190802Z-sin-claros-ambiguos"]
    assert app_datos.ordenar_versiones(nombres) == ["20261113T190802Z", "20261113T190802Z-sin-claros-ambiguos",
                                                     "20261113T190802Z-sin-claros"]
    assert app_datos.etiqueta_version("20261113T190802Z-sin-claros").startswith("Escenario: edificios S1")
    assert app_datos.etiqueta_version("20261113T190802Z") == "Base: datos del 13/11/2026"
    assert app_datos.etiqueta_version("20261113T190802Z-otro").startswith("Escenario: otro")


def test_los_selectores_abren_en_poblacion_total():
    """«total» va primero aunque «65+» vaya antes en orden alfabético."""
    assert app_datos.ordenar_objetivos(["75+", "total", "65+", "total"]) == ["total", "65+", "75+"]


def test_exportacion_sin_campos_personales():
    """Las columnas personales conocidas no salen en ninguna exportación."""
    tabla = pd.DataFrame({"unidad": ["u1"], "NIF": ["x"], "TITULARES_NOMBRE": ["y"], "con_acceso": [1.0]})
    assert list(app_datos.sin_campos_personales(tabla).columns) == ["unidad", "con_acceso"]


def test_atribuciones_literales():
    """Están los textos literales de INE, Comunidad, Ayuntamiento, CRTM y el crédito de OSM con la ODbL."""
    texto = "\n".join(app_datos.ATRIBUCIONES)
    for literal in ("Elaboración propia con datos extraídos del sitio web del INE: www.ine.es",
                    "Fuente de los datos: Comunidad de Madrid", "Origen de los datos: Ayuntamiento de Madrid",
                    "Powered by CRTM", "openstreetmap.org/copyright", "Open Database License"):
        assert literal in texto


def test_ninguna_etiqueta_prohibida_en_la_app_ni_en_el_paquete():
    """Grep de las etiquetas de R-MET-04 en la app, el código del paquete y la documentación."""
    archivos = [RAIZ / "app" / "streamlit_app.py", *sorted((RAIZ / "src" / "cercasalud").glob("*.py")),
                *sorted((RAIZ / "docs").glob("*.md")), RAIZ / "README.md"]
    for archivo in archivos:
        texto = archivo.read_text(encoding="utf-8").lower()
        for etiqueta in ETIQUETAS_PROHIBIDAS:
            assert etiqueta not in texto, (archivo.name, etiqueta)


def test_exportaciones_de_la_ficha_sin_datos_personales_ni_recursos_externos():
    """GeoJSON válido, manifiesto con solver, supuestos y atribuciones, y HTML sin enlaces a recursos externos."""
    detalle = pd.DataFrame({"componente": ["a_pie"], "zona": ["z1_2"], "lon": [-3.7], "lat": [40.4],
                            "municipio": ["28079"], "NIF": ["x"], "ganancia_cartera": [10.0]})
    geo = app_datos.geojson_zonas(detalle)
    assert geo["type"] == "FeatureCollection" and geo["features"][0]["geometry"]["coordinates"] == [-3.7, 40.4]
    assert "NIF" not in geo["features"][0]["properties"]
    fila = {"objetivo": "total", "k": 1, "milp_estado": "optimo", "milp_ganancia": 10.0}
    manifiesto = app_datos.manifiesto_escenario("v1", "a_pie", fila, {"umbral_min": 15}, {"conexion": 3.0})
    assert manifiesto["solver"]["estado"] == "optimo" and manifiesto["restricciones"] == {"k": 1}
    assert len(manifiesto["atribuciones"]) == len(app_datos.ATRIBUCIONES)
    html = app_datos.ficha_html("Ficha", manifiesto, detalle)
    assert "NIF" not in html and "<script" not in html and "<link" not in html
    for literal in ("Powered by CRTM", "www.ine.es"):
        assert literal in html


def test_alternativas_de_b1_en_la_ficha():
    """La ficha de B1 muestra la mejor cartera sin cada mercado, con la pérdida, en la app, el HTML y el JSON."""
    alternativas = [{"excluido": "Mercado A", "mercados": ["Mercado B", "Mercado C"], "estado": "optimo",
                     "peor_hora_despues": 99.4, "personas_hora_ganadas": 200.2, "perdida_peor_hora_pct": 1.234}]
    fila = {"objetivo": "total", "max_centros": 3, "max_centro_horas": 12, "milp_estado": "optimo",
            "alternativas_sin_mercado": json.dumps(alternativas)}
    tabla = app_datos.tabla_alternativas_b1(fila)
    assert tabla.loc[0, "Mejor cartera sin él"] == "Mercado B, Mercado C"
    assert tabla.loc[0, "Pérdida (% de la ganancia)"] == 1.2 and tabla.loc[0, "Peor hora"] == 99.0
    manifiesto = app_datos.manifiesto_escenario("v1", "b1", fila, {}, {})
    assert manifiesto["alternativas_sin_mercado"] == alternativas
    html = app_datos.ficha_html("Ficha", manifiesto, pd.DataFrame({"mercado": ["Mercado A"]}), tabla)
    assert "¿elección firme o empate?" in html and "Mercado B, Mercado C" in html
    assert app_datos.tabla_alternativas_b1({"objetivo": "total"}).empty


def test_ficha_html_con_resumen_y_limites_legibles():
    """La ficha descargable pone arriba el resumen y los límites, y sigue sin recursos externos."""
    fila = {"objetivo": "total", "k": 3, "milp_estado": "optimo", "milp_ganancia": 10.0}
    manifiesto = app_datos.manifiesto_escenario("v1", "a_transporte", fila, {}, {})
    html = app_datos.ficha_html("Ficha", manifiesto, pd.DataFrame({"Zona": ["z1"]}), None,
                                [("Ganancia", "51.489")], "Una zona no es un solar.")
    assert html.index("Ganancia") < html.index("Manifiesto técnico") and "Una zona no es un solar." in html
    assert "<script" not in html and "<link" not in html and "http://" not in html.split("Atribuciones")[0]
    assert "51.489" in app_datos.resumen_html([("Ganancia", "51.489")])


def test_alternativas_de_b1_con_la_perdida_delante_y_nombres_cortos():
    alternativas = [{"excluido": "Mercado municipal de Pacífico", "mercados": ["Mercado municipal de Prosperidad"],
                     "estado": "optimo", "peor_hora_despues": 99.4, "personas_hora_ganadas": 200.2,
                     "perdida_peor_hora_pct": 3.69}]
    tabla = app_datos.tabla_alternativas_b1({"alternativas_sin_mercado": json.dumps(alternativas)})
    assert list(tabla.columns)[:2] == ["Sin este mercado", "Pérdida (% de la ganancia)"]
    assert tabla.loc[0, "Sin este mercado"] == "Pacífico" and tabla.loc[0, "Mejor cartera sin él"] == "Prosperidad"


def test_la_app_arranca_solo_en_local_sin_telemetria_ni_boton_de_despliegue():
    """Opciones de arranque: 127.0.0.1, sin estadísticas de uso, sin menú de desarrollo y tema monocromo."""
    from cercasalud.cli import opciones_app

    opciones = opciones_app()
    pares = dict(zip(opciones[::2], opciones[1::2], strict=True))
    assert pares["--server.address"] == "127.0.0.1" and pares["--browser.gatherUsageStats"] == "false"
    assert pares["--client.toolbarMode"] == "minimal" and pares["--theme.primaryColor"] == "#1A1A1A"
