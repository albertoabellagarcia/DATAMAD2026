"""Refugios ampliados (decisión del usuario del 22/11/2026): niveles de evidencia, horarios curados, capas aparte
y orden de las tres líneas de cobertura (verificados ≤ con respaldo oficial ≤ máximo posible)."""

import pandas as pd
import pytest

from cercasalud import horarios
from cercasalud import refugios_ampliados as ra
from cercasalud.acceso import CON


def fila_csv(pk: str, tipo: str, horario: str = "De lunes a viernes de 9 a 21 h") -> dict:
    """Una fila mínima de un CSV de equipamientos de datos.madrid.es."""
    return {"PK": pk, "NOMBRE": f"Equipamiento {pk}", "TIPO": f"/contenido/entidadesYorganismos/{tipo}",
            "HORARIO": horario, "EMAIL": "", "COORDENADA-X": "440000", "COORDENADA-Y": "4474000",
            "CONTENT-URL": "https://www.madrid.es/ficha"}


def test_salas_de_estudio_nuevas_y_polideportivos_solo_horario():
    """El CSV de salas añade salas (no oficinas juveniles) como potenciales; el de polideportivos no añade espacios,
    solo da el horario de los que ya están por el Anexo VIII."""
    salas = pd.DataFrame([fila_csv("1", "SalasEstudioLectura"), fila_csv("2", "OficinasInformacionJuvenil"),
                          fila_csv("3", "SalasEstudioLectura")])
    filas = ra.espacios_csv("salas", salas, {"eq:3"})
    assert [f["id"] for f in filas] == ["eq:1"]
    assert filas[0]["tipo"] == "sala_estudio" and filas[0]["nivel"] == ra.POTENCIAL
    assert filas[0]["horario_texto"] == "De lunes a viernes de 9 a 21 h"
    assert "deportivos" in ra.SOLO_HORARIO and ra.CSV_CATALOGO["deportivos"] == "madrid_polideportivos"


def test_nivel_del_anexo_segun_climatizacion_y_servicio():
    """«Sí» da respaldo; «Parcial», blanco, gran capacidad y horario administrativo quedan en potencial."""
    assert ra.nivel_anexo("centro_mayores", "Sí", "general", "98")[0] == ra.RESPALDO
    assert ra.nivel_anexo("centro_deportivo", "Parcial", "general", "98")[0] == ra.POTENCIAL
    assert ra.nivel_anexo("centro_cultural", "", "general", "98")[0] == ra.POTENCIAL
    assert ra.nivel_anexo("centro_cultural", "Sí", "gran_capacidad", "127")[0] == ra.POTENCIAL
    assert ra.nivel_anexo("servicios_sociales", "Sí", "general", "98")[0] == ra.POTENCIAL
    nivel, evidencia = ra.nivel_anexo("biblioteca", "", "general", "122")
    assert nivel == ra.RESPALDO and "p. 86" in evidencia


@pytest.mark.parametrize(("texto", "esperado"), [
    ("Unidades deportivas al aire libre: piscina (vaso de 50 m), pista de atletismo.", True),
    ("Temporada de verano: piscina de verano y solárium.", True),
    ("Unidades deportivas cubiertas: piscina cubierta. Unidades deportivas al aire libre: 2 pistas de pádel.", False),
    ("Equipamientos: piscina Aparcabicicletas: exterior", False),
])
def test_piscina_al_aire_libre(texto, esperado):
    """La piscina tiene que estar en la lista «al aire libre» (hasta el punto) o nombrarse como de verano."""
    assert ra.tiene_piscina_al_aire_libre(texto) is esperado


def test_nombre_del_anexo_sin_llamada_a_nota():
    """Se prefiere el nombre del CSV municipal; si no hay, se quita la llamada a nota pegada al paréntesis."""
    assert ra.nombre_anexo("Biblioteca Gloria Fuertes (Barajas) 2", {}, "1") == "Biblioteca Gloria Fuertes (Barajas)"
    assert ra.nombre_anexo("Sala Maqueda (Latina)11", {}, "1") == "Sala Maqueda (Latina)"
    assert ra.nombre_anexo("Centro Daoíz y Velarde 1", {}, "1") == "Centro Daoíz y Velarde 1"   # no es una nota
    assert ra.nombre_anexo("X (Barajas) 2", {"7": "Nombre limpio"}, "7") == "Nombre limpio"


