"""Formato del comparador, los resultados y la ficha de la app (pantallas 5 a 7). No calcula (R-UI-01).

Solo elige columnas ya calculadas por `build` (etapa `actuaciones`), les pone nombre en castellano
y las ordena para leerlas. Ninguna cifra sale de una fórmula nueva: la ganancia, la ganancia
incremental, «sin opción después», la robustez y la reoptimización vienen en las tablas. No
importa Streamlit, para poder probarlo.
"""

import json

import pandas as pd

# Escenarios de sensibilidad de las carteras, con el nombre de sus columnas en cada tabla. En la
# tabla a pie, la robustez lleva solo la velocidad («robustez_ganancia_2.4») y la reoptimización,
# «velocidad_2.4»; en la de transporte, las dos llevan el mismo nombre.
ESCENARIOS_CARTERA = {
    "a_pie": [("2.4", "velocidad_2.4", "A pie a 2,4 km/h"), ("3.6", "velocidad_3.6", "A pie a 3,6 km/h")],
    "a_transporte": [
        ("franja_16_20", "franja_16_20", "Franja de 16 a 20 h"),
        ("inventario_ampliado", "inventario_ampliado", "Inventario ampliado (5 centros más del SERMAS)"),
        ("tp_p80", "tp_p80", "Percentil 80 de las salidas (en vez de la mediana)"),
        ("tp_margen_2", "tp_margen_2", "Transporte 2 min más lento"),
        ("tp_margen_4", "tp_margen_4", "Transporte 4 min más lento"),
        ("tp_margen_6", "tp_margen_6", "Transporte 6 min más lento"),
    ],
}

COLUMNAS_LEGIBLES = {
    "objetivo": "Población objetivo", "k": "Zonas (k)", "milp_estado": "Estado del solver",
    "milp_brecha": "Brecha del solver", "sin_opcion_antes": "Sin opción antes", "milp_ganancia": "Ganancia",
    "ganancia_incremental": "Ganancia adicional", "sin_opcion_despues": "Sin opción después",
    "regla_simple_ganancia": "Regla simple", "cartera_base_peor_ganancia": "Peor ganancia de la cartera",
    "maxmin_estado": "Estado (max-min)", "maxmin_peor_ganancia": "Peor ganancia (max-min)",
    "maxmin_ganancia_base": "Ganancia en la base (max-min)", "max_centros": "Mercados como máximo",
    "max_centro_horas": "Horas ampliadas como máximo", "milp_peor_hora_antes": "Peor hora, hoy",
    "milp_peor_hora_despues": "Peor hora, con la cartera", "regla_simple_peor_hora": "Peor hora, regla simple",
    "cota_todos_abiertos_peor_hora": "Peor hora, todos abiertos de 12 a 21 h (cota)",
    "milp_personas_hora_ganadas": "Personas-hora ganadas", "milp_centros": "Mercados elegidos",
    "milp_centro_horas": "Horas ampliadas", "tipo_dia": "Tipo de día",
    # HeatShield (B) y carencias coincidentes (C).
    "nombre": "Escenario", "denominador": "Población", "peor_hora": "Peor hora (hora de inicio)",
    "con_acceso_peor_hora": "Con acceso en la peor hora", "sin_opcion_peor_hora": "Sin opción en la peor hora",
    "no_evaluable_peor_hora": "No evaluable en la peor hora", "personas_hora_con_acceso": "Personas-hora con acceso",
    "personas_unicas_con_alguna_hora": "Personas con acceso alguna hora", "modo_a": "Modo de A",
    "grupo_edad": "Población objetivo", "carencia_coincidente": "Carencia coincidente",
    "sin_coincidencia": "Sin coincidencia", "no_evaluable": "No evaluable", "con_acceso_a_o_b": "Con acceso a A o a B",
    "cartera_pie_ganancia_en_transporte": "Cartera a pie, evaluada en transporte",
    "cartera_tp_ganancia_a_pie": "Esta cartera, evaluada a pie",
}

