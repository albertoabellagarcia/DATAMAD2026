#!/usr/bin/env python3
"""
probar_servidor.py · prueba servidor.py sin necesidad de un cliente de IA

Arranca servidor.py como lo haría Claude Desktop (stdio), se conecta con el
cliente oficial de MCP, lista las herramientas y las llama una a una.

Uso:   python probar_servidor.py ["consulta"]
       (por defecto: "calidad del aire", la prueba de la diapositiva)
Requisitos: pip install mcp httpx
"""

import asyncio
import json
import os
import sys
from pathlib import Path

from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

SERVIDOR = Path(__file__).with_name("servidor.py")
CONSULTA = sys.argv[1] if len(sys.argv) > 1 else "calidad del aire"


def attr(obj, *nombres):
    """Atributo compatible con mcp 1.x (camelCase) y 2.x (snake_case)."""
    for n in nombres:
        if hasattr(obj, n):
            return getattr(obj, n)
    return None


def contenido(resultado):
    """Texto (o JSON) de la respuesta de una herramienta."""
    estructurado = attr(resultado, "structured_content", "structuredContent")
    if estructurado:
        return estructurado
    textos = [c.text for c in resultado.content if getattr(c, "text", None)]
    try:
        return json.loads(textos[0]) if len(textos) == 1 else textos
    except (ValueError, IndexError):
        return textos


def mostrar(titulo, valor, maximo=900):
    texto = json.dumps(valor, ensure_ascii=False, indent=2)
    print(f"\n▶ {titulo}\n" + (texto[:maximo] + " …" if len(texto) > maximo else texto))


async def main():
    params = StdioServerParameters(command=sys.executable, args=[str(SERVIDOR)],
                                    env=dict(os.environ))
    async with stdio_client(params) as (leer, escribir):
        async with ClientSession(leer, escribir) as sesion:
            info = await sesion.initialize()
            print(f"Conectado a «{attr(info, "server_info", "serverInfo").name}»")

            herramientas = (await sesion.list_tools()).tools
            print("Herramientas:")
            for h in herramientas:
                print(f"  - {h.name}: {(h.description or '').splitlines()[0]}")

            r = await sesion.call_tool("buscar_datasets", {"consulta": CONSULTA, "filas": 5})
            if attr(r, "is_error", "isError"):
                mostrar("buscar_datasets -> ERROR", contenido(r))
                return
            titulos = contenido(r)
            if isinstance(titulos, dict) and "result" in titulos:
                titulos = titulos["result"]
            mostrar(f'buscar_datasets("{CONSULTA}")', titulos)

            # Detalle del primer resultado: buscamos su id con package_search
            import httpx
            ckan = os.environ.get("CKAN_URL", "https://datos.comunidad.madrid/api/3/action")
            busqueda = httpx.get(f"{ckan}/package_search",
                                 params={"q": CONSULTA, "rows": 1}, timeout=30).json()
            primero = busqueda["result"]["results"][0]["name"]
            r = await sesion.call_tool("detalle_dataset", {"id_dataset": primero})
            detalle = contenido(r)
            mostrar(f'detalle_dataset("{primero}")', detalle)

            con_datastore = [x for x in detalle.get("recursos", []) if x.get("datastore")]
            if con_datastore:
                rid = con_datastore[0]["id"]
                r = await sesion.call_tool("leer_datos", {"id_recurso": rid, "filas": 3})
                mostrar(f'leer_datos("{rid}", filas=3)', contenido(r))
            else:
                print("\n(ningún recurso de este dataset tiene DataStore; leer_datos no aplica)")


if __name__ == "__main__":
    asyncio.run(main())