def test_museos_municipales_por_nombre():
    """Los cinco museos del CALORMAD se reconocen sin tildes; uno parecido pero distinto, no."""
    assert ra.es_museo_municipal("Museo de San Isidro") == "Museo de San Isidro. Los Orígenes de Madrid"
    assert ra.es_museo_municipal("Planetario de Madrid") == "Planetario de Madrid"
    assert ra.es_museo_municipal("Museo de la Imprenta Municipal - Artes del Libro") == \
        "Imprenta Municipal - Artes del Libro"
    assert ra.es_museo_municipal("Museo Nacional Centro de Arte Reina Sofía") is None


def test_horario_curado_por_hora_y_tipo_de_dia():
    """08:30-20:00: abierta de 12 a 20 h y cerrada de 20 a 21 h; agosto cerrado si así se curó."""
    curados = pd.DataFrame([{"id": "eq:1", "laborables_julio": "08:30-20:00", "laborables_agosto": "cerrado",
                             "sabado": "cerrado", "domingo": "pendiente", "acceso_verificado": "sí"}])
    estados = ra.estados_curados(curados).set_index(["tipo_dia", "hora"])["estado"]
    assert estados[("laborable_julio", 12)] == horarios.ABIERTO
    assert estados[("laborable_julio", 19)] == horarios.ABIERTO
    assert estados[("laborable_julio", 20)] == horarios.CERRADO
    assert (estados.loc["laborable_agosto"] == horarios.CERRADO).all()
    assert (estados.loc["fin_de_semana"] == horarios.CERRADO).all()   # cerrado manda sobre pendiente


def test_archivo_curado_de_horarios():
    """36 bibliotecas (acceso verificado) y 157 espacios más con respaldo (acceso supuesto), con valores legibles."""
    curados = pd.read_csv(ra.HORARIOS_CURADOS, dtype=str, keep_default_na=False)
    assert curados["id"].is_unique and len(curados) == 36 + 157
    bibliotecas = curados[curados["tipo"] == "biblioteca"]
    assert len(bibliotecas) == 36 and set(bibliotecas["acceso_verificado"]) == {"sí"}
    assert set(curados.loc[curados["tipo"] != "biblioteca", "acceso_verificado"]) == {"no"}
    tramo = r"^\d{2}:\d{2}-\d{2}:\d{2}(, \d{2}:\d{2}-\d{2}:\d{2})*$"
    for col in ("laborables_julio", "laborables_agosto", "sabado", "domingo"):
        valores = curados[col]
        assert (valores.isin(["cerrado", "pendiente"]) | valores.str.match(tramo)).all(), col
    estados = ra.estados_curados(curados)
    assert set(estados["estado"]) == {horarios.ABIERTO, horarios.CERRADO, horarios.PENDIENTE}
    # Al menos 40 espacios que no son bibliotecas tienen algún tramo de verano curado.
    otros = curados[curados["tipo"] != "biblioteca"]
    assert otros[["laborables_julio", "laborables_agosto", "sabado", "domingo"]].apply(
        lambda c: c.str.contains(":")).any(axis=1).sum() >= 40


def espacios_sinteticos() -> pd.DataFrame:
    """Un mercado (verificado), una biblioteca con horario curado, un centro sin horario y un cine."""
    filas = [ra.fila_espacio("mercado:m1", "Mercado", "mercado", ra.VERIFICADO, "", "", "", 0, 0),
             ra.fila_espacio("eq:1", "Biblioteca", "biblioteca", ra.RESPALDO, "", "", "", 0, 0),
             ra.fila_espacio("eq:2", "Centro", "centro_mayores", ra.RESPALDO, "", "", "", 0, 0),
             ra.fila_espacio("osm:n3", "Cine", "cine", ra.POTENCIAL, "", "", "", 0, 0)]
    return pd.DataFrame(filas)


