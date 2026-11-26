"""CercaSalud MAD: app local (H6). Solo lee resultados precalculados por `build` (R-UI-01).

Arranque: `uv run cercasalud app` (solo en 127.0.0.1 y sin conexión: R-ARQ-02). El mapa no usa
mapa base de internet: dibuja las unidades sobre fondo neutro.

Pantallas (SPEC §11): inicio, 1 cobertura de datos, 2 primaria, 3 HeatShield, 4 carencias
coincidentes, 5 comparador, 6 resultados y 7 ficha de decisión y exportación.
"""

import json
import shutil
from pathlib import Path

import pandas as pd
import pydeck as pdk
import streamlit as st

from cercasalud import app_datos, vista_mapa, vista_resultados
from cercasalud.app_datos import ATRIBUCIONES, sin_campos_personales
from cercasalud.capas_mapa import ETIQUETAS_PCT_SIN, ETIQUETAS_QUINTIL
from cercasalud.ingesta import leer_snapshot
from cercasalud.rutas import carpeta_procesados, raiz_datos

# Mismo significado de color que el mapa de minutos: azul = con acceso, rojo = carencia, gris = no evaluable.
COLORES = {"con_acceso": [69, 117, 180], "sin_opcion_verificada": [215, 48, 39], "no_evaluable": [158, 158, 158],
           "carencia_coincidente": [215, 48, 39], "sin_coincidencia": [69, 117, 180]}
NOMBRES = {"con_acceso": "con acceso", "sin_opcion_verificada": "sin opción verificada", "no_evaluable": "no evaluable",
           "carencia_coincidente": "carencia coincidente", "sin_coincidencia": "sin coincidencia"}
# Estilo de mapa con solo un fondo neutro, servido por la propia app (app/static/, con
# server.enableStaticServing). Sin un estilo propio, Streamlit pone el mapa base de Carto y lo
# descarga de internet (comprobado el 14/11/2026 con el registro de red de Chrome); y su
# componente solo admite el estilo como URL, no como diccionario.
ESTILO_SIN_INTERNET = "/app/static/estilo_fondo.json"
COMPONENTES = {"a_pie": "A a pie: nuevos centros", "a_transporte": "A en transporte: nuevos centros",
               "b1": "B1: ampliar horas de los mercados"}
ESCENARIOS_PRIMARIA = {"base": "Base (9 a 13 h)", "franja_16_20": "Franja de 16 a 20 h",
                       "ambas_franjas": "Acceso en las dos franjas"}


def versiones_disponibles() -> list[str]:
    """Versiones de datos con resultados de acceso calculados, de la más reciente a la más antigua."""
    procesados = raiz_datos() / "procesados"
    return app_datos.ordenar_versiones([p.name for p in procesados.glob("*") if (p / "acceso" / "resumen.json").exists()])


@st.cache_data
def leer_csv(ruta: str) -> pd.DataFrame | None:
    """Lee una tabla de resultados, o None si ese cálculo no existe (R-UI-04: nada aparente)."""
    return pd.read_csv(ruta) if Path(ruta).exists() else None


@st.cache_data
def leer_parquet(ruta: str) -> pd.DataFrame | None:
    """Lee una capa precalculada, o None si no existe."""
    return pd.read_parquet(ruta) if Path(ruta).exists() else None


def no_evaluables_base(proc: Path) -> dict:
    """No evaluables por motivo del escenario base de A (Comunidad, población total)."""
    resumen = leer_csv(str(proc / "acceso" / "resumen_acceso.csv"))
    if resumen is None:
        return {}
    fila = resumen[(resumen["escenario"] == "base") & (resumen["modo"] == "transporte")
                   & (resumen["territorio"] == "comunidad") & (resumen["grupo_edad"] == "total")]
    return json.loads(fila["no_evaluable_por_motivo"].iloc[0]) if len(fila) else {}


def pie_de_vista(proc: Path, version: str, supuestos: str) -> None:
    """Supuestos, no evaluables, versión de datos y atribuciones al pie de cada vista (R-UI-02)."""
    st.divider()
    st.caption(f"**Supuestos:** {supuestos}")
    no_eval = no_evaluables_base(proc)
    texto = ", ".join(f"{motivo}: {vista_mapa.personas(personas)} personas" for motivo, personas in no_eval.items()) \
        or "ninguno"
    st.caption(f"**No evaluables de A (escenario base, Comunidad):** {texto}. Lo no evaluable nunca se cuenta como "
               "«sin acceso». En B, todo municipio sin lista oficial verificada es no evaluable por inventario.")
    st.caption(f"**Versión de datos:** {version}. Resultados precalculados; la app no calcula.")
    for linea in ATRIBUCIONES:
        st.caption(linea)


def mapa(capa: pd.DataFrame, columna: str) -> None:
    """Unidades coloreadas por estado, sin mapa base de internet."""
    datos = capa.dropna(subset=[columna]).assign(
        color=lambda t: t[columna].map(COLORES), radio=lambda t: 20 + t["poblacion_total"].clip(upper=400) / 4,
        estado_txt=lambda t: t[columna].map(NOMBRES))
    if datos.empty:
        st.info("No hay unidades con este estado calculado.")
        return
    capa_pdk = pdk.Layer("ScatterplotLayer", datos[["lon", "lat", "color", "radio", "estado_txt", "cusec"]],
                         get_position="[lon, lat]", get_fill_color="color", get_radius="radio", pickable=True)
    # Encuadre ajustado a lo que se pinta (toda la Comunidad o solo Madrid capital).
    vista = pdk.ViewState(longitude=float((datos["lon"].min() + datos["lon"].max()) / 2),
                          latitude=float((datos["lat"].min() + datos["lat"].max()) / 2),
                          zoom=vista_mapa.zoom_para(datos["lon"].min(), datos["lat"].min(), datos["lon"].max(),
                                                    datos["lat"].max(), 840, 500))
    st.pydeck_chart(pdk.Deck(layers=[capa_pdk], initial_view_state=vista, map_style=ESTILO_SIN_INTERNET,
                             tooltip={"text": "{estado_txt}\nsección {cusec}"}))
    st.caption("Rojo: sin opción verificada o carencia coincidente (no hay recurso verificado dentro del umbral; no "
               "significa «sin ningún recurso»). Azul: con acceso o sin coincidencia. Gris: no evaluable.")


def tabla_estados(tabla: pd.DataFrame) -> pd.DataFrame:
    """Columnas legibles de una tabla de resumen de estados."""
    columnas = ["territorio", "grupo_edad", "con_acceso", "sin_opcion_verificada", "no_evaluable", "denominador",
                "pct_con_acceso_sobre_total"]
    return tabla[[c for c in columnas if c in tabla.columns]].round(1)


RECORRIDO = (
    (1, "Cobertura de datos", "qué se ha podido evaluar, qué no y con qué fuentes"),
    (2, "Primaria", "a cuántos minutos está el centro de salud, a pie y en transporte, por municipio y distrito"),
    (3, "HeatShield", "refugios climáticos hora a hora donde hay lista oficial verificada (Madrid capital)"),
    (4, "Carencias coincidentes", "dónde faltan a la vez primaria y refugio, sin sumar necesidades distintas"),
    (5, "Comparador", "carteras calculadas frente a una regla simple, con las mismas condiciones"),
    (6, "Resultados", "antes y después, ganancia adicional, quién sigue fuera y robustez"),
    (7, "Ficha de decisión", "supuestos, límites, empates y archivos para continuar el estudio"),
)


