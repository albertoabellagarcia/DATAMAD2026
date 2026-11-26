"""Filtro de primaria pública (R-DAT-02) y eliminación de datos personales (R-DAT-03).

Datos sintéticos: cada caso está construido para provocar un motivo concreto.
"""

import pandas as pd

from cercasalud import primaria

CABECERA = ("centro_nro_registro;centro_tipo;dependecia_funcional;oferta_asistecial;"
            "municipio_nombre;localizacion_coordenada_x;localizacion_coordenada_y;NIF;dependecia_patrimonial\n")
PUBLICA = "Servicios o Institutos de Salud de las CC.AA"
FILAS = [
    # C1: centro de salud público en Madrid, dos filas coherentes -> incluido
    f"C1;Centro de salud;{PUBLICA};Medicina;Madrid;440000;4470000;DATO PERSONAL",
    f"C1;Centro de salud;{PUBLICA};Pediatría;Madrid;440000;4470000;DATO PERSONAL",
    # C2: consultorio público fuera de la capital -> incluido
    f"C2;Consultorio de atención primaria;{PUBLICA};Medicina;Alcalá de Henares;470000;4480000;B00000000",
    # C3: centro de salud privado -> excluido por dependencia
    "C3;Centro de salud;Privada;Medicina;Madrid;441000;4471000;B11111111",
    # C4: público sin coordenadas -> excluido
    f"C4;Centro de salud;{PUBLICA};Medicina;Getafe;;;B22222222",
    # C5: público con coordenada centinela -> excluido por rango
    f"C5;Centro de salud;{PUBLICA};Medicina;Leganés;-109;-208;B33333333",
    # C6: hospital -> no es de tipo primaria, no aparece en candidatos
    f"C6;Hospital;{PUBLICA};Urgencias;Madrid;442000;4472000;B44444444",
    # C7: dos filas con municipio distinto -> incluido, pero marcado como discrepancia
    f"C7;Centro de salud;{PUBLICA};Medicina;Móstoles;430000;4460000;B55555555",
    f"C7;Centro de salud;{PUBLICA};Pediatría;Alcorcón;430000;4460000;B55555555",
]


def resultado(tmp_path):
    """Escribe el CSV sintético (con BOM, como el origen) y aplica lectura y filtro."""
    ruta = tmp_path / "sanidad.csv"
    ruta.write_text(CABECERA + "\n".join(fila + ";" for fila in FILAS) + "\n", encoding="utf-8-sig")
    return primaria.filtrar_primaria(primaria.leer_registro(ruta))


def test_nif_se_elimina_al_leer(tmp_path):
    """La columna personal NIF no llega a ninguna salida."""
    salida = resultado(tmp_path)
    for tabla in (salida["incluidos"], salida["excluidos"]):
        assert "NIF" not in tabla.columns


def test_incluidos_y_motivos_de_exclusion(tmp_path):
    """Cada centro de tipo primaria queda incluido o excluido con el motivo esperado."""
    salida = resultado(tmp_path)
    assert sorted(salida["incluidos"]["centro_nro_registro"]) == ["C1", "C2", "C7"]
    motivos = dict(zip(salida["excluidos"]["centro_nro_registro"], salida["excluidos"]["motivo_exclusion"]))
    assert motivos == {"C3": "dependencia_no_publica_autonomica", "C4": "sin_coordenadas",
                       "C5": "coordenadas_fuera_de_rango"}


def test_discrepancia_detectada_antes_de_deduplicar(tmp_path):
    """C7 tiene municipios distintos en sus filas: se detecta aunque luego se quede una sola fila."""
    salida = resultado(tmp_path)
    assert salida["discrepancias"].to_dict("records") == [
        {"centro_nro_registro": "C7", "campo": "municipio_nombre", "valores_distintos": 2}]
    marcado = salida["incluidos"].set_index("centro_nro_registro")["discrepancia_entre_filas"]
    assert bool(marcado["C7"]) and not bool(marcado["C1"])


def test_cadena_de_conteos(tmp_path):
    """Filas -> centros -> tipo primaria -> dependencia -> coordenadas -> capital."""
    conteos = resultado(tmp_path)["conteos"]
    assert (conteos["filas"], conteos["centros_unicos"], conteos["centros_tipo_primaria"]) == (9, 7, 6)
    assert (conteos["tras_filtro_dependencia"], conteos["con_coordenadas_validas"]) == (5, 3)
    assert conteos["en_madrid_capital"] == 1
    assert conteos["centros_con_discrepancia_entre_filas"] == 1