TIPOS_DIA = {"laborable_julio": "Laborable de julio", "laborable_agosto": "Laborable de agosto",
             "fin_de_semana": "Fin de semana"}
MODOS_A = {"pie": "A pie", "transporte": "Transporte público (incluido ir andando)"}
ESCENARIOS_B = {"base_acreditable": "Acreditable (sin supuesto)", "base_central": "Estimada, cota central",
                "base_inferior": "Estimada, cota inferior", "base_superior": "Estimada, cota superior",
                "umbral_5": "Umbral de 5 min", "umbral_15": "Umbral de 15 min", "velocidad_2.4": "A 2,4 km/h",
                "velocidad_3.6": "A 3,6 km/h"}
# Líneas por cota de B: grises para las estimadas (la central, en negro) y rojo para la acreditable,
# que es el mensaje clave (es nula) y usa el mismo rojo que «carencia» en el mapa.
# Orden de dibujo: la central va la última para quedar encima cuando las cotas coinciden.
COTAS_B = {"acreditable": ("Acreditable (sin supuesto)", "#D73027"), "inferior": ("Estimada, cota inferior", "#737373"),
           "superior": ("Estimada, cota superior", "#BDBDBD"), "central": ("Estimada, cota central", "#1A1A1A")}

# Estados de `optimizacion.estado_solver` (R-OPT-01 y R-OPT-04).
ESTADOS_SOLVER = {"optimo": "óptimo acreditado por el solver",
                  "tiempo_agotado": "se agotó el tiempo: no acredita el óptimo",
                  "inviable": "sin solución con esas restricciones", "sin_ganancia": "ninguna cartera gana acceso",
                  "error": "error del solver"}


def decimal(valor: float) -> str:
    """3.0 → «3,0»; 2.4 → «2,4»."""
    return f"{valor:.1f}".replace(".", ",")


def condiciones(componente: str, primaria: dict, refugios: dict | None = None) -> str:
    """Supuestos de una comparación en una línea, leídos de la configuración copiada en los resultados."""
    pie, tp = primaria["pie"], primaria["transporte"]
    if componente == "a_pie":
        return f"A pie · {pie['umbral_min']} min a {decimal(pie['velocidad_kmh'])} km/h"
    if componente == "a_transporte":
        franja = tp["franja"].replace(":00", "").replace("-", " a ").lstrip("0")
        return (f"Transporte público, incluido ir andando · {tp['umbral_min']} min · de {franja} h · "
                f"percentil {tp['percentil_estado']} de las salidas · martes laborable")
    umbral = (refugios or {}).get("umbral_min", "?")
    return (f"Refugios a pie · {umbral} min a {decimal(pie['velocidad_kmh'])} km/h · peor hora del laborable de julio · "
            "acceso supuesto en horario comercial (D-33)")


