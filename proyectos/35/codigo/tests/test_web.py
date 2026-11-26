"""Página web (SPEC P-28): el exportador solo da formato a resultados de `build`, la capa «qué
cambia» cuadra con la ganancia de las tablas y la página no lleva etiquetas prohibidas, datos
personales ni recursos de internet.

Las pruebas de integración leen la versión base de la demo si está en este equipo; si no, se omiten.
"""

import json
import re
from pathlib import Path

import pandas as pd
import pytest

from cercasalud import web
from cercasalud.configuracion import leer_config
from cercasalud.rutas import raiz_datos

RAIZ = Path(__file__).resolve().parents[1]
ETIQUETAS_PROHIBIDAS = ("pacientes atendidos", "salud ganada", "muertes evitadas", "sin refugios")
# El texto de licencia del registro sanitario dice «la columna NIF se elimina en la ingesta»: se busca
# la columna (clave JSON o cabecera CSV), no la palabra.
CAMPOS_PERSONALES = ('"NIF"', "NIF,", ",NIF", "TITULARES_NOMBRE", "DATO PERSONAL")


def base_disponible() -> bool:
    """La versión base de la demo está calculada en este equipo."""
    try:
        return (raiz_datos() / "procesados" / web.VERSION_DEMO / "app" / "celdas_mapa.parquet").exists()
    except (OSError, ValueError):
        return False


# ------------------------------------------------------------------ horarios de los espacios


def test_horario_general_solo_si_no_hay_tramo_de_verano():
    """El horario general publicado se enseña, con su fuente, solo donde no hay ningún tramo de verano curado."""
    curados = pd.DataFrame([
        {"id": "eq:1", "laborables_julio": "09:00-14:00", "laborables_agosto": "cerrado", "sabado": "cerrado",
         "domingo": "cerrado", "regla": "r1"},
        {"id": "eq:2", "laborables_julio": "pendiente", "laborables_agosto": "cerrado", "sabado": "pendiente",
         "domingo": "pendiente", "regla": "r2"},
    ]).set_index("id")
    base = {"tipo": "centro_cultural", "nivel": "respaldo_oficial", "fuente": "Ayuntamiento de Madrid",
            "horario_texto": "Lunes a viernes de 9 a 21 h"}
    con_tramo = web.horario_espacio({**base, "id": "eq:1"}, curados)
    assert "de 9:00 a 14:00" in con_tramo and "Horario general" not in con_tramo
    sin_tramo = web.horario_espacio({**base, "id": "eq:2"}, curados)
    assert "r2" in sin_tramo and "(Ayuntamiento de Madrid), sin dato de verano: «Lunes a viernes de 9 a 21 h»" in sin_tramo
    osm = web.horario_espacio({**base, "id": "osm:n1", "nivel": "potencial", "horario_texto": "Tu-Su 10:00-20:00"},
                              curados)
    assert "«máximo posible»" in osm and "(OpenStreetMap, formato opening_hours)" in osm
    vacio = web.horario_espacio({**base, "id": "eq:3", "horario_texto": ""}, curados)
    assert "Horario general" not in vacio


# ------------------------------------------------------------------ unidades


def test_codificar_contorno_no_pierde_nada():
    """Contorno con 5 decimales → enteros con diferencias → el mismo contorno."""
    puntos = [[-3.62625, 41.08606], [-3.62626, 41.08696], [-3.62507, 41.08697], [-3.62506, 41.08607]]
    plano = web.codificar_contorno(puntos)
    assert plano[:2] == [-362625, 4108606] and plano[2:4] == [-1, 90]
    decodificado = web.decodificar_contorno(plano)
    assert [v for par in decodificado for v in par] == pytest.approx([v for par in puntos for v in par], abs=1e-9)