def vista_inicio(proc: Path) -> None:
    """Recorrido de salud pública regional (R-USR-01) con las tres cifras de partida, leídas de los resultados."""
    st.title("CercaSalud MAD")
    st.markdown("#### Ayuda a decidir dónde actuar para acercar la atención primaria y los refugios climáticos, "
                "y dice cuándo los datos no dan para afirmarlo.")
    resumen = leer_csv(str(proc / "acceso" / "resumen_acceso.csv"))
    carteras = tabla_cartera(proc, "a_transporte")
    if resumen is not None:
        base = resumen[(resumen["escenario"] == "base") & (resumen["territorio"] == "comunidad")
                       & (resumen["grupo_edad"] == "total") & (resumen["modo"] == "transporte")]
        columnas = st.columns(3)
        if len(base):
            fila = base.iloc[0]
            columnas[0].metric("Con un centro a 30 min o menos", vista_mapa.porcentaje(fila["pct_con_acceso_sobre_total"]),
                               help="A pie o en transporte público, de 9 a 13 h, un martes laborable. Comunidad de Madrid.")
            columnas[1].metric("Sin opción verificada", vista_mapa.personas(fila["sin_opcion_verificada"]),
                               help="Personas sin un centro a 30 min o menos con esos supuestos. No es «sin atención».")
        if carteras is not None:
            caso = carteras[(carteras["objetivo"] == "total") & (carteras["k"] == 3)]
            if len(caso):
                columnas[2].metric("Ganan opción con 3 zonas de estudio", vista_mapa.personas(caso.iloc[0]["milp_ganancia"]),
                                   help=f"Frente a {vista_mapa.personas(caso.iloc[0]['regla_simple_ganancia'])} con una "
                                        "regla simple que elige el mismo número de zonas: las celdas con más población "
                                        "sin opción. Transporte de 9 a 13 h, 30 min.")
    st.markdown("**Recorrido**")
    st.markdown("\n".join(f"{n}. [**{nombre}**](?pantalla={n}): {texto}." for n, nombre, texto in RECORRIDO))
    st.caption("Mide proximidad física potencial con supuestos declarados (umbrales, velocidad, franja). No mide citas, "
               "capacidad ni efectos sobre la salud. Resultados precalculados: la app no calcula ni usa internet.")


def vista_cobertura(proc: Path, version: str) -> None:
    """Pantalla 1: municipios por estado de inventario y fuentes con fecha."""
    st.header("1. Cobertura de datos")
    resumen = json.loads((proc / "acceso" / "resumen.json").read_text(encoding="utf-8"))
    franjas = ", ".join(resumen.get("franjas_transporte", ["9_13"])).replace("_", " a ")
    st.markdown(
        f"- **Primaria (A):** toda la Comunidad (179 municipios). Transporte: {resumen['transporte']}; franjas "
        f"calculadas: {franjas} h.\n"
        "- **Refugios (B):** solo **Madrid capital** (43 mercados municipales con aire acondicionado en zonas comunes). "
        "Coslada está documentada pero fuera del cálculo público hasta aclarar su licencia. En el resto de municipios, "
        "B es **no evaluable (inventario)**: que no haya lista verificada no significa que no haya refugios.\n"
        "- **Carencias coincidentes (C):** solo donde A y B son evaluables en la misma unidad.")
    municipios = leer_csv(str(proc / "acceso" / "por_municipio_base.csv"))
    if municipios is not None:
        st.subheader("Municipios: estado de inventario y población por estado de A en transporte")
        tabla = municipios[municipios["modo"] == "transporte"].drop(columns="modo").copy()
        tabla["inventario_b"] = tabla["cumun"].astype(str).map(
            {"28079": "lista oficial verificada", "28049": "documentado, fuera del cálculo (licencia)"}).fillna(
            "no evaluable (sin lista verificada)")
        st.dataframe(tabla.round(0), hide_index=True)
    try:
        archivos = leer_snapshot(raiz_datos(), version)["archivos"]
        st.subheader("Fuentes de la versión de datos")
        st.dataframe(pd.DataFrame(archivos)[["fuente", "organismo", "licencia", "fecha_adquisicion", "url"]],
                     hide_index=True)
    except FileNotFoundError:
        st.warning("No se encuentra el manifiesto de la versión de datos.")
    pie_de_vista(proc, version, "ver cada pantalla")


# ------------------------------ mapa de minutos (pantalla 2; SPEC P-27) -----------------------

ALTO_MAPA_PX, ANCHO_MAPA_PX = 760, 840  # el ancho solo sirve para calcular el zoom de encuadre
MODO_DE_VARIABLE = {"min_tp_9_13": "transporte", "min_tp_16_20": "transporte_16_20", "min_pie": "pie",
                    "quintil_renta": "transporte", "pct_sin_transporte": "transporte", "pct_sin_pie": "pie"}
TERRITORIO_INICIAL = "comunidad:28"
# Copia local de las capas de deck.gl, servida por la app en /app/static/ (no va a git).
CARPETA_ESTATICA = Path(__file__).resolve().parent / "static" / "capas"


@st.cache_resource
def leer_capas_mapa(carpeta: str) -> dict | None:
    """Tablas pequeñas del mapa de minutos preparadas por `build` (etapa `capas_app`), o None si faltan.

    Las capas grandes (celdas, municipios y líneas) no se cargan aquí: el navegador las lee como
    archivo (`url_capa`). Se guardan en caché sin copiar (`cache_resource`): nada las modifica.
    """
    app = Path(carpeta) / "app"
    archivos = ["lineas_mapa.parquet", "territorios_mapa.csv", "tramos_mapa.csv", "deck/celdas.json",
                "deck/municipios.json"]
    if not all((app / a).exists() for a in archivos):
        return None
    lineas = pd.read_parquet(app / "lineas_mapa.parquet")
    lineas = lineas[lineas["tipo"].isin(["limite_municipio", "limite_distrito"])].copy()
    lineas["camino"] = vista_mapa.contornos_listas(lineas["camino"])
    territorios = pd.read_csv(app / "territorios_mapa.csv", dtype={"codigo": str})
    territorios["clave"] = territorios["tipo"] + ":" + territorios["codigo"]
    tramos = pd.read_csv(app / "tramos_mapa.csv", dtype={"codigo": str})
    catalogo = json.loads((app / "resumen.json").read_text(encoding="utf-8"))["variables_minutos"]
    return {"lineas": lineas, "territorios": territorios.set_index("clave"), "tramos": tramos, "catalogo": catalogo}


def url_capa(proc: Path, version: str, nombre: str) -> str:
    """URL local de una capa de deck.gl de la versión; la copia a `app/static/` si falta o cambió.

    La marca `?v=` cambia con el archivo de origen, para que el navegador no use una copia vieja.
    """
    origen = proc / "app" / "deck" / f"{nombre}.json"
    destino = CARPETA_ESTATICA / version / f"{nombre}.json"
    if not destino.exists() or destino.stat().st_size != origen.stat().st_size or             destino.stat().st_mtime < origen.stat().st_mtime:
        destino.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(origen, destino)
    return f"/app/static/capas/{version}/{nombre}.json?v={int(origen.stat().st_mtime)}"


def opciones_variable(catalogo: dict) -> dict:
    """«¿Qué quieres colorear?»: una variable cada vez (no hay índice compuesto)."""
    opciones = {clave: {"titulo": catalogo[clave]["titulo"], "escala": "celdas", "paleta": vista_mapa.AZUL_ROJO,
                        "etiquetas": catalogo[clave]["etiquetas"], "umbral_tras": 2,
                        "ultimo_limite": catalogo[clave]["limites"][-1]}
                for clave in ("min_tp_9_13", "min_tp_16_20", "min_pie") if clave in catalogo}
    opciones["quintil_renta"] = {"titulo": "Renta neta media por persona de la sección (quintil, ADRH 2024)",
                                 "escala": "celdas", "paleta": vista_mapa.ROJO_AZUL_5,
                                 "etiquetas": list(ETIQUETAS_QUINTIL), "umbral_tras": None}
    for modo, texto in (("transporte", "a pie o en transporte público, de 9 a 13 h"), ("pie", "a pie")):
        opciones[f"pct_sin_{modo}"] = {"titulo": f"Por municipio: % sin opción verificada, {texto}",
                                       "escala": "municipios", "paleta": vista_mapa.AMARILLO_ROJO,
                                       "etiquetas": list(ETIQUETAS_PCT_SIN), "umbral_tras": None}
    return opciones