def unidades_sinteticas() -> pd.DataFrame:
    """Cuatro unidades de Madrid capital: cada una cerca de un espacio distinto."""
    return pd.DataFrame({"unidad": ["u1", "u2", "u3", "u4"], "cusec": ["2807901001"] * 4,
                         "enganchado": [True] * 4, "poblacion_total": [100.0, 200.0, 300.0, 400.0],
                         "poblacion_65_mas": [10.0] * 4, "poblacion_75_mas": [5.0] * 4,
                         "poblacion_85_mas": [1.0] * 4})


def test_lineas_ordenadas_y_cada_una_con_lo_suyo():
    """Mercado de 12 a 14 h; biblioteca de 8:30 a 20; centro pendiente; cine solo en el máximo."""
    mercados = pd.DataFrame([{"refugio": "m1", "tipo_dia": t, "hora": h,
                              "estado": horarios.ABIERTO if h < 14 else horarios.CERRADO}
                             for t in horarios.TIPOS_DIA for h in horarios.HORAS])
    curados = pd.DataFrame([{"id": "eq:1", "laborables_julio": "08:30-20:00", "laborables_agosto": "08:30-20:00",
                             "sabado": "cerrado", "domingo": "cerrado", "acceso_verificado": "sí"}])
    pares = pd.DataFrame({"unidad": ["u1", "u2", "u3", "u4"], "refugio": ["mercado:m1", "eq:1", "eq:2", "osm:n3"],
                          "minutos": [5.0] * 4})
    estados = ra.estados_por_linea(espacios_sinteticos(), mercados.assign(acceso_verificado=False), curados)
    filas, tablas = ra.lineas_cobertura(unidades_sinteticas(), pares, estados, 10)
    resumen = pd.DataFrame(filas)
    julio = resumen[(resumen["grupo_edad"] == "total") & (resumen["tipo_dia"] == "laborable_julio")]
    alguna = julio.set_index(["linea", "cota"])["personas_unicas_con_alguna_hora"]
    assert alguna[("verificados", "central")] == 100.0
    assert alguna[("respaldo_oficial", "central")] == 300.0          # mercado + biblioteca
    assert alguna[("respaldo_oficial", "acreditable")] == 200.0      # solo la biblioteca tiene acceso verificado
    assert alguna[("maximo_posible", "central")] == 1000.0           # todos, también el cine
    # El centro sin horario deja su unidad como no evaluable en la línea con respaldo, nunca «sin opción».
    u3 = tablas["respaldo_oficial"].query("unidad == 'u3'")
    assert (u3["estado"] == "no_evaluable").all()
    # A cada hora: verificados ≤ con respaldo ≤ máximo.
    for (tipo, hora), grupo in tablas["verificados"].groupby(["tipo_dia", "hora"]):
        con = {linea: int((t.query("tipo_dia == @tipo and hora == @hora")["estado"] == CON).sum())
               for linea, t in tablas.items()}
        assert con["verificados"] <= con["respaldo_oficial"] <= con["maximo_posible"]


# ------------------------------------------------------------------ zonas verdes de la Comunidad (23/11/2026)

X0, Y0 = 440000.0, 4470000.0   # un punto de Madrid en EPSG:25830


def cuadrado(x: float, y: float, lado: float):
    """Cuadrado de `lado` metros con la esquina inferior izquierda en (X0 + x, Y0 + y)."""
    from shapely.geometry import box
    return box(X0 + x, Y0 + y, X0 + x + lado, Y0 + y + lado)


def elementos_osm(filas: list[dict]):
    """Elementos como los devuelve `leer_verdes_osm` (las claves que falten van vacías)."""
    import geopandas as gpd
    claves = ("leisure", "landuse", "natural", "boundary", "amenity", "sport", "acceso", "tipo_jardin")
    completas = [{"osm": f["osm"], "nombre": f.get("nombre", ""), **{c: f.get(c) for c in claves},
                  "geometry": f["geometry"]} for f in filas]
    return gpd.GeoDataFrame(completas, geometry="geometry", crs="EPSG:25830")


