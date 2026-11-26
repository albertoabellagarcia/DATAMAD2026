"""R-ARQ-03: la huella de una etapa cambia si cambia una entrada y no cambia si nada cambia."""

from cercasalud import huellas


def preparar(tmp_path):
    """Raíz de datos mínima con la versión y la carpeta que lee `demanda` (poblacion/)."""
    (tmp_path / "snapshots").mkdir()
    (tmp_path / "snapshots" / "v1.json").write_text('{"id": "v1"}', encoding="utf-8")
    carpeta = tmp_path / "procesados" / "v1" / "poblacion"
    carpeta.mkdir(parents=True)
    (carpeta / "secciones.parquet").write_bytes(b"uno")
    return carpeta


def test_misma_entrada_misma_huella_y_se_omite(tmp_path):
    """Sin cambios, la huella se repite y la etapa guardada se da por vigente."""
    preparar(tmp_path)
    primera = huellas.huella(tmp_path, "v1", "demanda")
    assert primera == huellas.huella(tmp_path, "v1", "demanda")
    destino = tmp_path / "procesados" / "v1" / "demanda"
    destino.mkdir()
    huellas.guardar(destino, primera)
    assert huellas.sin_cambios(destino, primera)


def test_cambiar_una_entrada_cambia_la_huella(tmp_path):
    """Un archivo de entrada distinto (o una versión de datos distinta) obliga a recalcular."""
    carpeta = preparar(tmp_path)
    antes = huellas.huella(tmp_path, "v1", "demanda")
    (carpeta / "secciones.parquet").write_bytes(b"dos")
    assert huellas.huella(tmp_path, "v1", "demanda") != antes
    otra = huellas.huella(tmp_path, "v1", "demanda")
    (tmp_path / "snapshots" / "v1.json").write_text('{"id": "v1", "x": 1}', encoding="utf-8")
    assert huellas.huella(tmp_path, "v1", "demanda") != otra


def test_etapa_sin_huella_guardada_no_se_omite(tmp_path):
    """Una etapa que nunca terminó (sin .huella.json) siempre se ejecuta."""
    assert not huellas.sin_cambios(tmp_path, "cualquiera")