def etiquetas_modo(catalogo: dict) -> dict[str, str]:
    """Nombre de cada modo de la tarjeta y la franja de cifras, con su umbral."""
    pie, tp = catalogo["min_pie"], catalogo["min_tp_9_13"]
    return {"transporte": f"A pie o en transporte, 9 a 13 h ({tp['umbral']} min)",
            "transporte_16_20": f"A pie o en transporte, 16 a 20 h ({tp['umbral']} min)",
            "pie": f"A pie ({pie['umbral']} min, {pie['titulo'].split('(')[1].rstrip(')')})"}


def capas_fondo_y_datos(proc: Path, version: str, variable: str, opcion: dict) -> list:
    """Capas de color: municipios (fondo gris o color por % sin opción) y celdas pobladas.

    Cada fila del archivo lleva el color y el texto de todas las variables (`capas_deck.py`); aquí
    solo se elige el campo. `update_triggers` avisa a deck.gl de que el campo cambió.
    """
    municipios, disparador = url_capa(proc, version, "municipios"), [list(MODO_DE_VARIABLE).index(variable)]
    if opcion["escala"] == "municipios":
        return [pdk.Layer("PolygonLayer", municipios, id="municipios", get_polygon="p", get_fill_color=f"c_{variable}",
                          stroked=False, pickable=True, update_triggers={"getFillColor": disparador})]
    fondo = pdk.Layer("PolygonLayer", municipios, id="fondo", get_polygon="p",
                      get_fill_color=vista_mapa.rgb(vista_mapa.TERRITORIO), stroked=False, pickable=False)
    # El borde del mismo color asegura al menos un píxel por celda cuando se ve toda la Comunidad.
    celdas = pdk.Layer("PolygonLayer", url_capa(proc, version, "celdas"), id="celdas", get_polygon="p",
                       get_fill_color=f"c_{variable}", get_line_color=f"c_{variable}", stroked=True,
                       line_width_min_pixels=1, pickable=True,
                       update_triggers={"getFillColor": disparador, "getLineColor": disparador})
    return [fondo, celdas]


def en_capital(clave: str) -> bool:
    """El territorio elegido es Madrid capital o uno de sus distritos."""
    return clave == "municipio:28079" or clave.startswith("distrito:")


def capas_referencia(capas: dict, proc: Path, version: str, clave: str) -> list:
    """Límites, vías y contorno resaltado del territorio elegido."""
    lineas = capas["lineas"]
    estilos = [("limite_municipio", [255, 255, 255], 1.5), ("via_principal", [90, 90, 90], 1.4)]
    if en_capital(clave):
        estilos += [("via_capital", [130, 130, 130], 1.0), ("limite_distrito", [77, 77, 77], 1.5)]
    resultado = [pdk.Layer("PathLayer", url_capa(proc, version, f"lineas_{tipo}"), id=tipo, get_path="p",
                           get_color=color, width_units=pdk.types.String("pixels"), get_width=ancho, pickable=False)
                 for tipo, color, ancho in estilos]
    tipo, codigo = clave.split(":")
    if tipo != "comunidad":
        borde = "limite_distrito" if tipo == "distrito" else "limite_municipio"
        elegido = lineas[(lineas["tipo"] == borde) & (lineas["codigo"] == codigo)]
        resultado.append(pdk.Layer("PathLayer", elegido[["camino"]], id="seleccion", get_path="camino",
                                   get_color=[26, 26, 26], width_units=pdk.types.String("pixels"), get_width=3, pickable=False))
    return resultado


def rotulos(territorios: pd.DataFrame, clave: str, zoom: float) -> pd.DataFrame:
    """Nombres que se rotulan: municipios más poblados, distritos en la capital o vecinos del municipio.

    Van por orden de prioridad (el elegido primero, después por población) y se quitan los que se
    pisarían con otro a ese zoom.
    """
    municipios = territorios[territorios["tipo"] == "municipio"].sort_values("poblacion", ascending=False)
    if clave == TERRITORIO_INICIAL:
        elegidos = municipios.head(40)
    elif en_capital(clave):
        distritos = territorios[territorios["tipo"] == "distrito"].sort_values("poblacion", ascending=False)
        elegidos = pd.concat([territorios.loc[[clave]], distritos]) if clave.startswith("distrito:") else distritos
    else:
        fila = territorios.loc[clave]
        margen_lon, margen_lat = fila["lon_max"] - fila["lon_min"], fila["lat_max"] - fila["lat_min"]
        cerca = municipios[municipios["lon"].between(fila["lon_min"] - margen_lon, fila["lon_max"] + margen_lon)
                           & municipios["lat"].between(fila["lat_min"] - margen_lat, fila["lat_max"] + margen_lat)]
        elegidos = pd.concat([territorios.loc[[clave]], cerca.head(20)])
    elegidos = elegidos[~elegidos.index.duplicated()]
    tamano = [20 if c == "28079" and t == "municipio" else 14 for t, c in zip(elegidos["tipo"], elegidos["codigo"],
                                                                                strict=True)]
    datos = pd.DataFrame({"lon": elegidos["lon"], "lat": elegidos["lat"], "nombre": elegidos["nombre"], "tamano": tamano})
    return vista_mapa.rotulos_sin_solape(datos, zoom)


def capa_rotulos(datos: pd.DataFrame) -> pdk.Layer:
    """Rótulos negros con halo blanco, en la fuente del sistema."""
    return pdk.Layer("TextLayer", datos, id="rotulos", get_position="[lon, lat]", get_text="nombre",
                     get_size="tamano", size_units=pdk.types.String("pixels"), get_color=[26, 26, 26],
                     # Literales con pdk.types.String: pydeck lee las demás cadenas como expresiones.
                     font_family=pdk.types.String("Arial, sans-serif"), font_weight=pdk.types.String("bold"),
                     character_set=pdk.types.String(vista_mapa.caracteres(datos["nombre"])),
                     font_settings={"sdf": True, "fontSize": 96, "buffer": 16, "radius": 16},
                     outline_width=4, outline_color=[255, 255, 255], pickable=False)


def franja_cifras(fila: pd.Series, modo: str, etiqueta: str) -> None:
    """Cifras principales del territorio elegido, encima del mapa, con el modo y el umbral a la vista."""
    con, sin, no_eval = (fila[f"{modo}_{e}"] for e in ("con_acceso", "sin_opcion_verificada", "no_evaluable"))
    total = con + sin + no_eval
    st.caption(f"Cifras del territorio elegido · {etiqueta}")
    columnas = st.columns(3)
    columnas[0].metric("Con acceso", vista_mapa.porcentaje(100 * con / total))
    columnas[1].metric("Sin opción verificada", vista_mapa.personas(sin))
    columnas[2].metric("No evaluable", vista_mapa.personas(no_eval))


