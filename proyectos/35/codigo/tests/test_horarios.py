"""Lectura de horarios curados de refugios (H4): tramos, días, domingo y reglas de combinación."""

import pandas as pd
import pytest

from cercasalud import horarios
from cercasalud.construccion import ARCHIVO_REFUGIOS_MERCADOS


def test_hora_abierta_solo_si_el_tramo_la_cubre_entera():
    """09:00-14:00 cubre 13-14 pero no 14-15; 17:30-20:30 cubre 18-19 y 19-20, no 17-18 ni 20-21."""
    t = horarios.tramos("09:00-14:00 y 17:30-20:30")
    estados = {h: horarios.abierto_en(t, h) for h in horarios.HORAS}
    assert [h for h, e in estados.items() if e == horarios.ABIERTO] == [12, 13, 18, 19]


def test_laborables_por_dia_con_rangos():
    """«lunes a jueves …; viernes …» asigna cada día; falta de días es un error."""
    por_dia = horarios.laborables_por_dia("lunes a jueves 09:00-14:00 y 17:30-20:00; viernes 09:00-21:00")
    assert por_dia["miercoles"] == [(540, 840), (1050, 1200)] and por_dia["viernes"] == [(540, 1260)]
    with pytest.raises(ValueError):
        horarios.laborables_por_dia("lunes 09:00-14:00; viernes 09:00-21:00")


def test_laborable_manda_el_dia_mas_restrictivo():
    """Si el lunes cierra a mediodía, la franja 14-15 del laborable queda cerrada."""
    fila = pd.Series({"pk": "1", "laborables_comercial": "lunes 09:00-14:15 y 17:00-20:00; martes a viernes 09:00-21:00",
                      "sabado_comercial": "09:00-14:00", "domingo_comercial": "no figura"})
    tabla = pd.DataFrame(horarios.estados_refugio(fila)).set_index(["tipo_dia", "hora"])["estado"]
    assert tabla[("laborable_julio", 14)] == horarios.CERRADO
    assert tabla[("laborable_julio", 12)] == horarios.ABIERTO


def test_fin_de_semana_exige_sabado_y_domingo():
    """Sábado abierto y domingo sin dato: pendiente; sábado cerrado: cerrado aunque falte el domingo."""
    fila = pd.Series({"pk": "1", "laborables_comercial": "09:00-21:00", "sabado_comercial": "09:00-14:00",
                      "domingo_comercial": "no figura"})
    tabla = pd.DataFrame(horarios.estados_refugio(fila)).set_index(["tipo_dia", "hora"])["estado"]
    assert tabla[("fin_de_semana", 12)] == horarios.PENDIENTE
    assert tabla[("fin_de_semana", 15)] == horarios.CERRADO


def test_textos_de_domingo():
    """Los cinco tipos de texto de domingo de los 43 mercados."""
    assert horarios.domingo("no figura") == horarios.PENDIENTE
    assert horarios.domingo("no figura (mercado); la planta 2.ª abre de lunes a domingo de 10 a 24") == horarios.PENDIENTE
    assert horarios.domingo("solo el primer domingo de cada mes, 11:00-17:00") == horarios.CERRADO
    assert horarios.domingo("no figura (solo el primer domingo de diciembre)") == horarios.CERRADO
    assert horarios.domingo("11:00-17:00, solo ocio y restauración") == [(660, 1020)]


def test_los_43_mercados_curados_se_leen_sin_error():
    """El archivo curado real se convierte entero: 43 mercados × 3 tipos de día × 9 horas."""
    mercados = pd.read_csv(ARCHIVO_REFUGIOS_MERCADOS, dtype=str, keep_default_na=False)
    tabla = horarios.tabla_estados(mercados)
    assert len(mercados) == 43 and len(tabla) == 43 * 3 * 9
    assert set(tabla["estado"]) <= {horarios.ABIERTO, horarios.CERRADO, horarios.PENDIENTE}
