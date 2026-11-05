#!/usr/bin/env python3
"""
servidor.py · tu propio servidor MCP en Python (DATAMAD 2026, diapositiva 57)

Servidor MCP con herramientas sobre el catálogo CKAN de la Comunidad de Madrid.
Funciona con el SDK oficial de MCP en sus dos versiones:
  - mcp 1.x  ->  FastMCP   (from mcp.server.fastmcp import FastMCP)
  - mcp 2.x  ->  MCPServer (from mcp.server.mcpserver import MCPServer)

Herramientas:
  buscar_datasets(consulta, filas)        la de la diapositiva: títulos de datasets
  detalle_dataset(id_dataset)             descripción y recursos (formato y URL)
  leer_datos(id_recurso, filas, desde)    filas de un recurso con DataStore

Conexión en Claude Desktop (claude_desktop_config.json):
  {
    "mcpServers": {
      "datos-madrid": {
        "command": "uv",
        "args": ["run", "--with", "mcp", "--with", "httpx",
                 "python", "/ruta/servidor.py"]
      }
    }
  }

Prueba sin cliente de IA:  python probar_servidor.py
"""

import os

import httpx

try:  # mcp 2.x
    from mcp.server.mcpserver import MCPServer as Servidor
except ImportError:  # mcp 1.x (la versión del código de la diapositiva)
    from mcp.server.fastmcp import FastMCP as Servidor

mcp = Servidor("datos-madrid")
# Otro portal CKAN: variable de entorno CKAN_URL (p. ej. https://datos.madrid.es/api/3/action)
CKAN = os.environ.get("CKAN_URL", "https://datos.comunidad.madrid/api/3/action")
TIMEOUT = 30


def _ckan(accion: str, **params) -> dict:
    r = httpx.get(f"{CKAN}/{accion}", params=params, timeout=TIMEOUT,
                  follow_redirects=True)
    r.raise_for_status()
    datos = r.json()
    if not datos.get("success"):
        raise ValueError(f"CKAN respondió con error: {datos.get('error')}")
    return datos["result"]


@mcp.tool()
def buscar_datasets(consulta: str, filas: int = 5) -> list[str]:
    """Busca datasets en datos.comunidad.madrid."""
    resultado = _ckan("package_search", q=consulta, rows=filas)
    return [d["title"] for d in resultado["results"]]


@mcp.tool()
def detalle_dataset(id_dataset: str) -> dict:
    """Devuelve la descripción de un dataset de datos.comunidad.madrid y sus
    recursos (formato, URL de descarga e id para leer_datos).
    id_dataset puede ser el nombre corto o el identificador (p. ej. 1908061)."""
    d = _ckan("package_show", id=id_dataset)
    return {
        "titulo": d.get("title"),
        "descripcion": (d.get("notes") or "")[:1500],
        "organizacion": (d.get("organization") or {}).get("title"),
        "licencia": d.get("license_title"),
        "actualizado": d.get("metadata_modified"),
        "recursos": [
            {"id": r.get("id"), "nombre": r.get("name"),
             "formato": r.get("format"), "url": r.get("url"),
             "datastore": bool(r.get("datastore_active"))}
            for r in d.get("resources", [])
        ],
    }


@mcp.tool()
def leer_datos(id_recurso: str, filas: int = 20, desde: int = 0) -> dict:
    """Lee filas de un recurso tabular (solo los que tienen DataStore activo).
    Devuelve el total de filas, los campos y las filas pedidas."""
    filas = max(1, min(filas, 500))
    r = _ckan("datastore_search", resource_id=id_recurso, limit=filas, offset=desde)
    return {
        "total": r.get("total"),
        "campos": [f["id"] for f in r.get("fields", []) if f["id"] != "_id"],
        "filas": [{k: v for k, v in fila.items() if k != "_id"}
                  for fila in r.get("records", [])],
    }


if __name__ == "__main__":
    mcp.run()