def leyenda(capas: dict, clave: str, variable: str, opcion: dict) -> None:
    """Leyenda con barras de población por clase (celdas) o número de municipios por clase."""
    if opcion["escala"] == "municipios":
        municipios = capas["territorios"][capas["territorios"]["tipo"] == "municipio"]
        cuantos = municipios[f"clase_{variable}"].value_counts()
        filas = [(f"{etiqueta} · {int(cuantos.get(i, 0))} mun.", color, None)
                 for i, (etiqueta, color) in enumerate(zip(opcion["etiquetas"], opcion["paleta"], strict=True))]
        st.markdown(vista_mapa.leyenda_html("% sin opción verificada", "de la población total del municipio", filas,
                                            None), unsafe_allow_html=True)
        return
    tipo, codigo = clave.split(":")
    tramos = capas["tramos"]
    seleccion = tramos[(tramos["tipo"] == tipo) & (tramos["codigo"] == codigo) & (tramos["variable"] == variable)]
    filas, no_eval = vista_mapa.filas_tramos(seleccion, opcion["etiquetas"], opcion["paleta"])
    falta = "Sin dato de renta" if variable == "quintil_renta" else "No evaluable"
    extra = [(falta, vista_mapa.NO_EVALUABLE, no_eval), ("Sin población residencial", vista_mapa.TERRITORIO, None)]
    titulo = "Quintil de renta" if variable == "quintil_renta" else "Minutos al centro"
    st.markdown(vista_mapa.leyenda_html(titulo, "y % de la población evaluable", filas, opcion["umbral_tras"], extra),
                unsafe_allow_html=True)


nota_mapa = vista_mapa.nota_mapa  # textos comunes con la página web (P-28)


def mapa_minutos(proc: Path, version: str, capas: dict) -> None:
    """Mapa de minutos al estilo WikiBarrio: selector, buscador, cifras, mapa, tarjeta y leyenda."""
    territorios, opciones = capas["territorios"], opciones_variable(capas["catalogo"])
    modos = etiquetas_modo(capas["catalogo"])
    controles = st.columns([3, 2])
    # `?variable=…&territorio=…` abre el mapa con esa selección (enlaces de la demo, como `?pantalla=N`).
    pedida = st.query_params.get("variable")
    variable = controles[0].selectbox("¿Qué quieres colorear?", list(opciones),
                                      index=list(opciones).index(pedida) if pedida in opciones else 0,
                                      format_func=lambda v: opciones[v]["titulo"])
    claves = [TERRITORIO_INICIAL] + territorios[territorios["tipo"] == "municipio"].sort_values("nombre").index.tolist() \
        + territorios[territorios["tipo"] == "distrito"].sort_values("nombre").index.tolist()
    if st.session_state.get("territorio") not in claves:
        pedido = st.query_params.get("territorio")
        st.session_state["territorio"] = pedido if pedido in claves else TERRITORIO_INICIAL
    clave = controles[1].selectbox(
        "Buscar municipio o distrito", claves, key="territorio",
        format_func=lambda c: territorios.loc[c, "nombre"] + (" (distrito de Madrid)" if c.startswith("distrito:") else ""))
    fila, opcion, modo = territorios.loc[clave], opciones[variable], MODO_DE_VARIABLE[variable]
    franja_cifras(fila, modo, modos[modo])
    columna_mapa, columna_panel = st.columns([3, 1])
    vista = pdk.ViewState(longitude=(fila["lon_min"] + fila["lon_max"]) / 2, latitude=(fila["lat_min"] + fila["lat_max"]) / 2,
                          zoom=vista_mapa.zoom_para(fila["lon_min"], fila["lat_min"], fila["lon_max"], fila["lat_max"],
                                                    ANCHO_MAPA_PX, ALTO_MAPA_PX))
    capas_pdk = [*capas_fondo_y_datos(proc, version, variable, opcion), *capas_referencia(capas, proc, version, clave),
                 capa_rotulos(rotulos(territorios, clave, vista.zoom))]
    estilo_tarjeta = {"backgroundColor": "#FFFFFF", "color": vista_mapa.TEXTO, "fontSize": "14px",
                      "border": f"1px solid {vista_mapa.BORDE}", "fontFamily": "'Segoe UI', Arial, sans-serif",
                      "maxWidth": "340px", "whiteSpace": "normal"}
    with columna_mapa:
        st.pydeck_chart(pdk.Deck(layers=capas_pdk, initial_view_state=vista, map_style=ESTILO_SIN_INTERNET,
                                 tooltip={"html": f"<b>{{l}}</b><br/>{{d_{variable}}}<br/>{{g}}", "style": estilo_tarjeta}),
                        height=ALTO_MAPA_PX)
    with columna_panel:
        st.markdown(vista_mapa.tarjeta(fila.to_dict(), [(m, modos[m]) for m in ("transporte", "transporte_16_20", "pie")]))
        leyenda(capas, clave, variable, opcion)
    st.caption(nota_mapa(variable) + " Pasa el ratón por una zona para ver su dato; el buscador centra el mapa en "
               "un municipio o un distrito.")


def vista_primaria(proc: Path, version: str) -> None:
    """Pantalla 2: mapa de minutos y, debajo, A por escenario, modo, franja, edad y renta."""
    st.header("2. ¿A cuántos minutos está el centro de salud?")
    resumen = leer_csv(str(proc / "acceso" / "resumen_acceso.csv"))
    if resumen is None:
        st.error("El cálculo de acceso no existe para esta versión.")
        return
    capas = leer_capas_mapa(str(proc))
    if capas is None:
        st.warning("Las capas del mapa de minutos no están preparadas para esta versión: ejecuta "
                   "`uv run cercasalud build --snapshot <ID> --etapa capas_app`.")
    else:
        mapa_minutos(proc, version, capas)
    with st.expander("Escenarios, tablas por edad y renta, y mapa de estados", expanded=capas is None):
        tablas_primaria(proc, resumen)
    pie_de_vista(proc, version, "los del escenario elegido (columna «supuestos» de las tablas). El modo transporte "
                                "incluye ir andando. Martes laborable; se supone el centro abierto en la franja (SPEC §7).")


def tablas_primaria(proc: Path, resumen: pd.DataFrame) -> None:
    """A por escenario, modo y edad; mapa de estados y tabla por quintil de renta."""
    escenario = st.selectbox("Escenario (umbral, velocidad, percentil, margen o franja)",
                             sorted(resumen["escenario"].unique(), key=lambda e: e != "base"),
                             format_func=lambda e: ESCENARIOS_PRIMARIA.get(e, e))
    modo = st.radio("Modo", ["pie", "transporte", "al_menos_uno"], horizontal=True,
                    format_func={"pie": "A pie", "transporte": "Transporte público (incluido ir andando)",
                                 "al_menos_uno": "Al menos uno"}.get)
    st.caption("El umbral de cada modo es el del escenario elegido (por defecto, 15 min a pie y 30 en transporte).")
    filtrado = resumen[(resumen["escenario"] == escenario) & (resumen["modo"] == modo)]
    st.dataframe(tabla_estados(filtrado), hide_index=True)
    capa = leer_parquet(str(proc / "app" / "unidades_mapa.parquet"))
    sufijo = {"base": "", "franja_16_20": "_16_20", "ambas_franjas": "_ambas"}.get(escenario)
    columna = f"estado_{modo}" if modo == "pie" else f"estado_{modo}{sufijo}" if sufijo is not None else None
    if capa is not None and columna in capa.columns:
        mapa(capa, columna)
    else:
        st.caption("Mapa disponible para el escenario base y las franjas; el resto, solo en la tabla.")
    por_renta = leer_csv(str(proc / "renta" / "a_por_renta.csv"))
    if por_renta is not None and escenario == "base":
        st.subheader("Por quintil de renta de la sección (ADRH 2024; Q1 = renta más baja)")
        st.dataframe(por_renta[por_renta["modo"] == modo].round(0), hide_index=True)
        st.caption("Renta neta media por persona de la sección; quintiles con ~20 % de la población cada uno. Es "
                   "estratificación, no causa: la proximidad física no mide necesidad.")
    if len(filtrado):
        st.caption(f"**Supuestos del escenario elegido:** {filtrado['supuestos'].iloc[0]}")