def test_unidades_que_ganan_cuentan_a_cada_unidad_una_vez():
    """Una unidad cubierta por dos zonas elegidas gana una sola vez; la que no cubre ninguna, no gana."""
    sin = pd.DataFrame({"unidad": ["u1", "u2", "u3"], "poblacion_total": [10.0, 20.0, 30.0]})
    cubre = [frozenset({"z1", "z2"}), frozenset({"z3"}), frozenset()]
    ganan = web.unidades_que_ganan(sin, cubre, ["z1", "z2"])
    assert ganan["unidad"].tolist() == ["u1"] and ganan["poblacion_total"].sum() == 10.0


def test_comprobar_que_cambia_detecta_una_discrepancia():
    cambios = {"a|total|1": {"ganancia_objetivo": 100.0, "ganancia_tabla": 100.2},
               "a|total|3": {"ganancia_objetivo": 90.0, "ganancia_tabla": 100.0}}
    assert web.comprobar_que_cambia(cambios) == ["a|total|3"]


def test_barras_de_la_pagina_no_se_suman():
    """Dos barras con su propia cifra y largo relativo a la mayor; ninguna es la suma de las otras."""
    fila = {"regla_simple_ganancia": 9421.0, "milp_ganancia": 51489.16}
    barras = web.barras_texto(fila, "a_transporte")
    assert [b["texto"] for b in barras] == ["9.421", "51.489"]
    assert barras[1]["fraccion"] == 1.0 and barras[0]["fraccion"] == pytest.approx(9421 / 51489.16, abs=1e-4)


def test_cifras_de_un_territorio_separan_no_evaluable():
    """«No evaluable» se da aparte y nunca se cuenta como «sin opción»."""
    fila = {"pie_con_acceso": 60.0, "pie_sin_opcion_verificada": 30.0, "pie_no_evaluable": 10.0}
    cifras = web.cifras_modo(fila, "pie")
    assert cifras == {"con_acceso": "60,0 %", "sin_opcion": "30", "sin_opcion_pct": "30,0 %", "no_evaluable": "10"}


def test_clave_y_nombre_de_cartera():
    assert web.clave_cartera("a_transporte", {"objetivo": "total", "k": 3}) == "a_transporte|total|3"
    assert web.clave_cartera("b1", {"objetivo": "75+", "max_centros": 3, "max_centro_horas": 12}) == "b1|75+|3_12"
    assert web.nombre_opcion("a_pie", {"k": 1}) == "1 zona"
    assert web.nombre_opcion("b1", {"max_centros": 1, "max_centro_horas": 12}) == "1 mercado, 12 horas"


def test_la_carteras_se_leen_de_su_texto_en_csv():
    assert web.lista_elegidos("['z1', 'z2']") == ["z1", "z2"]
    assert web.lista_elegidos("") == []


# ------------------------------------------------------------------ archivos de la página


def archivos_pagina() -> list[Path]:
    return [web.CARPETA_WEB / nombre for nombre in web.ARCHIVOS_PAGINA if (web.CARPETA_WEB / nombre).exists()]


def test_la_pagina_no_pide_nada_a_internet():
    """Ningún script, hoja de estilo, fuente ni petición apunta fuera del propio sitio.

    Los enlaces que el usuario puede pulsar (licencias, fuentes) sí pueden ir a internet: son
    `<a href>` que no se cargan solos. Aquí se buscan solo las cargas automáticas.
    """
    cargas = re.compile(r"""(src\s*=\s*["']https?:|<link[^>]+href\s*=\s*["']https?:|fetch\(\s*["']https?:|"""
                        r"""@import|url\(\s*["']?https?:)""", re.IGNORECASE)
    for archivo in archivos_pagina():
        texto = archivo.read_text(encoding="utf-8")
        assert not cargas.search(texto), archivo.name


def test_ninguna_etiqueta_prohibida_en_la_pagina():
    for archivo in [*archivos_pagina(), RAIZ / "src" / "cercasalud" / "web.py"]:
        texto = archivo.read_text(encoding="utf-8").lower()
        for etiqueta in ETIQUETAS_PROHIBIDAS:
            assert etiqueta not in texto, (archivo.name, etiqueta)


# ------------------------------------------------------------------ integración con la versión base