def test_clase_verde_por_etiqueta_y_orden():
    """El parque manda sobre otras etiquetas; el césped urbano y los espacios protegidos no tienen clase."""
    e = elementos_osm([
        {"osm": "w1", "leisure": "park", "landuse": "village_green", "geometry": cuadrado(0, 0, 50)},
        {"osm": "w2", "leisure": "garden", "geometry": cuadrado(0, 0, 50)},
        {"osm": "w3", "landuse": "recreation_ground", "geometry": cuadrado(0, 0, 50)},
        {"osm": "w4", "leisure": "nature_reserve", "landuse": "forest", "geometry": cuadrado(0, 0, 50)},
        {"osm": "w5", "natural": "wood", "geometry": cuadrado(0, 0, 50)},
        {"osm": "w6", "landuse": "grass", "geometry": cuadrado(0, 0, 50)},
        {"osm": "r7", "boundary": "protected_area", "geometry": cuadrado(0, 0, 50)},
    ])
    assert ra.clase_verde(e).tolist() == ["parque", "jardin", "area_recreativa", "monte_bosque", "monte_bosque", "",
                                          ""]


def test_jardines_publicos_regla_del_23_11():
    """Con nombre entra aunque caiga en parcela residencial (la Quinta de Torre Arias); sin nombre, solo si es grande
    y está fuera de parcelas residenciales y recintos; fuera los privados, los de urbanización y los pequeños."""
    jardines = elementos_osm([
        {"osm": "con_nombre_en_residencial", "nombre": "Quinta de Torre Arias", "geometry": cuadrado(0, 0, 100)},
        {"osm": "sin_nombre_en_residencial", "geometry": cuadrado(200, 0, 100)},
        {"osm": "sin_nombre_fuera", "geometry": cuadrado(2000, 0, 100)},
        {"osm": "sin_nombre_pequeno_fuera", "geometry": cuadrado(2200, 0, 60)},
        {"osm": "urbanizacion", "nombre": "Jardín urbanización Los Pinos", "geometry": cuadrado(2400, 0, 100)},
        {"osm": "en_colegio", "nombre": "Jardín del colegio", "geometry": cuadrado(4000, 0, 50)},
        {"osm": "privado", "nombre": "Jardín Privado", "acceso": "private", "geometry": cuadrado(2600, 0, 100)},
        {"osm": "publico_declarado", "tipo_jardin": "public", "geometry": cuadrado(400, 0, 40)},
        {"osm": "tipo_residencial", "nombre": "Jardines X", "tipo_jardin": "residential",
         "geometry": cuadrado(2800, 0, 100)},
        {"osm": "con_nombre_pequeno", "nombre": "Plazuela", "geometry": cuadrado(3000, 0, 20)},
        {"osm": "nombre_de_una_letra", "nombre": "A", "geometry": cuadrado(3200, 0, 100)},
    ])
    residencial = elementos_osm([{"osm": "res", "landuse": "residential", "geometry": cuadrado(-10, -10, 1000)}])
    recintos = elementos_osm([{"osm": "col", "amenity": "school", "geometry": cuadrado(3990, -10, 100)}])
    entran = jardines.loc[ra.jardines_publicos(jardines, residencial, recintos).to_numpy(), "osm"].tolist()
    assert entran == ["con_nombre_en_residencial", "sin_nombre_fuera", "publico_declarado"]


def test_areas_recreativas_sin_circuitos_ni_urbanizaciones():
    """Fuera los circuitos de motor, los centros deportivos y las piscinas de urbanización."""
    areas = elementos_osm([
        {"osm": "libre", "nombre": "Área recreativa", "landuse": "recreation_ground", "geometry": cuadrado(0, 0, 50)},
        {"osm": "karting", "landuse": "recreation_ground", "sport": "karting", "geometry": cuadrado(0, 0, 50)},
        {"osm": "deportivo", "leisure": "sports_centre", "landuse": "recreation_ground",
         "geometry": cuadrado(0, 0, 50)},
        {"osm": "piscina", "nombre": "Piscinas Urbanización «Jarosa»", "landuse": "recreation_ground",
         "geometry": cuadrado(0, 0, 50)},
    ])
    assert areas.loc[ra.areas_recreativas_publicas(areas).to_numpy(), "osm"].tolist() == ["libre"]