def series_por_cota(por_hora: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    """Personas con acceso por hora, una columna por cota en orden fijo y con su color (para `st.line_chart`)."""
    tabla = por_hora.pivot_table(index="hora", columns="cota", values="con_acceso")
    cotas = [c for c in COTAS_B if c in tabla.columns]
    return tabla[cotas].rename(columns={c: COTAS_B[c][0] for c in cotas}), [COTAS_B[c][1] for c in cotas]


def texto_estado(estado: str) -> str:
    """Estado del solver tal cual (R-OPT-01), con su lectura: solo «optimo» acredita el óptimo."""
    return f"{estado} ({ESTADOS_SOLVER[estado]})" if estado in ESTADOS_SOLVER else str(estado)


def tabla_legible(tabla: pd.DataFrame, columnas: list[str]) -> pd.DataFrame:
    """Las columnas pedidas que existan, con nombre en castellano y personas redondeadas a la unidad."""
    presentes = [c for c in columnas if c in tabla.columns]
    salida = tabla[presentes].copy()
    for columna in presentes:
        if pd.api.types.is_float_dtype(salida[columna]) and columna != "milp_brecha":
            salida[columna] = salida[columna].round(0).astype("Int64")
    return salida.rename(columns=COLUMNAS_LEGIBLES)


def para_mostrar(tabla: pd.DataFrame) -> pd.DataFrame:
    """Columnas de enteros como texto con punto de miles («51.489»), para leerlas en castellano.

    La tabla de Streamlit pone los miles según el idioma del navegador, que puede ser inglés
    («51,489» se leería como decimal). Las celdas vacías quedan como «—».
    """
    salida = tabla.copy()
    for columna in salida.columns:
        if pd.api.types.is_integer_dtype(salida[columna]):
            salida[columna] = salida[columna].map(lambda v: "—" if pd.isna(v) else f"{int(v):,}".replace(",", "."))
        elif pd.api.types.is_float_dtype(salida[columna]):
            # Decimales con coma (porcentajes de pérdida, por ejemplo): 9.4 → «9,4».
            salida[columna] = salida[columna].map(lambda v: "—" if pd.isna(v) else f"{v:,.1f}".replace(",", " ")
                                                  .replace(".", ",").replace(" ", "."))
    return salida


def escenarios_cartera(fila: dict, componente: str) -> pd.DataFrame:
    """La misma cartera evaluada en cada escenario y la mejor cartera recalculada para ese escenario.

    Primera fila: la base. «Misma cartera» es `robustez_ganancia_*`; «reoptimizada», `reoptimo_*`.
    Si una columna falta en la tabla, la celda queda vacía (no se rellena con otra cifra).
    """
    filas = [{"Escenario": "Base", "Misma cartera": fila.get("milp_ganancia"),
              "Mejor cartera para ese escenario": fila.get("milp_ganancia"), "Estado del solver": fila.get("milp_estado")}]
    for robustez, reoptimo, nombre in ESCENARIOS_CARTERA.get(componente, []):
        filas.append({"Escenario": nombre, "Misma cartera": fila.get(f"robustez_ganancia_{robustez}"),
                      "Mejor cartera para ese escenario": fila.get(f"reoptimo_ganancia_{reoptimo}"),
                      "Estado del solver": fila.get(f"reoptimo_estado_{reoptimo}")})
    tabla = pd.DataFrame(filas)
    for columna in ("Misma cartera", "Mejor cartera para ese escenario"):
        tabla[columna] = pd.to_numeric(tabla[columna], errors="coerce").round(0).astype("Int64")
    return tabla


def barras_comparacion(fila: dict, componente: str) -> pd.DataFrame:
    """Barras del comparador, una al lado de otra (nunca apiladas: no se suman).

    A: regla simple y cartera calculada, en personas que ganan opción. B1: personas con acceso en
    la peor hora hoy, con la regla simple, con la cartera y con todos los mercados abiertos (cota).
    """
    if componente == "b1":
        pares = [("Hoy", "milp_peor_hora_antes"), ("Regla simple", "regla_simple_peor_hora"),
                 ("Cartera calculada", "milp_peor_hora_despues"),
                 ("Todos abiertos de 12 a 21 h (cota)", "cota_todos_abiertos_peor_hora")]
    else:
        pares = [("Regla simple", "regla_simple_ganancia"), ("Cartera calculada", "milp_ganancia")]
    return pd.DataFrame({"Opción": [nombre for nombre, _ in pares],
                         "Personas": [round(float(fila[columna])) for _, columna in pares], "orden": range(len(pares))})


# Interfaz casi monocroma (decisión del usuario, 15/11): grises; la cartera, en el tono más oscuro.
GRISES_BARRAS = {"Hoy": "#D0D0D0", "Regla simple": "#9E9E9E", "Cartera calculada": "#1A1A1A",
                 "Todos abiertos de 12 a 21 h (cota)": "#F2F2F2"}


def barras_html(barras: pd.DataFrame, ancho_max_px: int = 520) -> str:
    """Barras horizontales en HTML propio (sin bibliotecas de gráficos), con la cifra al lado.

    El largo es proporcional a las personas sobre la mayor de las barras; todas empiezan en cero.
    """
    import html

    mayor = max(float(barras["Personas"].max()), 1.0)
    filas = []
    for _, fila in barras.sort_values("orden").iterrows():
        largo = max(2, round(ancho_max_px * float(fila["Personas"]) / mayor))
        color = GRISES_BARRAS.get(fila["Opción"], "#9E9E9E")
        cifra = f"{float(fila['Personas']):,.0f}".replace(",", ".")
        filas.append(
            "<div style='display:flex;align-items:center;gap:12px;margin:8px 0'>"
            f"<span style='width:230px;text-align:right;font-size:0.95rem;color:#1A1A1A'>{html.escape(fila['Opción'])}</span>"
            f"<span style='display:inline-block;width:{largo}px;height:26px;background:{color};"
            "border:1px solid #1A1A1A'></span>"
            f"<span style='font-weight:700;font-size:1.05rem;color:#1A1A1A'>{cifra}</span></div>")
    return "<div>" + "".join(filas) + "</div>"


def _personas(valor) -> str:
    """Personas con punto de miles, o «—» si falta."""
    return "—" if valor is None or pd.isna(valor) else f"{float(valor):,.0f}".replace(",", ".")


def resumen_ficha(fila: dict, componente: str, texto_condiciones: str, texto_objetivo: str) -> list[tuple[str, str]]:
    """Filas «concepto: valor» de la ficha de decisión, todas de columnas ya calculadas."""
    if componente == "b1":
        centros, horas = int(fila["max_centros"]), int(fila["max_centro_horas"])
        filas = [
            ("Actuación que se propone estudiar",
             (f"Ampliar el horario de hasta {centros} mercado{'s' if centros != 1 else ''} municipal"
              f"{'es' if centros != 1 else ''}, con un máximo de {horas} horas en total")),
            ("Población objetivo", texto_objetivo),
            ("Peor hora, hoy (personas con acceso)", _personas(fila.get("milp_peor_hora_antes"))),
            ("Peor hora, con la cartera", _personas(fila.get("milp_peor_hora_despues"))),
            ("Peor hora, con la regla simple", _personas(fila.get("regla_simple_peor_hora"))),
            ("Personas-hora ganadas (no son personas)", _personas(fila.get("milp_personas_hora_ganadas"))),
            ("Mercados elegidos y horas ampliadas",
             f"{_personas(fila.get('milp_centros'))} mercados, {_personas(fila.get('milp_centro_horas'))} horas"),
        ]
        for tipo, nombre in (("laborable_agosto", "laborable de agosto"), ("fin_de_semana", "fin de semana")):
            if f"robustez_{tipo}_peor_hora_despues" in fila:
                antes, despues = fila[f"robustez_{tipo}_peor_hora_antes"], fila[f"robustez_{tipo}_peor_hora_despues"]
                valor = f"{_personas(antes)} → {_personas(despues)}"
                if antes == 0 and despues == 0:
                    # Fin de semana: abierto solo si abre esa hora el sábado y el domingo (D-20).
                    valor += (" (a alguna hora ningún mercado cuenta como abierto; la cartera gana "
                              f"{_personas(fila.get(f'robustez_{tipo}_personas_hora'))} personas-hora)")
                filas.append((f"Misma cartera en {nombre}: peor hora hoy → con la cartera", valor))
    else:
        k = int(fila["k"])
        filas = [
            ("Actuación que se propone estudiar",
             f"{k} zona{'s' if k != 1 else ''} de búsqueda para nuevos centros de atención primaria"),
            ("Población objetivo", texto_objetivo),
            ("Sin opción verificada, antes", _personas(fila.get("sin_opcion_antes"))),
            ("Sin opción verificada, después", _personas(fila.get("sin_opcion_despues"))),
            ("Ganancia (personas que pasan a tener opción)", _personas(fila.get("milp_ganancia"))),
            ("Regla simple con el mismo número de zonas", _personas(fila.get("regla_simple_ganancia"))),
            ("Peor ganancia de la cartera entre los escenarios calculados", _personas(fila.get("cartera_base_peor_ganancia"))),
            ("Restricción", f"Hasta {k} zona{'s' if k != 1 else ''}; presupuesto en número de actuaciones, no en euros"),
        ]
    filas += [("Condiciones", texto_condiciones), ("Estado del solver", texto_estado(fila.get("milp_estado")))]
    return filas


LIMITES_FICHA = {
    "a_pie": ("Una zona es una celda de búsqueda de 250 m con población residente, no un solar ni un edificio. La "
              "ganancia mide proximidad física potencial, no capacidad, citas ni efectos sobre la salud. El resultado "
              "cambia con los supuestos; los escenarios no son un intervalo de confianza."),
    "a_transporte": ("Una zona es una celda de búsqueda de 250 m, no un solar. El tiempo en transporte usa los horarios "
                     "GTFS de un martes laborable y supone el centro abierto en la franja. Mide proximidad, no "
                     "capacidad ni citas. Los escenarios no son un intervalo de confianza."),
    "b1": ("El acceso a la zona climatizada de los mercados no consta en ninguna ficha (D-33): la ganancia supone "
           "acceso dentro del horario abierto. Personas-hora no son personas. Solo Madrid capital, con la lista "
           "oficial de 43 mercados."),
}


def municipios_de_zonas(detalle: pd.DataFrame, nombres: dict[str, str]) -> str:
    """«Boadilla del Monte, Alcobendas y Rivas-Vaciamadrid» a partir del código INE de cada zona."""
    lista = [nombres.get(str(c), str(c)) for c in detalle.sort_values("orden")["municipio"]]
    return lista[0] if len(lista) == 1 else ", ".join(lista[:-1]) + " y " + lista[-1] if lista else ""


def detalle_zonas_legible(detalle: pd.DataFrame, nombres: dict[str, str]) -> pd.DataFrame:
    """Zonas de una cartera con municipio, población de la celda y coordenadas redondeadas."""
    if detalle.empty or "zona" not in detalle.columns:
        return detalle
    tabla = detalle.sort_values("orden").assign(
        Municipio=lambda t: t["municipio"].astype(str).map(lambda c: nombres.get(c, c)))
    return pd.DataFrame({"Orden": tabla["orden"], "Zona de búsqueda (celda de 250 m)": tabla["zona"],
                         "Municipio": tabla["Municipio"],
                         "Población residente en la celda": tabla["poblacion_celda"].round(0).astype("Int64"),
                         "Longitud": tabla["lon"].round(4), "Latitud": tabla["lat"].round(4)})


def bloques_b1_legibles(fila: dict) -> pd.DataFrame:
    """Horas que amplía la cartera de B1, agrupadas por mercado: «14–18 h y 20–21 h»."""
    bloques = pd.DataFrame(json.loads(fila.get("milp_bloques_detalle") or "[]"))
    if bloques.empty:
        return bloques
    filas = []
    for mercado, grupo in bloques.groupby("mercado", sort=False):
        horas = sorted(grupo["hora_inicio"].astype(int))
        tramos, inicio, previa = [], horas[0], horas[0]
        for hora in [*horas[1:], None]:
            if hora is not None and hora == previa + 1:
                previa = hora
                continue
            tramos.append(f"{inicio}–{previa + 1} h")
            if hora is not None:
                inicio = previa = hora
        filas.append({"Mercado": mercado.removeprefix("Mercado municipal de "), "Horas ampliadas": " y ".join(tramos),
                      "Número de horas": len(horas)})
    return pd.DataFrame(filas)