def vista_heatshield(proc: Path, version: str) -> None:
    """Pantalla 3: B hora a hora con cotas; acreditable separada de la estimada."""
    st.header("3. HeatShield: refugios climáticos a pie")
    resumen = leer_csv(str(proc / "refugios" / "b_resumen.csv"))
    por_hora = leer_csv(str(proc / "refugios" / "b_por_hora.csv"))
    if resumen is None or por_hora is None:
        st.error("El cálculo de refugios no existe para esta versión.")
        return
    controles = st.columns(2)
    tipo = controles[0].selectbox("Tipo de día", list(vista_resultados.TIPOS_DIA),
                                  format_func=vista_resultados.TIPOS_DIA.get)
    grupo = controles[1].selectbox("Población", ["total", "75+", "65+", "85+"], format_func=app_datos.texto_objetivo)
    capital = por_hora[(por_hora["tipo_dia"] == tipo) & (por_hora["grupo_edad"] == grupo)
                       & por_hora["nombre"].str.startswith("base_") & (por_hora["territorio"] == "madrid_capital")]
    st.subheader("Personas con un mercado climatizado a 10 min a pie, hora a hora (Madrid capital)")
    series, colores = vista_resultados.series_por_cota(capital)
    st.line_chart(series, color=colores, x_label="hora de inicio", y_label="personas con acceso")
    tabla = resumen[(resumen["tipo_dia"] == tipo) & (resumen["grupo_edad"] == grupo)
                    & (resumen["territorio"] == "madrid_capital")]
    columnas = ["nombre", "denominador", "peor_hora", "con_acceso_peor_hora", "sin_opcion_peor_hora",
                "no_evaluable_peor_hora", "personas_hora_con_acceso", "personas_unicas_con_alguna_hora"]

    def legible(filas: pd.DataFrame) -> pd.DataFrame:
        salida = vista_resultados.tabla_legible(filas, columnas)
        salida["Escenario"] = salida["Escenario"].map(lambda n: vista_resultados.ESCENARIOS_B.get(n, n))
        return vista_resultados.para_mostrar(salida.astype({"Peor hora (hora de inicio)": "Int64"}))

    st.markdown("**Cobertura acreditable (sin supuesto)**")
    st.dataframe(legible(tabla[tabla["nombre"] == "base_acreditable"]), hide_index=True, use_container_width=True)
    st.markdown("**Cobertura estimada bajo el supuesto de acceso en horario comercial (D-33)**")
    st.dataframe(legible(tabla[tabla["nombre"] != "base_acreditable"]), hide_index=True, use_container_width=True)
    st.info("**Cobertura acreditable sin supuesto:** ningún mercado documenta el acceso a su zona climatizada, así que "
            "es nula. Es **cobertura documental insuficiente**, no ausencia de servicio (SPEC D-33). "
            "Las personas-hora no son personas: nunca se suman horas como personas distintas.")
    capa = leer_parquet(str(proc / "app" / "unidades_mapa.parquet"))
    if capa is not None and "estado_b" in capa.columns:
        st.subheader("Estado en la peor hora del laborable de julio (cota central)")
        mapa(capa[capa["cusec"].str.startswith("28079")], "estado_b")
    pie_de_vista(proc, version, "10 min a pie a 3,0 km/h; acceso estimado dentro del horario comercial (D-33); "
                                "fin de semana abierto solo si abre sábado y domingo")


def vista_carencias(proc: Path, version: str) -> None:
    """Pantalla 4: carencias coincidentes, por edad y modo, y su dependencia de la hora de B."""
    st.header("4. Carencias coincidentes (C)")
    c = leer_csv(str(proc / "refugios" / "c_resumen.csv"))
    if c is None:
        st.error("El cálculo de carencias coincidentes no existe para esta versión.")
        return
    franja = str(c["franja_b"].iloc[0])
    for clave, texto in vista_resultados.TIPOS_DIA.items():
        franja = franja.replace(clave, texto.lower())
    st.markdown(f"Personas **sin opción verificada en A y en B a la vez**, con B en la franja de referencia "
                f"(**{franja}**, la peor hora; cota central). Solo donde A y B son evaluables: hoy, Madrid capital.")
    tabla_c = vista_resultados.tabla_legible(c, ["modo_a", "grupo_edad", "carencia_coincidente", "sin_coincidencia",
                                                 "no_evaluable", "con_acceso_a_o_b", "denominador"])
    tabla_c["Modo de A"] = tabla_c["Modo de A"].map(lambda m: vista_resultados.MODOS_A.get(m, m))
    tabla_c["Población objetivo"] = tabla_c["Población objetivo"].map(app_datos.texto_objetivo)
    st.dataframe(vista_resultados.para_mostrar(tabla_c), hide_index=True, use_container_width=True)
    por_hora = leer_csv(str(proc / "refugios" / "c_por_hora.csv"))
    if por_hora is not None:
        st.subheader("¿Cuánto depende C de la hora elegida para B?")
        controles = st.columns(2)
        modo = controles[0].radio("Modo de A", ["transporte", "pie"], horizontal=True,
                                  format_func=vista_resultados.MODOS_A.get)
        grupo = controles[1].selectbox("Población", ["total", "65+", "75+", "85+"], format_func=app_datos.texto_objetivo)
        datos = por_hora[(por_hora["modo_a"] == modo) & (por_hora["grupo_edad"] == grupo)]
        serie = datos.pivot_table(index="hora", columns="tipo_dia", values="carencia_coincidente")
        tipos = [t for t in vista_resultados.TIPOS_DIA if t in serie.columns]
        st.line_chart(serie[tipos].rename(columns=vista_resultados.TIPOS_DIA),
                      color=["#1A1A1A", "#737373", "#BDBDBD"][:len(tipos)], x_label="hora de inicio",
                      y_label="personas con carencia coincidente")
        st.caption("Como la cobertura de B es baja a cualquier hora, casi todo el que carece de A carece también de B: "
                   "C cambia poco con la hora. La peor hora se mantiene como escenario declarado.")
    capa = leer_parquet(str(proc / "app" / "unidades_mapa.parquet"))
    if capa is not None and "estado_c_transporte" in capa.columns:
        modo_mapa = st.radio("Mapa con A", ["transporte", "pie"], horizontal=True, key="mapa_c",
                             format_func=vista_resultados.MODOS_A.get)
        mapa(capa[capa["cusec"].str.startswith("28079")], f"estado_c_{modo_mapa}")
    c_renta = leer_csv(str(proc / "renta" / "c_por_renta.csv"))
    if c_renta is not None:
        st.subheader("C por quintil de renta de la sección (ADRH 2024; Q1 = renta más baja)")
        st.dataframe(c_renta.round(0), hide_index=True)
        st.caption("Fuera de Madrid capital, C es no evaluable (B sin lista verificada): de ahí la columna no_evaluable.")
    barrios = leer_csv(str(proc / "contexto" / "barrios.csv"))
    iguala = leer_csv(str(proc / "contexto" / "iguala_distritos.csv"))
    if barrios is not None and st.checkbox("Mostrar capas de contexto de Madrid capital (D-16)"):
        st.subheader("Contexto por barrio: personas que viven solas (Padrón municipal a 1/1/2026)")
        st.dataframe(barrios.sort_values("c_transporte", ascending=False).round(0), hide_index=True)
        st.caption("Solo contexto: no interviene en ningún cálculo ni priorización. Vivir solo no equivale a soledad "
                   "no deseada. Las personas solas son del Padrón (no son cifras oficiales de población); la población "
                   "65+ y las columnas de A y C, del INE 2025 y de este análisis. Fuente: Ayuntamiento de Madrid.")
        if iguala is not None:
            st.subheader(f"IGUALA por distrito ({int(iguala['Fecha datos'].iloc[0])})")
            st.dataframe(iguala.round(2), hide_index=True)
            st.caption("Índice de vulnerabilidad territorial del Ayuntamiento de Madrid. Solo se publica agregado por "
                       "distrito; por barrio hay indicadores sueltos que aquí no se usan.")
    pie_de_vista(proc, version, "A y B con sus supuestos de base; la unión A∪B cuenta a cada persona una vez")


