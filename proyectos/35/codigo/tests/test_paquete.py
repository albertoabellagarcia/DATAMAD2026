"""Prueba de humo: el paquete se instala y se importa en el entorno de uv."""

import sys

import cercasalud


def test_paquete_importable_con_version():
    """El paquete expone su versión; si falla, el entorno no se instaló bien."""
    assert cercasalud.__version__ == "0.1.0"


def test_python_del_producto_es_312():
    """El producto se ejecuta con CPython 3.12, como fija pyproject.toml."""
    assert sys.version_info[:2] == (3, 12)