@pytest.fixture(scope="module")
def exportado(tmp_path_factory) -> Path:
    if not base_disponible():
        pytest.skip("La versión base de la demo no está en este equipo.")
    destino = tmp_path_factory.mktemp("web") / "datos"
    web.exportar(raiz_datos(), web.VERSION_DEMO, destino, leer_config())
    return destino


def leer(destino: Path, nombre: str):
    return json.loads((destino / nombre).read_text(encoding="utf-8"))


def test_refugios_ampliados_en_la_pagina(exportado):
    """Tres líneas por separado, 43 mercados verificados, índices válidos y capas aparte (22/11/2026)."""
    ruta = exportado / "capas" / "refugios.json"
    if not ruta.exists():
        pytest.skip("La etapa refugios_ampliados no está calculada en este equipo.")
    r = leer(exportado, "capas/refugios.json")
    assert [linea["titulo"] for linea in r["lineas"]] == ["Solo verificados (43 mercados)", "Con respaldo oficial",
                                                          "Máximo posible si todos fueran refugios"]
    assert [n["clave"] for n in r["niveles"]] == ["verificado", "respaldo_oficial", "potencial"]
    verificados = [e for e in r["espacios"] if e[3] == 0]
    assert len(verificados) == 43 and {r["tipos"][e[2]]["clave"] for e in verificados} == {"mercado"}
    for e in r["espacios"]:
        assert 0 <= e[2] < len(r["tipos"]) and 0 <= e[5] < len(r["evidencias"]) and 0 <= e[6] < len(r["horarios"])
    assert r["parques"] and {f[2] for f in r["refresco"]} == {0, 1}


def test_caso_de_la_demo_con_las_cifras_de_la_tabla(exportado):
    """Transporte, población total, 3 zonas: 51.489 frente a 9.421 (carteras_a_transporte.csv), óptimo acreditado."""
    ficha = leer(exportado, "carteras.json")["carteras"]["a_transporte|total|3"]
    assert [b["texto"] for b in ficha["barras"]] == ["9.421", "51.489"]
    assert ficha["estado"] == "Óptimo acreditado por el solver"
    assert [z["municipio"] for z in ficha["zonas"]] == ["Boadilla del Monte", "Alcobendas", "Rivas-Vaciamadrid"]
    assert ficha["ganan"]["texto"] == "51.489" and len(ficha["ganan"]["secciones"]) > 0
    inicio = leer(exportado, "textos.json")["inicio"]
    assert [c["valor"] for c in inicio["cifras"]][2] == "51.489"


def test_que_cambia_esta_en_todas_las_carteras_de_a(exportado):
    """Las 12 carteras de A (a pie y en transporte; total y 65+; 1, 3 y 5 zonas) llevan su capa; B1 no."""
    carteras = leer(exportado, "carteras.json")["carteras"]
    con_capa = sorted(c for c, f in carteras.items() if "ganan" in f)
    assert len(con_capa) == 12 and all(not c.startswith("b1") for c in con_capa)


def test_secciones_suman_la_poblacion_de_la_comunidad(exportado):
    """Una fila por unidad, no por pieza de dibujo: las secciones suman los 7.113.886 habitantes del INE
    (REGISTRO-FALLOS 44), y cada parte dibujada apunta a una sección existente."""
    secciones = leer(exportado, "capas/secciones.json")
    assert secciones["n"] == len(secciones["cusec"]) == len(secciones["k_min_tp_9_13"]) == 4518
    assert sum(secciones["g"]) == pytest.approx(7_113_886, abs=secciones["n"])
    assert max(secciones["seccion_de_parte"]) < secciones["n"] and len(secciones["partes"]) >= secciones["n"]
    assert all(t.startswith(("municipio:", "distrito:")) for t in secciones["territorio"])


def test_que_cambia_por_seccion_suma_la_ganancia(exportado):
    """Las personas que ganan opción, sumadas por sección, dan la ganancia de la tabla (51.489 en el caso)."""
    ficha = leer(exportado, "carteras.json")["carteras"]["a_transporte|total|3"]
    assert sum(fila[2] for fila in ficha["ganan"]["secciones"] if fila[1] == 2) == pytest.approx(51_489, abs=50)