def tabla_cartera(proc: Path, componente: str) -> pd.DataFrame | None:
    """Tabla de carteras precalculada de un componente."""
    archivo = {"a_pie": "carteras_a_pie.csv", "a_transporte": "carteras_a_transporte.csv",
               "b1": "b1_ampliar_horas.csv"}[componente]
    return leer_csv(str(proc / "actuaciones" / archivo))


def componentes_disponibles(proc: Path) -> list[str]:
    """Componentes con carteras calculadas."""
    return [c for c in COMPONENTES if tabla_cartera(proc, c) is not None]


@st.cache_data
def nombres_municipios(carpeta: str) -> dict[str, str]:
    """Código INE → nombre del municipio, de la capa de territorios del mapa (si existe)."""
    ruta = Path(carpeta) / "app" / "territorios_mapa.csv"
    if not ruta.exists():
        return {}
    territorios = pd.read_csv(ruta, dtype={"codigo": str})
    municipios = territorios[territorios["tipo"] == "municipio"]
    return dict(zip(municipios["codigo"], municipios["nombre"], strict=True))


def condiciones_de(proc: Path, componente: str) -> str:
    """Supuestos de la comparación, de la configuración copiada en los resultados."""
    primaria = json.loads((proc / "acceso" / "resumen.json").read_text(encoding="utf-8"))["config"]["primaria"]
    ruta_b = proc / "refugios" / "resumen.json"
    refugios = json.loads(ruta_b.read_text(encoding="utf-8")).get("config_refugios") if ruta_b.exists() else None
    return vista_resultados.condiciones(componente, primaria, refugios)


def grafico_barras(barras: pd.DataFrame) -> None:
    """Barras horizontales una al lado de otra (nunca apiladas), con la cifra al final de cada barra."""
    st.markdown(vista_resultados.barras_html(barras), unsafe_allow_html=True)


def selector_cartera(componente: str, datos: pd.DataFrame, clave: str) -> dict:
    """Tamaño de la cartera: número de zonas (A, por defecto 3) o límites de mercados y horas (B1, por defecto 3 y 12)."""
    if componente == "b1":
        opciones = list(zip(datos["max_centros"], datos["max_centro_horas"], strict=True))
        inicial = opciones.index((3, 12)) if (3, 12) in opciones else 0
        centros, horas = st.radio("Límites de la cartera", opciones, index=inicial, horizontal=True, key=clave,
                                  format_func=lambda o: f"{o[0]} mercado{'s' if o[0] != 1 else ''}, {o[1]} horas")
        return datos[(datos["max_centros"] == centros) & (datos["max_centro_horas"] == horas)].iloc[0].to_dict()
    opciones = sorted(datos["k"].unique())
    k = st.radio("Número de zonas de estudio", opciones, index=opciones.index(3) if 3 in opciones else 0,
                 horizontal=True, key=clave, format_func=lambda v: f"{v} zona" + ("s" if v != 1 else ""))
    return datos[datos["k"] == k].iloc[0].to_dict()


def comparador_a(proc: Path, componente: str, fila: dict) -> None:
    """Cifras, barras y sensibilidad de una cartera de nuevos centros (A)."""
    k = int(fila["k"])
    columnas = st.columns(3)
    columnas[0].metric(f"Ganancia con {k} zona" + ("s" if k != 1 else ""), vista_mapa.personas(fila["milp_ganancia"]))
    columnas[1].metric("Regla simple, mismo número de zonas", vista_mapa.personas(fila["regla_simple_ganancia"]))
    columnas[2].metric("Siguen sin opción verificada", vista_mapa.personas(fila["sin_opcion_despues"]),
                       help=f"Antes de la cartera: {vista_mapa.personas(fila['sin_opcion_antes'])} personas.")
    st.markdown("**Personas que pasan de «sin opción verificada» a «con acceso»**")
    grafico_barras(vista_resultados.barras_comparacion(fila, componente))
    if k > 1 and pd.notna(fila.get("ganancia_incremental")):
        st.markdown(f"Ganancia adicional respecto a la cartera anterior más pequeña: "
                    f"**{vista_mapa.personas(fila['ganancia_incremental'])}** personas (no es la ganancia total).")
    detalle = leer_csv(str(proc / "actuaciones" / "carteras_detalle.csv"))
    if detalle is not None:
        zonas = detalle[(detalle["componente"] == componente) & (detalle["objetivo"] == fila["objetivo"])
                        & (detalle["k"] == k)]
        if len(zonas):
            st.markdown(f"**Zonas elegidas:** celdas de búsqueda de 250 m en "
                        f"{vista_resultados.municipios_de_zonas(zonas, nombres_municipios(str(proc)))}. "
                        "Son zonas para estudiar, no solares ni centros aprobados.")
    st.markdown("**¿Aguanta la cartera si cambian los supuestos?**")
    st.dataframe(vista_resultados.para_mostrar(vista_resultados.escenarios_cartera(fila, componente)), hide_index=True,
                 use_container_width=True)
    st.caption("«Misma cartera»: las zonas elegidas en la base, evaluadas con el otro supuesto. «Mejor cartera para ese "
               "escenario»: la que se elegiría si ese supuesto fuera el bueno. Son escenarios calculados, no un intervalo "
               f"de confianza. Peor ganancia de la cartera entre ellos: {vista_mapa.personas(fila['cartera_base_peor_ganancia'])}."
               if pd.notna(fila.get("cartera_base_peor_ganancia")) else "Escenarios calculados, no un intervalo de confianza.")


def comparador_b1(fila: dict) -> None:
    """Cifras y barras de la ampliación de horas de los mercados (B1)."""
    columnas = st.columns(3)
    columnas[0].metric("Peor hora, con la cartera", vista_mapa.personas(fila["milp_peor_hora_despues"]),
                       help=f"Hoy: {vista_mapa.personas(fila['milp_peor_hora_antes'])} personas con acceso en la peor hora.")
    columnas[1].metric("Peor hora, regla simple", vista_mapa.personas(fila["regla_simple_peor_hora"]))
    columnas[2].metric("Personas-hora ganadas", vista_mapa.personas(fila["milp_personas_hora_ganadas"]),
                       help="Una persona con acceso durante una hora más. No son personas distintas.")
    st.markdown("**Personas con acceso a un mercado climatizado en la peor hora**")
    grafico_barras(vista_resultados.barras_comparacion(fila, "b1"))
    st.markdown("**Horas que amplía la cartera**")
    st.dataframe(vista_resultados.bloques_b1_legibles(fila), hide_index=True)
    st.caption("La cota «todos abiertos» es el máximo posible con los 43 mercados abiertos todas las horas; no es una "
               "propuesta. Personas-hora no son personas: nunca se suman como personas distintas, ni con A.")


