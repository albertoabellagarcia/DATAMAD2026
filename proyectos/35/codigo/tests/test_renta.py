"""Renta por sección (ADRH): calidad del dato, quintiles por población y comprobación del manifiesto."""

import json

import numpy as np
import pandas as pd
import pytest

from cercasalud import renta


def test_calidad_segun_la_nota_del_ine():
    """Las notas de secreto estadístico y de comarca se clasifican; sin nota es dato."""
    assert renta.calidad(None) == "dato" and renta.calidad(float("nan")) == "dato"
    assert renta.calidad("Dato bajo secreto estadístico, por encima de la cota superior. Se proporciona") == "cota_superior"
    assert renta.calidad("... renta media de los municipios de la comarca agraria ...") == "media_comarca"


def test_quintiles_reparten_la_poblacion_y_ordenan_por_renta():
    """Con 100 secciones iguales, cada quintil tiene el 20 % de la población; más renta, quintil igual o mayor."""
    azar = np.random.default_rng(1)
    renta_sec = pd.Series(azar.uniform(8000, 30000, 100))
    poblacion = pd.Series(np.full(100, 50.0))
    quintil = renta.quintiles_poblacion(renta_sec, poblacion)
    assert sorted(quintil.unique()) == [1, 2, 3, 4, 5]
    assert all(poblacion[quintil == q].sum() == 1000.0 for q in range(1, 6))
    orden = renta_sec.sort_values().index
    assert (np.diff(quintil[orden].to_numpy()) >= 0).all()


def test_quintiles_seccion_no_imputa_secciones_sin_renta():
    """Una sección con población y sin renta hace fallar el cálculo."""
    adrh = pd.DataFrame({"cusec": ["a"], "renta_neta_persona": [10000.0], "calidad_renta": ["dato"]})
    unidades = pd.DataFrame({"cusec": ["a", "b"], "poblacion_total": [5.0, 5.0]})
    with pytest.raises(ValueError):
        renta.quintiles_seccion(adrh, unidades)


def test_manifiesto_distinto_falla(tmp_path):
    """Si el SHA-256 no coincide con el del manifiesto, no se usa el archivo."""
    archivo = tmp_path / "adrh.json"
    archivo.write_text(json.dumps({"features": []}), encoding="utf-8")
    (tmp_path / "adrh.json.source.json").write_text(json.dumps({"sha256": "0" * 64}), encoding="utf-8")
    with pytest.raises(ValueError):
        renta.comprobar_manifiesto(archivo)


def test_por_quintil_conserva_la_poblacion():
    """Los estados de cada quintil suman su denominador."""
    unidades = pd.DataFrame({"quintil_renta": [1, 1, 2], "poblacion_total": [3.0, 4.0, 5.0]})
    estados = pd.Series(["con_acceso", "sin_opcion_verificada", "con_acceso"])
    filas = renta.por_quintil(unidades, estados, "poblacion_total", ("con_acceso", "sin_opcion_verificada"))
    assert filas[0] == {"quintil_renta": 1, "con_acceso": 3.0, "sin_opcion_verificada": 4.0, "denominador": 7.0}