def test_coordenadas_curadas_solo_rellenan_vacias(tmp_path):
    """C4 (sin coordenadas) entra con las curadas; C1 conserva las del registro aunque haya curadas."""
    ruta = tmp_path / "sanidad.csv"
    ruta.write_text(CABECERA + "\n".join(fila + ";" for fila in FILAS) + "\n", encoding="utf-8-sig")
    curadas = pd.DataFrame({"centro_nro_registro": ["C4", "C1"], "x": [435000.0, 1.0], "y": [4460000.0, 1.0],
                            "precision": ["centro_osm", "centro_osm"]})
    salida = primaria.filtrar_primaria(primaria.leer_registro(ruta), curadas)
    incluidos = salida["incluidos"].set_index("centro_nro_registro")
    assert incluidos.loc["C4", "x"] == 435000.0 and incluidos.loc["C4", "origen_coordenadas"] == "curado_osm"
    assert incluidos.loc["C1", "x"] == 440000 and incluidos.loc["C1", "origen_coordenadas"] == "registro"
    assert "C4" not in set(salida["excluidos"]["centro_nro_registro"])
    assert salida["conteos"]["coordenadas_curadas_osm"] == 1


def test_coordenadas_numericas(tmp_path):
    """Las coordenadas se convierten a número para filtrar; el texto original se conserva."""
    incluidos = resultado(tmp_path)["incluidos"].set_index("centro_nro_registro")
    assert incluidos.loc["C1", "x"] == 440000 and isinstance(incluidos.loc["C1", "localizacion_coordenada_x"], str)
    assert pd.api.types.is_numeric_dtype(incluidos["y"])


def test_via_patrimonial_sermas_y_exclusiones(tmp_path):
    """Las cinco altas contrastadas entran por patrimonio; otros organismos no se amplían.

    Casos sintéticos con los códigos revisados el 14/11: no usan información personal.
    La primera vía prevalece si ambas dependencias cumplen el filtro.
    """
    altas = {"CS17064", "CS18571", "CS19640", "CS19930", "CS22316"}
    filas = [
        f"{codigo};Centro de salud;Otra dependencia;Medicina;Madrid;440000;4470000;;"
        f"{primaria.PATRIMONIAL_PUBLICA}" for codigo in sorted(altas)
    ]
    filas += [
        "CS15826;Centro de salud;Otros CESS Públicos;Medicina;Madrid;440000;4470000;;Municipal",
        "CS20540;Centro de salud;Privada;Medicina;Madrid;440000;4470000;;Privada",
        f"C1;Centro de salud;{PUBLICA};Medicina;Madrid;440000;4470000;;{primaria.PATRIMONIAL_PUBLICA}",
        "SINXY;Centro de salud;Otra dependencia;Medicina;Madrid;;;;Servicio Madrileño de Salud",
        "HOSP;Hospital;Otra dependencia;Medicina;Madrid;440000;4470000;;Servicio Madrileño de Salud",
    ]
    ruta = tmp_path / "sanidad.csv"
    ruta.write_text(CABECERA + "\n".join(filas) + "\n", encoding="utf-8-sig")
    salida = primaria.filtrar_primaria(primaria.leer_registro(ruta))
    incluidos = salida["incluidos"].set_index("centro_nro_registro")
    assert set(incluidos.index) == altas | {"C1"}
    assert incluidos.loc["C1", "via_inclusion"] == "funcional_autonomica"
    assert set(incluidos.loc[sorted(altas), "via_inclusion"]) == {"patrimonial_sermas"}
    assert set(salida["conteos"]["codigos_via_patrimonial"]) == altas
    assert salida["conteos"]["tras_filtro_dependencia"] == 7
    motivos = salida["excluidos"].set_index("centro_nro_registro")["motivo_exclusion"]
    assert motivos["SINXY"] == "sin_coordenadas"


def test_discrepancia_patrimonial_antes_de_deduplicar(tmp_path):
    """Una discrepancia de patrimonio se conserva aunque la primera fila ya fuera pública."""
    fila = f"C1;Centro de salud;{PUBLICA};Medicina;Madrid;440000;4470000;;"
    ruta = tmp_path / "sanidad.csv"
    ruta.write_text(CABECERA + fila + "Municipal\n" + fila + "Servicio Madrileño de Salud\n",
                    encoding="utf-8-sig")
    salida = primaria.filtrar_primaria(primaria.leer_registro(ruta))
    assert salida["discrepancias"].to_dict("records") == [
        {"centro_nro_registro": "C1", "campo": "dependecia_patrimonial", "valores_distintos": 2}]