def test_mediana_ponderada():
    import numpy as np
    assert web.mediana_ponderada(np.array([10.0, 20.0, 30.0]), np.array([1.0, 1.0, 10.0])) == 30.0
    assert web.mediana_ponderada(np.array([10.0, 20.0, 30.0]), np.array([5.0, 1.0, 1.0])) == 10.0


def test_la_comunidad_y_el_umbral_de_la_leyenda(exportado):
    """Leyenda de la Comunidad en transporte: 7 tramos, raya del umbral tras «20–30» y «No evaluable» aparte."""
    mapa = leer(exportado, "mapa.json")
    leyenda = mapa["leyendas"]["comunidad:28"]["min_tp_9_13"]
    assert len(leyenda["filas"]) == 7 and mapa["variables"]["min_tp_9_13"]["umbral_tras"] == 2
    assert leyenda["filas"][2]["etiqueta"] == "20–30" and leyenda["extra"][0]["etiqueta"] == "No evaluable"
    comunidad = next(t for t in mapa["territorios"] if t["clave"] == "comunidad:28")
    assert comunidad["modos"]["transporte"]["sin_opcion"] == "289.240"


def test_ningun_dato_personal_ni_etiqueta_prohibida_en_los_datos(exportado):
    for archivo in exportado.rglob("*"):
        if archivo.is_file() and archivo.suffix in {".json", ".html", ".csv", ".geojson"}:
            texto = archivo.read_text(encoding="utf-8")
            for campo in CAMPOS_PERSONALES:
                assert campo not in texto, (archivo.name, campo)
            for etiqueta in ETIQUETAS_PROHIBIDAS:
                assert etiqueta not in texto.lower(), (archivo.name, etiqueta)


def test_atribuciones_y_aviso_odbl(exportado):
    fuentes = leer(exportado, "textos.json")["fuentes"]
    texto = " ".join(fuentes["atribuciones"]) + fuentes["odbl"]
    for literal in ("Powered by CRTM", "www.ine.es", "Fuente de los datos: Comunidad de Madrid",
                    "Origen de los datos: Ayuntamiento de Madrid", "ODbL"):
        assert literal in texto
    assert fuentes["version"] == web.VERSION_DEMO


def test_el_exportador_no_borra_carpetas_ajenas(tmp_path):
    """Solo vacía una carpeta que generó él (con manifiesto.json) o una vacía; cualquier otra, la deja."""
    ajena = tmp_path / "ajena"
    ajena.mkdir()
    (ajena / "importante.txt").write_text("no borrar", encoding="utf-8")
    with pytest.raises(ValueError, match="no se borra"):
        web.vaciar_destino(ajena)
    assert (ajena / "importante.txt").exists()
    propia = tmp_path / "datos"
    propia.mkdir()
    (propia / "manifiesto.json").write_text("{}", encoding="utf-8")
    web.vaciar_destino(propia)
    assert not propia.exists()


def test_exportar_paquete_exige_la_pagina_antes_de_crear_nada(tmp_path):
    with pytest.raises(ValueError, match="Falta"):
        web.exportar_paquete(tmp_path / "sin_pagina", tmp_path / "destino")
    assert not (tmp_path / "destino").exists()


def test_los_pasos_de_la_demo_existen(exportado):
    """Cada parada de la demo apunta a un territorio, una variable y una cartera que existen en los datos."""
    textos, mapa = leer(exportado, "textos.json"), leer(exportado, "mapa.json")
    carteras = leer(exportado, "carteras.json")["carteras"]
    claves = {t["clave"] for t in mapa["territorios"]}
    for paso in textos["inicio"]["demo"]:
        assert paso.get("territorio", "comunidad:28") in claves
        assert paso.get("variable", "min_tp_9_13") in mapa["variables"]
        assert paso.get("cartera", "a_transporte|total|3") in carteras
    assert all(clave in claves for clave in mapa["ir_a"])


