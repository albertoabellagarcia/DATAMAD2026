"""Escritura atómica y huellas SHA-256 (R-OPS-01, R-DAT-01)."""

import hashlib

import pytest

from cercasalud import manifiestos


def test_sha256_coincide_con_hashlib(tmp_path):
    """El SHA-256 por bloques es el mismo que el de hashlib sobre el contenido completo."""
    archivo = tmp_path / "datos.bin"
    contenido = b"x" * (manifiestos.TAMANO_BLOQUE + 123)  # más de un bloque
    archivo.write_bytes(contenido)
    assert manifiestos.sha256_archivo(archivo) == hashlib.sha256(contenido).hexdigest()


def test_escritura_cortada_no_deja_archivo_final_ni_temporal(tmp_path, monkeypatch):
    """Si el renombrado falla, no queda ni el destino ni el temporal (test de interrupción)."""
    destino = tmp_path / "salida.json"

    def fallar(*_):
        raise OSError("corte simulado")

    monkeypatch.setattr(manifiestos.os, "replace", fallar)
    with pytest.raises(OSError):
        manifiestos.escribir_atomico(destino, b"contenido")
    assert not destino.exists()
    assert list(tmp_path.iterdir()) == []


def test_json_atomico_se_lee_igual(tmp_path):
    """Lo que se escribe con escribir_json_atomico se recupera con leer_json, con acentos."""
    destino = tmp_path / "a" / "m.json"
    manifiestos.escribir_json_atomico(destino, {"organismo": "Comunidad de Madrid", "n": 1})
    assert manifiestos.leer_json(destino) == {"organismo": "Comunidad de Madrid", "n": 1}