def vista_comparador(proc: Path, version: str) -> None:
    """Pantalla 5: cartera calculada frente a una regla simple, con las mismas condiciones."""
    st.header("5. Comparador de actuaciones")
    disponibles = componentes_disponibles(proc)
    if not disponibles:
        st.warning("Las actuaciones no están calculadas para esta versión.")
        return
    pedido = st.query_params.get("componente")
    componente = st.radio("Actuación", disponibles, format_func=COMPONENTES.get, horizontal=True,
                          index=disponibles.index(pedido) if pedido in disponibles else 0)
    tabla = tabla_cartera(proc, componente)
    controles = st.columns(2)
    with controles[0]:
        objetivo = st.selectbox("Población objetivo", app_datos.ordenar_objetivos(tabla["objetivo"]),
                                format_func=app_datos.texto_objetivo)
    with controles[1]:
        fila = selector_cartera(componente, tabla[tabla["objetivo"] == objetivo], f"cartera_{componente}")
    st.caption(f"{condiciones_de(proc, componente)} · {app_datos.texto_objetivo(objetivo)} · estado del solver: "
               f"{vista_resultados.texto_estado(fila['milp_estado'])}")
    if componente == "b1":
        comparador_b1(fila)
    else:
        comparador_a(proc, componente, fila)
        st.caption("La regla simple elige, con el mismo número de zonas, las celdas con más población sin opción dentro "
                   "de ellas (SPEC §10). Las dos se miden igual, con los mismos datos y supuestos.")
    pie_de_vista(proc, version, "presupuesto en número de actuaciones, no en euros; límite de 600 s por cartera")


def vista_resultados_pantalla(proc: Path, version: str) -> None:
    """Pantalla 6: antes y después, ganancia incremental, quién sigue fuera, robustez y solver."""
    st.header("6. Resultados")
    disponibles = componentes_disponibles(proc)
    if not disponibles:
        st.warning("Las actuaciones no están calculadas para esta versión.")
        return
    pedido = st.query_params.get("componente")
    componente = st.radio("Actuación", disponibles, format_func=COMPONENTES.get, horizontal=True, key="resultados_comp",
                          index=disponibles.index(pedido) if pedido in disponibles else 0)
    tabla = tabla_cartera(proc, componente)
    st.caption(condiciones_de(proc, componente))
    if componente == "b1":
        b1 = vista_resultados.tabla_legible(tabla, [
            "objetivo", "max_centros", "max_centro_horas", "milp_estado", "milp_peor_hora_antes", "milp_peor_hora_despues",
            "regla_simple_peor_hora", "cota_todos_abiertos_peor_hora", "milp_personas_hora_ganadas"])
        b1["Población objetivo"] = b1["Población objetivo"].map(app_datos.texto_objetivo)
        st.dataframe(vista_resultados.para_mostrar(b1), hide_index=True, use_container_width=True)
        st.caption("B1 se mide en personas (peor hora) y en personas-hora; nunca se suma con A.")
    else:
        legible = vista_resultados.tabla_legible(tabla, [
            "objetivo", "k", "milp_estado", "sin_opcion_antes", "milp_ganancia", "ganancia_incremental",
            "sin_opcion_despues", "regla_simple_ganancia"])
        legible["Población objetivo"] = legible["Población objetivo"].map(app_datos.texto_objetivo)
        st.markdown("**Antes y después de cada cartera**")
        st.dataframe(vista_resultados.para_mostrar(legible), hide_index=True, use_container_width=True)
        st.caption("«Sin opción después» es quién sigue fuera con la cartera. «Ganancia adicional» es lo que añade la "
                   "cartera respecto a la anterior más pequeña (1 → 3 → 5 zonas); no se suma a la ganancia total.")
        if "maxmin_estado" in tabla.columns:
            st.markdown("**Alternativa prudente (max-min): la cartera con la mejor ganancia en su peor escenario**")
            maxmin = vista_resultados.tabla_legible(tabla, ["objetivo", "k", "cartera_base_peor_ganancia", "maxmin_estado",
                                                            "maxmin_peor_ganancia", "maxmin_ganancia_base"])
            maxmin["Población objetivo"] = maxmin["Población objetivo"].map(app_datos.texto_objetivo)
            st.dataframe(vista_resultados.para_mostrar(maxmin), hide_index=True, use_container_width=True)
            st.caption("Compara la peor ganancia de la cartera base con la de la alternativa max-min: si se parecen, la "
                       "cartera base ya es prudente. Escenarios calculados, no un intervalo de confianza.")
    st.caption("El estado del solver se muestra tal cual (R-OPT-01): solo «optimo» acredita el óptimo.")
    pie_de_vista(proc, version, "los de cada componente; A y B tienen métricas propias y nunca se suman")


def vista_ficha(proc: Path, version: str) -> None:
    """Pantalla 7: ficha de decisión de una actuación y exportación (HTML, CSV, GeoJSON, JSON)."""
    st.header("7. Ficha de decisión y exportación")
    disponibles = componentes_disponibles(proc)
    if not disponibles:
        st.warning("Las actuaciones no están calculadas para esta versión.")
        return
    pedido, pedido_obj = st.query_params.get("componente"), st.query_params.get("objetivo")
    controles = st.columns(3)
    with controles[0]:
        componente = st.selectbox("Actuación", disponibles, format_func=COMPONENTES.get,
                                  index=disponibles.index(pedido) if pedido in disponibles else 0)
    tabla = tabla_cartera(proc, componente)
    objetivos = app_datos.ordenar_objetivos(tabla["objetivo"])
    with controles[1]:
        objetivo = st.selectbox("Población objetivo", objetivos, format_func=app_datos.texto_objetivo,
                                index=objetivos.index(pedido_obj) if pedido_obj in objetivos else 0)
    with controles[2]:
        fila = selector_cartera(componente, tabla[tabla["objetivo"] == objetivo], f"ficha_{componente}")
    texto_condiciones = condiciones_de(proc, componente)
    primaria = json.loads((proc / "acceso" / "resumen.json").read_text(encoding="utf-8"))["config"]["primaria"]
    if componente == "b1":
        detalle = pd.DataFrame(json.loads(fila.get("milp_bloques_detalle", "[]") or "[]"))
        ruta_b = proc / "refugios" / "resumen.json"
        refugios = json.loads(ruta_b.read_text(encoding="utf-8")).get("config_refugios", {}) if ruta_b.exists() else {}
        supuestos = {"tipo_dia": fila["tipo_dia"], "umbral_min": refugios.get("umbral_min"),
                     "velocidad_kmh": primaria["pie"]["velocidad_kmh"], "supuesto_acceso": "D-33"}
        legible = vista_resultados.bloques_b1_legibles(fila)
    else:
        todas = leer_csv(str(proc / "actuaciones" / "carteras_detalle.csv"))
        detalle = pd.DataFrame() if todas is None else todas[
            (todas["componente"] == componente) & (todas["objetivo"] == objetivo) & (todas["k"] == fila["k"])]
        supuestos = primaria["pie" if componente == "a_pie" else "transporte"]
        legible = vista_resultados.detalle_zonas_legible(detalle, nombres_municipios(str(proc)))
    manifiesto = app_datos.manifiesto_escenario(version, componente, fila, supuestos, no_evaluables_base(proc))
    resumen = vista_resultados.resumen_ficha(fila, componente, texto_condiciones, app_datos.texto_objetivo(objetivo))
    resumen.append(("Responsable propuesto", manifiesto["responsable_propuesto"]))
    limites = vista_resultados.LIMITES_FICHA[componente]
    alternativas = app_datos.tabla_alternativas_b1(fila) if componente == "b1" else pd.DataFrame()

    izquierda, derecha = st.columns([2, 1])
    with izquierda:
        st.markdown(app_datos.resumen_html(resumen), unsafe_allow_html=True)
    with derecha:
        st.markdown(f"**Límites que acompañan**\n\n{limites}")
        titulo = f"Ficha de decisión - {COMPONENTES[componente]} - {app_datos.texto_objetivo(objetivo)}"
        nombre = f"ficha_{componente}_{objetivo.replace('+', 'mas')}_{version}"
        st.markdown("**Llevarse la decisión**")
        st.download_button("Ficha legible (HTML)", app_datos.ficha_html(
            titulo, manifiesto, legible if len(legible) else detalle, alternativas, resumen, limites).encode("utf-8"),
            file_name=f"{nombre}.html", mime="text/html", type="primary")
        st.download_button("Zonas o bloques (CSV)", sin_campos_personales(detalle).to_csv(index=False).encode("utf-8"),
                           file_name=f"{nombre}.csv", mime="text/csv")
        if {"lon", "lat"} <= set(detalle.columns):
            st.download_button("Zonas (GeoJSON)",
                               json.dumps(app_datos.geojson_zonas(detalle), ensure_ascii=False, default=str).encode("utf-8"),
                               file_name=f"{nombre}.geojson", mime="application/geo+json")
        st.download_button("Escenario reproducible (JSON)",
                           json.dumps(manifiesto, ensure_ascii=False, indent=2, default=str).encode("utf-8"),
                           file_name=f"{nombre}.json", mime="application/json")
    if not alternativas.empty:
        st.markdown("**Alternativas: ¿elección firme o empate?**")
        st.dataframe(vista_resultados.para_mostrar(alternativas), hide_index=True, use_container_width=True)
        st.caption(app_datos.TEXTO_ALTERNATIVAS_B1)
    st.markdown("**Horas que amplía la cartera**" if componente == "b1" else "**Zonas de búsqueda elegidas**")
    st.dataframe(legible, hide_index=True, use_container_width=True)
    if componente != "b1":
        st.caption("La ganancia de una zona no es la población de su celda: cuenta a quienes viven alrededor y pasarían "
                   "a tener un centro dentro del umbral. Una celda con pocos residentes puede ganar mucho si está en "
                   "medio de una zona sin opción.")
    if {"lon", "lat"} <= set(detalle.columns) and len(detalle):
        mapa_zonas(proc, version, detalle)
    with st.expander("Tablas completas de esta versión (CSV)"):
        tablas_completas(proc, version)
    pie_de_vista(proc, version, "los de la actuación (manifiesto); el responsable es una propuesta a confirmar")