def test_zonas_verdes_recorta_quita_solapes_y_excluye_lo_que_no_cuenta():
    """Un jardín dentro de un parque no se dibuja dos veces; el monte se recorta al contorno y a El Pardo; el
    césped, los espacios protegidos, el monte pequeño y el parque privado no entran."""
    from shapely.geometry import box
    pardo = next(iter(ra.ZONAS_ACCESO_RESTRINGIDO))
    e = elementos_osm([
        {"osm": "parque", "nombre": "Parque", "leisure": "park", "geometry": cuadrado(0, 0, 300)},
        {"osm": "jardin_dentro", "nombre": "Rosaleda", "leisure": "garden", "geometry": cuadrado(50, 50, 100)},
        {"osm": "bosque_dentro", "natural": "wood", "geometry": cuadrado(10, 10, 200)},
        {"osm": "parque_privado", "leisure": "park", "acceso": "private", "geometry": cuadrado(1000, 0, 100)},
        {"osm": "cesped", "landuse": "grass", "geometry": cuadrado(1200, 0, 100)},
        {"osm": "reserva", "leisure": "nature_reserve", "geometry": cuadrado(-5000, -5000, 9000)},
        {"osm": "monte_mitad_fuera", "landuse": "forest", "geometry": cuadrado(1500, 0, 400)},
        {"osm": pardo, "boundary": "protected_area", "geometry": cuadrado(2500, 0, 1000)},
        {"osm": "monte_en_pardo", "landuse": "forest", "geometry": cuadrado(2300, 0, 400)},
        {"osm": "monte_pequeno", "landuse": "forest", "geometry": cuadrado(1400, -300, 50)},
    ])
    contorno = box(X0 - 100, Y0 - 1000, X0 + 1700, Y0 + 1000).union(box(X0 + 1700, Y0 - 1000, X0 + 4000, Y0 + 1000))
    contorno = contorno.difference(box(X0 + 1700, Y0 + 200, X0 + 2000, Y0 + 1000))   # deja fuera parte del monte
    verdes = ra.zonas_verdes(e, contorno)
    assert verdes.crs.to_epsg() == 4326 and list(verdes.columns) == ["nombre", "osm", "clase", "geometry"]
    assert sorted(verdes["osm"]) == ["monte_en_pardo", "monte_mitad_fuera", "parque"]
    metros = verdes.to_crs("EPSG:25830").set_index("osm").geometry.area
    assert metros["monte_mitad_fuera"] == pytest.approx(400 * 400 - 200 * 200, rel=0.01)   # recortado al contorno
    assert metros["monte_en_pardo"] == pytest.approx(200 * 400, rel=0.01)                  # sin la parte de El Pardo


def test_poligonos_verdes_monte_debajo_y_capas_antiguas_sin_clase():
    """La página pinta el monte primero (debajo); una capa anterior al 23/11 sin `clase` se rotula como parque."""
    import geopandas as gpd

    from cercasalud import web
    capa = gpd.GeoDataFrame({"nombre": ["P", "M"], "osm": ["w1", "w2"], "clase": ["parque", "monte_bosque"]},
                            geometry=[cuadrado(0, 0, 10), cuadrado(20, 0, 10)], crs="EPSG:25830")
    assert web.poligonos_verdes(capa)["clase"].tolist() == ["monte_bosque", "parque"]
    assert set(web.poligonos_verdes(capa.drop(columns="clase"))["clase"]) == {"parque"}


def test_refresco_solo_fuentes_operativas_para_personas_y_piscinas_al_aire_libre():
    """Fuera las fuentes fuera de servicio o solo para mascotas, y las piscinas cubiertas."""
    fuentes = pd.DataFrame({"ID": ["1", "2", "3"], "ESTADO": ["OPERATIVO", "FUERA_DE_SERVICIO", "OPERATIVO"],
                            "USO": ["PERSONAS", "PERSONAS", "MASCOTAS"], "TIPO_VIA": ["Calle"] * 3,
                            "NOM_VIA": ["A"] * 3, "NUM_VIA": ["1"] * 3, "COORD_GIS_X": ["440000"] * 3,
                            "COORD_GIS_Y": ["4470000"] * 3})
    piscinas = pd.DataFrame({"PK": ["9", "8"], "NOMBRE": ["CDM Uno", "CDM Dos"],
                             "EQUIPAMIENTO": ["Unidades deportivas al aire libre: piscina (vaso de 50 m).",
                                              "Unidades deportivas cubiertas: piscina cubierta."],
                             "COORDENADA-X": ["440000", "441000"], "COORDENADA-Y": ["4470000", "4471000"]})
    tabla = ra.refresco(fuentes, piscinas)
    assert sorted(tabla["id"]) == ["fuente:1", "piscina:9"]