def test_para_quien_lleva_su_limite_y_la_viabilidad(exportado):
    """El bloque «Para quién» dice que no consta que nadie vaya a usarla, y la viabilidad no promete servicios de pago."""
    fuentes = leer(exportado, "textos.json")["fuentes"]
    assert any("no se ha contactado con ningún organismo" in t for t in fuentes["para_quien"])
    assert any("AccessMod" in t for t in fuentes["para_quien"])
    assert any("MIT" in t for t in fuentes["viabilidad"])
    assert all(c["aporta"] for c in fuentes["conjuntos"])


def test_coordenadas_de_las_zonas_con_cuatro_decimales():
    tabla = pd.DataFrame({"Orden": [1], "Longitud": [-3.89911216], "Latitud": [40.41482354]})
    filas = web.tabla_texto(tabla)["filas"]
    assert filas[0][1:] == ["-3,8991", "40,4148"]


def test_capa_de_refugios_coincide_con_la_tabla_de_b(exportado):
    """Personas con refugio a alguna hora en Madrid capital = `personas_unicas_con_alguna_hora` de `b_resumen.csv`
    (laborable de julio, cota central); y solo hay valor de refugio en secciones de Madrid capital."""
    refugio = leer(exportado, "mapa.json")["desglose_refugio"]
    b = pd.read_csv(raiz_datos() / "procesados" / web.VERSION_DEMO / "refugios" / "b_resumen.csv")
    fila = b[(b["territorio"] == "madrid_capital") & (b["nombre"] == "base_central") & (b["grupo_edad"] == "total")
             & (b["tipo_dia"] == "laborable_julio")].iloc[0]
    cifra = int(refugio["por_territorio"]["municipio:28079"].split(" personas")[0].replace(".", ""))
    assert cifra == round(fila["personas_unicas_con_alguna_hora"])
    secciones = leer(exportado, "capas/secciones.json")
    con_valor = {c[:5] for c, v in zip(secciones["cusec"], secciones["refugio"], strict=True) if v is not None}
    assert con_valor == {"28079"}


# ------------------------------------------------------------------ simulador: probar una zona (23/11/2026)


def test_ganancia_por_candidato_cuenta_cada_unidad_una_vez_por_zona():
    """Una unidad cubierta por dos zonas suma en las dos (cada zona se evalúa sola), pero una sola vez en cada una."""
    sin = pd.DataFrame({"unidad": ["u1", "u2", "u3"], "poblacion_total": [10.0, 20.0, 30.0],
                        "poblacion_65_mas": [1.0, 2.0, 3.0]})
    cubre = [frozenset({"z1", "z2"}), frozenset({"z1"}), frozenset()]
    tabla = web.ganancia_por_candidato(sin, cubre)
    assert tabla.loc["z1", "poblacion_total"] == 30.0 and tabla.loc["z2", "poblacion_total"] == 10.0
    assert tabla.loc["z1", "poblacion_65_mas"] == 3.0 and "z3" not in tabla.index


def test_puestos_por_ganancia_y_cero_sin_ganancia():
    valores = pd.Series({"a": 5.0, "b": 0.0, "c": 9.0, "d": 1.0})
    assert web.puestos(valores).to_dict() == {"a": 2, "b": 0, "c": 1, "d": 3}


def test_comprobar_simulador_detecta_una_mejor_zona_que_no_es_la_del_milp(tmp_path):
    """Si la mayor ganancia individual no es la ganancia del MILP con una zona, se avisa."""
    (tmp_path / "actuaciones").mkdir()
    pd.DataFrame({"objetivo": ["total", "65+", "total"], "k": [1, 1, 3],
                  "milp_ganancia": [100.0, 20.0, 250.0]}).to_csv(tmp_path / "actuaciones" / "carteras_a_pie.csv",
                                                                 index=False)
    bien = {"modos_disponibles": ["a_pie"], "resumen": {"a_pie|total": {"maxima": 100.2}, "a_pie|65+": {"maxima": 20.0}}}
    mal = {"modos_disponibles": ["a_pie"], "resumen": {"a_pie|total": {"maxima": 90.0}, "a_pie|65+": {"maxima": 20.0}}}
    assert web.comprobar_simulador(bien, tmp_path) == []
    assert len(web.comprobar_simulador(mal, tmp_path)) == 1