def mapa_zonas(proc: Path, version: str, detalle: pd.DataFrame) -> None:
    """Zonas elegidas sobre los municipios y sus límites (capas locales del mapa de minutos)."""
    capas = []
    if (proc / "app" / "deck" / "municipios.json").exists():
        capas.append(pdk.Layer("PolygonLayer", url_capa(proc, version, "municipios"), id="fondo", get_polygon="p",
                               get_fill_color=vista_mapa.rgb(vista_mapa.TERRITORIO), stroked=False, pickable=False))
    if (proc / "app" / "deck" / "lineas_limite_municipio.json").exists():
        capas.append(pdk.Layer("PathLayer", url_capa(proc, version, "lineas_limite_municipio"), id="limites",
                               get_path="p", get_color=[160, 160, 160], width_units=pdk.types.String("pixels"),
                               get_width=1, pickable=False))
    puntos = detalle.assign(nombre=detalle["municipio"].astype(str).map(nombres_municipios(str(proc))))
    capas.append(pdk.Layer("ScatterplotLayer", puntos[["lon", "lat", "zona", "nombre", "orden"]], id="zonas",
                           get_position="[lon, lat]", get_fill_color=[26, 26, 26], get_line_color=[255, 255, 255],
                           stroked=True, line_width_min_pixels=2, get_radius=250, radius_min_pixels=8, pickable=True))
    capas.append(pdk.Layer("TextLayer", puntos[["lon", "lat", "orden"]].assign(texto=puntos["orden"].astype(str)),
                           id="numeros", get_position="[lon, lat]", get_text="texto", get_size=12,
                           size_units=pdk.types.String("pixels"), get_color=[255, 255, 255],
                           font_weight=pdk.types.String("bold"), pickable=False))
    nombres = puntos[["lon", "lat", "nombre"]].fillna({"nombre": ""})
    capas.append(pdk.Layer("TextLayer", nombres, id="nombres", get_position="[lon, lat]", get_text="nombre",
                           get_size=14, size_units=pdk.types.String("pixels"), get_color=[26, 26, 26],
                           get_text_anchor=pdk.types.String("start"), get_pixel_offset=[14, 0],
                           font_family=pdk.types.String("Arial, sans-serif"), font_weight=pdk.types.String("bold"),
                           character_set=pdk.types.String(vista_mapa.caracteres(nombres["nombre"])),
                           font_settings={"sdf": True, "fontSize": 96, "buffer": 16, "radius": 16},
                           outline_width=4, outline_color=[255, 255, 255], pickable=False))
    margen = 0.08
    vista = pdk.ViewState(longitude=float(detalle["lon"].mean()), latitude=float(detalle["lat"].mean()),
                          zoom=vista_mapa.zoom_para(detalle["lon"].min() - margen, detalle["lat"].min() - margen,
                                                    detalle["lon"].max() + margen, detalle["lat"].max() + margen, 840, 420))
    st.pydeck_chart(pdk.Deck(layers=capas, initial_view_state=vista, map_style=ESTILO_SIN_INTERNET,
                             tooltip={"text": "Zona {orden}: {nombre}"}), height=420)


def tablas_completas(proc: Path, version: str) -> None:
    """Descargas de las tablas completas de resultados de la versión."""
    for etiqueta, ruta in (("primaria_resumen", proc / "acceso" / "resumen_acceso.csv"),
                           ("carteras_a_pie", proc / "actuaciones" / "carteras_a_pie.csv"),
                           ("carteras_a_transporte", proc / "actuaciones" / "carteras_a_transporte.csv"),
                           ("b1_ampliar_horas", proc / "actuaciones" / "b1_ampliar_horas.csv"),
                           ("carencias_coincidentes", proc / "refugios" / "c_resumen.csv"),
                           ("carencias_por_hora", proc / "refugios" / "c_por_hora.csv")):
        completa = leer_csv(str(ruta))
        if completa is not None:
            st.download_button(f"Descargar {etiqueta}.csv", sin_campos_personales(completa).to_csv(index=False).encode("utf-8"),
                               file_name=f"{etiqueta}_{version}.csv", mime="text/csv", key=f"completa_{etiqueta}")


def main() -> None:
    """Navegación entre el inicio y las siete pantallas."""
    st.set_page_config(page_title="CercaSalud MAD", layout="wide")
    versiones = versiones_disponibles()
    if not versiones:
        st.error("No hay resultados calculados. Ejecuta antes `uv run cercasalud build --snapshot <ID>`.")
        return
    version = st.sidebar.selectbox("Versión de datos", versiones, format_func=app_datos.etiqueta_version)
    proc = carpeta_procesados(raiz_datos(), version)
    vistas = {"Inicio": vista_inicio, "1. Cobertura de datos": vista_cobertura, "2. Primaria": vista_primaria,
              "3. HeatShield": vista_heatshield, "4. Carencias coincidentes": vista_carencias,
              "5. Comparador": vista_comparador, "6. Resultados": vista_resultados_pantalla,
              "7. Ficha y exportación": vista_ficha}
    # `?pantalla=N` abre directamente la pantalla N (0 = inicio): enlaces de la demo y prueba sin conexión.
    pedida = st.query_params.get("pantalla", "0")
    inicial = int(pedida) if pedida.isdigit() and int(pedida) < len(vistas) else 0
    pantalla = st.sidebar.radio("Pantalla", list(vistas), index=inicial)
    if pantalla == "Inicio":
        vista_inicio(proc)
        pie_de_vista(proc, version, "los de cada pantalla")
    else:
        vistas[pantalla](proc, version)


main()