# ------------------------------------------------------------------ bibliotecas del resto de la Comunidad (23/11/2026)


def test_errata_l_a_del_directorio_de_la_comunidad():
    """«L-» es «l A» en el CSV de la Comunidad; el resto del texto no se toca."""
    assert ra.corregir_errata('Biblioteca Municipal "RafaeL-lberti"') == 'Biblioteca Municipal "Rafael Alberti"'
    assert ra.corregir_errata("Colmenar deL-rroyo") == "Colmenar del Arroyo"
    assert ra.corregir_errata("Biblioteca L-24 de Alcalá") == "Biblioteca L-24 de Alcalá"


def test_municipio_normalizado_iguala_el_nombre_ine_y_el_del_directorio():
    assert ra.municipio_normalizado("Boalo (El)") == ra.municipio_normalizado("El Boalo") == "el boalo"
    assert ra.municipio_normalizado("Cerceda") == "el boalo"
    assert ra.municipio_normalizado("San Agustín de Guadalix") == ra.municipio_normalizado("San Agustín del Guadalix")


def test_solo_bibliotecas_publicas_de_punto_fijo_fuera_de_la_capital():
    tabla = pd.DataFrame({"tipo_biblioteca": ["Biblioteca Pública. Punto fijo", "Biblioteca Pública. Punto fijo",
                                              "Bibliotecas universitarias"],
                          "nombre_biblioteca": ["A", "B", "C"], "localidad": ["Getafe", "Madrid", "Getafe"],
                          "horario": ["", "", ""]})
    assert ra.bibliotecas_publicas_cm(tabla)["nombre"].tolist() == ["A"]


def test_casar_bibliotecas_seguro_probable_y_sin_ubicar():
    """Nombre coincidente → seguro; única del municipio en las dos fuentes → probable; varias sin nombre que las
    distinga → sin ubicar; localidad que no es municipio → sin ubicar con su motivo."""
    import geopandas as gpd
    from shapely.geometry import Point, box
    municipios = gpd.GeoDataFrame({"CUMUN": ["28001", "28002", "28003"], "NMUN": ["Uno", "Dos", "Tres"]},
                                  geometry=[box(0, 0, 10, 10), box(10, 0, 20, 10), box(20, 0, 30, 10)], crs=25830)
    osm = gpd.GeoDataFrame({"osm": ["n1", "n2", "n3", "n4"], "CUMUN": ["28001", "28002", "28003", "28003"],
                            "nombre_osm": ["Biblioteca Municipal Pío Baroja", "Biblioteca La Casona",
                                           "Biblioteca Municipal", "Biblioteca Municipal"]},
                           geometry=[Point(1, 1), Point(11, 1), Point(21, 1), Point(22, 1)], crs=25830)
    publicas = pd.DataFrame({"nombre": ['Biblioteca Municipal "Pío Baroja"', "Biblioteca Municipal de Dos",
                                        'Biblioteca "Joan Miró"', 'Biblioteca "Rosalía de Castro"', "Otra"],
                             "localidad": ["Uno", "Dos", "Tres", "Tres", "Ninguno"], "horario": [""] * 5})
    ubicadas, sin = ra.casar_bibliotecas(publicas, osm, municipios)
    assert dict(zip(ubicadas["nombre"], ubicadas["calidad"], strict=True)) == {
        'Biblioteca Municipal "Pío Baroja"': "seguro", "Biblioteca Municipal de Dos": "probable"}
    assert ubicadas["osm"].is_unique
    motivos = dict(zip(sin["nombre"], sin["motivo"], strict=True))
    assert motivos["Otra"] == "localidad sin municipio INE"
    assert motivos['Biblioteca "Joan Miró"'] == "sin biblioteca de OSM con nombre coincidente"