def test_simulador_cuadra_con_la_cartera_de_una_zona(exportado):
    """La mejor zona de cada combinación da la ganancia del MILP con k = 1 (37.632 a pie, población total), cada
    zona tiene un lugar válido y alguna ganancia, y el puesto 1 es único."""
    s = leer(exportado, "capas/simulador.json")
    assert s["orden"] == ["a_pie|total", "a_pie|65+", "a_transporte|total", "a_transporte|65+"]
    assert round(s["resumen"]["a_pie|total"]["maxima"]) == 37632
    proc = raiz_datos() / "procesados" / web.VERSION_DEMO
    for componente, archivo in (("a_pie", "carteras_a_pie.csv"), ("a_transporte", "carteras_a_transporte.csv")):
        tabla = pd.read_csv(proc / "actuaciones" / archivo)
        filas = tabla[tabla["k"] == 1]
        if "franja" in filas.columns:
            filas = filas[filas["franja"].astype(str) == "9_13"]
        for fila in filas.to_dict("records"):
            assert s["resumen"][f"{componente}|{fila['objetivo']}"]["maxima"] == pytest.approx(fila["milp_ganancia"], abs=0.5)
    n = len(s["orden"])
    for z in s["zonas"]:
        assert len(z) == 3 + 2 * n and 0 <= z[2] < len(s["lugares"]) and max(z[3:3 + n]) > 0
    for j in range(n):
        assert sum(1 for z in s["zonas"] if z[3 + n + j] == 1) == 1


def test_comprobar_simulador_refugios_detecta_un_exceso():
    bien = {"resumen": {"b1|total": {"maxima": 100.0, "sin_refugio_peor_hora": 1000.0}}}
    mal = {"resumen": {"b1|total": {"maxima": 1200.0, "sin_refugio_peor_hora": 1000.0}}}
    assert web.comprobar_simulador_refugios(bien) == [] and web.comprobar_simulador_refugios(mal) == ["b1|total"]


def test_simulador_de_refugios_sin_mercados_y_con_sus_columnas(exportado):
    """Ningún mercado verificado como candidato, la parte «a ninguna hora» no supera la ganancia, el puesto 1 es único
    y ningún espacio da más personas que las que no tienen refugio en la peor hora."""
    ruta = exportado / "capas" / "simulador_refugios.json"
    if not ruta.exists():
        pytest.skip("La etapa refugios_ampliados no está calculada en este equipo.")
    s = leer(exportado, "capas/simulador_refugios.json")
    c = s["columnas"]
    assert s["orden"] == ["b1|total", "b1|75+"] and s["hora"] == 20
    assert "Verificado" not in {s["niveles"][z[c["nivel"]]] for z in s["zonas"]}
    for clave in s["orden"]:
        assert s["resumen"][clave]["maxima"] <= s["resumen"][clave]["sin_refugio_peor_hora"]
        assert sum(1 for z in s["zonas"] if z[c["puesto"][clave]] == 1) == 1
        assert all(z[c["extra"][clave]] <= z[c["valor"][clave]] for z in s["zonas"])


def test_bibliotecas_de_la_comunidad_solo_fuera_de_la_capital(exportado):
    """Las bibliotecas regionales van aparte (no son espacios de las líneas) y ninguna cae en Madrid capital."""
    r = leer(exportado, "capas/refugios.json")
    if "bibliotecas_cm" not in r:
        pytest.skip("La etapa refugios_ampliados no tiene aún las bibliotecas de la Comunidad.")
    b = r["bibliotecas_cm"]
    assert b["puntos"] and "bibliotecas" in r["casillas"]
    assert all(0 <= p[4] < len(b["horarios"]) and 0 <= p[5] < len(b["evidencias"]) for p in b["puntos"])
    assert not {p[3] for p in b["puntos"]} & {"Madrid"}
