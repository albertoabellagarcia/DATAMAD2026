"""Adquisición, versiones fechadas y verificación, sin red: las URL son file:// locales."""

from cercasalud import ingesta
from cercasalud.catalogo import ArchivoFuente
from cercasalud.manifiestos import leer_json, ruta_manifiesto


def archivo_local(tmp_path, contenido: bytes) -> ArchivoFuente:
    """Crea un 'servidor' local: un archivo cuyo URI file:// hace de URL de descarga."""
    origen = tmp_path / "servidor" / "datos.csv"
    origen.parent.mkdir(parents=True, exist_ok=True)
    origen.write_bytes(contenido)
    return ArchivoFuente("prueba", "datos.csv", origen.as_uri(), "Organismo de prueba", "CC BY 4.0")


def test_descarga_crea_version_y_manifiesto(tmp_path):
    """La primera descarga guarda el archivo en crudos/<fuente>/<ID>/ con su manifiesto."""
    raiz, archivo = tmp_path / "datos", archivo_local(tmp_path, b"a;b\n1;2\n")
    registro = ingesta.adquirir(raiz, archivo, "V1")
    destino = raiz / "crudos" / "prueba" / "V1" / "datos.csv"
    assert registro["accion"] == "descargada"
    assert destino.read_bytes() == b"a;b\n1;2\n"
    manifiesto = leer_json(ruta_manifiesto(destino))
    assert manifiesto["url"] == archivo.url and manifiesto["bytes"] == 8 and manifiesto["licencia"] == "CC BY 4.0"


def test_descarga_identica_reutiliza_la_version_existente(tmp_path):
    """Si el contenido no ha cambiado, no se crea una segunda copia ni una carpeta vacía."""
    raiz, archivo = tmp_path / "datos", archivo_local(tmp_path, b"igual")
    ingesta.adquirir(raiz, archivo, "V1")
    registro = ingesta.adquirir(raiz, archivo, "V2")
    assert registro["accion"] == "reutilizada_identica"
    assert registro["ruta"] == "crudos/prueba/V1/datos.csv"
    assert not (raiz / "crudos" / "prueba" / "V2").exists()


def test_descarga_distinta_no_sobrescribe_la_anterior(tmp_path):
    """Un contenido nuevo crea otra versión y la anterior queda intacta."""
    raiz, archivo = tmp_path / "datos", archivo_local(tmp_path, b"version 1")
    ingesta.adquirir(raiz, archivo, "V1")
    (tmp_path / "servidor" / "datos.csv").write_bytes(b"version 2")
    ingesta.adquirir(raiz, archivo, "V2")
    assert (raiz / "crudos" / "prueba" / "V1" / "datos.csv").read_bytes() == b"version 1"
    assert (raiz / "crudos" / "prueba" / "V2" / "datos.csv").read_bytes() == b"version 2"


def test_snapshot_elige_la_version_mas_reciente_y_verify_detecta_cambios(tmp_path, monkeypatch):
    """La versión fechada apunta a la última descarga; si alguien altera el archivo, verify lo detecta."""
    raiz, archivo = tmp_path / "datos", archivo_local(tmp_path, b"v1")
    monkeypatch.setattr(ingesta, "CATALOGO", (archivo,))
    ingesta.adquirir(raiz, archivo, "V1")
    (tmp_path / "servidor" / "datos.csv").write_bytes(b"v2")
    ingesta.adquirir(raiz, archivo, "V2")
    ingesta.crear_snapshot(raiz, "S1")
    entrada = ingesta.leer_snapshot(raiz, "S1")["archivos"][0]
    assert entrada["estado"] == "ok" and entrada["ruta"] == "crudos/prueba/V2/datos.csv"
    assert ingesta.verificar_snapshot(raiz, "S1") == []
    (raiz / entrada["ruta"]).write_bytes(b"alterado")
    assert ingesta.verificar_snapshot(raiz, "S1") == ["crudos/prueba/V2/datos.csv: el SHA-256 ya no coincide"]


def test_snapshot_declara_lo_que_falta(tmp_path, monkeypatch):
    """Un archivo del catálogo sin versión local aparece como sin_version_local, no se omite."""
    archivo = ArchivoFuente("prueba", "nada.csv", "file:///no/existe.csv", "Org", "CC BY 4.0")
    monkeypatch.setattr(ingesta, "CATALOGO", (archivo,))
    ingesta.crear_snapshot(tmp_path, "S1")
    assert ingesta.leer_snapshot(tmp_path, "S1")["archivos"][0]["estado"] == "sin_version_local"
